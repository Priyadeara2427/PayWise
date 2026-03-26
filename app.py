"""
PayWise - Fintech Decision Assistant
Complete Flask application with payment strategy, data preprocessing, and all backend integrations
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
from backend.engine.risk_engine import calculate_risk
from backend.engine.predictive_decision_engine import PredictiveDecisionEngine
from backend.engine.payment_strategy_analyzer import PaymentStrategyAnalyzer

from backend.ingestion.csv_parser import CSVParser
from backend.ingestion.pdf_parser import PDFParser
from backend.ingestion.ocr_parser import OCRParser
from backend.ingestion.pipeline import IngestionPipeline

from backend.models.obligation import Obligation, FinancialState, PartialPaymentTerms, TransactionType
from backend.preprocessing.financial_processor import (
    process_ingested_data, 
    get_partial_payment_summary,
    create_cash_flow_analysis,
    print_financial_summary,
    remove_duplicates,
    aggregate_by_category,
    get_payment_priorities
)

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
OBLIGATIONS_FILE = DATA_DIR / 'obligations.json'
FINANCIAL_STATE_FILE = OUTPUT_DIR / 'financial_state.json'
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
    
    if not OBLIGATIONS_FILE.exists():
        with open(OBLIGATIONS_FILE, 'w') as f:
            json.dump([], f)
    
    if not CASH_BALANCE_FILE.exists():
        with open(CASH_BALANCE_FILE, 'w') as f:
            json.dump({"cash_balance": 100000}, f)

init_data_files()

# Initialize engines
decision_engine = DecisionEngine()
normalizer = DataNormalizer()
communication_engine = CommunicationEngine(api_key=os.getenv('OPENROUTER_API_KEY'))
pipeline = IngestionPipeline(enable_decisions=True)

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

def save_financial_state(state):
    """Save financial state to file"""
    with open(FINANCIAL_STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2, default=str)

def load_financial_state():
    """Load financial state from file"""
    try:
        with open(FINANCIAL_STATE_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

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
                            "transaction_id": t.get("id"),
                            "payment_category": t.get("payment_category"),
                            "can_negotiate": t.get("can_negotiate", False),
                            "can_delay": t.get("can_delay", False),
                            "can_partial": t.get("can_partial", False),
                            "grace_days": t.get("grace_days", 0),
                            "message_template": t.get("message_template", "")
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
# Analysis Functions with Payment Strategy
# ------------------------------

def analyze_transaction(data):
    """Analyze a single transaction using backend logic with payment strategy"""
    try:
        # Calculate days late
        days_late = 0
        due_date = data.get('due_date')
        due_date_obj = None
        
        if due_date:
            try:
                due_date_obj = datetime.strptime(due_date, '%Y-%m-%d').date()
                today = datetime.today().date()
                days_late = max(0, (today - due_date_obj).days)
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
            priority = "critical"
        elif risk_score >= 0.4:
            priority = "medium"
        else:
            priority = "low"
        
        # Calculate penalty
        penalty_rate = 0.005
        penalty = amount * penalty_rate * days_late
        penalty = min(penalty, amount * 0.2)
        
        # Get payment strategy analysis
        if due_date_obj:
            payment_strategy = PaymentStrategyAnalyzer.analyze_payment(
                counterparty_type, amount, due_date_obj, days_late
            )
        else:
            payment_strategy = PaymentStrategyAnalyzer.analyze_payment(
                counterparty_type, amount, datetime.today().date(), days_late
            )
        
        # Generate recommendations based on payment strategy
        recommendations = []
        
        if payment_strategy.get('payment_action') == 'PAY_IMMEDIATELY':
            recommendations.append({
                "action": "Pay Immediately",
                "rationale": payment_strategy.get('recommendation', 'Critical payment - pay now'),
                "urgency": "critical"
            })
        elif payment_strategy.get('payment_action') == 'NEGOTIATE_EXTENSION':
            recommendations.append({
                "action": "Request Payment Extension",
                "rationale": payment_strategy.get('recommendation', 'Can negotiate extension'),
                "urgency": "medium"
            })
        elif payment_strategy.get('payment_action') == 'COMMUNICATE_AND_DELAY':
            recommendations.append({
                "action": "Communicate and Delay",
                "rationale": payment_strategy.get('recommendation', 'Flexible - communicate first'),
                "urgency": "low"
            })
        
        # Add partial payment recommendation if applicable
        if payment_strategy.get('can_partial') and data.get('accepts_partial', True):
            min_pct = data.get('minimum_partial_pct', 40)
            recommendations.append({
                "action": f"Propose Partial Payment ({min_pct}% Now)",
                "rationale": f"Offer {min_pct}% now, balance in 15 days",
                "urgency": "medium"
            })
        
        if penalty > 0 and payment_strategy.get('can_negotiate', False):
            recommendations.append({
                "action": f"Avoid ₹{penalty:,.0f} Penalty",
                "rationale": f"Pay within {max(0, 30 - days_late)} days or negotiate extension",
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
            "analyzed_at": datetime.now().isoformat(),
            
            # Payment Strategy Fields
            "payment_category": payment_strategy.get('category'),
            "can_negotiate": payment_strategy.get('can_negotiate', False),
            "can_delay": payment_strategy.get('can_delay', False),
            "can_partial": payment_strategy.get('can_partial', False),
            "grace_days": payment_strategy.get('grace_days', 0),
            "penalty_rate": payment_strategy.get('penalty_rate', 0),
            "payment_action": payment_strategy.get('payment_action'),
            "recommendation": payment_strategy.get('recommendation'),
            "risks": payment_strategy.get('risks', []),
            "message_template": payment_strategy.get('message_template', '')
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
    """Calculate comprehensive dashboard statistics from transactions"""
    transactions = get_transactions(limit=1000)
    
    total_transactions = len(transactions)
    total_amount = sum(t.get('amount', 0) for t in transactions)
    
    # Risk distribution
    high_risk = sum(1 for t in transactions if t.get('risk_score', 0) >= 0.7)
    medium_risk = sum(1 for t in transactions if 0.4 <= t.get('risk_score', 0) < 0.7)
    low_risk = sum(1 for t in transactions if t.get('risk_score', 0) < 0.4)
    
    # Status distribution
    overdue = sum(1 for t in transactions if t.get('days_late', 0) > 0)
    pending = sum(1 for t in transactions if t.get('status') == 'pending')
    paid = sum(1 for t in transactions if t.get('status') == 'paid')
    
    # Type distribution
    payables = sum(1 for t in transactions if t.get('transaction_type') == 'payable')
    receivables = sum(1 for t in transactions if t.get('transaction_type') == 'receivable')
    
    # Partial payment stats
    accepts_partial = sum(1 for t in transactions if t.get('accepts_partial', False))
    
    # Payment strategy distribution
    must_pay_count = sum(1 for t in transactions if t.get('payment_category') == 'must_pay')
    can_negotiate_count = sum(1 for t in transactions if t.get('payment_category') == 'can_negotiate')
    can_delay_count = sum(1 for t in transactions if t.get('payment_category') == 'can_delay')
    
    # Financial totals
    total_payables_amount = sum(t.get('amount', 0) for t in transactions if t.get('transaction_type') == 'payable')
    total_receivables_amount = sum(t.get('amount', 0) for t in transactions if t.get('transaction_type') == 'receivable')
    total_penalties = sum(t.get('penalty_analysis', {}).get('total_penalty', 0) for t in transactions)
    
    # Average risk score
    avg_risk_score = sum(t.get('risk_score', 0) for t in transactions) / max(total_transactions, 1)
    
    return {
        "total_transactions": total_transactions,
        "total_amount": total_amount,
        "high_risk_count": high_risk,
        "medium_risk_count": medium_risk,
        "low_risk_count": low_risk,
        "overdue_count": overdue,
        "pending_count": pending,
        "paid_count": paid,
        "payables_count": payables,
        "receivables_count": receivables,
        "accepts_partial_count": accepts_partial,
        "must_pay_count": must_pay_count,
        "can_negotiate_count": can_negotiate_count,
        "can_delay_count": can_delay_count,
        "total_payables_amount": total_payables_amount,
        "total_receivables_amount": total_receivables_amount,
        "total_penalties": total_penalties,
        "avg_risk_score": avg_risk_score,
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
            "payment_strategy_analyzer": "loaded",
            "financial_processor": "loaded",
            "parsers": "loaded"
        }
    })

@app.route('/api/analyze', methods=['POST'])
def analyze():
    """Analyze a transaction with payment strategy"""
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
    """Upload and parse a file with payment strategy"""
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
        
        # Process all obligations
        obligations = parsed.get('obligations', [])
        results = []
        
        for ob in obligations:
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
        
        if len(results) == 1:
            return jsonify(results[0])
        else:
            return jsonify({
                "payments": results,
                "cash_balance": parsed.get('cash_balance', get_cash_balance()),
                "total_obligations": len(results)
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

@app.route('/api/dashboard-data', methods=['GET'])
def get_dashboard_data():
    """Get comprehensive dashboard data with payment strategies"""
    try:
        transactions = get_transactions(limit=100)
        
        # Add payment strategy to each transaction if missing
        for t in transactions:
            if 'payment_category' not in t:
                due_date = t.get('due_date')
                due_date_obj = None
                if due_date:
                    try:
                        due_date_obj = datetime.strptime(due_date, '%Y-%m-%d').date()
                    except:
                        due_date_obj = datetime.today().date()
                else:
                    due_date_obj = datetime.today().date()
                
                strategy = PaymentStrategyAnalyzer.analyze_payment(
                    t.get('counterparty_type', 'unknown'),
                    t.get('amount', 0),
                    due_date_obj,
                    t.get('days_late', 0)
                )
                
                t['payment_category'] = strategy.get('category')
                t['can_negotiate'] = strategy.get('can_negotiate', False)
                t['can_delay'] = strategy.get('can_delay', False)
                t['can_partial'] = strategy.get('can_partial', False)
                t['grace_days'] = strategy.get('grace_days', 0)
                t['penalty_rate'] = strategy.get('penalty_rate', 0)
                t['payment_action'] = strategy.get('payment_action')
                t['recommendation'] = strategy.get('recommendation')
                t['risks'] = strategy.get('risks', [])
                t['message_template'] = strategy.get('message_template', '')
        
        return jsonify({
            "status": "success",
            "payments": transactions,
            "cash_balance": get_cash_balance()
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

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
    """Generate a communication message with payment strategy context"""
    data = request.get_json()
    transaction = data.get('transaction', {})
    action = data.get('action', 'request_extension')
    extra_context = data.get('extra_context', '')
    
    if not transaction:
        return jsonify({"error": "Transaction data required"}), 400
    
    try:
        # Use communication engine
        profile = communication_engine.get_relationship_profile(
            transaction.get('counterparty_type', 'unknown')
        )
        
        # Get payment strategy for better context
        due_date = transaction.get('due_date')
        due_date_obj = None
        if due_date:
            try:
                due_date_obj = datetime.strptime(due_date, '%Y-%m-%d').date()
            except:
                due_date_obj = datetime.today().date()
        else:
            due_date_obj = datetime.today().date()
        
        strategy = PaymentStrategyAnalyzer.analyze_payment(
            transaction.get('counterparty_type', 'unknown'),
            transaction.get('amount', 0),
            due_date_obj,
            transaction.get('days_late', 0)
        )
        
        obligation = {
            "party": transaction.get('counterparty_name', 'Vendor'),
            "amount": transaction.get('amount', 0),
            "due_date": transaction.get('due_date', ''),
            "days_late": transaction.get('days_late', 0),
            "type": transaction.get('counterparty_type', 'unknown')
        }
        
        # Use strategy message template if available
        if action == 'request_extension' and strategy.get('message_template'):
            email = strategy.get('message_template')
            subject = f"Request for Payment Extension - {obligation['party']}"
        elif action == 'propose_partial' and strategy.get('can_partial'):
            email = communication_engine.generate_partial_payment_proposal(
                obligation, profile,
                proposed_pct=transaction.get('minimum_partial_pct', 40),
                remaining_plan={"installments": 2, "days": 15}
            )
            subject = f"Proposed Partial Payment Arrangement - {obligation['party']}"
        elif action == 'request_extension':
            email = communication_engine.generate_payment_extension_request(
                obligation, profile, suggested_days=strategy.get('grace_days', 10)
            )
            subject = f"Request for Payment Extension - {obligation['party']}"
        elif action == 'payment_confirmation':
            subject = f"Payment Confirmation - {obligation['party']}"
            email = f"""Dear {obligation['party']},

