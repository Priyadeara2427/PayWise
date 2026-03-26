"""
Decision Engine for financial obligations with partial payment consideration
"""

from typing import List, Dict, Any, Optional
import logging
from datetime import date

from ..models.obligation import Obligation, Decision, Priority, Action

logger = logging.getLogger(__name__)

# Import financial_state functions
from . import financial_state as fs

class DecisionEngine:
    """Engine to make payment decisions based on risk scores, counterparty types, and partial payment availability"""
    
    @staticmethod
    def make_decision(obligation: Obligation) -> Decision:
        """Make decision for a single obligation with partial payment consideration"""
        
        # Get counterparty type and partial payment terms
        cp_type = obligation.counterparty.get('type', 'unknown')
        partial_terms = obligation.partial_payment
        
        # Determine priority based on risk score and counterparty type
        if cp_type in ['tax_authority', 'government']:
            priority = Priority.CRITICAL
        elif obligation.risk_score >= 0.7:
            priority = Priority.HIGH
        elif obligation.risk_score >= 0.4:
            priority = Priority.MEDIUM
        else:
            priority = Priority.LOW
        
        # Determine action based on risk, counterparty type, days late, and partial payment availability
        suggested_terms = None
        
        # Critical payments (tax, government)
        if cp_type in ['tax_authority', 'government']:
            action = Action.PAY_IMMEDIATELY
            reason = f"🚨 CRITICAL: {cp_type.replace('_', ' ').title()} - Legal consequences if delayed"
            if obligation.days_late > 0:
                reason += f" ({obligation.days_late} days overdue!)"
        
        # High risk payments
        elif obligation.risk_score >= 0.8:
            action = Action.PAY_IMMEDIATELY
            reason = "High risk - immediate payment required"
        
        # Medium risk - check if partial payment is possible
        elif obligation.risk_score >= 0.5:
            if partial_terms.accepts_partial and obligation.amount > partial_terms.minimum_partial_amount:
                action = Action.PAY_PARTIALLY
                suggested_amount = obligation.amount * partial_terms.suggested_pct / 100
                reason = f"Partial payment accepted - minimum {partial_terms.minimum_partial_pct}% (₹{partial_terms.minimum_partial_amount:,.2f})"
                suggested_terms = {
                    'percentage': partial_terms.suggested_pct,
                    'amount': suggested_amount,
                    'remaining_days': partial_terms.installment_days,
                    'max_installments': partial_terms.max_installments,
                    'minimum_required': partial_terms.minimum_partial_amount,
                    'notes': partial_terms.notes
                }
            else:
                action = Action.NEGOTIATE_EXTENSION
                reason = "Medium risk - negotiate extension"
                suggested_terms = {
                    'requested_days': min(obligation.days_late + 7, 30),
                    'reason': 'cash_flow_management',
                    'alternative': 'partial_payment'
                }
        
        # Significantly overdue
        elif obligation.days_late > 15:
            if partial_terms.accepts_partial:
                action = Action.PAY_PARTIALLY
                reason = f"Significantly overdue ({obligation.days_late} days) - offer partial payment"
                suggested_terms = {
                    'percentage': partial_terms.suggested_pct,
                    'amount': obligation.amount * partial_terms.suggested_pct / 100,
                    'apology': True,
                    'commitment_date': (date.today() + timedelta(days=partial_terms.installment_days)).isoformat()
                }
            else:
                action = Action.ESCALATE
                reason = f"Significantly overdue ({obligation.days_late} days) - escalate"
        
        # Personal relationships
        elif cp_type in ['friend', 'family']:
            action = Action.COMMUNICATE
            reason = "Personal relationship - communicate first"
            suggested_terms = {
                'suggested_payment': obligation.amount * 0.3,
                'message': "Be transparent about cash flow situation"
            }
        
        # Low risk - check partial payment availability
        else:
            if partial_terms.accepts_partial and obligation.amount > partial_terms.minimum_partial_amount:
                action = Action.PAY_PARTIALLY
                suggested_amount = obligation.amount * partial_terms.suggested_pct / 100
                reason = f"Low risk - partial payment available ({partial_terms.suggested_pct}%)"
                suggested_terms = {
                    'percentage': partial_terms.suggested_pct,
                    'amount': suggested_amount,
                    'remaining_days': partial_terms.installment_days,
                    'max_installments': partial_terms.max_installments,
                    'minimum_required': partial_terms.minimum_partial_amount,
                    'notes': partial_terms.notes
                }
            else:
                action = Action.PAY_PARTIALLY
                reason = "Low risk - consider partial payment"
                suggested_terms = {
                    'percentage': 50,
                    'remaining_days': 15,
                    'reason': 'temporary_cash_shortage'
                }
        
        # Adjust for vendor relationship
        if cp_type == 'vendor' and action == Action.PAY_PARTIALLY:
            if partial_terms.accepts_partial:
                action = Action.PAY_PARTIALLY
                reason = f"Vendor accepts partial payments - offer {partial_terms.suggested_pct}% now"
            else:
                action = Action.NEGOTIATE_EXTENSION
                reason = "Vendor relationship - negotiate extension instead of partial payment"
        
        return Decision(
            priority=priority,
            action=action,
            reason=reason,
            suggested_terms=suggested_terms,
            alternatives=None
        )
    
    @staticmethod
    def make_decisions(obligations: List[Obligation]) -> List[Dict[str, Any]]:
        """Make decisions for all obligations with partial payment details"""
        decisions = []
        for obligation in obligations:
            decision = DecisionEngine.make_decision(obligation)
            # Add decision to obligation
            obligation.decision = decision
            
            # Calculate partial payment suggestion if applicable
            partial_suggestion = None
            if decision.action == Action.PAY_PARTIALLY and obligation.partial_payment.accepts_partial:
                suggested_amount = obligation.amount * obligation.partial_payment.suggested_pct / 100
                partial_suggestion = {
                    'suggested_amount': suggested_amount,
                    'suggested_percentage': obligation.partial_payment.suggested_pct,
                    'minimum_required': obligation.partial_payment.minimum_partial_amount,
                    'minimum_percentage': obligation.partial_payment.minimum_partial_pct,
                    'max_installments': obligation.partial_payment.max_installments,
                    'installment_days': obligation.partial_payment.installment_days,
                    'notes': obligation.partial_payment.notes
                }
            
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
                "suggested_terms": decision.suggested_terms,
                "partial_available": obligation.partial_payment.accepts_partial,
                "partial_min_pct": obligation.partial_payment.minimum_partial_pct,
                "partial_min_amount": obligation.partial_payment.minimum_partial_amount,
                "partial_suggestion": partial_suggestion,
                "payment_history": [h.dict() for h in obligation.partial_payment.history] if obligation.partial_payment.history else []
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
    
    @staticmethod
    def get_best_partial_payment_strategy(obligation: Obligation, available_cash: float) -> Dict[str, Any]:
        """Get the best partial payment strategy based on available cash"""
        
        if not obligation.partial_payment.accepts_partial:
            return {
                'can_pay_partial': False,
                'reason': 'Counterparty does not accept partial payments',
                'suggested_action': 'pay_full_or_negotiate'
            }
        
        # Calculate minimum acceptable payment
        min_payment = max(
            obligation.amount * obligation.partial_payment.minimum_partial_pct / 100,
            obligation.partial_payment.minimum_partial_amount
        )
        
        if available_cash >= min_payment:
            suggested_payment = min(available_cash, obligation.amount)
            suggested_pct = (suggested_payment / obligation.amount) * 100
            
            # Determine if we can pay in installments
            remaining = obligation.amount - suggested_payment
            installments = []
            if remaining > 0 and obligation.partial_payment.max_installments > 1:
                installment_amount = remaining / obligation.partial_payment.max_installments
                for i in range(obligation.partial_payment.max_installments):
                    installments.append({
                        'installment': i + 1,
                        'amount': installment_amount,
                        'due_date': (date.today() + timedelta(days=obligation.partial_payment.installment_days * (i + 1))).isoformat()
                    })
            
            return {
                'can_pay_partial': True,
                'minimum_required': min_payment,
                'suggested_payment': suggested_payment,
                'suggested_percentage': suggested_pct,
                'remaining_balance': remaining,
                'installments': installments,
                'max_installments': obligation.partial_payment.max_installments,
                'installment_days': obligation.partial_payment.installment_days,
                'notes': obligation.partial_payment.notes
            }
        else:
            return {
                'can_pay_partial': False,
                'minimum_required': min_payment,
                'shortfall': min_payment - available_cash,
                'reason': f'Insufficient funds - need ₹{min_payment:,.2f} minimum',
                'suggested_action': 'negotiate_extension_or_borrow'
            }


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
        from ..models.obligation import Obligation, ClassificationDetails, TransactionType, PartialPaymentTerms
        
        obligations = []
        for ob_data in obligations_data:
            # Create classification details
            cp_data = ob_data.get('counterparty', {})
            classification = ClassificationDetails(
                type=cp_data.get('type', 'unknown'),
                confidence=cp_data.get('classification_confidence', 0.0),
                source='auto'
            )
            
            # Create partial payment terms
            partial_data = ob_data.get('partial_payment', {})
            partial_terms = PartialPaymentTerms(
                accepts_partial=partial_data.get('accepts_partial', True),
                minimum_partial_pct=partial_data.get('minimum_partial_pct', 50.0),
                minimum_partial_amount=partial_data.get('minimum_partial_amount', 5000.0),
                suggested_pct=partial_data.get('suggested_pct', 50.0),
                max_installments=partial_data.get('max_installments', 1),
                installment_days=partial_data.get('installment_days', 15),
                notes=partial_data.get('notes', ''),
                history=partial_data.get('history', [])
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
                partial_payment=partial_terms,
                transaction_type=TransactionType(ob_data.get('transaction_type', 'unknown')),
                note=ob_data.get('note'),
                invoice_number=ob_data.get('invoice_number'),
                gstin=ob_data.get('gstin'),
                pan=ob_data.get('pan')
            )
            obligations.append(obligation)
        
        # Generate decisions
        return DecisionEngine.make_decisions(obligations)
        
    except Exception as e:
        logger.error(f"Error in decision engine: {e}")
        return []