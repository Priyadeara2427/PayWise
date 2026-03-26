"""
Predictive Decision Engine with Real-Time Interactive Analysis, 
Partial Payment Support, Borrowing Suggestions, and Cascading Risk Analysis
"""

from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
import json

class PaymentLevel(Enum):
    """Payment priority levels with cascading risk"""
    LEVEL_1_STATUTORY = 1   # GST, TDS, tax, government - legal action risk
    LEVEL_2_OPERATIONAL = 2  # Bank EMI, electricity, internet - service disruption
    LEVEL_3_PEOPLE = 3       # Salaries, contractors - morale, trust
    LEVEL_4_KEY_SUPPLY = 4   # Primary vendors - cascade risk to revenue
    LEVEL_5_STANDARD = 5     # Secondary vendors - negotiable
    LEVEL_6_INFORMAL = 6     # Friends, informal - flexible

class ActionType(Enum):
    """Recommended actions"""
    PAY_IMMEDIATELY = "pay_immediately"
    PAY_THIS_WEEK = "pay_this_week"
    NEGOTIATE_EXTENSION = "negotiate_extension"
    PAY_PARTIALLY = "pay_partially"
    DELAY_IF_POSSIBLE = "delay_if_possible"
    REVIEW = "review"
    COMMUNICATE = "communicate"  # Add this line
    BORROW_FROM_FRIEND = "borrow_from_friend"
    TAKE_PERSONAL_LOAN = "take_personal_loan"
    USE_CREDIT_CARD = "use_credit_card"
    BUSINESS_OVERDRAFT = "business_overdraft"
    EMERGENCY_FUND = "emergency_fund"

@dataclass
class BorrowingOption:
    """Borrowing option details"""
    source: str
    amount: float
    interest_rate: float
    repayment_days: int
    urgency: str
    feasibility: float
    pros: List[str]
    cons: List[str]
    message: str

@dataclass
class CascadingRisk:
    """Cascading risk from delayed payment"""
    level: int
    level_name: str
    immediate_impact: str
    cascade_effect: str
    revenue_impact: float  # Percentage of revenue at risk
    time_to_crisis: int  # Days before serious impact

