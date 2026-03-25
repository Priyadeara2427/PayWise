from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional, Union, Dict, Any
from datetime import datetime, date
from enum import Enum
import uuid
from decimal import Decimal

# Updated Enums to match intelligent classification
class CounterpartyType(str, Enum):
    """Extended counterparty types from intelligent classification"""
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
    BOTH = "both"  # For transactions that could be both
    UNKNOWN = "unknown"

class Priority(str, Enum):
    CRITICAL = "critical"  # For tax, government, critical payments
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
    """Penalty structure with dynamic calculation"""
    financial: float = 0.0
    relationship: float = 0.0
    total: float = 0.0
    rate: Optional[float] = None  # Penalty rate used
    days_applied: Optional[int] = None  # Days penalty applied for

class ClassificationDetails(BaseModel):
    """Details about counterparty classification"""
    type: str = "unknown"
    confidence: float = 0.0
    source: str = "auto"  # auto, explicit, fallback
    matched_keywords: Optional[List[str]] = None
    context_used: Optional[str] = None

class Decision(BaseModel):
    """Decision structure with reasoning"""
    priority: Priority
    action: Action
    reason: Optional[str] = None
    suggested_terms: Optional[Dict[str, Any]] = None  # For negotiations
    alternatives: Optional[List[str]] = None

class ExtractionMetadata(BaseModel):
    """Metadata about extraction process"""
    source_type: str  # csv, pdf, image
    extraction_confidence: float = 0.0
    has_gst: bool = False
    has_pan: bool = False
    tables_extracted: int = 0
    warnings: List[str] = Field(default_factory=list)

class Obligation(BaseModel):
    """Dynamic obligation model without hardcoded values"""
    
    # Core fields - extracted from document
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
    
    # Metadata
    note: Optional[str] = None
    source_file: Optional[str] = None
    extracted_at: datetime = Field(default_factory=datetime.now)
    raw_context: Optional[str] = None  # Store raw extracted context for debugging
    
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
            # Calculate days late
            days_late = (payment_date - due_date).days
            self.days_late = max(0, days_late)
        elif due_date and not payment_date:
            # Not paid yet, calculate as of today
            days_late = (date.today() - due_date).days
            self.days_late = max(0, days_late)
        
        return self
    
    def calculate_penalty(self, penalty_rate: float = 0.005, relationship_factor: float = 1000):
        """Calculate penalty based on days late and counterparty type"""
        if self.days_late <= 0:
            return Penalty()
        
        # Financial penalty
        financial = self.amount * penalty_rate * self.days_late
        
        # Relationship penalty based on counterparty type
        relationship = 0
        if self.days_late > 7:
            cp_type = self.classification.type if hasattr(self.classification, 'type') else 'unknown'
            
            # Higher relationship penalty for important counterparties
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
    
    def calculate_risk_score(self, custom_weights: Optional[Dict[str, float]] = None):
        """Calculate risk score based on multiple factors"""
        # Default weights
        weights = {
            'days_late': 0.4,
            'amount': 0.3,
            'counterparty_type': 0.3
        }
        if custom_weights:
            weights.update(custom_weights)
        
        # Days late factor
        days_factor = min(self.days_late / 30, 1.0) * weights['days_late']
        
        # Amount factor (assuming 100,000 as max)
        amount_factor = min(self.amount / 100000, 1.0) * weights['amount']
        
        # Counterparty type factor
        cp_type = self.classification.type if hasattr(self.classification, 'type') else 'unknown'
        type_risk = {
            'tax_authority': 1.0,
            'government': 0.9,
            'bank': 0.85,
            'vendor': 0.8,
            'employee': 0.75,
            'utility': 0.7,
            'rent': 0.65,
            'customer': 0.5,
            'insurance': 0.6,
            'investment': 0.55,
            'friend': 0.3,
            'family': 0.25,
            'charity': 0.2,
            'unknown': 0.5
        }
        type_factor = type_risk.get(cp_type, 0.5) * weights['counterparty_type']
        
        risk_score = days_factor + amount_factor + type_factor
        self.risk_score = round(min(risk_score, 1.0), 2)
        return self.risk_score
    
    def generate_decision(self):
        """Generate decision based on risk score and counterparty type"""
        from backend.engine.decision_engine import DecisionEngine
        # This would be handled by the decision engine
        pass
    
    class Config:
        json_encoders = {
            date: lambda v: v.isoformat(),
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: float(v)
        }
        arbitrary_types_allowed = True

