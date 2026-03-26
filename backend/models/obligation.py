from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional, Union, Dict, Any, Tuple
from datetime import datetime, date
from enum import Enum
import uuid
from decimal import Decimal

class CounterpartyType(str, Enum):
    VENDOR = "vendor"
    CUSTOMER = "customer"
    TAX_AUTHORITY = "tax_authority"
    GOVERNMENT = "government"
    EMPLOYEE = "employee"
    FRIEND = "friend"
    FAMILY = "family"
    BANK = "bank"
    UTILITY = "utility"
    RENT = "rent"
    INSURANCE = "insurance"
    INVESTMENT = "investment"
    CHARITY = "charity"
    UNKNOWN = "unknown"

class TransactionType(str, Enum):
    PAYABLE = "payable"
    RECEIVABLE = "receivable"
    BOTH = "both"
    UNKNOWN = "unknown"

class Priority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class Action(str, Enum):
    PAY_IMMEDIATELY = "pay_immediately"
    NEGOTIATE_EXTENSION = "negotiate_deadline_extension"
    PAY_PARTIALLY = "pay_partially"
    ESCALATE = "escalate"
    IGNORE = "ignore"
    REVIEW = "review"
    COMMUNICATE = "communicate"

class Penalty(BaseModel):
    financial: float = 0.0
    relationship: float = 0.0
    total: float = 0.0
    rate: Optional[float] = None
    days_applied: Optional[int] = None

class PartialPaymentHistory(BaseModel):
    """History of partial payment negotiations"""
    date: date
    amount_paid: float
    amount_remaining: float
    status: str  # "proposed", "accepted", "rejected", "completed"
    notes: Optional[str] = None

class PartialPaymentTerms(BaseModel):
    """Partial payment terms for an obligation"""
    accepts_partial: bool = True
    minimum_partial_pct: float = 0.0  # Minimum percentage they accept
    minimum_partial_amount: float = 0.0  # Minimum absolute amount
    suggested_pct: float = 50.0  # Suggested percentage to offer
    max_installments: int = 1  # Maximum number of installments
    installment_days: int = 15  # Days between installments
    history: List[PartialPaymentHistory] = Field(default_factory=list)
    last_negotiation: Optional[date] = None
    notes: Optional[str] = None

class ClassificationDetails(BaseModel):
    type: str = "unknown"
    confidence: float = 0.0
    source: str = "auto"
    matched_keywords: Optional[List[str]] = None
    context_used: Optional[str] = None

class Decision(BaseModel):
    priority: Priority
    action: Action
    reason: Optional[str] = None
    suggested_terms: Optional[Dict[str, Any]] = None
    alternatives: Optional[List[str]] = None

class ExtractionMetadata(BaseModel):
    source_type: str
    extraction_confidence: float = 0.0
    has_gst: bool = False
    has_pan: bool = False
    tables_extracted: int = 0
    warnings: List[str] = Field(default_factory=list)

