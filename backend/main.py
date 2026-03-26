import io
import logging
import os
import tempfile
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from backend.engine.decision_engine import run_decision_engine, DecisionEngine
from backend.engine.financial_state import compute_days_to_zero, detect_shortfall
from backend.engine.llm_actions import generate_chain_of_thought, generate_negotiation_email
from backend.engine.normalizer import DataNormalizer
from backend.engine.communication_engine import CommunicationEngine, create_action_communications
from backend.ingestion.csv_parser import CSVParser
from backend.ingestion.ocr_parser import OCRParser
from backend.ingestion.pdf_parser import PDFParser
from backend.ingestion.pipeline import IngestionPipeline
from backend.models.obligation import FinancialState, Obligation, Decision, Action, Priority

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Fintech Decision Assistant API",
    description="API for processing financial documents and making payment decisions with intelligent classification and context-aware communications",
    version="4.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
normalizer = DataNormalizer()
decision_engine = DecisionEngine()
pipeline = IngestionPipeline(enable_decisions=True)

# Initialize communication engine with API key from environment
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', None)
communication_engine = CommunicationEngine(api_key=OPENROUTER_API_KEY)

# Request/Response Models
class AnalyzeRequest(BaseModel):
    cash_balance: float
    obligations: List[Dict[str, Any]]
    as_of_date: Optional[str] = None

class EmailRequest(BaseModel):
    obligation: Dict[str, Any]
    decision: Dict[str, Any]

class CommunicationRequest(BaseModel):
    cash_balance: float
    payables: List[Dict[str, Any]]
    receivables: List[Dict[str, Any]]
    decisions: List[Dict[str, Any]]

class UploadResponse(BaseModel):
    success: bool
    file: str
    file_type: str
    record_count: int
    financial_state: Dict[str, Any]
    decisions: Optional[List[Dict[str, Any]]] = None
    warnings: Optional[List[str]] = None
    parsed_data_summary: Dict[str, Any]

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "Fintech Decision Assistant API",
        "version": "4.0.0",
        "description": "Intelligent financial document processing with counterparty classification and context-aware communications",
        "features": [
            "Automatic counterparty classification (vendor, customer, tax authority, government, etc.)",
            "OCR for images and scanned documents",
            "PDF parsing with table extraction",
            "CSV/Excel file processing",
            "Intelligent decision making",
            "Email drafting for negotiations",
            "Risk scoring and penalty calculation",
            "Context-aware communication generation",
            "Emergency action planning"
        ],
        "endpoints": {
            "/upload": "Upload and parse financial documents",
            "/upload-batch": "Upload multiple documents",
            "/analyze": "Analyze financial state and get decisions",
            "/draft-email": "Generate negotiation email",
            "/generate-communications": "Generate all communications based on decisions",
            "/health": "Health check",
            "/classify": "Classify counterparty type",
            "/stats": "Get processing statistics"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "ocr": "available",
            "pdf_parser": "available",
            "csv_parser": "available",
            "decision_engine": "available",
            "classifier": "available",
            "communication_engine": "available" if OPENROUTER_API_KEY else "template_mode"
        },
        "version": "4.0.0"
    }