class FinancialState(BaseModel):
    """Dynamic financial state without hardcoded values"""
    cash_balance: float
    obligations: List[Obligation] = Field(default_factory=list)
    as_of_date: date = Field(default_factory=date.today)
    decisions: Optional[List[Dict[str, Any]]] = None  # Add this field
    
    # Calculated fields
    total_payables: float = 0.0
    total_receivables: float = 0.0
    total_penalties: float = 0.0
    high_risk_count: int = 0
    medium_risk_count: int = 0
    low_risk_count: int = 0
    
    # Classification statistics
    type_distribution: Dict[str, int] = Field(default_factory=dict)
    
    # Metadata
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
            # Sum amounts based on transaction type
            if hasattr(ob, 'transaction_type') and ob.transaction_type:
                if ob.transaction_type == TransactionType.PAYABLE:
                    total_payables += ob.amount
                elif ob.transaction_type == TransactionType.RECEIVABLE:
                    total_receivables += ob.amount
                elif ob.transaction_type == TransactionType.BOTH:
                    # For ambiguous transactions, default to payable
                    total_payables += ob.amount
            else:
                # Fallback: infer from counterparty type
                cp_type = ob.classification.type if hasattr(ob.classification, 'type') else 'unknown'
                if cp_type in ['vendor', 'tax_authority', 'government', 'utility', 'rent']:
                    total_payables += ob.amount
                elif cp_type in ['customer', 'client']:
                    total_receivables += ob.amount
                else:
                    total_payables += ob.amount  # Default to payable
            
            # Sum penalties
            total_penalties += ob.penalty.total
            
            # Count risk levels
            if ob.risk_score >= 0.7:
                high_risk_count += 1
            elif ob.risk_score >= 0.4:
                medium_risk_count += 1
            else:
                low_risk_count += 1
            
            # Count types
            cp_type = ob.classification.type if hasattr(ob.classification, 'type') else 'unknown'
            type_distribution[cp_type] = type_distribution.get(cp_type, 0) + 1
        
        self.total_payables = total_payables
        self.total_receivables = total_receivables
        self.total_penalties = total_penalties
        self.high_risk_count = high_risk_count
        self.medium_risk_count = medium_risk_count
        self.low_risk_count = low_risk_count
        self.type_distribution = type_distribution
        
        return self
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the financial state"""
        return {
            "total_obligations": len(self.obligations),
            "total_payables": self.total_payables,
            "total_receivables": self.total_receivables,
            "net_position": self.total_receivables - self.total_payables,
            "total_penalties": self.total_penalties,
            "cash_balance": self.cash_balance,
            "liquidity_status": "positive" if self.cash_balance > self.total_payables else "negative",
            "risk_distribution": {
                "high": self.high_risk_count,
                "medium": self.medium_risk_count,
                "low": self.low_risk_count
            },
            "counterparty_types": self.type_distribution
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with proper serialization"""
        return self.model_dump(exclude_none=True)
    
    class Config:
        json_encoders = {
            date: lambda v: v.isoformat(),
            datetime: lambda v: v.isoformat()
        }

# Helper functions for creating obligations from extracted data
def create_obligation_from_extracted(extracted_data: Dict[str, Any]) -> Obligation:
    """Create an Obligation from extracted parser data"""
    return Obligation(
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

class ObligationList(BaseModel):
    """Helper model for batch operations"""
    obligations: List[Obligation]
    total_count: int = 0
    total_amount: float = 0.0
    by_type: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    
    @model_validator(mode='after')
    def calculate_totals(self):
        """Calculate totals based on obligations"""
        self.total_count = len(self.obligations)
        self.total_amount = sum(ob.amount for ob in self.obligations)
        
        # Group by type
        by_type = {}
        for ob in self.obligations:
            cp_type = ob.classification.type
            if cp_type not in by_type:
                by_type[cp_type] = {'count': 0, 'total_amount': 0}
            by_type[cp_type]['count'] += 1
            by_type[cp_type]['total_amount'] += ob.amount
        
        self.by_type = by_type
        return self
    
    class Config:
        json_encoders = {
            date: lambda v: v.isoformat(),
            datetime: lambda v: v.isoformat()
        }