"""
PayWise - Fintech Decision Assistant
Complete Flask application with data preprocessing and duplicate removal
"""

import os
import sys
import json
import uuid
import logging
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import backend modules
from backend.engine.decision_engine import DecisionEngine
from backend.engine.normalizer import DataNormalizer
from backend.engine.communication_engine import CommunicationEngine
from backend.engine.counterparty_classifier import CounterpartyClassifier

from backend.ingestion.csv_parser import CSVParser
from backend.ingestion.pdf_parser import PDFParser
from backend.ingestion.ocr_parser import OCRParser
from backend.ingestion.pipeline import IngestionPipeline

from backend.models.obligation import Obligation, FinancialState, PartialPaymentTerms
from backend.preprocessing.financial_processor import (
    process_ingested_data,
    get_partial_payment_summary,
    create_cash_flow_analysis,
    print_financial_summary,
    remove_duplicates,
    aggregate_by_category,
    get_payment_priorities
)
from pydantic import BaseModel
from typing import Optional, List, Any, Dict

# Add this model definition
class ChatRequest(BaseModel):
    messages: List[Dict[str, str]]
    transaction: Optional[Dict[str, Any]] = None
    prompt: Optional[str] = None
    festivalContext: Optional[List[Dict[str, Any]]] = None

# If you also need a response model
class ChatResponse(BaseModel):
    reply: str
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__, static_folder='frontend/dist', static_url_path='')
CORS(app)

# Configuration
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / 'data'
UPLOAD_DIR = BASE_DIR / 'uploads'
OUTPUT_DIR = BASE_DIR / 'output'

# Create directories
DATA_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# File paths
TRANSACTIONS_FILE = DATA_DIR / 'transactions.json'
PROCESSED_DATA_FILE = OUTPUT_DIR / 'processed_financial_state.json'
CASH_BALANCE_FILE = DATA_DIR / 'cash_balance.json'

# Helper function to format currency
def format_currency(amount):
    """Format amount as currency"""
    return f"₹{amount:,.2f}"

# Initialize data files
def init_data_files():
    """Initialize data files if they don't exist"""
    if not TRANSACTIONS_FILE.exists():
        with open(TRANSACTIONS_FILE, 'w') as f:
            json.dump([], f)
    
    if not CASH_BALANCE_FILE.exists():
        # Initialize with default cash balance of ₹1,00,000
        with open(CASH_BALANCE_FILE, 'w') as f:
            json.dump({"cash_balance": 100000}, f)

init_data_files()

# Initialize engines
decision_engine = DecisionEngine()
normalizer = DataNormalizer()
communication_engine = CommunicationEngine(api_key=os.getenv('OPENROUTER_API_KEY'))

# ------------------------------
# Cash Balance Functions
# ------------------------------

def get_cash_balance():
    """Get current cash balance"""
    try:
        with open(CASH_BALANCE_FILE, 'r') as f:
            data = json.load(f)
            return data.get('cash_balance', 100000)
    except:
        return 100000

def set_cash_balance(amount):
    """Set cash balance"""
    with open(CASH_BALANCE_FILE, 'w') as f:
        json.dump({"cash_balance": amount}, f)
    return amount

# ------------------------------
# Data Storage Functions
# ------------------------------

def save_transaction(transaction):
    """Save a transaction to file"""
    try:
        with open(TRANSACTIONS_FILE, 'r') as f:
            transactions = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        transactions = []
    
    transaction['id'] = str(uuid.uuid4())[:8]
    transaction['created_at'] = datetime.now().isoformat()
    transactions.append(transaction)
    
    # Remove duplicates based on party, amount, due_date
    unique_transactions = remove_duplicates(transactions)
    
    with open(TRANSACTIONS_FILE, 'w') as f:
        json.dump(unique_transactions, f, indent=2, default=str)
    
    # Reprocess all data to update processed state
    process_all_transactions()
    
    return transaction

def get_transactions(limit=100):
    """Get all transactions"""
    try:
        with open(TRANSACTIONS_FILE, 'r') as f:
            transactions = json.load(f)
        return transactions[-limit:]
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def process_all_transactions():
    """Process all transactions using financial_processor and save to processed file"""
    transactions = get_transactions(limit=1000)
    
    if not transactions:
        return None
    
    # Get current cash balance
    cash_balance = get_cash_balance()
    
    # Convert transactions to the format expected by process_ingested_data
    data = {
        "successful": [
            {
                "financial_state": {
                    "obligations": [
                        {
                            "counterparty": {
                                "name": t.get("counterparty_name"),
                                "type": t.get("counterparty_type"),
                                "classification_confidence": 0.95
                            },
                            "amount": t.get("amount"),
                            "due_date": t.get("due_date"),
                            "payment_date": t.get("payment_date"),
                            "days_late": t.get("days_late", 0),
                            "risk_score": t.get("risk_score", 0.5),
                            "penalty": t.get("penalty_analysis", {}),
                            "decision": t.get("decision", {}),
                            "partial_payment": {
                                "accepts_partial": t.get("accepts_partial", True),
                                "minimum_partial_pct": t.get("minimum_partial_pct", 50),
                                "minimum_partial_amount": t.get("amount", 0) * t.get("minimum_partial_pct", 50) / 100
                            },
                            "note": t.get("note", ""),
                            "invoice_number": t.get("invoice_number"),
                            "transaction_id": t.get("id")
                        }
                        for t in transactions
                    ]
                }
            }
        ]
    }
    
    # Process with financial_processor
    processed = process_ingested_data(data, initial_balance=cash_balance, include_paid=True)
    
    # Ensure cash balance is set correctly
    processed['cash_balance'] = cash_balance
    
    # Save to file
    with open(PROCESSED_DATA_FILE, 'w') as f:
        json.dump(processed, f, indent=2, default=str)
    
    return processed