class Obligation(BaseModel):
    """Dynamic obligation model with partial payment support"""
    
    # Core fields
    transaction_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    counterparty: Dict[str, Any] = Field(default_factory=dict)
    amount: float
    due_date: date
    
    # Optional extracted fields
    payment_date: Optional[date] = None
    invoice_number: Optional[str] = None
    description: Optional[str] = None
    gstin: Optional[str] = None
    pan: Optional[str] = None
    
    # Calculated fields
    days_late: int = 0
    penalty: Penalty = Field(default_factory=Penalty)
    risk_score: float = 0.0
    
    # Decision fields
    decision: Optional[Decision] = None
    
    # Classification fields
    classification: ClassificationDetails = Field(default_factory=ClassificationDetails)
    transaction_type: TransactionType = TransactionType.UNKNOWN
    
    # Partial payment fields - NEW
    partial_payment: PartialPaymentTerms = Field(default_factory=PartialPaymentTerms)
    
    # Metadata
    note: Optional[str] = None
    source_file: Optional[str] = None
    extracted_at: datetime = Field(default_factory=datetime.now)
    raw_context: Optional[str] = None
    
    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Amount must be positive')
        return v
    
    @field_validator('risk_score')
    @classmethod
    def validate_risk_score(cls, v):
        if v < 0 or v > 1:
            raise ValueError('Risk score must be between 0 and 1')
        return v
    
    @model_validator(mode='after')
    def validate_dates(self):
        """Validate date consistency"""
        due_date = self.due_date
        payment_date = self.payment_date
        
        if due_date and payment_date:
            days_late = (payment_date - due_date).days
            self.days_late = max(0, days_late)
        elif due_date and not payment_date:
            days_late = (date.today() - due_date).days
            self.days_late = max(0, days_late)
        
        return self
    
    def infer_partial_terms(self):
        """Infer partial payment terms from counterparty type and context"""
        cp_type = self.classification.type
        
        # Default terms by counterparty type
        terms_map = {
            'vendor': {
                'accepts_partial': True,
                'minimum_partial_pct': 50,
                'minimum_partial_amount': 5000,
                'suggested_pct': 50,
                'max_installments': 2,
                'installment_days': 15,
                'notes': 'Many vendors accept partial payments with prior agreement'
            },
            'customer': {
                'accepts_partial': True,
                'minimum_partial_pct': 30,
                'minimum_partial_amount': 1000,
                'suggested_pct': 30,
                'max_installments': 3,
                'installment_days': 10,
                'notes': 'Customers often flexible with payment terms'
            },
            'tax_authority': {
                'accepts_partial': False,
                'minimum_partial_pct': 100,
                'minimum_partial_amount': self.amount,
                'suggested_pct': 100,
                'max_installments': 1,
                'installment_days': 0,
                'notes': 'Tax payments must be made in full'
            },
            'government': {
                'accepts_partial': False,
                'minimum_partial_pct': 100,
                'minimum_partial_amount': self.amount,
                'suggested_pct': 100,
                'max_installments': 1,
                'installment_days': 0,
                'notes': 'Government payments require full amount'
            },
            'bank': {
                'accepts_partial': False,
                'minimum_partial_pct': 100,
                'minimum_partial_amount': self.amount,
                'suggested_pct': 100,
                'max_installments': 1,
                'installment_days': 0,
                'notes': 'Loan EMIs require full payment'
            },
            'employee': {
                'accepts_partial': False,
                'minimum_partial_pct': 100,
                'minimum_partial_amount': self.amount,
                'suggested_pct': 100,
                'max_installments': 1,
                'installment_days': 0,
                'notes': 'Salary must be paid in full'
            },
            'utility': {
                'accepts_partial': True,
                'minimum_partial_pct': 70,
                'minimum_partial_amount': 500,
                'suggested_pct': 70,
                'max_installments': 2,
                'installment_days': 7,
                'notes': 'Utilities may accept partial payments to avoid disconnection'
            },
            'rent': {
                'accepts_partial': True,
                'minimum_partial_pct': 60,
                'minimum_partial_amount': 5000,
                'suggested_pct': 60,
                'max_installments': 2,
                'installment_days': 15,
                'notes': 'Landlords may accept partial rent with agreement'
            },
            'friend': {
                'accepts_partial': True,
                'minimum_partial_pct': 20,
                'minimum_partial_amount': 1000,
                'suggested_pct': 30,
                'max_installments': 4,
                'installment_days': 7,
                'notes': 'Friends usually flexible with payments'
            },
            'family': {
                'accepts_partial': True,
                'minimum_partial_pct': 10,
                'minimum_partial_amount': 500,
                'suggested_pct': 20,
                'max_installments': 6,
                'installment_days': 7,
                'notes': 'Family members often understanding'
            },
            'insurance': {
                'accepts_partial': False,
                'minimum_partial_pct': 100,
                'minimum_partial_amount': self.amount,
                'suggested_pct': 100,
                'max_installments': 1,
                'installment_days': 0,
                'notes': 'Insurance premiums require full payment'
            },
            'investment': {
                'accepts_partial': True,
                'minimum_partial_pct': 50,
                'minimum_partial_amount': 5000,
                'suggested_pct': 50,
                'max_installments': 3,
                'installment_days': 15,
                'notes': 'Investment firms may accept structured payments'
            },
            'charity': {
                'accepts_partial': True,
                'minimum_partial_pct': 25,
                'minimum_partial_amount': 1000,
                'suggested_pct': 25,
                'max_installments': 4,
                'installment_days': 30,
                'notes': 'Charities often accept flexible donations'
            },
            'unknown': {
                'accepts_partial': True,
                'minimum_partial_pct': 50,
                'minimum_partial_amount': 5000,
                'suggested_pct': 50,
                'max_installments': 2,
                'installment_days': 15,
                'notes': 'Negotiate partial payment terms'
            }
        }
        
        terms = terms_map.get(cp_type, terms_map['unknown'])
        
        # Adjust based on amount
        if self.amount < terms['minimum_partial_amount']:
            terms['minimum_partial_amount'] = self.amount * 0.5
        
        self.partial_payment = PartialPaymentTerms(
            accepts_partial=terms['accepts_partial'],
            minimum_partial_pct=terms['minimum_partial_pct'],
            minimum_partial_amount=terms['minimum_partial_amount'],
            suggested_pct=terms['suggested_pct'],
            max_installments=terms['max_installments'],
            installment_days=terms['installment_days'],
            notes=terms['notes']
        )
        
        return self.partial_payment
    
    def can_pay_partial(self, proposed_amount: float) -> Tuple[bool, str]:
        """Check if partial payment is acceptable"""
        if not self.partial_payment.accepts_partial:
            return False, f"{self.counterparty.get('name')} does not accept partial payments"
        
        pct = (proposed_amount / self.amount) * 100
        
        if pct < self.partial_payment.minimum_partial_pct:
            return False, f"Minimum partial payment is {self.partial_payment.minimum_partial_pct}% (₹{self.partial_payment.minimum_partial_amount:,.2f})"
        
        if proposed_amount < self.partial_payment.minimum_partial_amount:
            return False, f"Minimum partial amount is ₹{self.partial_payment.minimum_partial_amount:,.2f}"
        
        return True, "Partial payment acceptable"
    
    def add_partial_history(self, amount_paid: float, status: str, notes: str = None):
        """Add entry to partial payment history"""
        remaining = self.amount - amount_paid - sum(h.amount_paid for h in self.partial_payment.history)
        
        history_entry = PartialPaymentHistory(
            date=date.today(),
            amount_paid=amount_paid,
            amount_remaining=remaining,
            status=status,
            notes=notes
        )
        
        self.partial_payment.history.append(history_entry)
        self.partial_payment.last_negotiation = date.today()
    
    def calculate_penalty(self, penalty_rate: float = 0.005, relationship_factor: float = 1000):
        """Calculate penalty based on days late and counterparty type"""
        if self.days_late <= 0:
            return Penalty()
        
        financial = self.amount * penalty_rate * self.days_late
        
        relationship = 0
        if self.days_late > 7:
            cp_type = self.classification.type
            if cp_type in ['vendor', 'tax_authority', 'government', 'bank']:
                relationship = self.days_late * relationship_factor
            elif cp_type in ['customer', 'client']:
                relationship = self.days_late * (relationship_factor * 0.5)
            elif cp_type in ['friend', 'family']:
                relationship = self.days_late * (relationship_factor * 0.1)
        
        return Penalty(
            financial=round(financial, 2),
            relationship=round(relationship, 2),
            total=round(financial + relationship, 2),
            rate=penalty_rate,
            days_applied=self.days_late
        )
    
    class Config:
        json_encoders = {
            date: lambda v: v.isoformat(),
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: float(v)
        }
        arbitrary_types_allowed = True


