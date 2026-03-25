"""
Financial Data Processor
Handles cleaning, normalization, and categorization of financial obligations
"""

from datetime import datetime
import re
from typing import List, Dict, Any

# -------------------------------
# 1. CLEANING FUNCTIONS
# -------------------------------

def clean_name(name):
    if not name:
        return "Unknown"

    # Remove extra spaces, newlines, junk OCR text
    name = re.sub(r'\s+', ' ', name)
    name = name.strip()

    # Remove weird OCR artifacts but keep alphanumeric, spaces, dots, and ampersands
    name = re.sub(r'[^a-zA-Z0-9 &.]', '', name)
    
    # Remove any leftover multiple spaces
    name = re.sub(r'\s+', ' ', name)
    
    # Truncate if too long
    if len(name) > 100:
        name = name[:100]
    
    return name


def clean_amount(amount):
    try:
        return float(amount)
    except:
        return 0.0


def clean_date(date_str):
    if not date_str:
        return None
    
    try:
        # Handle string dates
        if isinstance(date_str, str):
            # Try different date formats
            formats = ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y-%m-%d %H:%M:%S']
            for fmt in formats:
                try:
                    return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
                except:
                    continue
        # Handle datetime objects
        elif isinstance(date_str, datetime):
            return date_str.strftime("%Y-%m-%d")
        elif hasattr(date_str, 'strftime'):
            return date_str.strftime("%Y-%m-%d")
    except:
        pass
    
    return None


# -------------------------------
# 2. NORMALIZATION
# -------------------------------

def normalize_obligation(o):
    """Normalize obligation from the enhanced JSON structure"""
    
    # Extract counterparty info with enhanced classification
    counterparty = o.get("counterparty", {})
    counterparty_name = counterparty.get("name", "Unknown")
    counterparty_type = counterparty.get("type", "unknown")
    classification_confidence = counterparty.get("classification_confidence", 0.0)
    
    # Get decision info
    decision = o.get("decision", {})
    
    return {
        "transaction_id": o.get("transaction_id"),
        "party": clean_name(counterparty_name),
        "type": counterparty_type,  # vendor, customer, tax_authority, government, etc.
        "classification_confidence": classification_confidence,
        "amount": clean_amount(o.get("amount", 0)),
        "due_date": clean_date(o.get("due_date")),
        "payment_date": clean_date(o.get("payment_date")),
        "days_late": o.get("days_late", 0),
        "risk_score": o.get("risk_score", 0),
        "penalty": o.get("penalty", {}).get("total", 0),
        "penalty_details": o.get("penalty", {}),  # Store full penalty details
        "decision": {
            "priority": decision.get("priority", "low"),
            "action": decision.get("action", "review"),
            "reason": decision.get("reason", ""),
            "suggested_terms": decision.get("suggested_terms", {})
        },
        "note": o.get("note", ""),
        "invoice_number": o.get("invoice_number"),
        "gstin": o.get("gstin"),
        "pan": o.get("pan")
    }


# -------------------------------
# 3. DUPLICATE REMOVAL
# -------------------------------

def remove_duplicates(obligations):
    """Remove duplicate obligations based on party, amount, and due date"""
    seen = set()
    unique = []

    for o in obligations:
        # Create a unique key
        key = (o["party"], o["amount"], o["due_date"])
        
        if key not in seen:
            seen.add(key)
            unique.append(o)

    return unique


# -------------------------------
# 4. SMART CATEGORIZATION
# -------------------------------