# ------------------------------
# Analysis Functions
# ------------------------------

def analyze_transaction(data):
    """Analyze a single transaction using backend logic"""
    try:
        # Calculate days late
        days_late = 0
        due_date = data.get('due_date')
        if due_date:
            try:
                due = datetime.strptime(due_date, '%Y-%m-%d').date()
                today = datetime.today().date()
                days_late = max(0, (today - due).days)
            except:
                days_late = 0
        
        # Calculate risk score
        risk_score = 0.5
        risk_factors = []
        
        if days_late > 0:
            risk_score += min(days_late / 60, 0.3)
            risk_factors.append(f"Payment is {days_late} days overdue")
        
        amount = float(data.get('amount', 0))
        if amount > 50000:
            risk_score += 0.2
            risk_factors.append(f"High transaction amount (₹{amount:,.0f})")
        
        counterparty_type = data.get('counterparty_type', 'unknown')
        if counterparty_type in ['tax_authority', 'government']:
            risk_score += 0.3
            risk_factors.append("Critical counterparty type - regulatory risk")
        
        risk_score = min(risk_score, 1.0)
        
        # Determine priority
        if risk_score >= 0.7:
            priority = "High"
        elif risk_score >= 0.4:
            priority = "Medium"
        else:
            priority = "Low"
        
        # Calculate penalty
        penalty_rate = 0.005
        penalty = amount * penalty_rate * days_late
        penalty = min(penalty, amount * 0.2)
        
        # Generate recommendations
        recommendations = []
        if counterparty_type in ['tax_authority', 'government'] and days_late > 0:
            recommendations.append({
                "action": "Pay Immediately - Legal Risk",
                "rationale": f"Tax/government payment {days_late} days overdue. Legal penalties may apply.",
                "urgency": "critical"
            })
        
        if risk_score >= 0.7:
            recommendations.append({
                "action": "Prioritize This Payment",
                "rationale": f"High risk score ({risk_score:.2f}) - immediate attention required",
                "urgency": "high"
            })
        elif risk_score >= 0.4:
            if data.get('accepts_partial', True):
                recommendations.append({
                    "action": f"Propose Partial Payment ({data.get('minimum_partial_pct', 40)}% Now)",
                    "rationale": f"Offer {data.get('minimum_partial_pct', 40)}% now, balance in 15 days",
                    "urgency": "medium"
                })
            else:
                recommendations.append({
                    "action": "Request Payment Extension",
                    "rationale": "Request 7-10 day extension",
                    "urgency": "medium"
                })
        else:
            recommendations.append({
                "action": "Pay on Schedule",
                "rationale": "Low risk - maintain good payment history",
                "urgency": "low"
            })
        
        if penalty > 0:
            recommendations.append({
                "action": f"Avoid ₹{penalty:,.0f} Penalty",
                "rationale": f"Pay within {max(0, 30 - days_late)} days to avoid penalty",
                "urgency": "medium" if days_late > 0 else "low"
            })
        
        # Assumptions
        assumptions = []
        if not data.get('due_date'):
            assumptions.append("Due date not provided. Using current date for calculation.")
        if not data.get('payment_date'):
            assumptions.append("Payment date not provided. Assuming not yet paid.")
        
        result = {
            "id": str(uuid.uuid4())[:8],
            "counterparty_name": data.get('counterparty_name', 'Unknown'),
            "counterparty_type": counterparty_type,
            "amount": amount,
            "transaction_type": data.get('transaction_type', 'payable'),
            "status": data.get('status', 'pending'),
            "due_date": data.get('due_date'),
            "payment_date": data.get('payment_date'),
            "days_late": days_late,
            "priority": priority,
            "risk_score": risk_score,
            "risk_factors": risk_factors,
            "penalty_analysis": {
                "total_penalty": penalty,
                "penalty_breakdown": [{
                    "type": "Late Payment Penalty",
                    "calculation": f"{penalty_rate*100}% per day × {days_late} days",
                    "amount": penalty
                }],
                "penalty_as_pct_of_amount": (penalty / amount * 100) if amount > 0 else 0,
                "total_effective_cost": amount + penalty
            },
            "recommended_actions": recommendations[:4],
            "assumptions_made": assumptions,
            "accepts_partial": data.get('accepts_partial', True),
            "minimum_partial_pct": data.get('minimum_partial_pct', 40),
            "analyzed_at": datetime.now().isoformat()
        }
        
        # Save to file
        save_transaction(result)
        
        return result
        
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        import traceback
        traceback.print_exc()
        raise