@app.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    generate_decisions: bool = Query(True, description="Generate decisions for obligations")
):
    """
    Upload and parse financial documents (CSV, PDF, Images)
    
    Features:
    - Automatic counterparty classification (tax authority, government, vendor, customer, etc.)
    - GST/PAN number detection
    - Risk scoring and penalty calculation
    - Optional decision generation
    
    Returns:
        Normalized obligations, financial state, and decisions
    """
    temp_file = None
    temp_path = None
    
    try:
        # Read file contents
        contents = await file.read()
        ext = file.filename.split(".")[-1].lower()
        
        logger.info(f"Processing file: {file.filename} (type: {ext})")
        
        # Validate file size (10MB limit)
        if len(contents) > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail="File too large. Maximum size is 10MB"
            )
        
        # Parse based on file type
        if ext == "csv":
            with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp_file:
                tmp_file.write(contents)
                temp_path = tmp_file.name
            
            parsed_data = CSVParser.parse(temp_path)
                
        elif ext == "pdf":
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                tmp_file.write(contents)
                temp_path = tmp_file.name
            
            parsed_data = PDFParser.parse(temp_path)
                
        elif ext in ["jpg", "jpeg", "png"]:
            with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{ext}') as tmp_file:
                tmp_file.write(contents)
                temp_path = tmp_file.name
            
            parsed_data = OCRParser.parse(temp_path)
            
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file format: {ext}. Supported formats: CSV, PDF, JPG, PNG"
            )
        
        # Normalize obligations with classification
        obligations = normalizer.normalize_batch(
            parsed_data.get('obligations', []),
            source_file=file.filename
        )
        
        # Log classification results
        for ob in obligations:
            logger.debug(f"Classified '{ob.counterparty['name']}' as {ob.counterparty['type']} "
                        f"(confidence: {ob.counterparty.get('classification_confidence', 0):.2f})")
        
        # Create financial state
        cash_balance = parsed_data.get('cash_balance', 0.0)
        financial_state = normalizer.create_financial_state(obligations, cash_balance)
        
        # Generate decisions if requested
        decisions = []
        if generate_decisions and obligations:
            decisions = decision_engine.make_decisions(obligations)
            logger.info(f"Generated {len(decisions)} decisions")
        
        # Prepare response
        response = {
            "success": True,
            "file": file.filename,
            "file_type": ext,
            "record_count": len(obligations),
            "financial_state": financial_state.dict(),
            "parsed_data_summary": {
                "source_type": parsed_data.get('source_type', ext),
                "record_count": parsed_data.get('record_count', len(obligations)),
                "extraction_confidence": parsed_data.get('confidence', 1.0),
                "has_gst_numbers": bool(parsed_data.get('gst_numbers')),
                "has_pan_numbers": bool(parsed_data.get('pan_numbers')),
                "tables_extracted": len(parsed_data.get('tables', []))
            }
        }
        
        # Add decisions if generated
        if decisions:
            response["decisions"] = decisions
        
        # Add warnings
        warnings = []
        if len(obligations) == 0:
            warnings.append("No obligations were extracted from the file")
        if parsed_data.get('confidence', 1.0) < 0.5:
            warnings.append(f"Low extraction confidence: {parsed_data.get('confidence', 0)}")
        
        # Check for unknown classifications
        unknown_count = sum(1 for ob in obligations if ob.counterparty.get('type') == 'unknown')
        if unknown_count > 0:
            warnings.append(f"{unknown_count} obligations have unknown counterparty type")
        
        if warnings:
            response["warnings"] = warnings
        
        logger.info(f"Successfully processed {file.filename}: {len(obligations)} obligations extracted")
        
        return JSONResponse(content=response)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing file {file.filename}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
    finally:
        # Clean up temp file
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except:
                pass

@app.post("/upload-batch")
async def upload_batch(
    files: List[UploadFile] = File(...),
    generate_decisions: bool = Query(True, description="Generate decisions for obligations")
):
    """
    Upload and parse multiple financial documents
    
    Returns:
        Combined results from all files
    """
    try:
        all_obligations = []
        all_decisions = []
        processing_results = []
        
        for file in files:
            temp_path = None
            try:
                contents = await file.read()
                ext = file.filename.split(".")[-1].lower()
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{ext}') as tmp_file:
                    tmp_file.write(contents)
                    temp_path = tmp_file.name
                
                try:
                    if ext == "csv":
                        parsed_data = CSVParser.parse(temp_path)
                    elif ext == "pdf":
                        parsed_data = PDFParser.parse(temp_path)
                    elif ext in ["jpg", "jpeg", "png"]:
                        parsed_data = OCRParser.parse(temp_path)
                    else:
                        processing_results.append({
                            "file": file.filename,
                            "status": "error",
                            "error": f"Unsupported format: {ext}"
                        })
                        continue
                    
                    obligations = normalizer.normalize_batch(
                        parsed_data.get('obligations', []),
                        source_file=file.filename
                    )
                    all_obligations.extend(obligations)
                    
                    # Generate decisions if requested
                    if generate_decisions and obligations:
                        decisions = decision_engine.make_decisions(obligations)
                        all_decisions.extend(decisions)
                    
                    processing_results.append({
                        "file": file.filename,
                        "status": "success",
                        "obligations_found": len(obligations),
                        "classified_types": list(set(ob.counterparty.get('type') for ob in obligations))
                    })
                    
                finally:
                    if temp_path and os.path.exists(temp_path):
                        os.unlink(temp_path)
                    
            except Exception as e:
                logger.error(f"Error processing {file.filename}: {e}")
                processing_results.append({
                    "file": file.filename,
                    "status": "error",
                    "error": str(e)
                })
        
        # Create combined financial state
        if all_obligations:
            financial_state = normalizer.create_financial_state(all_obligations, 0.0)
        else:
            financial_state = None
        
        # Count by type
        type_counts = {}
        for ob in all_obligations:
            cp_type = ob.counterparty.get('type', 'unknown')
            type_counts[cp_type] = type_counts.get(cp_type, 0) + 1
        
        return JSONResponse(content={
            "success": True,
            "total_files": len(files),
            "total_obligations": len(all_obligations),
            "total_decisions": len(all_decisions),
            "financial_state": financial_state.dict() if financial_state else None,
            "type_distribution": type_counts,
            "processing_results": processing_results
        })
        
    except Exception as e:
        logger.error(f"Error in batch processing: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing batch: {str(e)}")

