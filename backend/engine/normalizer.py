from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional
import re
from decimal import Decimal
import logging

from ..models.obligation import Obligation, Penalty, FinancialState, CounterpartyType

logger = logging.getLogger(__name__)

class DataNormalizer:
    """Enhanced data normalizer with smart inference and validation"""
    
    DEFAULT_PENALTY_RATE = 0.005  # 0.5% per day default
    RELATIONSHIP_PENALTY_FACTOR = 1000  # Base relationship penalty per day
    
    @classmethod
    def normalize_obligation(cls, raw_data: Dict[str, Any], source_file: Optional[str] = None) -> Obligation:
        """Convert raw extracted data to structured Obligation"""
        
        # Apply smart defaults and inferences
        normalized = cls._apply_defaults(raw_data)
        normalized = cls._infer_missing_fields(normalized)
        
        # Create obligation
        obligation = Obligation(
            counterparty=normalized.get('counterparty', {'name': 'Unknown', 'type': 'unknown'}),
            amount=normalized.get('amount', 0.0),
            due_date=normalized.get('due_date', date.today()),
            payment_date=normalized.get('payment_date'),
            source_file=source_file,
            note=normalized.get('note')
        )
        
        # Calculate derived fields
        obligation.days_late = cls._calculate_days_late(obligation.due_date, obligation.payment_date)
        obligation.penalty = cls._calculate_penalty(obligation.amount, obligation.days_late, normalized.get('penalty_rate', cls.DEFAULT_PENALTY_RATE))
        obligation.risk_score = cls._calculate_risk_score(obligation)
        
        return obligation
    
    @classmethod
    def _apply_defaults(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply smart defaults for missing fields"""
        defaults = {
            'counterparty': {'name': 'Unknown', 'type': 'unknown'},
            'amount': 0.0,
            'due_date': date.today(),
            'penalty_rate': cls.DEFAULT_PENALTY_RATE
        }
        
        for key, default_value in defaults.items():
            if key not in data or data[key] is None:
                data[key] = default_value
        
        return data
    
    @classmethod
    def _infer_missing_fields(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Infer missing values from available data"""
        
        # Infer counterparty type from name if missing
        if data['counterparty']['type'] == 'unknown' and data['counterparty']['name'] != 'Unknown':
            data['counterparty']['type'] = cls._infer_counterparty_type(data['counterparty']['name'])
        
        # Infer payment date if missing (assuming not paid yet)
        if 'payment_date' not in data or data['payment_date'] is None:
            data['payment_date'] = None
            data['note'] = (data.get('note', '') + " Payment date not provided, assuming not paid.").strip()
        
        # Validate and clean amount
        if isinstance(data['amount'], str):
            data['amount'] = cls._parse_amount(data['amount'])
        
        # Convert date strings to date objects
        for date_field in ['due_date', 'payment_date']:
            if date_field in data and isinstance(data[date_field], str):
                data[date_field] = cls._parse_date(data[date_field])
        
        return data
    
    @staticmethod
    def _infer_counterparty_type(name: str) -> str:
        """Infer counterparty type from name"""
        name_lower = name.lower()
        vendor_keywords = ['vendor', 'supplier', 'enterprises', 'industries', 'trading', 'fabrics']
        customer_keywords = ['customer', 'client', 'retail', 'store', 'mart']
        
        if any(keyword in name_lower for keyword in vendor_keywords):
            return 'vendor'
        elif any(keyword in name_lower for keyword in customer_keywords):
            return 'customer'
        return 'unknown'
    
    @staticmethod
    def _parse_amount(amount_str: str) -> float:
        """Parse amount from various string formats"""
        # Remove currency symbols and commas
        cleaned = re.sub(r'[^\d.-]', '', amount_str.strip())
        try:
            return float(cleaned)
        except ValueError:
            return 0.0
    
    @staticmethod
    def _parse_date(date_str: str) -> date:
        """Parse date from various string formats"""
        date_formats = [
            '%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', 
            '%d-%m-%Y', '%m-%d-%Y', '%d %b %Y', '%b %d %Y'
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue
        
        # If all formats fail, return today
        logger.warning(f"Could not parse date: {date_str}, using today")
        return date.today()
    
    @staticmethod
    def _calculate_days_late(due_date: date, payment_date: Optional[date] = None) -> int:
        """Calculate number of days late"""
        if payment_date is None:
            payment_date = date.today()
        
        days_late = (payment_date - due_date).days
        return max(0, days_late)
    
    @classmethod
    def _calculate_penalty(cls, amount: float, days_late: int, penalty_rate: float) -> Penalty:
        """Calculate financial and relationship penalties"""
        financial = amount * penalty_rate * days_late
        relationship = days_late * cls.RELATIONSHIP_PENALTY_FACTOR if days_late > 7 else 0
        
        return Penalty(
            financial=round(financial, 2),
            relationship=round(relationship, 2),
            total=round(financial + relationship, 2)
        )
    
    @classmethod
    def _calculate_risk_score(cls, obligation: Obligation) -> float:
        """Calculate risk score based on multiple factors"""
        risk = 0.0
        
        # Days late factor (up to 0.4)
        days_factor = min(obligation.days_late / 30, 1.0) * 0.4
        risk += days_factor
        
        # Amount factor (up to 0.3)
        amount_factor = min(obligation.amount / 100000, 1.0) * 0.3
        risk += amount_factor
        
        # Counterparty factor (up to 0.3)
        if obligation.counterparty.get('type') == 'vendor':
            risk += 0.2  # Vendor delays are more critical
        elif obligation.counterparty.get('type') == 'customer':
            risk += 0.1
        
        return round(min(risk, 1.0), 2)
    
    @classmethod
    def normalize_batch(cls, raw_obligations: List[Dict[str, Any]], source_file: Optional[str] = None) -> List[Obligation]:
        """Normalize a batch of obligations"""
        normalized = []
        for raw in raw_obligations:
            try:
                obligation = cls.normalize_obligation(raw, source_file)
                normalized.append(obligation)
            except Exception as e:
                logger.error(f"Failed to normalize obligation: {e}")
                continue
        return normalized
    
    @classmethod
    def create_financial_state(cls, obligations: List[Obligation], cash_balance: float = 0.0) -> FinancialState:
        """Create FinancialState from list of obligations"""
        payables = [o for o in obligations if o.counterparty.get('type') == 'vendor']
        receivables = [o for o in obligations if o.counterparty.get('type') == 'customer']
        
        total_payables = sum(o.amount for o in payables)
        total_receivables = sum(o.amount for o in receivables)
        total_penalties = sum(o.penalty.total for o in obligations)
        high_risk_count = sum(1 for o in obligations if o.risk_score >= 0.7)
        
        return FinancialState(
            cash_balance=cash_balance,
            obligations=obligations,
            as_of_date=date.today(),
            total_payables=total_payables,
            total_receivables=total_receivables,
            total_penalties=total_penalties,
            high_risk_count=high_risk_count
        )