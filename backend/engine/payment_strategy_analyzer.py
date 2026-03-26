# backend/engine/payment_strategy_analyzer.py
"""
Payment Strategy Analyzer - Determines payment flexibility based on who you owe money to
"""

from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional
from enum import Enum

class PaymentCategory(Enum):
    MUST_PAY = "must_pay"           # Must pay on time (tax, government, bank)
    CAN_NEGOTIATE = "can_negotiate" # Can negotiate extension (vendors, suppliers)
    CAN_DELAY = "can_delay"         # Can delay payment (friends, family)
    CAN_PARTIAL = "can_partial"     # Can pay partially (utilities, rent)
    CRITICAL = "critical"           # Critical - pay immediately or face consequences

class PaymentStrategyAnalyzer:
    """
    Analyzes payment obligations and determines flexibility based on relationship
    """
    
    PAYMENT_RULES = {
        'tax_authority': {
            'category': PaymentCategory.MUST_PAY,
            'can_negotiate': False,
            'can_delay': False,
            'can_partial': False,
            'grace_days': 0,
            'penalty_rate': 0.18,
            'priority': 100,
            'strategy': 'PAY_IMMEDIATELY',
            'reason': 'Tax payment - legal obligation, cannot delay',
            'collection_urgency': 'critical'
        },
        'government': {
            'category': PaymentCategory.MUST_PAY,
            'can_negotiate': False,
            'can_delay': False,
            'can_partial': False,
            'grace_days': 0,
            'penalty_rate': 0.12,
            'priority': 95,
            'strategy': 'PAY_IMMEDIATELY',
            'reason': 'Government payment - strict deadline',
            'collection_urgency': 'critical'
        },
        'bank': {
            'category': PaymentCategory.MUST_PAY,
            'can_negotiate': False,
            'can_delay': False,
            'can_partial': False,
            'grace_days': 3,
            'penalty_rate': 0.24,
            'priority': 90,
            'strategy': 'PAY_ON_TIME',
            'reason': 'Bank loan - affects credit score, minimal grace period',
            'collection_urgency': 'high'
        },
        'employee': {
            'category': PaymentCategory.MUST_PAY,
            'can_negotiate': False,
            'can_delay': False,
            'can_partial': False,
            'grace_days': 0,
            'penalty_rate': 0.10,
            'priority': 85,
            'strategy': 'PAY_IMMEDIATELY',
            'reason': 'Salary payment - legal requirement, morale impact',
            'collection_urgency': 'high'
        },
        'vendor': {
            'category': PaymentCategory.CAN_NEGOTIATE,
            'can_negotiate': True,
            'can_delay': True,
            'can_partial': True,
            'grace_days': 7,
            'penalty_rate': 0.05,
            'priority': 70,
            'strategy': 'NEGOTIATE_EXTENSION',
            'reason': 'Vendor - can negotiate payment terms',
            'collection_urgency': 'medium'
        },
        'supplier': {
            'category': PaymentCategory.CAN_NEGOTIATE,
            'can_negotiate': True,
            'can_delay': True,
            'can_partial': True,
            'grace_days': 7,
            'penalty_rate': 0.05,
            'priority': 70,
            'strategy': 'NEGOTIATE_EXTENSION',
            'reason': 'Supplier - can discuss payment schedule',
            'collection_urgency': 'medium'
        },
        'utility': {
            'category': PaymentCategory.CAN_PARTIAL,
            'can_negotiate': True,
            'can_delay': True,
            'can_partial': True,
            'grace_days': 15,
            'penalty_rate': 0.02,
            'priority': 60,
            'strategy': 'PAY_PARTIAL_OR_DELAY',
            'reason': 'Utility - can pay partially to avoid disconnection',
            'collection_urgency': 'medium'
        },
        'rent': {
            'category': PaymentCategory.CAN_NEGOTIATE,
            'can_negotiate': True,
            'can_delay': True,
            'can_partial': True,
            'grace_days': 10,
            'penalty_rate': 0.03,
            'priority': 65,
            'strategy': 'NEGOTIATE_EXTENSION',
            'reason': 'Rent - can discuss with landlord',
            'collection_urgency': 'medium'
        },
        'insurance': {
            'category': PaymentCategory.CAN_NEGOTIATE,
            'can_negotiate': True,
            'can_delay': True,
            'can_partial': True,
            'grace_days': 30,
            'penalty_rate': 0.01,
            'priority': 55,
            'strategy': 'NEGOTIATE_EXTENSION',
            'reason': 'Insurance - grace period available',
            'collection_urgency': 'low'
        },
        'friend': {
            'category': PaymentCategory.CAN_DELAY,
            'can_negotiate': True,
            'can_delay': True,
            'can_partial': True,
            'grace_days': 30,
            'penalty_rate': 0.0,
            'priority': 30,
            'strategy': 'COMMUNICATE_AND_DELAY',
            'reason': 'Friend - communicate openly, can delay',
            'collection_urgency': 'low'
        },
        'family': {
            'category': PaymentCategory.CAN_DELAY,
            'can_negotiate': True,
            'can_delay': True,
            'can_partial': True,
            'grace_days': 60,
            'penalty_rate': 0.0,
            'priority': 25,
            'strategy': 'COMMUNICATE_AND_DELAY',
            'reason': 'Family - flexible arrangement',
            'collection_urgency': 'low'
        },
        'customer': {
            'category': PaymentCategory.CAN_NEGOTIATE,
            'can_negotiate': True,
            'can_delay': False,
            'can_partial': True,
            'grace_days': 15,
            'penalty_rate': 0.05,
            'priority': 50,
            'strategy': 'OFFER_PARTIAL',
            'reason': 'Customer - maintain relationship, offer partial',
            'collection_urgency': 'medium'
        },
        'charity': {
            'category': PaymentCategory.CAN_DELAY,
            'can_negotiate': True,
            'can_delay': True,
            'can_partial': True,
            'grace_days': 90,
            'penalty_rate': 0.0,
            'priority': 20,
            'strategy': 'DELAY_IF_NEEDED',
            'reason': 'Charity - can delay donation',
            'collection_urgency': 'low'
        },
        'unknown': {
            'category': PaymentCategory.CAN_NEGOTIATE,
            'can_negotiate': True,
            'can_delay': True,
            'can_partial': True,
            'grace_days': 7,
            'penalty_rate': 0.05,
            'priority': 40,
            'strategy': 'NEGOTIATE',
            'reason': 'Unknown - try to negotiate',
            'collection_urgency': 'medium'
        }
    }
    
    @classmethod
    def analyze_payment(cls, counterparty_type: str, amount: float, due_date: date, 
                        days_late: int = 0, cash_balance: float = 0) -> Dict[str, Any]:
        """
        Analyze payment flexibility based on who you owe money to
        
        Args:
            counterparty_type: Who you owe money to (tax_authority, vendor, friend, etc.)
            amount: Amount you owe
            due_date: When payment is due
            days_late: How many days overdue
            cash_balance: Current cash available
        
        Returns:
            Dictionary with payment strategy analysis
        """
        rules = cls.PAYMENT_RULES.get(counterparty_type, cls.PAYMENT_RULES['unknown'])
        
        today = date.today()
        days_until_due = (due_date - today).days if due_date > today else 0
        
        urgency_score = cls._calculate_urgency(days_late, days_until_due, rules)
        
        can_afford = cash_balance >= amount if cash_balance > 0 else None
        
        return {
            'counterparty_type': counterparty_type,
            'category': rules['category'].value,
            'can_negotiate': rules['can_negotiate'],
            'can_delay': rules['can_delay'],
            'can_partial': rules['can_partial'],
            'grace_days': rules['grace_days'],
            'penalty_rate': rules['penalty_rate'],
            'priority': rules['priority'],
            'strategy': rules['strategy'],
            'reason': rules['reason'],
            'days_late': days_late,
            'days_until_due': days_until_due,
            'urgency_score': urgency_score,
            'can_afford': can_afford,
            'payment_action': cls._get_payment_action(rules, days_late, days_until_due),
            'recommendation': cls._get_recommendation(rules, days_late, days_until_due, amount),
            'risks': cls._get_risks(counterparty_type, days_late),
            'message_template': cls._get_message_template(rules, counterparty_type, amount, days_late)
        }
    
    @classmethod
    def _calculate_urgency(cls, days_late: int, days_until_due: int, rules: Dict) -> float:
        """Calculate urgency score (0-1) - higher means more urgent"""
        if days_late > 0:
            if rules['category'] == PaymentCategory.MUST_PAY:
                return min(1.0, days_late / 7)
            elif rules['category'] == PaymentCategory.CAN_NEGOTIATE:
                return min(0.7, days_late / 30)
            else:
                return min(0.5, days_late / 60)
        elif days_until_due <= 0:
            return 0.5
        elif days_until_due <= 3:
            return 0.7
        elif days_until_due <= 7:
            return 0.4
        else:
            return 0.2
    
    @classmethod
    def _get_payment_action(cls, rules: Dict, days_late: int, days_until_due: int) -> str:
        """Get recommended payment action"""
        if days_late > 0:
            if rules['category'] == PaymentCategory.MUST_PAY:
                return "PAY_IMMEDIATELY"
            elif rules['category'] == PaymentCategory.CAN_NEGOTIATE:
                return "NEGOTIATE_EXTENSION"
            elif rules['category'] == PaymentCategory.CAN_DELAY:
                return "COMMUNICATE_AND_DELAY"
            else:
                return "PAY_AS_SOON_AS_POSSIBLE"
        elif days_until_due <= 3:
            if rules['category'] == PaymentCategory.MUST_PAY:
                return "PREPARE_FOR_PAYMENT"
            else:
                return "CAN_REQUEST_EXTENSION"
        else:
            if rules['category'] == PaymentCategory.MUST_PAY:
                return "MARK_IN_CALENDAR"
            else:
                return "CAN_WAIT"
    
    @classmethod
    def _get_recommendation(cls, rules: Dict, days_late: int, days_until_due: int, amount: float) -> str:
        """Get human-readable payment recommendation"""
        if days_late > 0:
            if rules['category'] == PaymentCategory.MUST_PAY:
                return f"⚠️ CRITICAL: {rules['reason']}. Pay ₹{amount:,.2f} immediately to avoid {rules['penalty_rate']*100:.0f}% penalty."
            elif rules['can_negotiate']:
                return f"📞 {rules['reason']}. Contact them to negotiate extension for ₹{amount:,.2f}."
            elif rules['can_delay']:
                return f"💬 {rules['reason']}. Send a message explaining delay for ₹{amount:,.2f}."
            else:
                return f"⚠️ {rules['reason']}. Pay ₹{amount:,.2f} as soon as possible."
        elif days_until_due <= 3:
            if rules['category'] == PaymentCategory.MUST_PAY:
                return f"🔔 Due in {days_until_due} days. {rules['reason']}. Prepare ₹{amount:,.2f}."
            else:
                return f"📅 Due in {days_until_due} days. Can request extension for ₹{amount:,.2f} if needed."
        else:
            if rules['category'] == PaymentCategory.MUST_PAY:
                return f"📅 Due in {days_until_due} days. Mark ₹{amount:,.2f} payment in calendar."
            else:
                return f"✅ Due in {days_until_due} days. Time to plan ₹{amount:,.2f} payment."
    
    @classmethod
    def _get_risks(cls, counterparty_type: str, days_late: int) -> List[str]:
        """Get risks of delaying payment"""
        risks = []
        
        if counterparty_type == 'tax_authority':
            risks.append("Legal penalties and interest")
            risks.append("Tax assessment issues")
            if days_late > 30:
                risks.append("Possible legal action")
        
        elif counterparty_type == 'government':
            risks.append("Contract cancellation")
            risks.append("Blacklisting from future contracts")
        
        elif counterparty_type == 'bank':
            risks.append("Credit score reduction")
            risks.append("Late payment fees")
            if days_late > 90:
                risks.append("Asset seizure risk")
        
        elif counterparty_type == 'employee':
            risks.append("Employee morale impact")
            risks.append("Legal complaints")
            risks.append("Resignation risk")
        
        elif counterparty_type in ['vendor', 'supplier']:
            risks.append("Supply disruption")
            risks.append("Relationship damage")
            if days_late > 45:
                risks.append("COD terms enforced")
        
        elif counterparty_type == 'utility':
            risks.append("Service disconnection")
            risks.append("Reconnection fees")
        
        elif counterparty_type == 'rent':
            risks.append("Eviction risk")
            risks.append("Legal notice")
        
        elif counterparty_type in ['friend', 'family']:
            risks.append("Relationship strain")
            risks.append("Trust erosion")
            risks.append("Future borrowing difficulty")
        
        return risks
    
    @classmethod
    def _get_message_template(cls, rules: Dict, counterparty_type: str, amount: float, days_late: int) -> str:
        """Get message template for communication"""
        if days_late > 0:
            if counterparty_type in ['friend', 'family']:
                return f"Hey, I wanted to be transparent about the ₹{amount:,.2f} I owe you. I'm facing some temporary cash flow issues. Can we discuss a short extension?"
            elif counterparty_type in ['vendor', 'supplier']:
                return f"Dear {counterparty_type.title()}, I'm writing regarding our outstanding payment of ₹{amount:,.2f}. Due to temporary cash flow constraints, I'd like to request a 15-day extension. I value our partnership and will ensure payment by then."
            elif counterparty_type == 'rent':
                return f"Dear Landlord, I'm writing regarding the rent of ₹{amount:,.2f}. I'm experiencing a temporary cash flow issue. Could we arrange a partial payment or short extension?"
            elif counterparty_type == 'utility':
                return f"Dear Utility Provider, I acknowledge the overdue amount of ₹{amount:,.2f}. I'll make a partial payment now and clear the balance within 15 days to avoid service disruption."
            else:
                return f"Regarding the overdue payment of ₹{amount:,.2f}, I'm working on arranging the funds and will update you shortly."
        else:
            if counterparty_type in ['friend', 'family']:
                return f"Just a reminder about the ₹{amount:,.2f} due. Let me know when's a good time to pay."
            else:
                return f"Payment of ₹{amount:,.2f} is coming up on the due date. I'll process it on time."
    
    @classmethod
    def get_payment_priority_score(cls, counterparty_type: str, amount: float, 
                                    days_late: int, days_until_due: int) -> float:
        """Calculate priority score for payment ordering (higher = pay first)"""
        rules = cls.PAYMENT_RULES.get(counterparty_type, cls.PAYMENT_RULES['unknown'])
        
        base_priority = rules['priority']
        
        late_multiplier = 1.0
        if days_late > 0:
            if rules['category'] == PaymentCategory.MUST_PAY:
                late_multiplier = min(2.0, 1.0 + (days_late / 30))
            elif rules['category'] == PaymentCategory.CAN_NEGOTIATE:
                late_multiplier = min(1.5, 1.0 + (days_late / 45))
            else:
                late_multiplier = min(1.2, 1.0 + (days_late / 60))
        
        amount_factor = min(1.5, 1.0 + (amount / 100000))
        
        urgency_factor = 1.0
        if days_late > 0:
            urgency_factor = 1.5
        elif days_until_due <= 3:
            urgency_factor = 1.3
        elif days_until_due <= 7:
            urgency_factor = 1.1
        
        final_score = base_priority * late_multiplier * amount_factor * urgency_factor
        
        return min(100, final_score)