@app.post("/analyze")
async def analyze(state: Dict[str, Any]):
    """
    Analyze financial state and generate decisions
    
    Expected state format:
    {
        "cash_balance": float,
        "obligations": List[Obligation],  # or "payables"/"receivables" for backward compatibility
        "as_of_date": str (optional)
    }
    
    Returns:
        Analysis results with decisions and explanations
    """
    try:
        # Handle backward compatibility with old format
        if "payables" in state and "receivables" in state:
            obligations = []
            for payable in state.get("payables", []):
                if isinstance(payable, dict):
                    obligations.append(payable)
            for receivable in state.get("receivables", []):
                if isinstance(receivable, dict):
                    obligations.append(receivable)
            
            financial_state = normalizer.create_financial_state(
                normalizer.normalize_batch(obligations),
                state.get("cash_balance", 0.0)
            )
        elif "obligations" in state:
            financial_state = normalizer.create_financial_state(
                normalizer.normalize_batch(state["obligations"]),
                state.get("cash_balance", 0.0)
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid state format. Expected 'obligations' or 'payables'/'receivables'"
            )
        
        # Calculate financial metrics
        payables = [o for o in financial_state.obligations if o.counterparty.get('type') in ['vendor', 'tax_authority', 'government', 'utility']]
        shortfall = detect_shortfall(financial_state.cash_balance, payables)
        days_zero = compute_days_to_zero(financial_state.cash_balance, payables)
        
        # Run decision engine for each obligation
        decisions = decision_engine.make_decisions(financial_state.obligations)
        
        # Generate chain of thought
        cot = generate_chain_of_thought(decisions)
        
        # Add classification statistics
        type_stats = {}
        for ob in financial_state.obligations:
            cp_type = ob.counterparty.get('type', 'unknown')
            type_stats[cp_type] = type_stats.get(cp_type, 0) + 1
        
        return JSONResponse(content={
            "success": True,
            "summary": {
                "total_obligations": len(financial_state.obligations),
                "total_payables": financial_state.total_payables,
                "total_receivables": financial_state.total_receivables,
                "total_penalties": financial_state.total_penalties,
                "high_risk_count": financial_state.high_risk_count,
                "type_distribution": type_stats
            },
            "shortfall": shortfall,
            "days_to_zero": days_zero,
            "decisions": decisions,
            "explanation": cot
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in analysis: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error analyzing financial state: {str(e)}")

@app.post("/generate-communications")
async def generate_communications(request: CommunicationRequest):
    """
    Generate context-aware communications based on decisions
    
    Args:
        request: Contains cash_balance, payables, receivables, and decisions
    
    Returns:
        Generated emails and messages for all parties
    """
    try:
        communications = create_action_communications(
            cash_balance=request.cash_balance,
            payables=request.payables,
            receivables=request.receivables,
            decisions=request.decisions,
            api_key=OPENROUTER_API_KEY
        )
        
        return JSONResponse(content={
            "success": True,
            "communications": communications,
            "summary": {
                "total_communications": communications["summary"]["total_communications"],
                "payable_communications": len(communications["payables"]),
                "receivable_communications": len(communications["receivables"])
            }
        })
        
    except Exception as e:
        logger.error(f"Error generating communications: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generating communications: {str(e)}")

@app.post("/draft-email")
async def draft_email(payload: EmailRequest):
    """
    Generate negotiation email for an obligation (legacy endpoint)
    
    Args:
        payload: Obligation and decision details
    
    Returns:
        Generated email
    """
    try:
        # Use the communication engine for better context-aware generation
        profile = communication_engine.get_relationship_profile(
            payload.obligation.get("counterparty", {}).get("type", "unknown")
        )
        
        if payload.decision.get("action") == "negotiate_deadline_extension":
            email = communication_engine.generate_payment_extension_request(
                payload.obligation, 
                profile,
                payload.decision.get("suggested_terms", {}).get("requested_days", 15)
            )
        elif payload.decision.get("action") == "pay_partially":
            email = communication_engine.generate_partial_payment_proposal(
                payload.obligation,
                profile,
                payload.decision.get("suggested_terms", {}).get("percentage", 50),
                {"installments": 2, "days": 15}
            )
        else:
            # Fallback to legacy generation
            email = generate_negotiation_email(payload.obligation, payload.decision)
        
        # Add metadata
        response = {
            "success": True,
            "email": email,
            "metadata": {
                "counterparty": payload.obligation.get("counterparty", {}).get("name", "Unknown"),
                "counterparty_type": payload.obligation.get("counterparty", {}).get("type", "unknown"),
                "action": payload.decision.get("action", "unknown"),
                "priority": payload.decision.get("priority", "unknown"),
                "generated_at": datetime.now().isoformat()
            }
        }
        
        return JSONResponse(content=response)
        
    except Exception as e:
        logger.error(f"Error generating email: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generating email: {str(e)}")

@app.post("/classify")
async def classify_counterparty(name: str, context: Optional[str] = None):
    """
    Classify a counterparty type based on name and context
    
    Args:
        name: Counterparty name
        context: Additional context (optional)
    
    Returns:
        Classification result with confidence
    """
    try:
        from backend.engine.counterparty_classifier import CounterpartyClassifier
        
        category, confidence = CounterpartyClassifier.classify(name, context or "")
        
        return JSONResponse(content={
            "success": True,
            "name": name,
            "type": category.value,
            "confidence": confidence,
            "details": CounterpartyClassifier.get_category_details(category)
        })
        
    except Exception as e:
        logger.error(f"Error classifying counterparty: {e}")
        raise HTTPException(status_code=500, detail=f"Error classifying: {str(e)}")

@app.post("/emergency-plan")
async def emergency_plan(
    cash_balance: float,
    critical_obligations: List[Dict[str, Any]],
    shortfall: float
):
    """
    Generate emergency action plan for critical shortfall
    
    Args:
        cash_balance: Current cash balance
        critical_obligations: List of critical unpaid obligations
        shortfall: Amount of cash shortfall
    
    Returns:
        Emergency action plan with communications
    """
    try:
        plan = communication_engine.generate_emergency_action_plan(
            critical_obligations,
            shortfall,
            ["borrow", "partial_payments", "negotiate"]
        )
        
        return JSONResponse(content={
            "success": True,
            "emergency_plan": plan
        })
        
    except Exception as e:
        logger.error(f"Error generating emergency plan: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generating emergency plan: {str(e)}")

@app.get("/stats")
async def get_stats():
    """
    Get system statistics
    """
    return {
        "success": True,
        "stats": {
            "version": "4.0.0",
            "features": [
                "counterparty_classification",
                "ocr_support",
                "pdf_parsing",
                "decision_engine",
                "email_generation",
                "context_aware_communications",
                "emergency_planning"
            ],
            "supported_formats": [".csv", ".xlsx", ".pdf", ".jpg", ".jpeg", ".png"],
            "classification_types": [
                "vendor", "customer", "tax_authority", "government",
                "employee", "friend", "family", "bank", "utility",
                "rent", "insurance", "investment", "charity"
            ],
            "communication_modes": "ai_generated" if OPENROUTER_API_KEY else "template_based"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)