def calculate_dashboard_stats():
    """Calculate comprehensive dashboard statistics from processed data"""
    try:
        # Load processed data
        if PROCESSED_DATA_FILE.exists():
            with open(PROCESSED_DATA_FILE, 'r') as f:
                processed = json.load(f)
        else:
            processed = process_all_transactions()
        
        if not processed:
            return {
                "total_transactions": 0,
                "total_amount": 0,
                "high_risk_count": 0,
                "medium_risk_count": 0,
                "low_risk_count": 0,
                "overdue_count": 0,
                "pending_count": 0,
                "paid_count": 0,
                "payables_count": 0,
                "receivables_count": 0,
                "accepts_partial_count": 0,
                "total_payables_amount": 0,
                "total_receivables_amount": 0,
                "total_penalties": 0,
                "avg_risk_score": 0,
                "cash_balance": get_cash_balance()
            }
        
        payables = processed.get('payables', [])
        
        # Calculate statistics from processed data
        total_transactions = processed['summary']['total_obligations']
        total_amount = processed['summary']['total_payables'] + processed['summary']['total_receivables']
        
        # Risk distribution
        high_risk = sum(1 for p in payables if p.get('risk_score', 0) >= 0.7)
        medium_risk = sum(1 for p in payables if 0.4 <= p.get('risk_score', 0) < 0.7)
        low_risk = sum(1 for p in payables if p.get('risk_score', 0) < 0.4)
        
        # Status distribution
        overdue = sum(1 for p in payables if p.get('days_late', 0) > 0)
        pending = sum(1 for p in payables if p.get('days_late', 0) == 0)
        
        # Partial payment stats
        accepts_partial = sum(1 for p in payables if p.get('partial_payment', {}).get('accepts_partial', False))
        
        return {
            "total_transactions": total_transactions,
            "total_amount": total_amount,
            "high_risk_count": high_risk,
            "medium_risk_count": medium_risk,
            "low_risk_count": low_risk,
            "overdue_count": overdue,
            "pending_count": pending,
            "paid_count": 0,
            "payables_count": processed['summary']['payables_count'],
            "receivables_count": processed['summary']['receivables_count'],
            "accepts_partial_count": accepts_partial,
            "total_payables_amount": processed['summary']['total_payables'],
            "total_receivables_amount": processed['summary']['total_receivables'],
            "total_penalties": processed['summary']['total_penalties'],
            "avg_risk_score": sum(p.get('risk_score', 0) for p in payables) / max(len(payables), 1),
            "cash_balance": get_cash_balance()
        }
        
    except Exception as e:
        logger.error(f"Error calculating stats: {e}")
        return {
            "total_transactions": 0,
            "total_amount": 0,
            "high_risk_count": 0,
            "medium_risk_count": 0,
            "low_risk_count": 0,
            "overdue_count": 0,
            "pending_count": 0,
            "paid_count": 0,
            "payables_count": 0,
            "receivables_count": 0,
            "accepts_partial_count": 0,
            "total_payables_amount": 0,
            "total_receivables_amount": 0,
            "total_penalties": 0,
            "avg_risk_score": 0,
            "cash_balance": get_cash_balance()
        }


# ------------------------------
# API Routes
# ------------------------------

@app.route('/')
def index():
    """Serve the main page"""
    return send_from_directory('frontend', 'index.html')

@app.route('/api/health', methods=['GET'])
def health():
    """Health check"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "modules": {
            "decision_engine": "loaded",
            "communication_engine": "loaded",
            "financial_processor": "loaded"
        }
    })

@app.route('/api/analyze', methods=['POST'])
def analyze():
    """Analyze a transaction"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    try:
        result = analyze_transaction(data)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/upload', methods=['POST'])
def upload():
    """Upload and parse a file, return parsed data for user to edit"""
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files['file']
    ext = os.path.splitext(file.filename)[1].lower()
    
    # Save temporarily
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = UPLOAD_DIR / filename
    file.save(filepath)
    
    try:
        if ext == '.csv':
            parsed = CSVParser.parse(str(filepath))
        elif ext == '.pdf':
            parsed = PDFParser.parse(str(filepath))
        elif ext in ['.png', '.jpg', '.jpeg']:
            parsed = OCRParser.parse(str(filepath))
        else:
            return jsonify({"error": f"Unsupported file type: {ext}"}), 400
        
        # Return the parsed data as editable JSON
        return jsonify({
            "success": True, 
            "data": parsed,
            "message": "Data parsed successfully. Please review and edit if needed before confirming."
        })
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        try:
            filepath.unlink()
        except:
            pass

@app.route('/api/confirm-upload', methods=['POST'])
def confirm_upload():
    """Confirm and process the user-edited data"""
    data = request.get_json()
    
    if not data or 'obligations' not in data:
        return jsonify({"error": "No obligations data provided"}), 400
    
    try:
        # Process each obligation
        results = []
        for ob in data.get('obligations', []):
            counterparty = ob.get('counterparty', {})
            
            transaction = {
                "counterparty_name": counterparty.get('name', 'Unknown'),
                "counterparty_type": counterparty.get('type', 'unknown'),
                "amount": ob.get('amount', 0),
                "due_date": ob.get('due_date'),
                "payment_date": ob.get('payment_date'),
                "description": ob.get('description', ''),
                "status": "overdue" if ob.get('days_late', 0) > 0 else "pending",
                "accepts_partial": ob.get('partial_payment', {}).get('accepts_partial', True),
                "minimum_partial_pct": ob.get('partial_payment', {}).get('minimum_pct', 40)
            }
            
            result = analyze_transaction(transaction)
            results.append(result)
        
        return jsonify({"success": True, "results": results})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/transactions', methods=['GET'])
def get_transactions_api():
    """Get all transactions"""
    transactions = get_transactions()
    return jsonify({"transactions": transactions, "count": len(transactions)})

@app.route('/api/processed-data', methods=['GET'])
def get_processed_data():
    """Get processed financial data"""
    try:
        if PROCESSED_DATA_FILE.exists():
            with open(PROCESSED_DATA_FILE, 'r') as f:
                data = json.load(f)
            return jsonify({"success": True, "data": data})
        else:
            processed = process_all_transactions()
            return jsonify({"success": True, "data": processed})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/dashboard/stats', methods=['GET'])
