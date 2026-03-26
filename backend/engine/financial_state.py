"""
Financial state calculations and helper functions with partial payment support
"""

from typing import List, Dict, Any, Optional
from datetime import date, timedelta
import logging

logger = logging.getLogger(__name__)

def detect_shortfall(cash_balance: float, payables: List[Dict[str, Any]], 
                     consider_partial: bool = False) -> Dict[str, Any]:
    """
    Detect cash shortfall compared to payables with partial payment consideration
    
    Args:
        cash_balance: Current cash balance
        payables: List of payable obligations
        consider_partial: Whether to consider partial payment options
    
    Returns:
        Dictionary with shortfall details
    """
    total_payables = sum(p.get('amount', 0) for p in payables)
    shortfall = cash_balance - total_payables
    
    result = {
        "total_payables": total_payables,
        "shortfall": shortfall,
        "has_shortfall": shortfall < 0,
        "shortfall_amount": abs(shortfall) if shortfall < 0 else 0
    }
    
    # Consider partial payments if requested
    if consider_partial and shortfall < 0:
        # Calculate minimum payments if all accept partial
        partial_min_total = 0
        partial_available_count = 0
        
        for p in payables:
            partial = p.get('partial_payment', {})
            if partial.get('accepts_partial', False):
                partial_available_count += 1
                min_payment = max(
                    partial.get('minimum_partial_amount', 0),
                    p['amount'] * partial.get('minimum_partial_pct', 50) / 100
                )
                partial_min_total += min_payment
            else:
                partial_min_total += p['amount']
        
        result["partial_consideration"] = {
            "partial_available_count": partial_available_count,
            "minimum_cash_needed_with_partial": partial_min_total,
            "partial_shortfall": cash_balance - partial_min_total,
            "can_cover_with_partial": cash_balance >= partial_min_total
        }
    
    return result

def compute_days_to_zero(cash_balance: float, payables: List[Dict[str, Any]], 
                         daily_burn_rate: float = None, 
                         consider_partial: bool = False) -> Dict[str, Any]:
    """
    Compute days until cash reaches zero based on payables with partial payment options
    
    Args:
        cash_balance: Current cash balance
        payables: List of payable obligations
        daily_burn_rate: Optional daily burn rate
        consider_partial: Whether to consider partial payments
    
    Returns:
        Dictionary with days to zero calculation
    """
    if cash_balance <= 0:
        return {"days_to_zero": 0, "status": "already_negative"}
    
    result = {}
    
    # Standard calculation (without partial)
    if daily_burn_rate is None and payables:
        total_amount = sum(p.get('amount', 0) for p in payables)
        if payables:
            sorted_payables = sorted(payables, key=lambda x: x.get('due_date', date.today()))
            
            if sorted_payables:
                first_date = sorted_payables[0].get('due_date', date.today())
                last_date = sorted_payables[-1].get('due_date', date.today())
                days_span = (last_date - first_date).days
                if days_span > 0:
                    daily_burn_rate = total_amount / days_span
                else:
                    daily_burn_rate = total_amount / 30
    
    if daily_burn_rate and daily_burn_rate > 0:
        days = int(cash_balance / daily_burn_rate)
        result["standard_days_to_zero"] = max(0, days)
    else:
        result["standard_days_to_zero"] = 30
    
    # Consider partial payments
    if consider_partial and payables:
        # Calculate weighted burn rate with partial payments
        weighted_total = 0
        for p in payables:
            partial = p.get('partial_payment', {})
            if partial.get('accepts_partial', False):
                # If accepts partial, use minimum payment instead of full
                min_payment = max(
                    partial.get('minimum_partial_amount', 0),
                    p['amount'] * partial.get('minimum_partial_pct', 50) / 100
                )
                weighted_total += min_payment
            else:
                weighted_total += p['amount']
        
        # Calculate new burn rate with partial
        sorted_payables = sorted(payables, key=lambda x: x.get('due_date', date.today()))
        if sorted_payables:
            first_date = sorted_payables[0].get('due_date', date.today())
            last_date = sorted_payables[-1].get('due_date', date.today())
            days_span = (last_date - first_date).days
            if days_span > 0:
                partial_burn_rate = weighted_total / days_span
            else:
                partial_burn_rate = weighted_total / 30
            
            if partial_burn_rate > 0:
                partial_days = int(cash_balance / partial_burn_rate)
                result["partial_days_to_zero"] = max(0, partial_days)
                result["improvement_days"] = result["partial_days_to_zero"] - result["standard_days_to_zero"]
    
    return result