@dataclass
class ObligationModel:
    """Complete model for an obligation with cascading risk"""
    transaction_id: str
    party: str
    amount: float
    due_date: date
    days_late: int
    counterparty_type: str
    urgency_score: float
    risk_score: float
    penalty: float
    flexibility: str
    payment_window: int
    relationship_impact: float
    regulatory_risk: float = 0.0
    priority_score: float = 0.0
    manual_rank: Optional[int] = None
    accepts_partial: bool = True
    min_partial_pct: float = 50.0
    min_partial_amount: float = 5000.0
    suggested_pct: float = 50.0
    max_installments: int = 1
    installment_days: int = 15
    payment_level: PaymentLevel = PaymentLevel.LEVEL_5_STANDARD
    cascading_risk: Optional[CascadingRisk] = None
    
    def get_payment_level(self) -> PaymentLevel:
        """Determine payment level based on counterparty type"""
        level_map = {
            # Level 1 - STATUTORY (pay immediately)
            'tax_authority': PaymentLevel.LEVEL_1_STATUTORY,
            'government': PaymentLevel.LEVEL_1_STATUTORY,
            
            # Level 2 - OPERATIONAL CRITICAL
            'bank': PaymentLevel.LEVEL_2_OPERATIONAL,
            'utility': PaymentLevel.LEVEL_2_OPERATIONAL,
            'internet': PaymentLevel.LEVEL_2_OPERATIONAL,
            'electricity': PaymentLevel.LEVEL_2_OPERATIONAL,
            
            # Level 3 - PEOPLE
            'employee': PaymentLevel.LEVEL_3_PEOPLE,
            
            # Level 4 - KEY SUPPLY CHAIN
            'vendor': PaymentLevel.LEVEL_4_KEY_SUPPLY,
            'supplier': PaymentLevel.LEVEL_4_KEY_SUPPLY,
            
            # Level 5 - STANDARD PAYABLES
            'rent': PaymentLevel.LEVEL_5_STANDARD,
            'insurance': PaymentLevel.LEVEL_5_STANDARD,
            'investment': PaymentLevel.LEVEL_5_STANDARD,
            
            # Level 6 - INFORMAL
            'friend': PaymentLevel.LEVEL_6_INFORMAL,
            'family': PaymentLevel.LEVEL_6_INFORMAL,
            'charity': PaymentLevel.LEVEL_6_INFORMAL,
            'unknown': PaymentLevel.LEVEL_5_STANDARD
        }
        return level_map.get(self.counterparty_type, PaymentLevel.LEVEL_5_STANDARD)
    
    def get_cascading_risk(self) -> CascadingRisk:
        """Calculate cascading risk if payment is delayed"""
        level = self.get_payment_level()
        
        risk_map = {
            PaymentLevel.LEVEL_1_STATUTORY: CascadingRisk(
                level=1,
                level_name="STATUTORY",
                immediate_impact="🔴 LEGAL NOTICES & PENALTIES",
                cascade_effect="🚨 Business closure, prosecution, asset attachment, 18%+ interest",
                revenue_impact=100.0,
                time_to_crisis=7
            ),
            PaymentLevel.LEVEL_2_OPERATIONAL: CascadingRisk(
                level=2,
                level_name="OPERATIONAL",
                immediate_impact="⚡ Service disruption, credit score drop",
                cascade_effect="📉 No power/internet = no operations = revenue loss, loan default",
                revenue_impact=50.0,
                time_to_crisis=15
            ),
            PaymentLevel.LEVEL_3_PEOPLE: CascadingRisk(
                level=3,
                level_name="PEOPLE",
                immediate_impact="👥 Morale drop, trust erosion",
                cascade_effect="😔 Employee attrition, legal complaints, productivity loss",
                revenue_impact=30.0,
                time_to_crisis=30
            ),
            PaymentLevel.LEVEL_4_KEY_SUPPLY: CascadingRisk(
                level=4,
                level_name="KEY SUPPLY CHAIN",
                immediate_impact="📦 Supply disruption",
                cascade_effect="🏭 Production halt, delayed deliveries, customer loss",
                revenue_impact=70.0,
                time_to_crisis=21
            ),
            PaymentLevel.LEVEL_5_STANDARD: CascadingRisk(
                level=5,
                level_name="STANDARD",
                immediate_impact="📄 Late fee, reminder calls",
                cascade_effect="🤝 Relationship strain, reduced credit terms",
                revenue_impact=10.0,
                time_to_crisis=45
            ),
            PaymentLevel.LEVEL_6_INFORMAL: CascadingRisk(
                level=6,
                level_name="INFORMAL",
                immediate_impact="😟 Personal discomfort",
                cascade_effect="💔 Relationship strain, future borrowing difficulty",
                revenue_impact=0.0,
                time_to_crisis=90
            )
        }
        
        return risk_map.get(level, risk_map[PaymentLevel.LEVEL_5_STANDARD])
    
    def calculate_priority_score(self) -> float:
        """Calculate weighted priority score with cascading risk multiplier"""
        if self.counterparty_type in ['tax_authority', 'government']:
            return 1.0
        
        # Base priority from level
        level_scores = {
            PaymentLevel.LEVEL_1_STATUTORY: 1.0,
            PaymentLevel.LEVEL_2_OPERATIONAL: 0.95,
            PaymentLevel.LEVEL_3_PEOPLE: 0.85,
            PaymentLevel.LEVEL_4_KEY_SUPPLY: 0.8,
            PaymentLevel.LEVEL_5_STANDARD: 0.6,
            PaymentLevel.LEVEL_6_INFORMAL: 0.3
        }
        
        level = self.get_payment_level()
        level_score = level_scores.get(level, 0.5)
        
        weights = {
            'urgency': 0.30,
            'risk': 0.25,
            'penalty': 0.20,
            'relationship': 0.15,
            'flexibility': 0.10
        }
        
        urgency = min(self.days_late / 30, 1.0)
        
        flexibility_score = {
            'rigid': 1.0,
            'negotiable': 0.5,
            'flexible': 0.2
        }.get(self.flexibility, 0.5)
        
        penalty_ratio = min(self.penalty / max(self.amount, 1), 1.0)
        
        priority_score = (
            urgency * weights['urgency'] +
            self.risk_score * weights['risk'] +
            penalty_ratio * weights['penalty'] +
            self.relationship_impact * weights['relationship'] +
            flexibility_score * weights['flexibility']
        )
        
        # Multiply by level score (higher level = higher priority)
        final_score = priority_score * level_score * 1.2
        
        return min(final_score, 1.0)
    
    def get_risk_level(self) -> str:
        """Get human-readable risk level with cascading risk warning"""
        level = self.get_payment_level()
        if self.days_late > self.cascading_risk.time_to_crisis:
            return f"🔴 CRITICAL - {self.cascading_risk.cascade_effect[:50]}..."
        elif self.counterparty_type in ['tax_authority', 'government']:
            return "🔴 CRITICAL - Legal/Regulatory"
        elif self.priority_score > 0.8:
            return "🔴 HIGH"
        elif self.priority_score > 0.5:
            return "🟡 MEDIUM"
        elif self.priority_score > 0.2:
            return "🟢 LOW"
        else:
            return "⚪ MINIMAL"
    
    def get_recommended_action(self) -> Tuple[ActionType, str]:
        """Get recommended action based on priority score, type, and cascading risk"""
        level = self.get_payment_level()
        cascading = self.cascading_risk
        
        # Level 1 - STATUTORY: Pay immediately regardless
        if level == PaymentLevel.LEVEL_1_STATUTORY:
            if self.days_late > 0:
                return ActionType.PAY_IMMEDIATELY, f"🚨 CRITICAL: {self.counterparty_type.replace('_', ' ').title()} - {self.days_late} days overdue! {cascading.cascade_effect}"
            else:
                return ActionType.PAY_IMMEDIATELY, f"⚠️ CRITICAL: {self.counterparty_type.replace('_', ' ').title()} - Pay before due date to avoid {cascading.immediate_impact}"
        
        # Level 2 - OPERATIONAL: Pay before service disruption
        if level == PaymentLevel.LEVEL_2_OPERATIONAL:
            if self.days_late > cascading.time_to_crisis:
                return ActionType.PAY_IMMEDIATELY, f"⚡ SERVICE RISK: {cascading.cascade_effect} - Pay now!"
            elif self.days_late > 0:
                return ActionType.PAY_THIS_WEEK, f"⚠️ {cascading.immediate_impact} - Pay within {cascading.time_to_crisis - self.days_late} days"
            else:
                return ActionType.PAY_THIS_WEEK, f"Pay before due to avoid {cascading.immediate_impact}"
        
        # Level 3 - PEOPLE: Pay salaries on time
        if level == PaymentLevel.LEVEL_3_PEOPLE:
            if self.days_late > 7:
                return ActionType.PAY_IMMEDIATELY, f"👥 EMPLOYEE MORALE: {cascading.cascade_effect} - Pay now!"
            elif self.days_late > 0:
                return ActionType.PAY_THIS_WEEK, f"⚠️ Pay delayed salaries to maintain trust"
            else:
                return ActionType.PAY_THIS_WEEK, "Pay salaries on time to maintain team morale"
        
        # Level 4 - KEY SUPPLY: Negotiate or pay partial to avoid cascade
        if level == PaymentLevel.LEVEL_4_KEY_SUPPLY:
            if self.days_late > cascading.time_to_crisis:
                return ActionType.PAY_IMMEDIATELY, f"🏭 SUPPLY CHAIN RISK: {cascading.cascade_effect} - Pay now!"
            elif self.accepts_partial:
                return ActionType.PAY_PARTIALLY, f"Key supplier - pay {self.suggested_pct}% now to maintain supply"
            else:
                return ActionType.NEGOTIATE_EXTENSION, "Negotiate with key supplier to avoid supply disruption"
        
        # Level 5 - STANDARD: Can negotiate or pay partially
        if level == PaymentLevel.LEVEL_5_STANDARD:
            if self.accepts_partial:
                return ActionType.PAY_PARTIALLY, f"Standard payable - consider {self.suggested_pct}% partial payment"
            else:
                return ActionType.NEGOTIATE_EXTENSION, "Negotiate extension with standard vendor"
        
        # Level 6 - INFORMAL: Flexible
        if level == PaymentLevel.LEVEL_6_INFORMAL:
            return ActionType.COMMUNICATE, f"Informal obligation - communicate delay to maintain relationship"
        
        # Default
        return ActionType.REVIEW, "Review before action"
    
    def get_consequences_of_delay(self) -> str:
        """Get cascading consequences of delaying this payment"""
        cascading = self.cascading_risk
        if self.days_late > cascading.time_to_crisis:
            return f"🚨 CASCADING CRISIS: {cascading.cascade_effect}"
        elif self.days_late > 0:
            return f"⚠️ {cascading.immediate_impact} → {cascading.cascade_effect[:80]}"
        else:
            return f"📋 {cascading.immediate_impact} if delayed beyond {cascading.time_to_crisis} days"
    
    def get_partial_payment_suggestion(self) -> Optional[Dict[str, Any]]:
        """Get partial payment suggestion if available"""
        if not self.accepts_partial:
            return None
        
        return {
            "minimum_payment": max(self.min_partial_amount, self.amount * self.min_partial_pct / 100),
            "minimum_percentage": self.min_partial_pct,
            "suggested_payment": self.amount * self.suggested_pct / 100,
            "suggested_percentage": self.suggested_pct,
            "max_installments": self.max_installments,
            "installment_days": self.installment_days
        }


