from datetime import datetime, date, timedelta
from typing import Dict, List, Any, Optional
import re
from decimal import Decimal
import logging

from ..models.obligation import Obligation, Penalty, FinancialState, CounterpartyType, PartialPaymentTerms, PartialPaymentHistory

logger = logging.getLogger(__name__)

class DataNormalizer:
    """Enhanced data normalizer with smart inference, validation, and partial payment handling"""
    
    DEFAULT_PENALTY_RATE = 0.005  # 0.5% per day default
    RELATIONSHIP_PENALTY_FACTOR = 1000  # Base relationship penalty per day
    
    @classmethod
    def normalize_obligation(cls, raw_data: Dict[str, Any], source_file: Optional[str] = None) -> Obligation:
        """Convert raw extracted data to structured Obligation with partial payment terms"""
        
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
            note=normalized.get('note'),
            invoice_number=normalized.get('invoice_number'),
            gstin=normalized.get('gstin'),
            pan=normalized.get('pan'),
            description=normalized.get('description')
        )
        
        # Set partial payment terms
        if 'partial_payment' in normalized:
            partial_data = normalized['partial_payment']
            obligation.partial_payment = PartialPaymentTerms(
                accepts_partial=partial_data.get('accepts_partial', True),
                minimum_partial_pct=partial_data.get('minimum_partial_pct', 50.0),
                minimum_partial_amount=partial_data.get('minimum_partial_amount', 5000.0),
                suggested_pct=partial_data.get('suggested_pct', 50.0),
                max_installments=partial_data.get('max_installments', 1),
                installment_days=partial_data.get('installment_days', 15),
                notes=partial_data.get('notes', ''),
                history=partial_data.get('history', [])
            )
        else:
            # Infer partial terms from counterparty type
            obligation.infer_partial_terms()
        
        # Calculate derived fields
        obligation.days_late = cls._calculate_days_late(obligation.due_date, obligation.payment_date)
        obligation.penalty = cls._calculate_penalty(obligation.amount, obligation.days_late, 
                                                     normalized.get('penalty_rate', cls.DEFAULT_PENALTY_RATE))
        obligation.risk_score = cls._calculate_risk_score(obligation)
        
        # Set transaction type based on counterparty
        if obligation.counterparty.get('type') in ['vendor', 'tax_authority', 'government', 'bank', 'employee', 'utility', 'rent']:
            obligation.transaction_type = 'payable'
        elif obligation.counterparty.get('type') in ['customer', 'client']:
            obligation.transaction_type = 'receivable'
        
        return obligation
    
    @classmethod
    def _apply_defaults(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply smart defaults for missing fields"""
        defaults = {
            'counterparty': {'name': 'Unknown', 'type': 'unknown'},
            'amount': 0.0,
            'due_date': date.today(),
            'penalty_rate': cls.DEFAULT_PENALTY_RATE,
            'partial_payment': {
                'accepts_partial': True,
                'minimum_partial_pct': 50.0,
                'minimum_partial_amount': 5000.0,
                'suggested_pct': 50.0,
                'max_installments': 1,
                'installment_days': 15,
                'notes': '',
                'history': []
            }
        }
        
        for key, default_value in defaults.items():
            if key not in data or data[key] is None:
                data[key] = default_value
        
        # Merge partial payment defaults if partial_payment exists but missing fields
        if 'partial_payment' in data and isinstance(data['partial_payment'], dict):
            for subkey, subdefault in defaults['partial_payment'].items():
                if subkey not in data['partial_payment']:
                    data['partial_payment'][subkey] = subdefault
        
        return data
    
    @classmethod
    def _infer_missing_fields(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Infer missing values from available data"""
        
        # Infer counterparty type from name if missing
        if data['counterparty']['type'] == 'unknown' and data['counterparty']['name'] != 'Unknown':
            data['counterparty']['type'] = cls._infer_counterparty_type(
                data['counterparty']['name'], 
                data.get('context', '')
            )
        
        # If we have classification confidence from parser, use it
        if 'classification_confidence' in data.get('counterparty', {}):
            data['counterparty']['classification_confidence'] = data['counterparty']['classification_confidence']
        
        # Infer payment date if missing (assuming not paid yet)
        if 'payment_date' not in data or data['payment_date'] is None:
            data['payment_date'] = None
            if data.get('note'):
                data['note'] = data['note'] + " Payment date not provided, assuming not paid."
            else:
                data['note'] = "Payment date not provided, assuming not paid."
        
        # Validate and clean amount
        if isinstance(data['amount'], str):
            data['amount'] = cls._parse_amount(data['amount'])
        
        # Convert date strings to date objects
        for date_field in ['due_date', 'payment_date']:
            if date_field in data and isinstance(data[date_field], str):
                data[date_field] = cls._parse_date(data[date_field])
        
        # Adjust partial payment terms based on amount
        if 'partial_payment' in data:
            amount = data['amount']
            partial = data['partial_payment']
            
            # Ensure minimum amount is not greater than the obligation amount
            if partial.get('minimum_partial_amount', 0) > amount:
                partial['minimum_partial_amount'] = amount * (partial.get('minimum_partial_pct', 50) / 100)
            
            # Suggested percentage shouldn't be less than minimum
            if partial.get('suggested_pct', 50) < partial.get('minimum_partial_pct', 50):
                partial['suggested_pct'] = partial['minimum_partial_pct']
        
        # Infer if this is a critical payment based on type
        if data['counterparty'].get('type') in ['tax_authority', 'government']:
            data['is_critical'] = True
        
        return data
    
    @staticmethod
    def _infer_counterparty_type(name: str, context: str = "") -> str:
        """Infer counterparty type from name and context"""
        name_lower = name.lower()
        context_lower = context.lower()
        combined = f"{name_lower} {context_lower}"
        
        # Government/Tax indicators
        if any(word in combined for word in ['tax', 'gst', 'income tax', 'govt', 'government', 'municipal']):
            if 'tax' in combined or 'gst' in combined:
                return 'tax_authority'
            return 'government'
        
        # Bank/Financial indicators
        if any(word in combined for word in ['bank', 'hdfc', 'sbi', 'icici', 'axis', 'loan', 'emi']):
            return 'bank'
        
        # Utility indicators
        if any(word in combined for word in ['electricity', 'water', 'gas', 'broadband', 'internet', 'phone']):
            return 'utility'
        
        # Rent indicators
        if any(word in combined for word in ['rent', 'lease', 'landlord', 'property']):
            return 'rent'
        
        # Employee/Salary indicators
        if any(word in combined for word in ['salary', 'wages', 'employee', 'staff', 'payroll']):
            return 'employee'
        
        # Vendor/Supplier indicators
        vendor_keywords = ['vendor', 'supplier', 'enterprises', 'industries', 'trading', 'fabrics', 
                          'solutions', 'technologies', 'services', 'pvt ltd', 'ltd', 'llp']
        if any(keyword in name_lower for keyword in vendor_keywords):
            return 'vendor'
        
        # Customer indicators
        customer_keywords = ['customer', 'client', 'retail', 'store', 'mart', 'shop']
        if any(keyword in name_lower for keyword in customer_keywords):
            return 'customer'
        
        # Friend/Family indicators
        if any(word in combined for word in ['friend', 'family', 'brother', 'sister', 'relative']):
            if 'friend' in combined:
                return 'friend'
            return 'family'
        
        # Charity indicators
        if any(word in combined for word in ['charity', 'ngo', 'foundation', 'trust', 'non-profit']):
            return 'charity'
        
        # Investment indicators
        if any(word in combined for word in ['investment', 'mutual fund', 'stock', 'share', 'broker']):
            return 'investment'
        
        # Insurance indicators
        if any(word in combined for word in ['insurance', 'policy', 'premium', 'lic']):
            return 'insurance'
        
        return 'unknown'
    
    @staticmethod
    def _parse_amount(amount_str: str) -> float:
        """Parse amount from various string formats"""
        # Remove currency symbols and commas
        cleaned = re.sub(r'[^\d.-]', '', amount_str.strip())
        try:
            return float(cleaned)
        except ValueError:
            logger.warning(f"Could not parse amount: {amount_str}")
            return 0.0
    
    @staticmethod
    def _parse_date(date_str: str) -> date:
        """Parse date from various string formats"""
        date_formats = [
            '%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', 
            '%d-%m-%Y', '%m-%d-%Y', '%d %b %Y', '%b %d %Y',
            '%d/%m/%y', '%d-%m-%y', '%d %b %y'
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
            total=round(financial + relationship, 2),
            rate=penalty_rate,
            days_applied=days_late
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
        
        # Counterparty type factor (up to 0.3)
        cp_type = obligation.counterparty.get('type', 'unknown')
        type_risk = {
            'tax_authority': 0.3,
            'government': 0.3,
            'bank': 0.25,
            'employee': 0.25,
            'vendor': 0.2,
            'utility': 0.15,
            'rent': 0.15,
            'insurance': 0.12,
            'investment': 0.1,
            'customer': 0.1,
            'friend': 0.05,
            'family': 0.03,
            'charity': 0.02,
            'unknown': 0.1
        }
        risk += type_risk.get(cp_type, 0.1)
        
        # Regulatory risk factor (additional for critical payments)
        if cp_type in ['tax_authority', 'government'] and obligation.days_late > 0:
            risk += 0.2
        
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
                logger.debug(f"Raw data: {raw}")
                continue
        return normalized
    
    @classmethod
    def create_financial_state(cls, obligations: List[Obligation], cash_balance: float = 0.0) -> FinancialState:
        """Create FinancialState from list of obligations with enhanced categorization"""
        
        # Categorize obligations
        payables = []
        receivables = []
        
        for o in obligations:
            cp_type = o.counterparty.get('type', 'unknown')
            
            # Determine if payable or receivable
            if cp_type in ['vendor', 'tax_authority', 'government', 'bank', 'employee', 'utility', 'rent', 'insurance', 'investment']:
                payables.append(o)
            elif cp_type in ['customer', 'client']:
                receivables.append(o)
            elif o.transaction_type == 'payable':
                payables.append(o)
            elif o.transaction_type == 'receivable':
                receivables.append(o)
            else:
                # Default to payable for unknown
                payables.append(o)
        
        total_payables = sum(o.amount for o in payables)
        total_receivables = sum(o.amount for o in receivables)
        total_penalties = sum(o.penalty.total for o in obligations)
        
        # Count risk levels
        high_risk_count = sum(1 for o in obligations if o.risk_score >= 0.7)
        medium_risk_count = sum(1 for o in obligations if 0.4 <= o.risk_score < 0.7)
        low_risk_count = sum(1 for o in obligations if o.risk_score < 0.4)
        
        # Count by type
        type_distribution = {}
        for o in obligations:
            cp_type = o.counterparty.get('type', 'unknown')
            type_distribution[cp_type] = type_distribution.get(cp_type, 0) + 1
        
        # Count partial payment availability
        partial_available = sum(1 for o in obligations if o.partial_payment.accepts_partial)
        
        return FinancialState(
            cash_balance=cash_balance,
            obligations=obligations,
            as_of_date=date.today(),
            total_payables=total_payables,
            total_receivables=total_receivables,
            total_penalties=total_penalties,
            high_risk_count=high_risk_count,
            medium_risk_count=medium_risk_count,
            low_risk_count=low_risk_count,
            type_distribution=type_distribution
        )
    
    @classmethod
    def merge_duplicate_obligations(cls, obligations: List[Obligation]) -> List[Obligation]:
        """Merge duplicate obligations based on party and amount"""
        seen = {}
        merged = []
        
        for ob in obligations:
            key = (ob.counterparty.get('name', ''), ob.amount, ob.due_date)
            
            if key not in seen:
                seen[key] = ob
                merged.append(ob)
            else:
                existing = seen[key]
                logger.info(f"Merging duplicate for {ob.counterparty.get('name')} - amount: {ob.amount}")
                # Combine notes
                if ob.note:
                    existing.note = (existing.note or '') + f" | Duplicate: {ob.note}"
        
        return merged