This is to confirm that payment of {format_currency(obligation['amount'])} has been processed and should reflect in your account shortly.

Thank you for your business.

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
        else:
            subject = f"Payment Reminder - {obligation['party']}"
            email = strategy.get('message_template') or f"""Dear {obligation['party']},

This is a reminder that payment of {format_currency(obligation['amount'])} is now {obligation.get('days_late', 0)} days overdue.

Please process at your earliest convenience.

Best regards,
Finance Team"""
        
        return jsonify({"subject": subject, "body": email})
        
    except Exception as e:
        logger.error(f"Message generation error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    """Chat endpoint with payment strategy awareness"""
    data = request.get_json()
    messages = data.get('messages', [])
    transaction = data.get('transaction', {})
    
    if not messages:
        return jsonify({"error": "Messages required"}), 400
    
    try:
        last_message = messages[-1]['content'].lower() if messages else ""
        
        # Get payment strategy if transaction exists
        strategy = None
        if transaction:
            due_date = transaction.get('due_date')
            due_date_obj = None
            if due_date:
                try:
                    due_date_obj = datetime.strptime(due_date, '%Y-%m-%d').date()
                except:
                    due_date_obj = datetime.today().date()
            else:
                due_date_obj = datetime.today().date()
            
            strategy = PaymentStrategyAnalyzer.analyze_payment(
                transaction.get('counterparty_type', 'unknown'),
                transaction.get('amount', 0),
                due_date_obj,
                transaction.get('days_late', 0)
            )
        
        if "negotiate" in last_message or "extension" in last_message:
            if strategy and strategy.get('can_negotiate'):
                response = f"**Negotiation Strategy**\n\n{strategy.get('recommendation')}\n\n"
                response += f"**Message Template:**\n{strategy.get('message_template', '')}\n\n"
                response += "Would you like me to draft a formal extension request?"
            else:
                response = "This payment may not be negotiable. Check the counterparty type and due date."
                
        elif "partial" in last_message:
            if strategy and strategy.get('can_partial'):
                min_pct = transaction.get('minimum_partial_pct', 40)
                response = f"**Partial Payment Strategy**\n\n• Offer {min_pct}% now, remaining in {strategy.get('grace_days', 15)} days\n"
                response += f"• {strategy.get('recommendation')}\n\n"
                response += "Would you like me to draft a partial payment proposal?"
            else:
                response = "Partial payment may not be accepted for this counterparty type."
                
        elif "delay" in last_message or "postpone" in last_message:
            if strategy and strategy.get('can_delay'):
                response = f"**Delay Strategy**\n\n{strategy.get('recommendation')}\n\n"
                response += f"Grace period: {strategy.get('grace_days', 0)} days\n"
                response += "Make sure to communicate clearly to maintain the relationship."
            else:
                response = "This payment should not be delayed. Pay on time to avoid consequences."
                
        elif "risk" in last_message:
            if transaction:
                risk = transaction.get('risk_score', 0)
                priority = transaction.get('priority', 'Medium')
                response = f"**Risk Analysis**\n\nRisk Score: {risk:.2f}/1.00 ({priority} Priority)\n\n"
                if strategy:
                    response += f"**Payment Category:** {strategy.get('category', 'unknown')}\n"
                    response += f"**Can Negotiate:** {'Yes' if strategy.get('can_negotiate') else 'No'}\n"
                    response += f"**Can Delay:** {'Yes' if strategy.get('can_delay') else 'No'}\n\n"
                if risk > 0.7:
                    response += "⚠️ **HIGH RISK** - Immediate action recommended.\n"
                elif risk > 0.4:
                    response += "🟡 **MEDIUM RISK** - Monitor closely.\n"
                else:
                    response += "✅ **LOW RISK** - Maintain regular schedule.\n"
            else:
                response = "No transaction selected. Please analyze a transaction first."
                
        elif "penalty" in last_message and transaction:
            penalty = transaction.get('penalty_analysis', {}).get('total_penalty', 0)
            days_late = transaction.get('days_late', 0)
            response = f"**Penalty Analysis**\n\nCurrent Penalty: {format_currency(penalty)}\nDays Late: {days_late}\n\n"
            if days_late > 0:
                response += f"⚠️ Paying today would avoid additional penalties.\n"
                if strategy and strategy.get('can_negotiate'):
                    response += f"\n💡 You can also request extension to waive penalties."
            else:
                response += "✅ No penalty incurred yet. Pay before due date to avoid penalties."
                
        elif "message" in last_message or "template" in last_message:
            if strategy and strategy.get('message_template'):
                response = f"**Message Template**\n\n{strategy.get('message_template')}\n\n"
                response += "You can copy and customize this message."
            else:
                response = "No specific message template available. Would you like me to draft a custom message?"
                
        elif "hello" in last_message or "hi" in last_message:
            response = "👋 **Hello! I'm PayWise AI**\n\nI can help you with:\n"
            response += "• **Payment Strategy** - Understand if you can negotiate, delay, or pay partial\n"
            response += "• **Risk Analysis** - Understand your transaction risk\n"
            response += "• **Penalty Calculation** - Calculate late payment penalties\n"
            response += "• **Message Templates** - Get communication templates\n"
            response += "• **Negotiation Advice** - Get tips for extension requests\n\n"
            response += "What would you like to know?"
            
        else:
            response = f"I can help you analyze your payment. "
            if strategy:
                response += f"This payment is **{strategy.get('category', 'unknown')}**. "
                response += f"{strategy.get('recommendation', '')}\n\n"
            response += "Ask me about: negotiation, partial payment, delay options, or message templates."
        
        return jsonify({"reply": response})
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/demo', methods=['GET'])
def demo():
    """Return demo transaction with payment strategy"""
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

@app.route('/api/demo-batch', methods=['GET'])
def demo_batch():
    """Return multiple demo transactions for dashboard testing"""
    demo_payments = [
        {
            "counterparty_name": "Income Tax Department",
            "counterparty_type": "tax_authority",
            "amount": 50000,
            "due_date": (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d'),
            "days_late": 5,
            "priority": "critical",
            "risk_score": 0.95
        },
        {
            "counterparty_name": "Raj Fabrics",
            "counterparty_type": "vendor",
            "amount": 25000,
            "due_date": datetime.now().strftime('%Y-%m-%d'),
            "days_late": 0,
            "priority": "medium",
            "risk_score": 0.4
        },
        {
            "counterparty_name": "HDFC Bank",
            "counterparty_type": "bank",
            "amount": 15000,
            "due_date": (datetime.now() + timedelta(days=3)).strftime('%Y-%m-%d'),
            "days_late": 0,
            "priority": "high",
            "risk_score": 0.7
        },
        {
            "counterparty_name": "Friend - Rajesh",
            "counterparty_type": "friend",
            "amount": 10000,
            "due_date": (datetime.now() + timedelta(days=15)).strftime('%Y-%m-%d'),
            "days_late": 0,
            "priority": "low",
            "risk_score": 0.1
        },
        {
            "counterparty_name": "Electricity Board",
            "counterparty_type": "utility",
            "amount": 3500,
            "due_date": (datetime.now() + timedelta(days=10)).strftime('%Y-%m-%d'),
            "days_late": 0,
            "priority": "medium",
            "risk_score": 0.3
        },
        {
            "counterparty_name": "Office Rent",
            "counterparty_type": "rent",
            "amount": 20000,
            "due_date": (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d'),
            "days_late": 0,
            "priority": "medium",
            "risk_score": 0.35
        },
        {
            "counterparty_name": "Employee Salary",
            "counterparty_type": "employee",
            "amount": 45000,
            "due_date": (datetime.now() + timedelta(days=2)).strftime('%Y-%m-%d'),
            "days_late": 0,
            "priority": "high",
            "risk_score": 0.8
        }
    ]
    
    results = []
    for payment in demo_payments:
        due_date = datetime.strptime(payment['due_date'], '%Y-%m-%d').date()
        
        strategy = PaymentStrategyAnalyzer.analyze_payment(
            payment['counterparty_type'],
            payment['amount'],
            due_date,
            payment.get('days_late', 0)
        )
        
        results.append({
            **payment,
            'payment_category': strategy.get('category'),
            'can_negotiate': strategy.get('can_negotiate', False),
            'can_delay': strategy.get('can_delay', False),
            'can_partial': strategy.get('can_partial', False),
            'grace_days': strategy.get('grace_days', 0),
            'penalty_rate': strategy.get('penalty_rate', 0),
            'payment_action': strategy.get('payment_action'),
            'recommendation': strategy.get('recommendation'),
            'risks': strategy.get('risks', []),
            'message_template': strategy.get('message_template', ''),
            'days_until_due': max(0, (due_date - datetime.today().date()).days)
        })
    
    return jsonify({
        "status": "success",
        "payments": results,
        "cash_balance": get_cash_balance()
    })

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
                "message": f"Applied {percentage}% partial payment. Remaining: {format_currency(t['amount'])}"
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

@app.route('/api/update-cash', methods=['POST'])
def update_cash():
    """Update cash balance"""
    data = request.get_json()
    cash_balance = data.get('cash_balance', 0)
    
    try:
        # Update cash balance
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

@app.route('/api/get-cash', methods=['GET'])
def get_cash():
    """Get current cash balance"""
    return jsonify({
        "success": True,
        "cash_balance": get_cash_balance()
    })

@app.route('/api/initialize-cash', methods=['POST'])
def initialize_cash():
    """Initialize or reset cash balance"""
    data = request.get_json()
    initial_cash = data.get('cash_balance', 100000)
    
    try:
        set_cash_balance(initial_cash)
        
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

@app.route('/api/cleanup-duplicates', methods=['POST'])
def cleanup_duplicates():
    """Remove duplicate transactions from the database"""
    try:
        with open(TRANSACTIONS_FILE, 'r') as f:
            transactions = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return jsonify({"error": "No transactions found"}), 404
    
    original_count = len(transactions)
    
    seen = set()
    unique_transactions = []
    removed_count = 0
    
    for t in transactions:
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
    
    with open(TRANSACTIONS_FILE, 'w') as f:
        json.dump(unique_transactions, f, indent=2, default=str)
    
    process_all_transactions()
    
    return jsonify({
        "success": True,
        "original_count": original_count,
        "unique_count": len(unique_transactions),
        "removed_count": removed_count,
        "message": f"Removed {removed_count} duplicate transactions"
    })

@app.route('/api/calculate-projection', methods=['POST'])
def calculate_projection():
    """Calculate real-time projection for custom payment order"""
    data = request.get_json()
    order_data = data.get('order', [])
    cash_balance = data.get('cash_balance', get_cash_balance())
    
    try:
        if PROCESSED_DATA_FILE.exists():
            with open(PROCESSED_DATA_FILE, 'r') as f:
                processed = json.load(f)
        else:
            processed = process_all_transactions()
        
        payables = processed.get('payables', [])
        transaction_map = {}
        
        for p in payables:
            if p.get('transaction_id'):
                transaction_map[p.get('transaction_id')] = p
            if p.get('id'):
                transaction_map[p.get('id')] = p
        
        try:
            with open(TRANSACTIONS_FILE, 'r') as f:
                all_transactions = json.load(f)
                for t in all_transactions:
                    if t.get('id'):
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
        
        order_ids = []
        for item in order_data:
            if isinstance(item, dict):
                tid = item.get('transaction_id') or item.get('id')
                if tid:
                    order_ids.append(tid)
            elif isinstance(item, str):
                order_ids.append(item)
        
        remaining_cash = cash_balance
        total_penalties = 0
        obligations_fulfilled = 0
        risk_exposure = 0
        fulfilled_amount = 0
        partial_payments_used = 0
        partial_payments_saved = 0
        
        total_obligations_amount = 0
        valid_obligations = []
        
        for tid in order_ids:
            t = transaction_map.get(tid)
            if t:
                amount = t.get('amount', 0)
                total_obligations_amount += amount
                valid_obligations.append(t)
        
        payment_plan = []
        
        for idx, t in enumerate(valid_obligations):
            amount = t.get('amount', 0)
            penalty = t.get('penalty', 0)
            risk_score = t.get('risk_score', 0.5)
            party = t.get('party', t.get('counterparty_name', 'Unknown'))
            cp_type = t.get('type', t.get('counterparty_type', 'unknown'))
            
            partial = t.get('partial_payment', {})
            accepts_partial = partial.get('accepts_partial', True)
            min_pct = partial.get('minimum_pct', partial.get('minimum_partial_pct', 50))
            min_amount = partial.get('minimum_amount', amount * min_pct / 100)
            suggested_pct = partial.get('suggested_pct', min_pct)
            suggested_amount = amount * suggested_pct / 100
            
            payment_status = "unpaid"
            paid_amount = 0
            
            if remaining_cash >= amount:
                remaining_cash -= amount
                total_penalties += penalty
                obligations_fulfilled += 1
                fulfilled_amount += amount
                payment_status = "paid_full"
                paid_amount = amount
            elif accepts_partial and remaining_cash >= min_amount:
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

@app.route('/api/risk-analysis', methods=['GET'])
def risk_analysis():
    """Get enhanced risk analysis with days to zero and cash flow projection"""
    try:
        if PROCESSED_DATA_FILE.exists():
            with open(PROCESSED_DATA_FILE, 'r') as f:
                processed = json.load(f)
        else:
            processed = process_all_transactions()
        
        if not processed:
            return jsonify({"success": False, "error": "No data found"}), 404
        
        from backend.engine.risk_engine import calculate_risk
        
        risk_report = calculate_risk(processed, consider_partial=True)
        
        cash_flow_projection = []
        current_cash = processed.get('cash_balance', 0)
        payables = processed.get('payables', [])
        receivables = processed.get('receivables', [])
        
        for i in range(61):
            day = i
            date = datetime.today().date() + timedelta(days=i)
            daily_cash = current_cash
            
            for p in payables:
                due_date = p.get('due_date')
                if due_date:
                    if isinstance(due_date, str):
                        due = datetime.strptime(due_date, "%Y-%m-%d").date()
                    else:
                        due = due_date
                    if due == date:
                        daily_cash -= p.get('amount', 0)
            
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
        return jsonify({"error": str(e)}), 500

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
    print(f"🔧 Payment Strategy Analyzer: ✅ Loaded")
    print(f"🌐 Server: http://localhost:5000")
    print("="*60 + "\n")
    
    # Process existing transactions on startup
    process_all_transactions()
    
    app.run(debug=True, host='0.0.0.0', port=5000)