def analyze_payment_batch(obligations: List[Dict], cash_balance: float = 0) -> List[Dict]:
    """
    Analyze multiple payment obligations
    
    Args:
        obligations: List of obligations (money you owe)
        cash_balance: Current cash available
    
    Returns:
        Updated obligations with payment strategy analysis
    """
    for obligation in obligations:
        counterparty_type = obligation.get('counterparty', {}).get('type', 'unknown')
        amount = obligation.get('amount', 0)
        due_date = obligation.get('due_date')
        days_late = obligation.get('days_late', 0)
        
        if due_date and isinstance(due_date, str):
            due_date = datetime.strptime(due_date, '%Y-%m-%d').date()
        elif not due_date:
            due_date = date.today()
        
        analysis = PaymentStrategyAnalyzer.analyze_payment(
            counterparty_type, amount, due_date, days_late, cash_balance
        )
        
        obligation['payment_strategy_analysis'] = analysis
        obligation['payment_category'] = analysis['category']
        obligation['can_negotiate'] = analysis['can_negotiate']
        obligation['can_delay'] = analysis['can_delay']
        obligation['can_partial'] = analysis['can_partial']
        obligation['payment_action'] = analysis['payment_action']
        obligation['urgency_score'] = analysis['urgency_score']
        obligation['priority_score'] = analysis['priority']
        
    return obligations