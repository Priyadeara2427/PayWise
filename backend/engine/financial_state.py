"""
Financial state calculations and helper functions
"""

from typing import List, Dict, Any
from datetime import date, timedelta
import logging

logger = logging.getLogger(__name__)

def detect_shortfall(cash_balance: float, payables: List[Dict[str, Any]]) -> float:
    """
    Detect cash shortfall compared to payables
    
    Args:
        cash_balance: Current cash balance
        payables: List of payable obligations
    
    Returns:
        Shortfall amount (negative if surplus)
    """
    total_payables = sum(p.get('amount', 0) for p in payables)
    shortfall = cash_balance - total_payables
    
    return shortfall

def compute_days_to_zero(cash_balance: float, payables: List[Dict[str, Any]], 
                         daily_burn_rate: float = None) -> int:
    """
    Compute days until cash reaches zero based on payables
    
    Args:
        cash_balance: Current cash balance
        payables: List of payable obligations
        daily_burn_rate: Optional daily burn rate, if not provided, calculated from payables
    
    Returns:
        Days until cash reaches zero
    """
    if cash_balance <= 0:
        return 0
    
    if daily_burn_rate is None and payables:
        # Calculate average daily payment from payables
        total_amount = sum(p.get('amount', 0) for p in payables)
        if payables:
            # Sort payables by due date
            sorted_payables = sorted(payables, key=lambda x: x.get('due_date', date.today()))
            
            # Calculate days span
            if sorted_payables:
                first_date = sorted_payables[0].get('due_date', date.today())
                last_date = sorted_payables[-1].get('due_date', date.today())
                days_span = (last_date - first_date).days
                if days_span > 0:
                    daily_burn_rate = total_amount / days_span
                else:
                    daily_burn_rate = total_amount / 30  # Default to 30 days
    
    if daily_burn_rate and daily_burn_rate > 0:
        days = int(cash_balance / daily_burn_rate)
        return max(0, days)
    
    return 30  # Default if can't compute

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