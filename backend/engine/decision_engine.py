"""
Decision Engine for financial obligations
"""

from typing import List, Dict, Any, Optional
import logging
from datetime import date

from ..models.obligation import Obligation, Decision, Priority, Action

logger = logging.getLogger(__name__)

# Import financial_state functions
from . import financial_state as fs

class DecisionEngine:
    """Engine to make payment decisions based on risk scores and counterparty types"""
    
    @staticmethod
    def make_decision(obligation: Obligation) -> Decision:
        """Make decision for a single obligation"""
        
        # Determine priority based on risk score and counterparty type
        cp_type = obligation.counterparty.get('type', 'unknown')
        
        # Critical priority for tax and government
        if cp_type in ['tax_authority', 'government']:
            priority = Priority.CRITICAL
        elif obligation.risk_score >= 0.7:
            priority = Priority.HIGH
        elif obligation.risk_score >= 0.4:
            priority = Priority.MEDIUM
        else:
            priority = Priority.LOW
        
        # Determine action based on risk, counterparty type, and days late
        if cp_type in ['tax_authority', 'government']:
            action = Action.PAY_IMMEDIATELY
            reason = "Critical payment - tax/government obligation"
        elif obligation.risk_score >= 0.8:
            action = Action.PAY_IMMEDIATELY
            reason = "High risk - immediate payment required"
        elif obligation.risk_score >= 0.5:
            action = Action.NEGOTIATE_EXTENSION
            reason = "Medium risk - negotiate extension"
        elif obligation.days_late > 15:
            action = Action.ESCALATE
            reason = "Significantly overdue - escalate"
        elif cp_type in ['friend', 'family']:
            action = Action.COMMUNICATE
            reason = "Personal relationship - communicate first"
        else:
            action = Action.PAY_PARTIALLY
            reason = "Low risk - consider partial payment"
        
        # Adjust for counterparty type
        if cp_type == 'vendor' and action == Action.PAY_PARTIALLY:
            action = Action.NEGOTIATE_EXTENSION
            reason = "Vendor relationship - negotiate instead of partial payment"
        
        # Add suggested terms for negotiations
        suggested_terms = None
        if action == Action.NEGOTIATE_EXTENSION:
            suggested_terms = {
                'requested_days': min(obligation.days_late + 7, 30),
                'reason': 'cash_flow_management',
                'alternative': 'partial_payment'
            }
        elif action == Action.PAY_PARTIALLY:
            suggested_terms = {
                'percentage': 50,
                'remaining_days': 15,
                'reason': 'temporary_cash_shortage'
            }
        
        return Decision(
            priority=priority,
            action=action,
            reason=reason,
            suggested_terms=suggested_terms,
            alternatives=None
        )
    
    @staticmethod
    def make_decisions(obligations: List[Obligation]) -> List[Dict[str, Any]]:
        """Make decisions for all obligations"""
        decisions = []
        for obligation in obligations:
            decision = DecisionEngine.make_decision(obligation)
            # Add decision to obligation
            obligation.decision = decision
            
            decisions.append({
                "transaction_id": obligation.transaction_id,
                "counterparty": obligation.counterparty.get('name'),
                "counterparty_type": obligation.counterparty.get('type'),
                "amount": obligation.amount,
                "due_date": obligation.due_date.isoformat() if obligation.due_date else None,
                "days_late": obligation.days_late,
                "risk_score": obligation.risk_score,
                "priority": decision.priority.value,
                "action": decision.action.value,
                "reason": decision.reason,
                "suggested_terms": decision.suggested_terms
            })
        
        return decisions
    
    @staticmethod
    def get_priority_score(obligation: Obligation) -> int:
        """Get numerical priority score for sorting"""
        cp_type = obligation.counterparty.get('type', 'unknown')
        
        # Priority mapping
        priority_scores = {
            'critical': 100,
            'high': 80,
            'medium': 50,
            'low': 20
        }
        
        if cp_type in ['tax_authority', 'government']:
            return priority_scores['critical']
        elif obligation.risk_score >= 0.7:
            return priority_scores['high']
        elif obligation.risk_score >= 0.4:
            return priority_scores['medium']
        else:
            return priority_scores['low']


# Legacy function for backward compatibility
def run_decision_engine(financial_state: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Legacy function to run decision engine on financial state
    
    Args:
        financial_state: Dictionary containing financial state
    
    Returns:
        List of decisions
    """
    try:
        obligations_data = financial_state.get('obligations', [])
        
        # Convert to Obligation objects
        from ..models.obligation import Obligation, ClassificationDetails, TransactionType
        
        obligations = []
        for ob_data in obligations_data:
            # Create classification details
            cp_data = ob_data.get('counterparty', {})
            classification = ClassificationDetails(
                type=cp_data.get('type', 'unknown'),
                confidence=cp_data.get('classification_confidence', 0.0),
                source='auto'
            )
            
            # Create obligation
            obligation = Obligation(
                transaction_id=ob_data.get('transaction_id'),
                counterparty=cp_data,
                amount=ob_data.get('amount', 0),
                due_date=ob_data.get('due_date', date.today()),
                payment_date=ob_data.get('payment_date'),
                days_late=ob_data.get('days_late', 0),
                risk_score=ob_data.get('risk_score', 0),
                classification=classification,
                transaction_type=TransactionType(ob_data.get('transaction_type', 'unknown')),
                note=ob_data.get('note')
            )
            obligations.append(obligation)
        
        # Generate decisions
        return DecisionEngine.make_decisions(obligations)
        
    except Exception as e:
        logger.error(f"Error in decision engine: {e}")
        return []