def calculate_net_worth(cash_balance: float, payables: List[Dict], 
                        receivables: List[Dict]) -> float:
    """
    Calculate net worth based on cash, payables and receivables
    
    Args:
        cash_balance: Current cash balance
        payables: List of payable obligations
        receivables: List of receivable obligations
    
    Returns:
        Net worth
    """
    total_payables = sum(p.get('amount', 0) for p in payables)
    total_receivables = sum(r.get('amount', 0) for r in receivables)
    
    net_worth = cash_balance + total_receivables - total_payables
    return net_worth

def calculate_liquidity_ratio(cash_balance: float, payables: List[Dict]) -> float:
    """
    Calculate liquidity ratio (cash / total payables)
    
    Args:
        cash_balance: Current cash balance
        payables: List of payable obligations
    
    Returns:
        Liquidity ratio (1.0 = sufficient, <1.0 = shortfall)
    """
    total_payables = sum(p.get('amount', 0) for p in payables)
    
    if total_payables == 0:
        return float('inf')
    
    return cash_balance / total_payables

def get_payment_priority(obligation: Dict[str, Any]) -> int:
    """
    Determine payment priority based on counterparty type and days late
    
    Args:
        obligation: Obligation dictionary
    
    Returns:
        Priority score (higher = more urgent)
    """
    cp_type = obligation.get('counterparty', {}).get('type', 'unknown')
    days_late = obligation.get('days_late', 0)
    
    # Base priority by type
    priority_map = {
        'tax_authority': 100,
        'government': 90,
        'bank': 85,
        'employee': 80,
        'vendor': 75,
        'utility': 70,
        'rent': 65,
        'insurance': 60,
        'customer': 50,
        'investment': 45,
        'friend': 30,
        'family': 25,
        'charity': 20,
        'unknown': 40
    }
    
    base_priority = priority_map.get(cp_type, 40)
    
    # Add urgency based on days late
    urgency_bonus = min(days_late, 30)  # Cap at 30 days
    
    return base_priority + urgency_bonus

def calculate_average_payment_amount(payables: List[Dict]) -> float:
    """Calculate average payment amount"""
    if not payables:
        return 0.0
    
    total = sum(p.get('amount', 0) for p in payables)
    return total / len(payables)

def get_upcoming_payments(payables: List[Dict], days: int = 7) -> List[Dict]:
    """Get payments due in the next N days"""
    today = date.today()
    cutoff = today + timedelta(days=days)
    
    upcoming = []
    for p in payables:
        due_date = p.get('due_date')
        if due_date and isinstance(due_date, date):
            if today <= due_date <= cutoff:
                upcoming.append(p)
    
    return upcoming