@dataclass
class ScenarioResult:
    """Results of a scenario projection"""
    scenario_name: str
    actions: List[Dict[str, Any]]
    final_cash: float
    total_penalties: float
    risk_exposure: float
    relationship_impact: float
    regulatory_risk: float
    cash_flow: List[float]
    trade_off_justification: str
    metrics: Dict[str, Any] = field(default_factory=dict)
    partial_payments_used: int = 0
    partial_payments_saved: float = 0.0
    borrowing_recommendations: List[BorrowingOption] = field(default_factory=list)


class PredictiveDecisionEngine:
    """Interactive predictive decision engine with cascading risk analysis"""
    
    def __init__(self, cash_balance: float):
        self.cash_balance = cash_balance
        self.manual_order = {}
    
    def _get_borrowing_recommendations(self, shortfall: float, urgency: str = "medium") -> List[BorrowingOption]:
        """Get borrowing recommendations based on shortfall amount"""
        recommendations = []
        
        if shortfall <= 50000:
            recommendations.append(BorrowingOption(
                source="Friend/Family",
                amount=shortfall,
                interest_rate=0,
                repayment_days=30,
                urgency="Low",
                feasibility=0.9,
                pros=["No interest", "Flexible terms", "No credit check"],
                cons=["Personal relationship risk", "May strain relationships"],
                message="💝 Consider borrowing from friends/family - no interest, flexible terms"
            ))
        
        if shortfall <= 100000:
            recommendations.append(BorrowingOption(
                source="Personal Loan",
                amount=shortfall,
                interest_rate=12,
                repayment_days=365,
                urgency="Medium",
                feasibility=0.7,
                pros=["Fixed monthly payments", "Builds credit score", "No collateral needed"],
                cons=["Interest charges", "Processing time 2-5 days", "Credit check required"],
                message="🏦 Personal loan available at ~12% interest, quick approval"
            ))
        
        if shortfall <= 50000:
            recommendations.append(BorrowingOption(
                source="Credit Card",
                amount=shortfall,
                interest_rate=36,
                repayment_days=45,
                urgency="High",
                feasibility=0.95,
                pros=["Instant access", "No approval needed", "Reward points"],
                cons=["High interest rate", "Minimum payment trap", "Credit utilization impact"],
                message="💳 Credit card - immediate access but high interest, pay within 45 days"
            ))
        
        if shortfall <= 200000:
            recommendations.append(BorrowingOption(
                source="Business Overdraft",
                amount=shortfall,
                interest_rate=10,
                repayment_days=90,
                urgency="Medium",
                feasibility=0.6,
                pros=["Flexible repayment", "Only pay interest on used amount", "Revolving credit"],
                cons=["Requires business account", "Approval may take time", "Bank relationship needed"],
                message="💼 Business overdraft facility - flexible repayment"
            ))
        
        recommendations.append(BorrowingOption(
            source="Emergency Fund",
            amount=shortfall,
            interest_rate=0,
            repayment_days=0,
            urgency="Immediate",
            feasibility=0.5,
            pros=["No interest", "Immediate availability", "No credit impact"],
            cons=["Depletes savings", "May need time to rebuild"],
            message="💰 Use emergency savings - no interest, immediate availability"
        ))
        
        if shortfall <= 150000:
            recommendations.append(BorrowingOption(
                source="Gold Loan",
                amount=shortfall,
                interest_rate=9,
                repayment_days=180,
                urgency="Medium",
                feasibility=0.65,
                pros=["Lower interest rate", "Quick processing", "No credit score required"],
                cons=["Need gold as collateral", "Risk of losing gold"],
                message="🥇 Gold loan at ~9% interest - quick processing with collateral"
            ))
        
        return recommendations
    
    def apply_partial_payment(self, transaction_id: str, partial_percentage: float) -> Dict[str, Any]:
        """
        Apply partial payment to an obligation
        
        Args:
            transaction_id: ID of the obligation
            partial_percentage: Percentage to pay (e.g., 50 for 50%)
        
        Returns:
            Result of partial payment application
        """
        for model in self.models:
            if model.transaction_id == transaction_id:
                if not model.accepts_partial:
                    return {"success": False, "error": "This obligation does not accept partial payments"}
                
                if partial_percentage < model.min_partial_pct:
                    return {"success": False, "error": f"Minimum partial payment is {model.min_partial_pct}%"}
                
                suggested_amount = model.amount * partial_percentage / 100
                return {
                    "success": True,
                    "party": model.party,
                    "original_amount": model.amount,
                    "partial_percentage": partial_percentage,
                    "partial_amount": suggested_amount,
                    "remaining": model.amount - suggested_amount,
                    "message": f"Will pay {partial_percentage}% (₹{suggested_amount:,.2f}) now, remaining ₹{model.amount - suggested_amount:,.2f} later"
                }
        
        return {"success": False, "error": "Obligation not found"}

    
    def model_obligations(self, obligations: List[Dict]) -> List[ObligationModel]:
        """Convert raw obligations to enhanced models with cascading risk"""
        models = []
        
        for ob in obligations:
            cp_type = ob.get('type', ob.get('counterparty_type', 'unknown'))
            
            # Get partial payment info
            partial = ob.get('partial_payment', {})
            accepts_partial = partial.get('accepts_partial', True)
            min_partial_pct = partial.get('minimum_pct', partial.get('minimum_partial_pct', 50.0))
            min_partial_amount = partial.get('minimum_amount', partial.get('minimum_partial_amount', 5000.0))
            suggested_pct = partial.get('suggested_pct', min_partial_pct)
            max_installments = partial.get('max_installments', 1)
            installment_days = partial.get('installment_days', 15)
            
            # Regulatory risk based on counterparty type
            regulatory_risk = {
                'tax_authority': 1.0, 'government': 1.0, 'bank': 0.9,
                'employee': 0.85, 'vendor': 0.6, 'utility': 0.5,
                'customer': 0.3, 'rent': 0.4, 'insurance': 0.4,
                'friend': 0.1, 'family': 0.05, 'unknown': 0.3
            }.get(cp_type, 0.3)
            
            relationship_impact = {
                'tax_authority': 1.0, 'government': 1.0, 'bank': 0.9,
                'vendor': 0.8, 'employee': 0.85, 'utility': 0.7,
                'customer': 0.5, 'friend': 0.3, 'family': 0.2, 'unknown': 0.4
            }.get(cp_type, 0.5)
            
            days_late = ob.get('days_late', 0)
            flexibility = 'rigid'
            if cp_type in ['friend', 'family']:
                flexibility = 'flexible'
            elif cp_type in ['vendor', 'customer']:
                flexibility = 'negotiable'
            elif days_late > 15:
                flexibility = 'negotiable'
            
            payment_window = 7
            if cp_type in ['tax_authority', 'government']:
                payment_window = 0
            elif cp_type in ['bank']:
                payment_window = 3
            elif days_late > 0:
                payment_window = 0
            
            due_date = ob.get('due_date')
            if due_date and isinstance(due_date, str):
                try:
                    due_date = datetime.strptime(due_date, "%Y-%m-%d").date()
                except:
                    due_date = datetime.today().date()
            elif not due_date:
                due_date = datetime.today().date()
            
            model = ObligationModel(
                transaction_id=ob.get('transaction_id', ob.get('id', 'unknown')),
                party=ob.get('party', ob.get('counterparty', {}).get('name', 'Unknown')),
                amount=float(ob.get('amount', 0)),
                due_date=due_date,
                days_late=days_late,
                counterparty_type=cp_type,
                urgency_score=min(days_late / 30, 1.0),
                risk_score=float(ob.get('risk_score', 0.5)),
                penalty=float(ob.get('penalty', 0)),
                flexibility=flexibility,
                payment_window=payment_window,
                relationship_impact=relationship_impact,
                regulatory_risk=regulatory_risk,
                accepts_partial=accepts_partial,
                min_partial_pct=min_partial_pct,
                min_partial_amount=min_partial_amount,
                suggested_pct=suggested_pct,
                max_installments=max_installments,
                installment_days=installment_days
            )
            
            model.payment_level = model.get_payment_level()
            model.cascading_risk = model.get_cascading_risk()
            model.priority_score = model.calculate_priority_score()
            
            if model.transaction_id in self.manual_order:
                model.manual_rank = self.manual_order[model.transaction_id]
            
            models.append(model)
        
        return models
    
    def set_manual_order(self, ordered_ids: List[str]):
        """Set manual payment order"""
        for rank, tid in enumerate(ordered_ids, 1):
            self.manual_order[tid] = rank
    
    def clear_manual_order(self):
        """Clear manual order and revert to automatic"""
        self.manual_order.clear()
    
    def get_sorted_obligations(self, models: List[ObligationModel]) -> List[ObligationModel]:
        """Get obligations sorted by payment level and priority score"""
        # Sort by payment level first, then priority score
        return sorted(models, key=lambda x: (x.payment_level.value, -x.priority_score))
    
    def project_with_custom_order(self, models: List[ObligationModel], scenario_name: str = "Custom Order") -> ScenarioResult:
        """Project cash flow based on custom payment order with cascading risk"""
        remaining_cash = self.cash_balance
        actions = []
        cash_flow = [remaining_cash]
        total_penalties = 0
        risk_exposure = 0
        regulatory_risk = 0
        obligations_fulfilled = 0
        partial_payments_used = 0
        partial_payments_saved = 0
        
        sorted_models = self.get_sorted_obligations(models)
        
        for model in sorted_models:
            action, reason = model.get_recommended_action()
            
            pay_amount = model.amount
            
            if action == ActionType.PAY_PARTIALLY and model.accepts_partial:
                min_payment = max(model.min_partial_amount, model.amount * model.min_partial_pct / 100)
                suggested_payment = model.amount * model.suggested_pct / 100
                
                if remaining_cash >= model.amount:
                    pay_amount = model.amount
                elif remaining_cash >= min_payment:
                    pay_amount = suggested_payment
                else:
                    pay_amount = 0
            
            if pay_amount > 0 and remaining_cash >= pay_amount:
                remaining_cash -= pay_amount
                
                if pay_amount < model.amount:
                    partial_payments_used += 1
                    partial_payments_saved += model.amount - pay_amount
                
                actions.append({
                    'party': model.party,
                    'action': action.value,
                    'amount': pay_amount,
                    'original_amount': model.amount,
                    'is_partial': pay_amount < model.amount,
                    'payment_level': model.payment_level.value,
                    'level_name': model.payment_level.name,
                    'cascading_risk': model.cascading_risk.cascade_effect if model.cascading_risk else None,
                    'penalty_incurred': model.penalty * (pay_amount / model.amount),
                    'priority_score': model.priority_score,
                    'type': model.counterparty_type,
                    'regulatory_risk': model.regulatory_risk,
                    'manual_rank': model.manual_rank,
                    'risk_level': model.get_risk_level(),
                    'consequences': model.get_consequences_of_delay(),
                    'partial_details': model.get_partial_payment_suggestion() if pay_amount < model.amount else None,
                    'reason': reason,
                    'cash_after': remaining_cash
                })
                total_penalties += model.penalty * (pay_amount / model.amount)
                obligations_fulfilled += pay_amount / model.amount
            else:
                risk_exposure += model.amount
                regulatory_risk += model.amount * model.regulatory_risk
                actions.append({
                    'party': model.party,
                    'action': 'delay',
                    'amount': model.amount,
                    'payment_level': model.payment_level.value,
                    'level_name': model.payment_level.name,
                    'cascading_risk': model.cascading_risk.cascade_effect if model.cascading_risk else None,
                    'priority_score': model.priority_score,
                    'type': model.counterparty_type,
                    'regulatory_risk': model.regulatory_risk,
                    'manual_rank': model.manual_rank,
                    'risk_level': model.get_risk_level(),
                    'consequences': model.get_consequences_of_delay(),
                    'partial_available': model.accepts_partial,
                    'reason': 'insufficient_funds'
                })
            
            cash_flow.append(remaining_cash)
        
        # Calculate shortfall and get borrowing recommendations
        total_required = sum(m.amount for m in models)
        shortfall = max(0, total_required - self.cash_balance)
        borrowing_recommendations = []
        
        if shortfall > 0:
            borrowing_recommendations = self._get_borrowing_recommendations(shortfall, "high" if regulatory_risk > 0 else "medium")
        
        metrics = {
            'obligations_fulfilled': obligations_fulfilled,
            'obligations_delayed': len(models) - int(obligations_fulfilled),
            'cash_remaining': remaining_cash,
            'efficiency_score': obligations_fulfilled / max(len(models), 1),
            'total_penalties': total_penalties,
            'penalties_avoided': sum(m.penalty for m in models) - total_penalties,
            'regulatory_risk_score': min(regulatory_risk / max(sum(m.amount for m in models), 1), 1.0),
            'partial_payments_used': partial_payments_used,
            'partial_payments_saved': partial_payments_saved,
            'shortfall': shortfall
        }
        
        return ScenarioResult(
            scenario_name=scenario_name,
            actions=actions,
            final_cash=remaining_cash,
            total_penalties=total_penalties,
            risk_exposure=risk_exposure,
            relationship_impact=self._calculate_relationship_impact(actions),
            regulatory_risk=regulatory_risk,
            cash_flow=cash_flow,
            trade_off_justification=self._generate_justification(scenario_name, actions, metrics),
            metrics=metrics,
            partial_payments_used=partial_payments_used,
            partial_payments_saved=partial_payments_saved,
            borrowing_recommendations=borrowing_recommendations
        )
    
    def _calculate_relationship_impact(self, actions: List[Dict]) -> float:
        """Calculate relationship impact score with level weighting"""
        delayed_parties = [a.get('party') for a in actions if a.get('action') in ['delay', 'cannot_pay']]
        unique_delayed = len(set(delayed_parties))
        
        # Weight by payment level
        level_weights = {1: 1.0, 2: 0.8, 3: 0.6, 4: 0.5, 5: 0.3, 6: 0.1}
        weighted_impact = 0
        for a in actions:
            if a.get('action') in ['delay', 'cannot_pay']:
                level = a.get('payment_level', 5)
                weighted_impact += level_weights.get(level, 0.5)
        
        impact = weighted_impact / max(len(actions), 1)
        return min(impact, 1.0)
    
    def _generate_justification(self, scenario: str, actions: List[Dict], metrics: Dict) -> str:
        """Generate justification for scenario with cascading risk"""
        paid = [a for a in actions if a.get('action') not in ['delay', 'cannot_pay']]
        delayed = [a for a in actions if a.get('action') in ['delay', 'cannot_pay']]
        
        # Count by level
        level_counts = {}
        for a in delayed:
            level = a.get('payment_level', 5)
            level_name = a.get('level_name', 'UNKNOWN')
            level_counts[level_name] = level_counts.get(level_name, 0) + 1
        
        justification = f"Scenario: {scenario}\n"
        justification += f"📊 Fulfilled: {metrics.get('obligations_fulfilled', 0):.1f} obligations\n"
        justification += f"💰 Final Cash: ₹{metrics.get('cash_remaining', 0):,.2f}\n"
        justification += f"✅ Paid: {len(paid)} | ⏰ Delayed: {len(delayed)}\n"
        justification += f"💳 Partial: {metrics.get('partial_payments_used', 0)} used, saved ₹{metrics.get('partial_payments_saved', 0):,.2f}\n"
        justification += f"⚠️ Penalties: ₹{metrics.get('total_penalties', 0):,.2f}\n"
        
        if level_counts:
            justification += f"\n🚨 DELAYED BY LEVEL:\n"
            for level, count in level_counts.items():
                justification += f"   • {level}: {count} obligations\n"
        
        if metrics.get('shortfall', 0) > 0:
            justification += f"\n💰 CASH SHORTFALL: ₹{metrics['shortfall']:,.2f}\n"
        
        return justification
    
    def run_analysis_with_custom_order(self, obligations: List[Dict]) -> Dict[str, Any]:
        """Run analysis with custom payment order and cascading risk"""
        models = self.model_obligations(obligations)
        
        if not models:
            return {"error": "No valid obligations to analyze"}
        
        custom_scenario = self.project_with_custom_order(models, "Your Custom Order")
        sorted_models = self.get_sorted_obligations(models)
        regulatory_risks = [m for m in models if m.regulatory_risk > 0.8]
        
        return {
            "custom_scenario": {
                "final_cash": custom_scenario.final_cash,
                "total_penalties": custom_scenario.total_penalties,
                "risk_exposure": custom_scenario.risk_exposure,
                "regulatory_risk": custom_scenario.regulatory_risk,
                "relationship_impact": custom_scenario.relationship_impact,
                "efficiency_score": custom_scenario.metrics.get('efficiency_score', 0),
                "obligations_fulfilled": custom_scenario.metrics.get('obligations_fulfilled', 0),
                "partial_payments_used": custom_scenario.partial_payments_used,
                "partial_payments_saved": custom_scenario.partial_payments_saved,
                "shortfall": custom_scenario.metrics.get('shortfall', 0),
                "actions": custom_scenario.actions
            },
            "borrowing_recommendations": [
                {
                    "source": opt.source,
                    "amount": opt.amount,
                    "interest_rate": opt.interest_rate,
                    "repayment_days": opt.repayment_days,
                    "feasibility": opt.feasibility,
                    "pros": opt.pros,
                    "cons": opt.cons,
                    "message": opt.message
                }
                for opt in custom_scenario.borrowing_recommendations
            ],
            "current_order": [{
                "rank": i + 1,
                "transaction_id": m.transaction_id,
                "party": m.party,
                "amount": m.amount,
                "type": m.counterparty_type,
                "payment_level": m.payment_level.value,
                "level_name": m.payment_level.name,
                "cascading_risk": m.cascading_risk.cascade_effect if m.cascading_risk else None,
                "priority_score": round(m.priority_score, 3),
                "days_late": m.days_late,
                "risk_score": m.risk_score,
                "regulatory_risk": m.regulatory_risk,
                "risk_level": m.get_risk_level(),
                "consequences": m.get_consequences_of_delay(),
                "manual_rank": m.manual_rank,
                "accepts_partial": m.accepts_partial,
                "partial_min_pct": m.min_partial_pct,
                "partial_min_amount": m.min_partial_amount,
                "recommended_action": m.get_recommended_action()[0].value,
                "reason": m.get_recommended_action()[1]
            } for i, m in enumerate(sorted_models)],
            "partial_payment_summary": {
                "total_accept_partial": sum(1 for m in models if m.accepts_partial),
                "total_minimum_required": sum(max(m.min_partial_amount, m.amount * m.min_partial_pct / 100) for m in models if m.accepts_partial),
                "total_suggested_partial": sum(m.amount * m.suggested_pct / 100 for m in models if m.accepts_partial)
            },
            "cascading_risk_summary": {
                "level_1_statutory": sum(1 for m in models if m.payment_level == PaymentLevel.LEVEL_1_STATUTORY),
                "level_2_operational": sum(1 for m in models if m.payment_level == PaymentLevel.LEVEL_2_OPERATIONAL),
                "level_3_people": sum(1 for m in models if m.payment_level == PaymentLevel.LEVEL_3_PEOPLE),
                "level_4_key_supply": sum(1 for m in models if m.payment_level == PaymentLevel.LEVEL_4_KEY_SUPPLY),
                "level_5_standard": sum(1 for m in models if m.payment_level == PaymentLevel.LEVEL_5_STANDARD),
                "level_6_informal": sum(1 for m in models if m.payment_level == PaymentLevel.LEVEL_6_INFORMAL)
            },
            "regulatory_warning": {
                "has_critical_obligations": len(regulatory_risks) > 0,
                "critical_count": len(regulatory_risks),
                "critical_parties": [m.party for m in regulatory_risks],
                "message": "⚠️ CRITICAL: Government/Tax obligations must be prioritized to avoid legal consequences!"
            },
            "summary": {
                "total_obligations": len(models),
                "total_amount": sum(m.amount for m in models),
                "total_potential_penalties": sum(m.penalty for m in models),
                "current_cash": self.cash_balance
            }
        }


