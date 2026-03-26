"""
Financial Data Processor
Handles cleaning, normalization, and categorization of financial obligations with partial payment support
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
    """Normalize obligation from the enhanced JSON structure with partial payment fields"""
    
    # Extract counterparty info with enhanced classification
    counterparty = o.get("counterparty", {})
    counterparty_name = counterparty.get("name", "Unknown")
    counterparty_type = counterparty.get("type", "unknown")
    classification_confidence = counterparty.get("classification_confidence", 0.0)
    
    # Get decision info
    decision = o.get("decision", {})
    
    # Get partial payment info
    partial_payment = o.get("partial_payment", {})
    
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
        "partial_payment": {
            "accepts_partial": partial_payment.get("accepts_partial", True),
            "minimum_partial_pct": partial_payment.get("minimum_partial_pct", 50.0),
            "minimum_partial_amount": partial_payment.get("minimum_partial_amount", 5000.0),
            "suggested_pct": partial_payment.get("suggested_pct", 50.0),
            "max_installments": partial_payment.get("max_installments", 1),
            "installment_days": partial_payment.get("installment_days", 15),
            "notes": partial_payment.get("notes", ""),
            "history": partial_payment.get("history", [])
        },
        "note": o.get("note", ""),
        "invoice_number": o.get("invoice_number"),
        "gstin": o.get("gstin"),
        "pan": o.get("pan")
    }


# -------------------------------
# 3. DUPLICATE REMOVAL (UPDATED)
# -------------------------------

def remove_duplicates(obligations):
    """Remove duplicate obligations based on party, amount, and due date"""
    seen = set()
    unique = []
    duplicate_count = 0

    for o in obligations:
        # Create a unique key using party, amount, and due_date
        # Handle missing fields gracefully
        party = o.get("party", "")
        amount = o.get("amount", 0)
        due_date = o.get("due_date", "")
        
        key = (party, amount, due_date)
        
        if key not in seen:
            seen.add(key)
            unique.append(o)
        else:
            duplicate_count += 1
    
    if duplicate_count > 0:
        print(f"⚠️ Removed {duplicate_count} duplicate transaction(s) based on party, amount, and due date")
    
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
                "partial_available": 0,
                "items": []
            }
        
        summary[category]["count"] += 1
        summary[category]["total_amount"] += o["amount"]
        summary[category]["total_penalty"] += o.get("penalty", 0)
        
        # Count partial payment availability
        partial = o.get("partial_payment", {})
        if partial.get("accepts_partial", False):
            summary[category]["partial_available"] += 1
        
        summary[category]["items"].append({
            "party": o["party"],
            "amount": o["amount"],
            "due_date": o["due_date"],
            "priority": o.get("priority", "medium"),
            "accepts_partial": partial.get("accepts_partial", False),
            "min_partial_pct": partial.get("minimum_partial_pct", 0)
        })
    
    return summary


def get_payment_priorities(obligations):
    """Get obligations sorted by payment priority with partial payment info"""
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
    Process ingested JSON data from the pipeline with partial payment support
    
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
        partial = o.get("partial_payment", {})
        
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
                "gstin": o.get("gstin"),
                "partial_payment": {
                    "accepts_partial": partial.get("accepts_partial", False),
                    "minimum_pct": partial.get("minimum_partial_pct", 0),
                    "minimum_amount": partial.get("minimum_partial_amount", 0),
                    "suggested_pct": partial.get("suggested_pct", 0),
                    "max_installments": partial.get("max_installments", 1),
                    "installment_days": partial.get("installment_days", 0),
                    "notes": partial.get("notes", "")
                }
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
                "days_late": o["days_late"],
                "partial_payment": {
                    "accepts_partial": partial.get("accepts_partial", False),
                    "minimum_pct": partial.get("minimum_partial_pct", 0)
                }
            })
    
    # Step 4: Calculate totals
    total_payables = sum(p["amount"] for p in payables)
    total_receivables = sum(r["amount"] for r in receivables)
    total_penalties = sum(p.get("penalty", 0) for p in payables)
    
    # Calculate partial payment statistics
    partial_available_count = sum(1 for p in payables if p.get("partial_payment", {}).get("accepts_partial", False))
    total_partial_minimum = sum(
        max(
            p.get("partial_payment", {}).get("minimum_amount", 0),
            p["amount"] * p.get("partial_payment", {}).get("minimum_pct", 50) / 100
        )
        for p in payables if p.get("partial_payment", {}).get("accepts_partial", False)
    )
    
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
        "partial_payment_summary": {
            "partial_available_count": partial_available_count,
            "total_partial_minimum": total_partial_minimum,
            "partial_percentage": (partial_available_count / len(payables) * 100) if payables else 0
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
    """Print a formatted financial summary with partial payment info"""
    
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
    
    # Partial payment summary
    partial_summary = result.get('partial_payment_summary', {})
    if partial_summary:
        print(f"\n💳 Partial Payment Availability:")
        print(f"   - Accept Partial Payments: {partial_summary['partial_available_count']} obligations")
        print(f"   - Total Minimum Partial Amount: ₹{partial_summary['total_partial_minimum']:,.2f}")
        print(f"   - Percentage: {partial_summary['partial_percentage']:.1f}% of payables")
    
    print("\n📂 Category Breakdown:")
    for category, stats in result['category_summary'].items():
        partial_info = f" (Partial: {stats.get('partial_available', 0)}/{stats['count']})" if stats.get('partial_available') else ""
        print(f"   • {category.upper()}: {stats['count']} items, ₹{stats['total_amount']:,.2f}{partial_info}")
    
    print("\n🔥 Top Priority Payments:")
    for i, p in enumerate(result['priority_payables'][:5], 1):
        partial_indicator = " [Partial OK]" if p.get("partial_payment", {}).get("accepts_partial") else ""
        print(f"   {i}. {p['party']} - ₹{p['amount']:,.2f} (Priority: {p['priority']}, Days Late: {p['days_late']}){partial_indicator}")
        
        # Show partial payment details if available
        if p.get("partial_payment", {}).get("accepts_partial"):
            min_pct = p["partial_payment"].get("minimum_pct", 0)
            min_amount = p["partial_payment"].get("minimum_amount", 0)
            suggested_pct = p["partial_payment"].get("suggested_pct", min_pct)
            print(f"      → Partial available: min {min_pct}% (₹{min_amount:,.2f}), suggested {suggested_pct}%")
    
    print("\n" + "="*60)


# -------------------------------
# 9. PARTIAL PAYMENT FUNCTIONS
# -------------------------------

def filter_by_partial_availability(payables, only_available=True):
    """Filter payables by partial payment availability"""
    if only_available:
        return [p for p in payables if p.get("partial_payment", {}).get("accepts_partial", False)]
    else:
        return [p for p in payables if not p.get("partial_payment", {}).get("accepts_partial", False)]


def get_partial_payment_options(payable):
    """Get partial payment options for a specific payable"""
    partial = payable.get("partial_payment", {})
    if not partial.get("accepts_partial", False):
        return None
    
    amount = payable["amount"]
    min_pct = partial.get("minimum_pct", 50)
    min_amount = partial.get("minimum_amount", amount * min_pct / 100)
    suggested_pct = partial.get("suggested_pct", min_pct)
    
    return {
        "party": payable["party"],
        "amount": amount,
        "minimum_payment": max(min_amount, amount * min_pct / 100),
        "minimum_percentage": min_pct,
        "suggested_payment": amount * suggested_pct / 100,
        "suggested_percentage": suggested_pct,
        "max_installments": partial.get("max_installments", 1),
        "installment_days": partial.get("installment_days", 15),
        "notes": partial.get("notes", "")
    }


def get_partial_payment_summary(payables):
    """
    Get a comprehensive summary of partial payment availability
    
    Args:
        payables: List of payable obligations
    
    Returns:
        Dictionary with detailed partial payment summary
    """
    summary = {
        "total_obligations": len(payables),
        "accept_partial": 0,
        "reject_partial": 0,
        "by_type": {},
        "total_minimum_partial": 0,
        "total_suggested_partial": 0,
        "obligations_with_partial": []
    }
    
    for p in payables:
        partial = p.get("partial_payment", {})
        accepts = partial.get("accepts_partial", False)
        cp_type = p.get("type", "unknown")
        
        if accepts:
            summary["accept_partial"] += 1
            min_payment = max(
                partial.get("minimum_amount", 0),
                p["amount"] * partial.get("minimum_pct", 50) / 100
            )
            suggested_payment = p["amount"] * partial.get("suggested_pct", 50) / 100
            
            summary["total_minimum_partial"] += min_payment
            summary["total_suggested_partial"] += suggested_payment
            
            summary["obligations_with_partial"].append({
                "party": p["party"],
                "amount": p["amount"],
                "minimum_pct": partial.get("minimum_pct", 0),
                "minimum_amount": min_payment,
                "suggested_pct": partial.get("suggested_pct", 0),
                "suggested_amount": suggested_payment,
                "max_installments": partial.get("max_installments", 1),
                "installment_days": partial.get("installment_days", 15),
                "notes": partial.get("notes", "")
            })
        else:
            summary["reject_partial"] += 1
        
        # Track by type
        if cp_type not in summary["by_type"]:
            summary["by_type"][cp_type] = {"total": 0, "accept": 0, "reject": 0}
        summary["by_type"][cp_type]["total"] += 1
        if accepts:
            summary["by_type"][cp_type]["accept"] += 1
        else:
            summary["by_type"][cp_type]["reject"] += 1
    
    # Calculate percentages
    if summary["total_obligations"] > 0:
        summary["accept_percentage"] = (summary["accept_partial"] / summary["total_obligations"]) * 100
        summary["reject_percentage"] = (summary["reject_partial"] / summary["total_obligations"]) * 100
    
    return summary

# -------------------------------
# 10. CASH FLOW FUNCTIONS
# -------------------------------

def create_cash_flow_dataframe(processed_data):
    """
    Create a detailed DataFrame of cash flow events
    
    Args:
        processed_data: Processed financial data from process_ingested_data
    
    Returns:
        DataFrame with cash flow timeline
    """
    import pandas as pd
    from datetime import datetime, timedelta
    
    cash_balance = processed_data["cash_balance"]
    payables = processed_data["payables"]
    receivables = processed_data["receivables"]
    
    # Create events list
    events = []
    
    # Initial cash balance
    events.append({
        'date': datetime.today().date(),
        'type': 'starting_balance',
        'party': 'Opening Balance',
        'amount': cash_balance,
        'running_balance': cash_balance,
        'description': f'Initial Cash Balance'
    })
    
    # Add all payables
    for p in payables:
        due_date = p.get("due_date")
        if due_date:
            if isinstance(due_date, str):
                due = datetime.strptime(due_date, "%Y-%m-%d").date()
            else:
                due = due_date
            
            events.append({
                'date': due,
                'type': 'payable',
                'party': p['party'],
                'amount': -p['amount'],
                'running_balance': None,
                'description': f"Payment to {p['party']} - ₹{p['amount']:,.2f}"
            })
    
    # Add all receivables
    for r in receivables:
        expected_date = r.get("expected_date")
        if expected_date:
            if isinstance(expected_date, str):
                expected = datetime.strptime(expected_date, "%Y-%m-%d").date()
            else:
                expected = expected_date
            
            events.append({
                'date': expected,
                'type': 'receivable',
                'party': r['party'],
                'amount': r['amount'],
                'running_balance': None,
                'description': f"Receipt from {r['party']} - ₹{r['amount']:,.2f}"
            })
    
    # Sort by date
    events.sort(key=lambda x: x['date'])
    
    # Calculate running balance
    running = cash_balance
    for event in events:
        if event['type'] != 'starting_balance':
            running += event['amount']
            event['running_balance'] = running
    
    # Convert to DataFrame
    df = pd.DataFrame(events)
    
    # Add day of week
    df['day_of_week'] = df['date'].apply(lambda x: x.strftime('%A'))
    
    return df


def create_cash_flow_graph(processed_data, risk_report=None):
    """
    Create a cash flow graph showing how money is deducted and increased
    
    Args:
        processed_data: Processed financial data
        risk_report: Optional risk report for annotations
    
    Returns:
        matplotlib figure
    """
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    import numpy as np
    from datetime import datetime, timedelta
    
    cash_balance = processed_data["cash_balance"]
    payables = processed_data["payables"]
    receivables = processed_data["receivables"]
    
    # Create timeline
    today = datetime.today().date()
    days_to_project = 90
    
    # Create date range
    dates = [today + timedelta(days=i) for i in range(days_to_project)]
    
    # Initialize cash balance array
    cash_flow = [cash_balance]
    
    # Create events list for annotations
    events = []
    
    # Track cash flow day by day
    for i in range(1, days_to_project):
        current_date = dates[i]
        previous_balance = cash_flow[-1]
        daily_change = 0
        
        # Add incoming cash from receivables
        for r in receivables:
            expected_date = r.get("expected_date")
            if expected_date:
                if isinstance(expected_date, str):
                    expected = datetime.strptime(expected_date, "%Y-%m-%d").date()
                else:
                    expected = expected_date
                
                if expected == current_date:
                    daily_change += r["amount"]
                    events.append({
                        "date": current_date,
                        "type": "receivable",
                        "amount": r["amount"],
                        "party": r["party"]
                    })
        
        # Subtract payables
        for p in payables:
            due_date = p.get("due_date")
            if due_date:
                if isinstance(due_date, str):
                    due = datetime.strptime(due_date, "%Y-%m-%d").date()
                else:
                    due = due_date
                
                if due == current_date:
                    daily_change -= p["amount"]
                    events.append({
                        "date": current_date,
                        "type": "payable",
                        "amount": p["amount"],
                        "party": p["party"]
                    })
        
        new_balance = previous_balance + daily_change
        cash_flow.append(new_balance)
    
    # Create the graph
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
    fig.suptitle('Cash Flow Analysis', fontsize=16, fontweight='bold')
    
    # Graph 1: Cash Flow Over Time
    ax1.plot(dates, cash_flow, 'b-', linewidth=2, label='Cash Balance')
    ax1.axhline(y=0, color='r', linestyle='--', linewidth=1, label='Zero Cash Line')
    
    # Add events as markers
    for event in events:
        if event["date"] in dates:
            idx = dates.index(event["date"])
            color = 'green' if event["type"] == "receivable" else 'red'
            marker = '^' if event["type"] == "receivable" else 'v'
            ax1.plot(event["date"], cash_flow[idx], marker, color=color, 
                    markersize=10, markeredgewidth=2)
            
            # Add annotation
            annotation = f"{event['party']}\n₹{event['amount']:,.0f}"
            ax1.annotate(annotation, 
                        xy=(event["date"], cash_flow[idx]),
                        xytext=(10, 10), textcoords='offset points',
                        fontsize=8, alpha=0.7,
                        bbox=dict(boxstyle="round,pad=0.3", facecolor=color, alpha=0.2))
    
    # Formatting
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Cash Balance (₹)')
    ax1.set_title('Cash Flow Projection')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    # Graph 2: Cash Flow Waterfall (Weekly)
    weekly_data = []
    for i in range(0, len(dates), 7):
        week_dates = dates[i:min(i+7, len(dates))]
        week_cash = cash_flow[i:min(i+7, len(cash_flow))]
        weekly_data.append({
            'week_start': week_dates[0],
            'end_balance': week_cash[-1] if week_cash else cash_flow[i]
        })
    
    weeks = [w['week_start'] for w in weekly_data]
    balances = [w['end_balance'] for w in weekly_data]
    
    colors = ['green' if b > 0 else 'red' for b in balances]
    ax2.bar(weeks, balances, color=colors, alpha=0.7, edgecolor='black')
    ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    
    ax2.set_xlabel('Week')
    ax2.set_ylabel('Cash Balance (₹)')
    ax2.set_title('Weekly Cash Position')
    ax2.grid(True, alpha=0.3, axis='y')
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    # Add zero cash line annotation
    if min(cash_flow) < 0:
        for i, balance in enumerate(cash_flow):
            if balance < 0:
                zero_date = dates[i]
                ax1.axvline(x=zero_date, color='orange', linestyle=':', 
                           linewidth=2, alpha=0.7, label='Cash Depletion Date')
                ax1.annotate(f'Cash Depletion\n{zero_date.strftime("%Y-%m-%d")}',
                           xy=(zero_date, 0), xytext=(10, 20),
                           textcoords='offset points', fontsize=9,
                           bbox=dict(boxstyle="round,pad=0.3", facecolor='orange', alpha=0.3))
                break
    
    plt.tight_layout()
    return fig


def create_cash_flow_analysis(processed_data, risk_report=None):
    """
    Create comprehensive cash flow analysis with graph and table
    
    Args:
        processed_data: Processed financial data
        risk_report: Optional risk report
    
    Returns:
        Dictionary with cash flow analysis results
    """
    from datetime import datetime
    
    # Create DataFrame
    df = create_cash_flow_dataframe(processed_data)
    
    # Create and show graph
    fig = create_cash_flow_graph(processed_data, risk_report)
    
    # Return statistics
    today = datetime.today().date()
    future_events = df[df['date'] > today]
    
    upcoming_payments = future_events[future_events['type'] == 'payable']['amount'].sum()
    upcoming_receipts = future_events[future_events['type'] == 'receivable']['amount'].sum()
    
    # Find days to zero
    days_to_zero = None
    for _, row in df.iterrows():
        if row['running_balance'] < 0:
            days_to_zero = (row['date'] - today).days
            break
    
    return {
        'df': df,
        'fig': fig,
        'upcoming_payments': -upcoming_payments,
        'upcoming_receipts': upcoming_receipts,
        'net_future_cashflow': upcoming_receipts + upcoming_payments,
        'days_to_zero': days_to_zero,
        'lowest_cash': df['running_balance'].min(),
        'highest_cash': df['running_balance'].max()
    }


def print_cash_flow_table(df):
    """
    Print a formatted cash flow table
    
    Args:
        df: DataFrame from create_cash_flow_dataframe
    """
    from datetime import datetime
    
    print("\n" + "="*100)
    print("CASH FLOW SCHEDULE")
    print("="*100)
    
    # Separate into future and past
    today = datetime.today().date()
    future_events = df[df['date'] >= today].copy()
    past_events = df[df['date'] < today].copy()
    
    if not past_events.empty:
        print("\n📜 PAST TRANSACTIONS:")
        print("-"*100)
        for _, row in past_events.iterrows():
            if row['type'] != 'starting_balance':
                arrow = "↓" if row['amount'] < 0 else "↑"
                color = "🔴" if row['amount'] < 0 else "🟢"
                print(f"   {row['date']} ({row['day_of_week']}) | {color} {arrow} {row['party']:<30} | "
                      f"₹{row['amount']:>12,.2f} | Balance: ₹{row['running_balance']:>12,.2f}")
    
    if not future_events.empty:
        print("\n📅 FUTURE TRANSACTIONS:")
        print("-"*100)
        for _, row in future_events.iterrows():
            if row['type'] != 'starting_balance':
                arrow = "↓" if row['amount'] < 0 else "↑"
                color = "🔴" if row['amount'] < 0 else "🟢"
                days_until = (row['date'] - today).days
                print(f"   {row['date']} ({row['day_of_week']}) | {color} {arrow} {row['party']:<30} | "
                      f"₹{row['amount']:>12,.2f} | Balance: ₹{row['running_balance']:>12,.2f} "
                      f"| Days: {days_until}")
    
    print("\n" + "="*100)


def print_partial_payment_summary(summary):
    """
    Print a formatted partial payment summary
    
    Args:
        summary: Summary from get_partial_payment_summary()
    """
    print("\n" + "="*60)
    print("PARTIAL PAYMENT AVAILABILITY SUMMARY")
    print("="*60)
    
    print(f"\n📊 Overall Statistics:")
    print(f"   Total Obligations: {summary['total_obligations']}")
    print(f"   Accept Partial: {summary['accept_partial']} ({summary['accept_percentage']:.1f}%)")
    print(f"   Reject Partial: {summary['reject_partial']} ({summary['reject_percentage']:.1f}%)")
    print(f"   Total Minimum Partial Required: ₹{summary['total_minimum_partial']:,.2f}")
    print(f"   Total Suggested Partial Payment: ₹{summary['total_suggested_partial']:,.2f}")
    
    print("\n📂 By Counterparty Type:")
    for cp_type, stats in summary['by_type'].items():
        accept_pct = (stats['accept'] / stats['total'] * 100) if stats['total'] > 0 else 0
        print(f"   • {cp_type.upper()}: {stats['accept']}/{stats['total']} accept partial ({accept_pct:.1f}%)")
    
    if summary['obligations_with_partial']:
        print("\n💳 Obligations Accepting Partial Payments:")
        for ob in summary['obligations_with_partial'][:5]:  # Show top 5
            print(f"\n   • {ob['party']}: ₹{ob['amount']:,.2f}")
            print(f"     Minimum: {ob['minimum_pct']}% (₹{ob['minimum_amount']:,.2f})")
            print(f"     Suggested: {ob['suggested_pct']}% (₹{ob['suggested_amount']:,.2f})")
            if ob['max_installments'] > 1:
                print(f"     Installments: {ob['max_installments']} x every {ob['installment_days']} days")
            if ob['notes']:
                print(f"     Notes: {ob['notes']}")
    
    print("\n" + "="*60)