def categorize(o):
    """
    Enhances classification beyond vendor/customer using the intelligent classification
    """
    
    # Use the classification from the system
    classification_type = o.get("type", "unknown")
    name = o["party"].lower()
    
    # Priority mapping based on classification
    priority_map = {
        'tax_authority': 'critical',
        'government': 'critical',
        'bank': 'high',
        'vendor': 'high',
        'employee': 'high',
        'utility': 'high',
        'rent': 'medium',
        'insurance': 'medium',
        'customer': 'medium',
        'investment': 'low',
        'friend': 'low',
        'family': 'low',
        'charity': 'low',
        'unknown': 'medium'
    }
    
    # Map to category for backward compatibility
    if classification_type in ['tax_authority', 'government']:
        o["category"] = "tax"
    elif classification_type == 'bank':
        o["category"] = "financial"
    elif classification_type == 'employee':
        o["category"] = "salary"
    elif classification_type == 'utility':
        o["category"] = "utility"
    elif classification_type == 'rent':
        o["category"] = "rent"
    elif classification_type == 'vendor':
        o["category"] = "supplier"
    elif classification_type == 'customer':
        o["category"] = "income"
    elif classification_type in ['friend', 'family']:
        o["category"] = "personal"
    elif classification_type == 'charity':
        o["category"] = "donation"
    else:
        # Fallback to keyword matching
        if "rent" in name:
            o["category"] = "rent"
        elif "salary" in name or "wage" in name:
            o["category"] = "salary"
        elif "tax" in name or "gst" in name or "income tax" in name:
            o["category"] = "tax"
        elif "electricity" in name or "water" in name or "gas" in name:
            o["category"] = "utility"
        elif "bank" in name or "loan" in name or "emi" in name:
            o["category"] = "financial"
        else:
            o["category"] = "other"
    
    # Add priority
    o["priority"] = priority_map.get(classification_type, 'medium')
    
    # Add urgency score (higher = more urgent)
    days_late = o.get("days_late", 0)
    if days_late > 30:
        o["urgency"] = "critical"
    elif days_late > 15:
        o["urgency"] = "high"
    elif days_late > 7:
        o["urgency"] = "medium"
    elif days_late > 0:
        o["urgency"] = "low"
    else:
        o["urgency"] = "none"
    
    return o


# -------------------------------
# 5. AGGREGATION FUNCTIONS
# -------------------------------

def aggregate_by_category(obligations):
    """Aggregate obligations by category"""
    summary = {}
    
    for o in obligations:
        category = o.get("category", "other")
        if category not in summary:
            summary[category] = {
                "count": 0,
                "total_amount": 0,
                "total_penalty": 0,
                "items": []
            }
        
        summary[category]["count"] += 1
        summary[category]["total_amount"] += o["amount"]
        summary[category]["total_penalty"] += o.get("penalty", 0)
        summary[category]["items"].append({
            "party": o["party"],
            "amount": o["amount"],
            "due_date": o["due_date"],
            "priority": o.get("priority", "medium")
        })
    
    return summary


def get_payment_priorities(obligations):
    """Get obligations sorted by payment priority"""
    # Sort by priority (critical > high > medium > low)
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    
    sorted_obligations = sorted(
        obligations,
        key=lambda x: (priority_order.get(x.get("priority", "medium"), 2), -x["days_late"])
    )
    
    return sorted_obligations


# -------------------------------
# 6. MAIN PROCESS FUNCTION
# -------------------------------