# Interactive CLI
def interactive_cli():
    """Interactive command-line interface with partial payment selection"""
    
    print("\n" + "="*80)
    print("INTERACTIVE PREDICTIVE DECISION ENGINE")
    print("WITH PARTIAL PAYMENT & BORROWING SUPPORT")
    print("="*80)
    print("\n📌 Features:")
    print("   • Government/Tax obligations have MAXIMUM priority!")
    print("   • Partial payment suggestions based on vendor terms")
    print("   • Real-time cash flow projection with partial payments")
    print("   • Borrowing recommendations when cash is insufficient")
    print("   • Manual reordering capability")
    print("   • Choose partial payment amounts manually\n")
    
    # Sample data with proper risk scores
    today = datetime.today().date()
    
    obligations = [
        {
            "transaction_id": "1",
            "party": "Income Tax Department",
            "amount": 50000,
            "due_date": (today - timedelta(days=10)).isoformat(),
            "days_late": 10,
            "type": "tax_authority",
            "risk_score": 0.95,
            "penalty": 5000,
            "partial_payment": {"accepts_partial": False}
        },
        {
            "transaction_id": "2",
            "party": "Raj Fabrics",
            "amount": 45000,
            "due_date": (today + timedelta(days=5)).isoformat(),
            "days_late": 0,
            "type": "vendor",
            "risk_score": 0.4,
            "penalty": 2250,
            "partial_payment": {"accepts_partial": True, "minimum_pct": 50, "minimum_amount": 5000, "suggested_pct": 50}
        },
        {
            "transaction_id": "3",
            "party": "Tech Solutions",
            "amount": 25000,
            "due_date": (today + timedelta(days=10)).isoformat(),
            "days_late": 0,
            "type": "vendor",
            "risk_score": 0.35,
            "penalty": 1250,
            "partial_payment": {"accepts_partial": True, "minimum_pct": 50, "minimum_amount": 5000, "suggested_pct": 50}
        },
        {
            "transaction_id": "4",
            "party": "Friend Loan",
            "amount": 10000,
            "due_date": (today + timedelta(days=15)).isoformat(),
            "days_late": 0,
            "type": "friend",
            "risk_score": 0.1,
            "penalty": 0,
            "partial_payment": {"accepts_partial": True, "minimum_pct": 20, "minimum_amount": 1000, "suggested_pct": 30}
        }
    ]
    
    cash_balance = 50000
    engine = PredictiveDecisionEngine(cash_balance)
    engine.models = []  # Store models for partial payment application
    
    while True:
        print("\n" + "="*80)
        print("CURRENT PAYMENT ORDER")
        print("="*80)
        
        result = engine.run_analysis_with_custom_order(obligations)
        
        if result.get('error'):
            print(f"\n❌ Error: {result['error']}")
            break
        
        if result['regulatory_warning']['has_critical_obligations']:
            print(f"\n{result['regulatory_warning']['message']}")
        
        print("\n📋 CURRENT PAYMENT ORDER:")
        print("-"*80)
        for item in result['current_order']:
            manual_indicator = "🔧 MANUAL" if item['manual_rank'] else "⚙️ AUTO"
            risk_icon = "🔴" if item['regulatory_risk'] > 0.8 else ("🟡" if item['risk_score'] > 0.6 else "🟢")
            partial_indicator = " [Partial OK]" if item['accepts_partial'] else ""
            print(f"\n   {item['rank']}. {manual_indicator} | {risk_icon} {item['party']}{partial_indicator}")
            print(f"      Amount: ₹{item['amount']:,.2f} | Type: {item['type']}")
            print(f"      Payment Level: {item.get('level_name', 'N/A')}")
            print(f"      Risk Level: {item['risk_level']}")
            print(f"      Risk Score: {item['risk_score']} | Days Late: {item['days_late']}")
            if item['accepts_partial']:
                print(f"      💳 Partial: min {item['partial_min_pct']}% (₹{item['partial_min_amount']:,.2f})")
            if item['regulatory_risk'] > 0.8:
                print(f"      🚨 {item['consequences'][:80]}...")
            print(f"      → Recommended: {item['recommended_action'].replace('_', ' ').upper()}")
        
        custom = result['custom_scenario']
        print("\n" + "="*80)
        print("📊 PROJECTED OUTCOME WITH CURRENT ORDER:")
        print("-"*80)
        print(f"   Final Cash: ₹{custom['final_cash']:,.2f}")
        print(f"   Total Penalties: ₹{custom['total_penalties']:,.2f}")
        print(f"   Risk Exposure: ₹{custom['risk_exposure']:,.2f}")
        print(f"   Partial Payments Used: {custom['partial_payments_used']} (Saved: ₹{custom['partial_payments_saved']:,.2f})")
        
        if custom.get('shortfall', 0) > 0:
            print(f"\n💰 CASH SHORTFALL DETECTED: ₹{custom['shortfall']:,.2f}")
        
        if custom['regulatory_risk'] > 0:
            print(f"   🚨 REGULATORY RISK: ₹{custom['regulatory_risk']:,.2f}")
        
        print(f"   Efficiency: {custom['efficiency_score']*100:.0f}%")
        
        # Show cascading risk summary
        cascading_summary = result.get('cascading_risk_summary', {})
        if cascading_summary:
            print(f"\n🚨 CASCADING RISK SUMMARY:")
            if cascading_summary.get('level_1_statutory', 0) > 0:
                print(f"   • Level 1 (Statutory): {cascading_summary['level_1_statutory']} obligations - LEGAL RISK")
            if cascading_summary.get('level_2_operational', 0) > 0:
                print(f"   • Level 2 (Operational): {cascading_summary['level_2_operational']} obligations - SERVICE DISRUPTION")
            if cascading_summary.get('level_3_people', 0) > 0:
                print(f"   • Level 3 (People): {cascading_summary['level_3_people']} obligations - MORALE IMPACT")
            if cascading_summary.get('level_4_key_supply', 0) > 0:
                print(f"   • Level 4 (Key Supply): {cascading_summary['level_4_key_supply']} obligations - REVENUE RISK")
        
        # Show borrowing recommendations if there's a shortfall
        borrowing_recs = result.get('borrowing_recommendations', [])
        if borrowing_recs:
            print("\n" + "="*80)
            print("💰 BORROWING RECOMMENDATIONS:")
            print("-"*80)
            for i, rec in enumerate(borrowing_recs[:3], 1):
                interest_str = f"{rec['interest_rate']}%" if rec['interest_rate'] > 0 else "No interest"
                print(f"\n   {i}. {rec['source']}:")
                print(f"      Amount: ₹{rec['amount']:,.2f}")
                print(f"      Interest: {interest_str} | Repayment: {rec['repayment_days']} days")
                print(f"      Feasibility: {rec['feasibility']*100:.0f}%")
                print(f"      💡 {rec['message']}")
        
        # Show partial payment summary
        partial_summary = result.get('partial_payment_summary', {})
        if partial_summary.get('total_accept_partial', 0) > 0:
            print("\n💳 PARTIAL PAYMENT SUMMARY:")
            print(f"   Obligations accepting partial: {partial_summary['total_accept_partial']}")
            print(f"   Minimum total required: ₹{partial_summary['total_minimum_required']:,.2f}")
            print(f"   Suggested total: ₹{partial_summary['total_suggested_partial']:,.2f}")
        
        delayed = [a for a in custom['actions'] if a.get('action') == 'delay']
        if delayed:
            print(f"\n   ⚠️ DELAYED OBLIGATIONS ({len(delayed)}):")
            for d in delayed[:3]:
                partial_note = " [Partial Available]" if d.get('partial_available') else ""
                level_note = f" [Level {d.get('payment_level', '?')}]" if d.get('payment_level') else ""
                print(f"      - {d['party']}{partial_note}{level_note}: {d.get('consequences', 'Risk of delay')[:60]}")
        
        print("\n" + "="*80)
        print("OPTIONS:")
        print("1. Reorder payments (change priority order)")
        print("2. Apply partial payment to an obligation")
        print("3. Reset to auto order")
        print("4. Change cash balance")
        print("5. Compare with optimized order")
        print("6. Exit")
        
        choice = input("\nEnter choice (1-6): ").strip()
        
        if choice == '1':
            print("\n📋 Current order:")
            for i, item in enumerate(result['current_order'], 1):
                partial_marker = " [Partial OK]" if item['accepts_partial'] else ""
                risk_marker = "🚨" if item['regulatory_risk'] > 0.8 else ""
                level_marker = f" [L{item.get('payment_level', '?')}]" if item.get('payment_level') else ""
                print(f"   {i}. {risk_marker} {item['party']}{partial_marker}{level_marker} - ₹{item['amount']:,.2f}")
            
            print("\n📝 Enter new order by listing numbers in desired sequence")
            print("   Example: 3,1,4,2")
            print("   (Press Enter to keep current order)")
            
            order_input = input("\nNew order: ").strip()
            
            if order_input:
                try:
                    order_indices = [int(x.strip()) - 1 for x in order_input.split(',')]
                    current_items = result['current_order']
                    ordered_ids = [current_items[idx]['transaction_id'] for idx in order_indices]
                    
                    all_ids = [item['transaction_id'] for item in current_items]
                    for tid in all_ids:
                        if tid not in ordered_ids:
                            ordered_ids.append(tid)
                    
                    engine.set_manual_order(ordered_ids)
                    print("\n✅ Payment order updated!")
                except (ValueError, IndexError):
                    print("\n❌ Invalid order format.")
        
        elif choice == '2':
            # Apply partial payment
            print("\n💳 PARTIAL PAYMENT OPTIONS:")
            print("-"*80)
            
            # Show obligations that accept partial payments
            partial_options = []
            for item in result['current_order']:
                if item['accepts_partial']:
                    partial_options.append(item)
                    min_payment = max(item['partial_min_amount'], item['amount'] * item['partial_min_pct'] / 100)
                    suggested_payment = item['amount'] * 50 / 100  # Default 50%
                    print(f"\n   {len(partial_options)}. {item['party']}")
                    print(f"      Amount: ₹{item['amount']:,.2f}")
                    print(f"      Min %: {item['partial_min_pct']}% (₹{min_payment:,.2f})")
                    print(f"      Suggested: 50% (₹{suggested_payment:,.2f})")
                    print(f"      Custom: Enter your own percentage")
            
            if not partial_options:
                print("   No obligations accept partial payments.")
                input("\nPress Enter to continue...")
                continue
            
            print("\n📝 Select obligation to pay partially:")
            try:
                ob_choice = int(input("Enter obligation number (or 0 to cancel): ").strip())
                if ob_choice == 0:
                    continue
                if 1 <= ob_choice <= len(partial_options):
                    selected = partial_options[ob_choice - 1]
                    
                    print(f"\n💳 Partial Payment for {selected['party']}:")
                    print(f"   Full Amount: ₹{selected['amount']:,.2f}")
                    print(f"   Minimum %: {selected['partial_min_pct']}%")
                    print(f"   Minimum Amount: ₹{max(selected['partial_min_amount'], selected['amount'] * selected['partial_min_pct'] / 100):,.2f}")
                    
                    print("\nChoose payment option:")
                    print("   1. Pay suggested amount (50%)")
                    print("   2. Pay minimum amount")
                    print("   3. Enter custom percentage")
                    print("   4. Cancel")
                    
                    pay_choice = input("\nEnter choice (1-4): ").strip()
                    
                    if pay_choice == '1':
                        percentage = 50
                        amount = selected['amount'] * 0.5
                        print(f"\n✅ Will pay 50% (₹{amount:,.2f}) now")
                        print(f"   Remaining: ₹{selected['amount'] - amount:,.2f} to be paid later")
                        
                    elif pay_choice == '2':
                        percentage = selected['partial_min_pct']
                        amount = max(selected['partial_min_amount'], selected['amount'] * percentage / 100)
                        print(f"\n✅ Will pay minimum {percentage}% (₹{amount:,.2f}) now")
                        print(f"   Remaining: ₹{selected['amount'] - amount:,.2f} to be paid later")
                        
                    elif pay_choice == '3':
                        try:
                            percentage = float(input("Enter percentage to pay (e.g., 30): ").strip())
                            if percentage < selected['partial_min_pct']:
                                print(f"❌ Percentage must be at least {selected['partial_min_pct']}%")
                                input("\nPress Enter to continue...")
                                continue
                            amount = selected['amount'] * percentage / 100
                            print(f"\n✅ Will pay {percentage}% (₹{amount:,.2f}) now")
                            print(f"   Remaining: ₹{selected['amount'] - amount:,.2f} to be paid later")
                        except ValueError:
                            print("❌ Invalid percentage")
                            input("\nPress Enter to continue...")
                            continue
                    else:
                        continue
                    
                    # Confirm and apply
                    confirm = input("\nApply this partial payment? (y/n): ").strip().lower()
                    if confirm == 'y':
                        # Update the obligation in the list
                        for ob in obligations:
                            if ob['party'] == selected['party']:
                                ob['amount'] = selected['amount'] - amount
                                ob['partial_payment_already_applied'] = True
                                print(f"\n✅ Partial payment applied! Remaining amount: ₹{ob['amount']:,.2f}")
                                break
                    else:
                        print("Cancelled.")
                    
                else:
                    print("❌ Invalid selection")
            except ValueError:
                print("❌ Invalid input")
            
            input("\nPress Enter to continue...")
        
        elif choice == '3':
            engine.clear_manual_order()
            print("\n✅ Reset to automatic order!")
        
        elif choice == '4':
            try:
                new_balance = float(input("Enter new cash balance: ₹"))
                cash_balance = new_balance
                engine.cash_balance = new_balance
                print(f"✅ Cash balance updated to ₹{new_balance:,.2f}")
            except ValueError:
                print("❌ Invalid amount")
        
        elif choice == '5':
            print("\n📊 OPTIMIZED ORDER (based on risk scores):")
            print("-"*80)
            temp_engine = PredictiveDecisionEngine(cash_balance)
            temp_result = temp_engine.run_analysis_with_custom_order(obligations)
            
            for item in temp_result['current_order']:
                partial_marker = " [Partial OK]" if item['accepts_partial'] else ""
                risk_marker = "🚨" if item['regulatory_risk'] > 0.8 else ""
                level_marker = f" [L{item.get('payment_level', '?')}]" if item.get('payment_level') else ""
                print(f"\n   {item['rank']}. {risk_marker} {item['party']}{partial_marker}{level_marker}")
                print(f"      Amount: ₹{item['amount']:,.2f}")
                print(f"      Risk Level: {item['risk_level']}")
                print(f"      Priority Score: {item['priority_score']}")
                if item['accepts_partial']:
                    print(f"      Partial: min {item['partial_min_pct']}%")
            
            print("\n💡 Optimized order considers:")
            print("   • Government/tax obligations (CRITICAL priority)")
            print("   • Days overdue and penalties")
            print("   • Partial payment availability")
            print("   • Cascading risk impact")
            print("   • Relationship impact")
            
            input("\nPress Enter to continue...")
        
        elif choice == '6':
            print("\n👋 Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")


if __name__ == "__main__":
    interactive_cli()