class FinancialState(BaseModel):
    """Dynamic financial state"""
    cash_balance: float
    obligations: List[Obligation] = Field(default_factory=list)
    as_of_date: date = Field(default_factory=date.today)
    decisions: Optional[List[Dict[str, Any]]] = None
    
    total_payables: float = 0.0
    total_receivables: float = 0.0
    total_penalties: float = 0.0
    high_risk_count: int = 0
    medium_risk_count: int = 0
    low_risk_count: int = 0
    
    type_distribution: Dict[str, int] = Field(default_factory=dict)
    extraction_metadata: Optional[ExtractionMetadata] = None
    
    @model_validator(mode='after')
    def calculate_totals(self):
        """Calculate totals based on obligations"""
        total_payables = 0.0
        total_receivables = 0.0
        total_penalties = 0.0
        high_risk_count = 0
        medium_risk_count = 0
        low_risk_count = 0
        type_distribution = {}
        
        for ob in self.obligations:
            if ob.transaction_type == TransactionType.PAYABLE:
                total_payables += ob.amount
            elif ob.transaction_type == TransactionType.RECEIVABLE:
                total_receivables += ob.amount
            
            total_penalties += ob.penalty.total
            
            if ob.risk_score >= 0.7:
                high_risk_count += 1
            elif ob.risk_score >= 0.4:
                medium_risk_count += 1
            else:
                low_risk_count += 1
            
            cp_type = ob.classification.type
            type_distribution[cp_type] = type_distribution.get(cp_type, 0) + 1
        
        self.total_payables = total_payables
        self.total_receivables = total_receivables
        self.total_penalties = total_penalties
        self.high_risk_count = high_risk_count
        self.medium_risk_count = medium_risk_count
        self.low_risk_count = low_risk_count
        self.type_distribution = type_distribution
        
        return self


def create_obligation_from_extracted(extracted_data: Dict[str, Any]) -> Obligation:
    """Create an Obligation from extracted parser data with partial terms"""
    obligation = Obligation(
        amount=extracted_data.get('amount', 0.0),
        due_date=extracted_data.get('due_date', date.today()),
        counterparty=extracted_data.get('counterparty', {'name': 'Unknown'}),
        payment_date=extracted_data.get('payment_date'),
        description=extracted_data.get('description'),
        invoice_number=extracted_data.get('invoice_number'),
        gstin=extracted_data.get('gstin'),
        pan=extracted_data.get('pan'),
        note=extracted_data.get('note'),
        source_file=extracted_data.get('source_file'),
        raw_context=extracted_data.get('context'),
        classification=ClassificationDetails(
            type=extracted_data.get('counterparty', {}).get('type', 'unknown'),
            confidence=extracted_data.get('counterparty', {}).get('classification_confidence', 0.0),
            source='auto',
            matched_keywords=extracted_data.get('matched_keywords', []),
            context_used=extracted_data.get('context')
        ),
        transaction_type=TransactionType(extracted_data.get('txn_type', 'unknown'))
    )
    
    # Infer partial payment terms
    obligation.infer_partial_terms()
    
    return obligation