def dashboard_stats():
    """Get dashboard statistics"""
    stats = calculate_dashboard_stats()
    return jsonify(stats)

@app.route('/api/partial-summary', methods=['GET'])
def partial_summary():
    """Get partial payment summary"""
    try:
        if PROCESSED_DATA_FILE.exists():
            with open(PROCESSED_DATA_FILE, 'r') as f:
                processed = json.load(f)
            payables = processed.get('payables', [])
            summary = get_partial_payment_summary(payables)
            return jsonify({"success": True, "summary": summary})
        return jsonify({"success": True, "summary": {"total_obligations": 0, "accept_partial": 0}})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/generate-message', methods=['POST'])
def generate_message():
    """Generate a communication message with AI enhancements"""
    data = request.get_json()
    transaction = data.get('transaction', {})
    action = data.get('action', 'request_extension')
    extra_context = data.get('extra_context', '')
    
    if not transaction:
        return jsonify({"error": "Transaction data required"}), 400
    
    try:
        # Get relationship profile
        profile = communication_engine.get_relationship_profile(
            transaction.get('counterparty_type', 'unknown')
        )
        
        # Prepare obligation details
        obligation = {
            "party": transaction.get('counterparty_name', 'Vendor'),
            "amount": transaction.get('amount', 0),
            "due_date": transaction.get('due_date', ''),
            "days_late": transaction.get('days_late', 0),
            "type": transaction.get('counterparty_type', 'unknown'),
            "risk_score": transaction.get('risk_score', 0),
            "priority": transaction.get('priority', 'Medium')
        }
        
        # Generate context-aware messages based on action
        if action == 'request_extension':
            # Smart extension request based on days late
            if obligation['days_late'] > 0:
                subject = f"Request for Payment Extension - {obligation['party']}"
                email = f"""Dear {obligation['party']},

I hope this email finds you well.

I am writing regarding the payment of {format_currency(obligation['amount'])} which is currently {obligation['days_late']} days overdue. Due to [brief reason, e.g., unexpected cash flow constraints / bank delays], I would like to request a short extension.

Could we please extend the payment deadline by [X] days? I propose making the payment by [new date].

{extra_context}

I value our business relationship and appreciate your understanding. Please let me know if this works for you.

Best regards,
Finance Team"""
            else:
                subject = f"Payment Schedule Request - {obligation['party']}"
                email = f"""Dear {obligation['party']},

I hope you're doing well.

I'm writing to discuss the upcoming payment of {format_currency(obligation['amount'])} due on {obligation['due_date']}. To better align with our cash flow, I'd like to request a payment extension of [X] days.

{extra_context}

Thank you for your flexibility. I look forward to your response.

Best regards,
Finance Team"""
                
        elif action == 'propose_partial':
            min_pct = transaction.get('minimum_partial_pct', 40)
            subject = f"Proposed Partial Payment Arrangement - {obligation['party']}"
            email = f"""Dear {obligation['party']},

I hope this email finds you well.

Regarding the outstanding amount of {format_currency(obligation['amount'])}, I'd like to propose a partial payment arrangement to settle this efficiently.

Proposal:
• Immediate payment: {min_pct}% ({format_currency(obligation['amount'] * min_pct / 100)})
• Balance payment: Remaining {100 - min_pct}% within 15 days

{extra_context}

This arrangement helps maintain cash flow while ensuring we meet our commitment. Please let me know if this works for you.

Best regards,
Finance Team"""
                
        elif action == 'payment_confirmation':
            subject = f"Payment Confirmation - {obligation['party']}"
            email = f"""Dear {obligation['party']},

This is to confirm that payment of {format_currency(obligation['amount'])} has been processed and should reflect in your account shortly.

Transaction Reference: [Reference Number]
Payment Date: {datetime.now().strftime('%Y-%m-%d')}

{extra_context}

Thank you for your patience and cooperation.

Best regards,
Finance Team"""
                
        elif action == 'apology_delay':
            subject = f"Apology for Payment Delay - {obligation['party']}"
            email = f"""Dear {obligation['party']},

I sincerely apologize for the delay in processing payment of {format_currency(obligation['amount'])}, which was due on {obligation['due_date']}.

{extra_context or "This delay was due to an unexpected administrative issue that has now been resolved."}

I confirm that the payment will be processed by [date]. Thank you for your patience and understanding.

Best regards,
Finance Team"""
                
        elif action == 'demand_payment':
            subject = f"Payment Reminder - {obligation['party']}"
            email = f"""Dear {obligation['party']},

This is a reminder regarding the outstanding payment of {format_currency(obligation['amount'])} which is now {obligation['days_late']} days overdue.

Please arrange to process this payment by [date] to avoid any further escalation.

{extra_context}

If you have already made the payment, please disregard this notice. Otherwise, please confirm when we can expect the payment.

Best regards,
Finance Team"""
                
        else:
            subject = f"Payment Related Communication - {obligation['party']}"
            email = f"""Dear {obligation['party']},

I'm writing regarding the transaction of {format_currency(obligation['amount'])}.

{extra_context}

Please let me know if you have any questions.

Best regards,
Finance Team"""
        
        # Add risk-based urgency if applicable
        if obligation['risk_score'] > 0.7:
            email += f"\n\n⚠️ Note: This payment is flagged as high priority in our system."
        
        return jsonify({"subject": subject, "body": email})
        
    except Exception as e:
        logger.error(f"Message generation error: {e}")
        return jsonify({"error": str(e)}), 500