def process_ingested_data(data, initial_balance=0, include_paid=False):
    """
    Process ingested JSON data from the pipeline
    
    Args:
        data: The JSON output from ingestion pipeline
        initial_balance: Starting cash balance
        include_paid: Whether to include already paid obligations
    
    Returns:
        Processed financial state
    """
    
    all_obligations = []
    processing_stats = {
        "total_files_processed": 0,
        "total_obligations_raw": 0,
        "paid_obligations_skipped": 0,
        "duplicates_removed": 0
    }
    
    # Collect all obligations from all files
    if isinstance(data, dict) and "successful" in data:
        # New format from batch processing
        files = data["successful"]
        processing_stats["total_files_processed"] = len(files)
    elif isinstance(data, list):
        # Old format - direct array
        files = data
        processing_stats["total_files_processed"] = len(files)
    else:
        # Single file result
        files = [data]
        processing_stats["total_files_processed"] = 1
    
    for file_data in files:
        # Handle different JSON structures
        if "financial_state" in file_data:
            obligations = file_data["financial_state"].get("obligations", [])
        elif "obligations" in file_data:
            obligations = file_data.get("obligations", [])
        else:
            continue
        
        processing_stats["total_obligations_raw"] += len(obligations)
        
        for o in obligations:
            # Skip already paid if not included
            if not include_paid and o.get("payment_date") is not None:
                processing_stats["paid_obligations_skipped"] += 1
                continue
            
            normalized = normalize_obligation(o)
            all_obligations.append(normalized)
    
    # Step 1: Remove duplicates
    original_count = len(all_obligations)
    unique_obligations = remove_duplicates(all_obligations)
    processing_stats["duplicates_removed"] = original_count - len(unique_obligations)
    
    # Step 2: Categorize
    categorized = [categorize(o) for o in unique_obligations]
    
    # Step 3: Split payables & receivables based on type
    payables = []
    receivables = []
    
    for o in categorized:
        # Map type to payables/receivables
        if o["type"] in ["vendor", "tax_authority", "government", "bank", "employee", 
                         "utility", "rent", "insurance", "investment", "charity"]:
            payables.append({
                "transaction_id": o["transaction_id"],
                "party": o["party"],
                "amount": o["amount"],
                "due_date": o["due_date"],
                "category": o["category"],
                "type": o["type"],
                "risk_score": o["risk_score"],
                "penalty": o["penalty"],
                "priority": o["priority"],
                "urgency": o["urgency"],
                "decision": o["decision"],
                "days_late": o["days_late"],
                "invoice_number": o.get("invoice_number"),
                "gstin": o.get("gstin")
            })
        elif o["type"] in ["customer", "client"]:
            receivables.append({
                "transaction_id": o["transaction_id"],
                "party": o["party"],
                "amount": o["amount"],
                "expected_date": o["due_date"],
                "category": o["category"],
                "type": o["type"],
                "risk_score": o["risk_score"],
                "priority": o["priority"]
            })
        else:
            # Default to payable for unknown types
            payables.append({
                "transaction_id": o["transaction_id"],
                "party": o["party"],
                "amount": o["amount"],
                "due_date": o["due_date"],
                "category": o["category"],
                "type": "unknown",
                "risk_score": o["risk_score"],
                "penalty": o["penalty"],
                "priority": o["priority"],
                "days_late": o["days_late"]
            })
    
    # Step 4: Calculate totals
    total_payables = sum(p["amount"] for p in payables)
    total_receivables = sum(r["amount"] for r in receivables)
    total_penalties = sum(p.get("penalty", 0) for p in payables)
    
    # Step 5: Get payment priorities
    priority_payables = get_payment_priorities(payables)
    
    # Step 6: Aggregate by category
    category_summary = aggregate_by_category(payables)
    
    # Step 7: Calculate cash position
    net_cash_position = initial_balance + total_receivables - total_payables - total_penalties
    
    # Prepare final result
    result = {
        "cash_balance": initial_balance,
        "payables": payables,
        "receivables": receivables,
        "summary": {
            "total_payables": total_payables,
            "total_receivables": total_receivables,
            "total_penalties": total_penalties,
            "net_position": net_cash_position,
            "payables_count": len(payables),
            "receivables_count": len(receivables),
            "total_obligations": len(categorized)
        },
        "category_summary": category_summary,
        "priority_payables": priority_payables[:10],  # Top 10 priority payments
        "processing_stats": processing_stats
    }
    
    return result


# -------------------------------
# 7. USAGE EXAMPLE
# -------------------------------

def process_json_file(json_file_path, initial_balance=0):
    """Process a JSON file from the ingestion pipeline"""
    import json
    
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return process_ingested_data(data, initial_balance)


# -------------------------------
# 8. PRINT SUMMARY FUNCTION
# -------------------------------

def print_financial_summary(result):
    """Print a formatted financial summary"""
    
    print("\n" + "="*60)
    print("FINANCIAL SUMMARY")
    print("="*60)
    
    print(f"\n💰 Cash Balance: ₹{result['cash_balance']:,.2f}")
    print(f"📤 Total Payables: ₹{result['summary']['total_payables']:,.2f}")
    print(f"📥 Total Receivables: ₹{result['summary']['total_receivables']:,.2f}")
    print(f"⚠️ Total Penalties: ₹{result['summary']['total_penalties']:,.2f}")
    print(f"📊 Net Position: ₹{result['summary']['net_position']:,.2f}")
    
    print(f"\n📋 Obligations: {result['summary']['total_obligations']} total")
    print(f"   - Payables: {result['summary']['payables_count']}")
    print(f"   - Receivables: {result['summary']['receivables_count']}")
    
    print("\n📂 Category Breakdown:")
    for category, stats in result['category_summary'].items():
        print(f"   • {category.upper()}: {stats['count']} items, ₹{stats['total_amount']:,.2f}")
    
    print("\n🔥 Top Priority Payments:")
    for i, p in enumerate(result['priority_payables'][:5], 1):
        print(f"   {i}. {p['party']} - ₹{p['amount']:,.2f} (Priority: {p['priority']}, Days Late: {p['days_late']})")
    
    print("\n" + "="*60)