def calculate_partial_payment_strategy(cash_balance: float, 
                                       payables: List[Dict]) -> Dict[str, Any]:
    """
    Calculate optimal partial payment strategy
    
    Args:
        cash_balance: Current cash balance
        payables: List of payable obligations with partial payment info
    
    Returns:
        Strategy dictionary with recommendations
    """
    # Separate obligations by partial payment availability
    partial_available = []
    partial_unavailable = []
    
    for p in payables:
        partial = p.get('partial_payment', {})
        if partial.get('accepts_partial', False):
            partial_available.append(p)
        else:
            partial_unavailable.append(p)
    
    # Calculate minimum required for non-partial
    non_partial_total = sum(p['amount'] for p in partial_unavailable)
    
    # Calculate what we can do with partial payments
    strategy = {
        "non_partial_total": non_partial_total,
        "partial_available_count": len(partial_available),
        "partial_available_total": sum(p['amount'] for p in partial_available),
        "minimum_cash_needed": non_partial_total,
        "recommendations": []
    }
    
    # If we can't cover non-partial obligations
    if cash_balance < non_partial_total:
        strategy["recommendations"].append({
            "type": "critical_shortfall",
            "message": f"Insufficient funds for mandatory payments (need ₹{non_partial_total:,.2f})",
            "shortfall": non_partial_total - cash_balance,
            "action": "prioritize_critical_payments"
        })
    else:
        remaining = cash_balance - non_partial_total
        
        # Suggest partial payment strategy
        for p in sorted(partial_available, key=lambda x: x.get('days_late', 0), reverse=True):
            partial = p.get('partial_payment', {})
            min_payment = max(
                partial.get('minimum_partial_amount', 0),
                p['amount'] * partial.get('minimum_partial_pct', 50) / 100
            )
            
            if remaining >= p['amount']:
                # Can pay in full
                strategy["recommendations"].append({
                    "party": p['party'],
                    "action": "pay_full",
                    "amount": p['amount'],
                    "reason": "Sufficient funds available"
                })
                remaining -= p['amount']
            elif remaining >= min_payment:
                # Can pay partial
                suggested_pct = partial.get('suggested_pct', 50)
                suggested_amount = p['amount'] * suggested_pct / 100
                
                strategy["recommendations"].append({
                    "party": p['party'],
                    "action": "pay_partial",
                    "full_amount": p['amount'],
                    "suggested_amount": suggested_amount,
                    "suggested_percentage": suggested_pct,
                    "minimum_required": min_payment,
                    "remaining_balance": p['amount'] - suggested_amount,
                    "max_installments": partial.get('max_installments', 1),
                    "installment_days": partial.get('installment_days', 15),
                    "notes": partial.get('notes', ''),
                    "reason": "Partial payment arrangement recommended"
                })
                remaining -= suggested_amount
            else:
                # Cannot pay even minimum
                strategy["recommendations"].append({
                    "party": p['party'],
                    "action": "negotiate_extension",
                    "full_amount": p['amount'],
                    "minimum_required": min_payment,
                    "shortfall": min_payment - remaining,
                    "reason": "Insufficient funds for minimum partial payment"
                })
    
    return strategy

def get_partial_payment_stats(payables: List[Dict]) -> Dict[str, Any]:
    """
    Get statistics about partial payment availability
    
    Args:
        payables: List of payable obligations
    
    Returns:
        Statistics dictionary
    """
    total = len(payables)
    partial_accepting = sum(1 for p in payables 
                           if p.get('partial_payment', {}).get('accepts_partial', False))
    
    partial_details = []
    for p in payables:
        partial = p.get('partial_payment', {})
        if partial.get('accepts_partial', False):
            partial_details.append({
                "party": p['party'],
                "amount": p['amount'],
                "minimum_pct": partial.get('minimum_partial_pct', 0),
                "minimum_amount": partial.get('minimum_partial_amount', 0),
                "suggested_pct": partial.get('suggested_pct', 0),
                "max_installments": partial.get('max_installments', 1),
                "installment_days": partial.get('installment_days', 15)
            })
    
    total_minimum_partial = sum(
        max(
            p['partial_payment'].get('minimum_partial_amount', 0),
            p['amount'] * p['partial_payment'].get('minimum_partial_pct', 50) / 100
        )
        for p in payables 
        if p.get('partial_payment', {}).get('accepts_partial', False)
    )
    
    return {
        "total_obligations": total,
        "partial_accepting_count": partial_accepting,
        "partial_accepting_percentage": (partial_accepting / total * 100) if total > 0 else 0,
        "total_minimum_partial_payment": total_minimum_partial,
        "partial_details": partial_details
    }