# ------------------------------
# Chat Endpoint with Festival Detection
# ------------------------------

@app.route('/api/chat', methods=['POST'])
def chat():
    """Chat endpoint with festival detection and Groq integration"""
    data = request.get_json()
    messages = data.get('messages', [])
    transaction = data.get('transaction', {})
    festival_context = data.get('festivalContext', [])
    custom_prompt = data.get('prompt', '')
    
    if not messages:
        return jsonify({"error": "Messages required"}), 400
    
    try:
        last_message = messages[-1]['content'].lower() if messages else ""
        
        # Check if this is a festival-related question
        festival_keywords = ['festival', 'diwali', 'holi', 'ganesh', 'navratri', 'eid', 
                            'christmas', 'new year', 'celebration', 'gift', 'bonus']
        is_festival_question = any(keyword in last_message for keyword in festival_keywords)
        
        # If we have festival context and it's a festival question, provide detailed advice
        if festival_context and is_festival_question:
            # Build festival-specific response
            festivals_str = ""
            for f in festival_context:
                festivals_str += f"\n- **{f.get('name')}**: {f.get('date')} ({f.get('daysAway')} days away, Impact: {f.get('impact')})"
            
            response = f"""🎉 **Festival Financial Planning**

Detected upcoming festivals:
{festivals_str}

**Key Recommendations:**

1. **Cash Reserve Strategy**
   • Set aside {format_currency(min(50000, transaction.get('amount', 50000) if transaction else 50000))} for festival expenses
   • Build buffer of 30-40% above normal operating cash

2. **Payment Timing**
   • Pay critical vendors 7-10 days before festival
   • Schedule NEFT/RTGS before bank holidays
   • Use UPI for urgent payments during festival week

3. **Vendor Negotiation**
   • Request extensions from flexible vendors
   • Offer partial payments (40-50%) before festival
   • Communicate early about payment schedules

4. **Collection Strategy**
   • Accelerate customer collections before festival week
   • Send reminders 2 weeks before festival
   • Offer small discounts for early payments

Would you like me to draft a specific email for any of these festivals?"""
            
            return jsonify({"reply": response})
        
        # Check for Groq integration (if available)
        elif custom_prompt and os.getenv('OPENROUTER_API_KEY'):
            # Use Groq for advanced responses
            try:
                from groq import Groq
                groq_client = Groq(api_key=os.getenv('OPENROUTER_API_KEY'))
                
                # Build system prompt
                system_prompt = f"""You are PayWise AI, a financial assistant for small businesses.
                Current Date: {datetime.now().strftime('%Y-%m-%d')}

{festival_context and f"Upcoming Festivals: {festival_context}" or ""}

Provide practical, actionable financial advice. Be concise and professional."""
                
                completion = groq_client.chat.completions.create(
                    model="mixtral-8x7b-32768",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": custom_prompt or last_message}
                    ],
                    temperature=0.7,
                    max_tokens=500
                )
                
                response = completion.choices[0].message.content
                return jsonify({"reply": response})
                
            except Exception as e:
                logger.error(f"Groq error: {e}")
                # Fall back to regular response
        
        # Regular response handling (fallback)
        if "risk" in last_message and transaction:
            risk = transaction.get('risk_score', 0)
            priority = transaction.get('priority', 'Medium')
            response = f"**Risk Analysis**\n\nRisk Score: {risk:.2f}/1.00 ({priority} Priority)\n\n"
            if risk > 0.7:
                response += "⚠️ **HIGH RISK** - Immediate action recommended.\nConsider paying immediately or contacting the counterparty urgently."
            elif risk > 0.4:
                response += "🟡 **MEDIUM RISK** - Monitor closely.\nConsider negotiating an extension or partial payment."
            else:
                response += "✅ **LOW RISK** - Maintain regular schedule.\nPay on time to maintain good relationship."
                
        elif "penalty" in last_message and transaction:
            penalty = transaction.get('penalty_analysis', {}).get('total_penalty', 0)
            days_late = transaction.get('days_late', 0)
            response = f"**Penalty Analysis**\n\nCurrent Penalty: ₹{penalty:,.2f}\nDays Late: {days_late}\n\n"
            if days_late > 0:
                response += f"⚠️ Paying today would avoid additional penalties of ₹{penalty * 0.3:,.2f} per week."
            else:
                response += "✅ No penalty incurred yet. Pay before due date to avoid penalties."
                
        elif "partial" in last_message:
            min_pct = transaction.get('minimum_partial_pct', 40) if transaction else 40
            response = f"**Partial Payment Strategy**\n\n• Offer {min_pct}% now, remaining in 15 days\n• Most vendors accept this arrangement\n• Maintains relationship and cash flow\n\nWould you like me to draft a partial payment proposal?"
            
        elif "hello" in last_message or "hi" in last_message:
            response = """👋 **Hello! I'm PayWise AI**

I can help you with:
• **Risk Analysis** - Understand your transaction risk
• **Penalty Calculation** - Calculate late payment penalties
• **Payment Strategies** - Get recommendations
• **Festival Planning** - Prepare for upcoming festivals
• **Communication Drafting** - Create professional emails

What would you like to know?"""
            
        elif festival_context and not is_festival_question:
            # Suggest festival planning even if not asked
            festivals_list = [f.get('name') for f in festival_context[:2]]
            response = f"""📅 **Did you know?** Upcoming festivals: {', '.join(festivals_list)}.

Would you like me to help you plan your finances for these festivals? I can provide:
• Cash reserve recommendations
• Vendor payment scheduling
• Festival expense budgeting
• Collection strategies

Type "festival planning" to get started!"""
            
        else:
            response = "I can help you analyze your financial transactions. Ask me about:\n• Risk analysis\n• Penalty calculations\n• Payment strategies\n• Festival planning\n• Email drafting"
        
        return jsonify({"reply": response})
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/demo', methods=['GET'])
def demo():
    """Return demo transaction"""
    demo_data = {
        "counterparty_name": "Income Tax Department",
        "counterparty_type": "tax_authority",
        "amount": 50000,
        "transaction_type": "payable",
        "status": "overdue",
        "due_date": (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d'),
        "accepts_partial": False,
        "minimum_partial_pct": 100
    }
    return jsonify(analyze_transaction(demo_data))

@app.route('/api/predictive-analysis', methods=['GET'])
def predictive_analysis():
    """Get predictive analysis with cascading risk and borrowing recommendations"""
    try:
        # Load processed data
        if PROCESSED_DATA_FILE.exists():
            with open(PROCESSED_DATA_FILE, 'r') as f:
                processed = json.load(f)
        else:
            processed = process_all_transactions()
        
        if not processed or not processed.get('payables'):
            return jsonify({"error": "No obligations found"}), 404
        
        # Get current cash balance
        cash_balance = get_cash_balance()
        
        # Import predictive engine
        from backend.engine.predictive_decision_engine import PredictiveDecisionEngine
        
        # Create engine and run analysis
        engine = PredictiveDecisionEngine(cash_balance)
        
        # Convert payables to format expected by engine
        obligations = []
        for p in processed.get('payables', []):
            obligations.append({
                "transaction_id": p.get('transaction_id'),
                "party": p.get('party'),
                "amount": p.get('amount'),
                "due_date": p.get('due_date'),
                "days_late": p.get('days_late', 0),
                "type": p.get('type', 'unknown'),
                "risk_score": p.get('risk_score', 0.5),
                "penalty": p.get('penalty', 0),
                "partial_payment": p.get('partial_payment', {})
            })
        
        result = engine.run_analysis_with_custom_order(obligations)
        
        # Add cash balance to result
        result['cash_balance'] = cash_balance
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Predictive analysis error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/apply-partial', methods=['POST'])
def apply_partial():
    """Apply partial payment to an obligation"""
    data = request.get_json()
    transaction_id = data.get('transaction_id')
    percentage = data.get('percentage', 50)
    
    try:
        # Load transactions
        with open(TRANSACTIONS_FILE, 'r') as f:
            transactions = json.load(f)
        
        # Find and update transaction
        updated = False
        for t in transactions:
            if t.get('id') == transaction_id:
                original_amount = t.get('amount', 0)
                partial_amount = original_amount * percentage / 100
                t['amount'] = original_amount - partial_amount
                t['partial_payment_applied'] = True
                t['partial_percentage'] = percentage
                t['partial_amount_paid'] = partial_amount
                updated = True
                break
        
        if updated:
            # Save updated transactions
            with open(TRANSACTIONS_FILE, 'w') as f:
                json.dump(transactions, f, indent=2, default=str)
            
            # Reprocess data
            process_all_transactions()
            
            return jsonify({
                "success": True,
                "message": f"Applied {percentage}% partial payment. Remaining: ₹{t['amount']:,.2f}"
            })
        else:
            return jsonify({"success": False, "error": "Transaction not found"}), 404
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/reorder-payments', methods=['POST'])
def reorder_payments():
    """Set manual payment order"""
    data = request.get_json()
    order = data.get('order', [])
    
    try:
        # Save order to a file
        ORDER_FILE = DATA_DIR / 'payment_order.json'
        with open(ORDER_FILE, 'w') as f:
            json.dump({"order": order}, f)
        
        return jsonify({"success": True, "message": "Payment order updated"})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/update-cash', methods=['POST'])
def update_cash():
    """Update cash balance"""
    data = request.get_json()
    cash_balance = data.get('cash_balance', 0)
    
    try:
        # Update cash balance in separate file
        set_cash_balance(cash_balance)
        
        # Update processed data
        if PROCESSED_DATA_FILE.exists():
            with open(PROCESSED_DATA_FILE, 'r') as f:
                processed = json.load(f)
            processed['cash_balance'] = cash_balance
            with open(PROCESSED_DATA_FILE, 'w') as f:
                json.dump(processed, f, indent=2, default=str)
        
        return jsonify({"success": True, "cash_balance": cash_balance})
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/calculate-projection', methods=['POST'])
def calculate_projection():
    """Calculate real-time projection for custom payment order"""
    data = request.get_json()
    order_data = data.get('order', [])
    cash_balance = data.get('cash_balance', get_cash_balance())
    
    try:
        # Load processed data for full context
        if PROCESSED_DATA_FILE.exists():
            with open(PROCESSED_DATA_FILE, 'r') as f:
                processed = json.load(f)
        else:
            processed = process_all_transactions()
        
        # Create mapping of transactions by ID
        payables = processed.get('payables', [])
        transaction_map = {}
        
        # Build a comprehensive map with multiple ID formats
        for p in payables:
            # Store by transaction_id
            if p.get('transaction_id'):
                transaction_map[p.get('transaction_id')] = p
            # Also store by id if exists
            if p.get('id'):
                transaction_map[p.get('id')] = p
        
        # Also add transactions from the original transactions file if needed
        try:
            with open(TRANSACTIONS_FILE, 'r') as f:
                all_transactions = json.load(f)
                for t in all_transactions:
                    if t.get('id'):
                        # Convert to format similar to payables
                        converted = {
                            'transaction_id': t.get('id'),
                            'party': t.get('counterparty_name'),
                            'amount': t.get('amount'),
                            'due_date': t.get('due_date'),
                            'type': t.get('counterparty_type', 'unknown'),
                            'risk_score': t.get('risk_score', 0.5),
                            'penalty': t.get('penalty_analysis', {}).get('total_penalty', 0),
                            'days_late': t.get('days_late', 0),
                            'partial_payment': {
                                'accepts_partial': t.get('accepts_partial', True),
                                'minimum_pct': t.get('minimum_partial_pct', 50)
                            }
                        }
                        transaction_map[t.get('id')] = converted
        except:
            pass
        
        # Extract transaction IDs - handle both string IDs and objects with transaction_id
        order_ids = []
        for item in order_data:
            if isinstance(item, dict):
                # If it's a dictionary, try to get the transaction_id
                tid = item.get('transaction_id') or item.get('id')
                if tid:
                    order_ids.append(tid)
                else:
                    # If no ID found, log warning
                    logger.warning(f"Item without ID: {item}")
            elif isinstance(item, str):
                # If it's a string, use it directly
                order_ids.append(item)
            else:
                logger.warning(f"Unexpected item type: {type(item)}")
        
        # Calculate projection with partial payment support
        remaining_cash = cash_balance
        total_penalties = 0
        obligations_fulfilled = 0
        risk_exposure = 0
        fulfilled_amount = 0
        partial_payments_used = 0
        partial_payments_saved = 0
        
        total_obligations_amount = 0
        valid_obligations = []
        
        # First pass: get valid obligations and total amount
        for tid in order_ids:
            t = transaction_map.get(tid)
            if t:
                amount = t.get('amount', 0)
                total_obligations_amount += amount
                valid_obligations.append(t)
            else:
                logger.warning(f"Transaction not found: {tid}")
        
        # Track payments in order
        payment_plan = []
        
        for idx, t in enumerate(valid_obligations):
            amount = t.get('amount', 0)
            penalty = t.get('penalty', 0)
            risk_score = t.get('risk_score', 0.5)
            party = t.get('party', t.get('counterparty_name', 'Unknown'))
            cp_type = t.get('type', t.get('counterparty_type', 'unknown'))
            
            # Get partial payment info
            partial = t.get('partial_payment', {})
            accepts_partial = partial.get('accepts_partial', True)
            min_pct = partial.get('minimum_pct', partial.get('minimum_partial_pct', 50))
            min_amount = partial.get('minimum_amount', amount * min_pct / 100)
            suggested_pct = partial.get('suggested_pct', min_pct)
            suggested_amount = amount * suggested_pct / 100
            
            payment_status = "unpaid"
            paid_amount = 0
            
            if remaining_cash >= amount:
                # Can pay full amount
                remaining_cash -= amount
                total_penalties += penalty
                obligations_fulfilled += 1
                fulfilled_amount += amount
                payment_status = "paid_full"
                paid_amount = amount
            elif accepts_partial and remaining_cash >= min_amount:
                # Can pay partial
                pay_amount = min(suggested_amount, remaining_cash)
                if pay_amount >= min_amount:
                    remaining_cash -= pay_amount
                    penalty_incurred = penalty * (pay_amount / amount)
                    total_penalties += penalty_incurred
                    obligations_fulfilled += (pay_amount / amount)
                    fulfilled_amount += pay_amount
                    partial_payments_used += 1
                    partial_payments_saved += amount - pay_amount
                    payment_status = "paid_partial"
                    paid_amount = pay_amount
                else:
                    risk_exposure += amount
                    payment_status = "unpaid_insufficient"
            else:
                # Cannot pay at all
                risk_exposure += amount
                if accepts_partial:
                    payment_status = "unpaid_min_required"
                else:
                    payment_status = "unpaid_no_partial"
            
            payment_plan.append({
                "rank": idx + 1,
                "party": party,
                "amount": amount,
                "type": cp_type,
                "risk_score": risk_score,
                "accepts_partial": accepts_partial,
                "min_partial_pct": min_pct,
                "min_partial_amount": min_amount,
                "payment_status": payment_status,
                "paid_amount": paid_amount,
                "remaining": amount - paid_amount if paid_amount > 0 else amount
            })
        
        efficiency = fulfilled_amount / total_obligations_amount if total_obligations_amount > 0 else 0
        shortfall = max(0, total_obligations_amount - cash_balance)
        
        return jsonify({
            "success": True,
            "projection": {
                "final_cash": remaining_cash,
                "total_penalties": total_penalties,
                "obligations_fulfilled": obligations_fulfilled,
                "total_obligations": len(valid_obligations),
                "efficiency": efficiency,
                "risk_exposure": risk_exposure,
                "partial_payments_used": partial_payments_used,
                "partial_payments_saved": partial_payments_saved,
                "shortfall": shortfall,
                "payment_plan": payment_plan
            }
        })
        
    except Exception as e:
        logger.error(f"Projection calculation error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    
@app.route('/api/get-saved-order', methods=['GET'])
def get_saved_order():
    """Get saved payment order"""
    try:
        ORDER_FILE = DATA_DIR / 'payment_order.json'
        if ORDER_FILE.exists():
            with open(ORDER_FILE, 'r') as f:
                data = json.load(f)
                return jsonify({"success": True, "order": data.get('order', [])})
        return jsonify({"success": True, "order": []})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/risk-analysis', methods=['GET'])
def risk_analysis():
    """Get enhanced risk analysis with days to zero and cash flow projection"""
    try:
        # Load processed data
        if PROCESSED_DATA_FILE.exists():
            with open(PROCESSED_DATA_FILE, 'r') as f:
                processed = json.load(f)
        else:
            processed = process_all_transactions()
        
        if not processed:
            return jsonify({"success": False, "error": "No data found"}), 404
        
        # Import risk engine
        from backend.engine.risk_engine import calculate_risk
        
        # Calculate risk with partial payment consideration
        risk_report = calculate_risk(processed, consider_partial=True)
        
        # Generate cash flow projection for graph (next 60 days)
        cash_flow_projection = []
        current_cash = processed.get('cash_balance', 0)
        payables = processed.get('payables', [])
        receivables = processed.get('receivables', [])
        
        from datetime import datetime, timedelta
        
        for i in range(61):  # 60 days projection
            day = i
            date = datetime.today().date() + timedelta(days=i)
            daily_cash = current_cash
            
            # Subtract payables due on this day
            for p in payables:
                due_date = p.get('due_date')
                if due_date:
                    if isinstance(due_date, str):
                        due = datetime.strptime(due_date, "%Y-%m-%d").date()
                    else:
                        due = due_date
                    if due == date:
                        daily_cash -= p.get('amount', 0)
            
            # Add receivables due on this day
            for r in receivables:
                expected_date = r.get('expected_date')
                if expected_date:
                    if isinstance(expected_date, str):
                        expected = datetime.strptime(expected_date, "%Y-%m-%d").date()
                    else:
                        expected = expected_date
                    if expected == date:
                        daily_cash += r.get('amount', 0)
            
            cash_flow_projection.append({
                "day": day,
                "cash_balance": daily_cash
            })
            current_cash = daily_cash
        
        return jsonify({
            "success": True,
            "data": {
                **risk_report,
                "cash_flow_projection": cash_flow_projection
            }
        })
        
    except Exception as e:
        logger.error(f"Risk analysis error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    

    
@app.route('/api/clear-saved-order', methods=['POST'])
def clear_saved_order():
    """Clear saved payment order"""
    try:
        ORDER_FILE = DATA_DIR / 'payment_order.json'
        if ORDER_FILE.exists():
            ORDER_FILE.unlink()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/initialize-cash', methods=['POST'])
def initialize_cash():
    """Initialize or reset cash balance"""
    data = request.get_json()
    initial_cash = data.get('cash_balance', 100000)  # Default ₹1,00,000
    
    try:
        # Set cash balance
        set_cash_balance(initial_cash)
        
        # Update processed data
        if PROCESSED_DATA_FILE.exists():
            with open(PROCESSED_DATA_FILE, 'r') as f:
                processed = json.load(f)
            processed['cash_balance'] = initial_cash
            with open(PROCESSED_DATA_FILE, 'w') as f:
                json.dump(processed, f, indent=2, default=str)
        
        return jsonify({
            "success": True,
            "cash_balance": initial_cash,
            "message": f"Cash balance initialized to {format_currency(initial_cash)}"
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/get-cash', methods=['GET'])
def get_cash():
    """Get current cash balance"""
    return jsonify({
        "success": True,
        "cash_balance": get_cash_balance()
    })

@app.route('/api/cleanup-duplicates', methods=['POST'])
def cleanup_duplicates():
    """Remove duplicate transactions from the database"""
    try:
        with open(TRANSACTIONS_FILE, 'r') as f:
            transactions = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return jsonify({"error": "No transactions found"}), 404
    
    original_count = len(transactions)
    
    # Remove duplicates using the same logic as financial_processor
    seen = set()
    unique_transactions = []
    removed_count = 0
    
    for t in transactions:
        # Create key based on counterparty_name, amount, due_date
        key = (
            t.get("counterparty_name", ""),
            t.get("amount", 0),
            t.get("due_date", "")
        )
        
        if key not in seen:
            seen.add(key)
            unique_transactions.append(t)
        else:
            removed_count += 1
    
    # Save back only unique transactions
    with open(TRANSACTIONS_FILE, 'w') as f:
        json.dump(unique_transactions, f, indent=2, default=str)
    
    # Reprocess all data
    process_all_transactions()
    
    return jsonify({
        "success": True,
        "original_count": original_count,
        "unique_count": len(unique_transactions),
        "removed_count": removed_count,
        "message": f"Removed {removed_count} duplicate transactions"
    })

# ------------------------------
# Run the app
# ------------------------------
if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 PayWise Fintech Decision Assistant")
    print("="*60)
    print(f"📁 Data directory: {DATA_DIR}")
    print(f"📁 Upload directory: {UPLOAD_DIR}")
    print(f"📁 Output directory: {OUTPUT_DIR}")
    print(f"📄 Processed data: {PROCESSED_DATA_FILE}")
    print(f"💰 Initial cash balance: {format_currency(get_cash_balance())}")
    print(f"🔑 OpenRouter API: {'✅ Configured' if os.getenv('OPENROUTER_API_KEY') else '⚠️ Not set'}")
    print(f"🌐 Server: http://localhost:5000")
    print("="*60 + "\n")
    
    # Process existing transactions on startup
    process_all_transactions()
    
    app.run(debug=True, host='0.0.0.0', port=5000)