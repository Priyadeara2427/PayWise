import pandas as pd
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import re
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.counterparty_classifier import CounterpartyClassifier, CounterpartyCategory

logger = logging.getLogger(__name__)

class CSVParser:
    """Enhanced CSV parser with validation, flexible column mapping, intelligent classification, and partial payment extraction"""
    
    REQUIRED_COLUMNS = ['amount', 'due_date']
    OPTIONAL_COLUMNS = [
        'counterparty', 'payment_date', 'type', 'description', 'invoice_no', 
        'gstin', 'pan', 'accepts_partial', 'min_payment_pct', 'min_payment_amount',
        'payment_terms', 'max_installments', 'installment_days'
    ]
    
    @classmethod
    def parse(cls, file_path: str, column_mapping: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Parse CSV file and extract obligations with intelligent classification and partial payment terms
        
        Args:
            file_path: Path to CSV file
            column_mapping: Optional mapping of CSV columns to standard fields
        
        Returns:
            Dictionary with cash_balance and obligations
        """
        try:
            # Read CSV with encoding detection
            df = cls._read_csv_safe(file_path)
            
            # Clean column names
            df.columns = cls._clean_column_names(df.columns)
            
            # Apply column mapping if provided
            if column_mapping:
                df = df.rename(columns=column_mapping)
            
            # Validate required columns
            cls._validate_columns(df)
            
            # Parse obligations from rows
            obligations = cls._parse_obligations(df)
            
            # Extract cash balance if present
            cash_balance = cls._extract_cash_balance(df)
            
            return {
                'cash_balance': cash_balance,
                'obligations': obligations,
                'source_type': 'csv',
                'record_count': len(obligations)
            }
            
        except Exception as e:
            logger.error(f"Failed to parse CSV {file_path}: {e}")
            raise
    
    @staticmethod
    def _read_csv_safe(file_path: str) -> pd.DataFrame:
        """Read CSV with automatic encoding detection"""
        encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252']
        
        for encoding in encodings:
            try:
                return pd.read_csv(file_path, encoding=encoding)
            except UnicodeDecodeError:
                continue
        
        raise ValueError("Could not decode CSV file with common encodings")
    
    @staticmethod
    def _clean_column_names(columns: List[str]) -> List[str]:
        """Clean column names by removing special characters and standardizing"""
        cleaned = []
        for col in columns:
            # Convert to lowercase, replace spaces with underscores
            col = str(col).lower().strip()
            col = re.sub(r'[^a-z0-9_]', '_', col)
            col = re.sub(r'_+', '_', col)
            cleaned.append(col)
        return cleaned
    
    @classmethod
    def _validate_columns(cls, df: pd.DataFrame):
        """Validate that required columns exist"""
        missing = [col for col in cls.REQUIRED_COLUMNS if col not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
    
    @classmethod
    def _extract_partial_payment_terms(cls, row: pd.Series, amount: float) -> Dict[str, Any]:
        """
        Extract partial payment terms from row data
        
        Args:
            row: DataFrame row
            amount: The obligation amount
        
        Returns:
            Dictionary with partial payment terms
        """
        # Default values
        accepts_partial = True
        minimum_partial_pct = 50.0
        minimum_partial_amount = 5000.0
        suggested_pct = 50.0
        max_installments = 2
        installment_days = 15
        notes = ""
        
        # Check if partial payment terms are explicitly provided in columns
        if 'accepts_partial' in row and pd.notna(row['accepts_partial']):
            val = str(row['accepts_partial']).lower()
            accepts_partial = val in ['true', 'yes', '1', 'y']
        
        if 'min_payment_pct' in row and pd.notna(row['min_payment_pct']):
            try:
                minimum_partial_pct = float(row['min_payment_pct'])
            except:
                pass
        
        if 'min_payment_amount' in row and pd.notna(row['min_payment_amount']):
            try:
                minimum_partial_amount = float(row['min_payment_amount'])
            except:
                pass
        
        # Check description for partial payment indicators
        description = ""
        if 'description' in row and pd.notna(row['description']):
            description = str(row['description']).lower()
            
            # Look for partial payment keywords
            if 'no partial' in description or 'full payment only' in description:
                accepts_partial = False
            elif 'partial accepted' in description or 'partial payment allowed' in description:
                accepts_partial = True
            
            # Look for minimum percentage
            pct_match = re.search(r'min(?:imum)?\s*(\d+)%', description)
            if pct_match:
                minimum_partial_pct = float(pct_match.group(1))
            
            # Look for minimum amount
            amount_match = re.search(r'min(?:imum)?\s*₹?(\d+(?:,\d{3})*(?:\.\d{2})?)', description)
            if amount_match:
                min_amount_str = amount_match.group(1).replace(',', '')
                minimum_partial_amount = float(min_amount_str)
            
            # Look for installment terms
            install_match = re.search(r'(\d+)\s*installments?', description)
            if install_match:
                max_installments = int(install_match.group(1))
            
            days_match = re.search(r'(\d+)\s*days?', description)
            if days_match and 'installment' in description or 'payment' in description:
                installment_days = int(days_match.group(1))
        
        # Check payment_terms column if available
        if 'payment_terms' in row and pd.notna(row['payment_terms']):
            terms = str(row['payment_terms']).lower()
            
            if 'net 30' in terms or 'net 45' in terms or 'net 60' in terms:
                # Extract net days
                net_match = re.search(r'net\s*(\d+)', terms)
                if net_match:
                    installment_days = int(net_match.group(1))
                    max_installments = 1
            
            if '2% 10 net 30' in terms or 'discount' in terms:
                # Early payment discount terms
                notes = "Early payment discount available - pay within 10 days for 2% discount"
            
            if 'installment' in terms:
                install_match = re.search(r'(\d+)\s*installments?', terms)
                if install_match:
                    max_installments = int(install_match.group(1))
        
        # Adjust based on amount
        if amount < minimum_partial_amount:
            minimum_partial_amount = amount * 0.5
        
        # Calculate suggested percentage (minimum or default)
        suggested_pct = max(minimum_partial_pct, 50.0)
        
        # For friends/family, suggest lower percentage
        counterparty_type = row.get('type', '') if 'type' in row else ''
        if counterparty_type in ['friend', 'family']:
            suggested_pct = 30.0
            max_installments = 4
            installment_days = 7
            notes = "Friends/family usually flexible - consider lower partial payment"
        
        # For tax/government, no partial payments
        if counterparty_type in ['tax_authority', 'government']:
            accepts_partial = False
            suggested_pct = 100.0
            minimum_partial_pct = 100.0
            minimum_partial_amount = amount
            notes = "Tax/government payments must be made in full"
        
        # For banks/loans
        if counterparty_type == 'bank':
            accepts_partial = False
            suggested_pct = 100.0
            notes = "Loan payments typically require full amount"
        
        return {
            'accepts_partial': accepts_partial,
            'minimum_partial_pct': minimum_partial_pct,
            'minimum_partial_amount': minimum_partial_amount,
            'suggested_pct': suggested_pct,
            'max_installments': max_installments,
            'installment_days': installment_days,
            'notes': notes,
            'history': []  # Initialize empty history
        }
    
    @classmethod
    def _parse_obligations(cls, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Parse each row into an obligation dictionary with context for classification and partial terms"""
        obligations = []
        
        for idx, row in df.iterrows():
            # Build comprehensive context for classification
            context_parts = []
            
            # Collect all available information for context
            if 'description' in row and pd.notna(row['description']):
                context_parts.append(f"Description: {row['description']}")
            
            if 'invoice_no' in row and pd.notna(row['invoice_no']):
                context_parts.append(f"Invoice: {row['invoice_no']}")
            
            if 'gstin' in row and pd.notna(row['gstin']):
                context_parts.append(f"GSTIN: {row['gstin']}")
            
            if 'pan' in row and pd.notna(row['pan']):
                context_parts.append(f"PAN: {row['pan']}")
            
            if 'note' in row and pd.notna(row['note']):
                context_parts.append(f"Note: {row['note']}")
            
            if 'payment_terms' in row and pd.notna(row['payment_terms']):
                context_parts.append(f"Payment Terms: {row['payment_terms']}")
            
            # Add amount and date context
            amount = cls._parse_amount(row.get('amount', 0))
            due_date = cls._parse_date(row.get('due_date'))
            context_parts.append(f"Amount: {amount}, Due: {due_date}")
            
            context = ' | '.join(context_parts)
            
            # Get counterparty name
            counterparty_name = row.get('counterparty', 'Unknown')
            if pd.isna(counterparty_name):
                counterparty_name = 'Unknown'
            else:
                counterparty_name = str(counterparty_name).strip()
            
            # Get explicit type if provided
            explicit_type = None
            if 'type' in row and pd.notna(row['type']):
                explicit_type = str(row['type']).lower()
            
            # Classify counterparty type intelligently
            classified_type, confidence = cls._classify_counterparty(
                counterparty_name, 
                context,
                explicit_type
            )
            
            # Extract partial payment terms
            partial_terms = cls._extract_partial_payment_terms(row, amount)
            
            # Override partial terms based on classified type if not explicitly set
            if 'accepts_partial' not in row or pd.isna(row.get('accepts_partial')):
                if classified_type in ['tax_authority', 'government', 'bank']:
                    partial_terms['accepts_partial'] = False
                    partial_terms['notes'] = f"{classified_type.replace('_', ' ').title()} payments require full amount"
                elif classified_type in ['friend', 'family']:
                    partial_terms['accepts_partial'] = True
                    partial_terms['suggested_pct'] = 30
                    partial_terms['max_installments'] = 4
                    partial_terms['notes'] = "Personal relationships allow flexible payments"
            
            # Create obligation
            obligation = {
                'amount': amount,
                'due_date': due_date,
                'counterparty': {
                    'name': counterparty_name,
                    'type': classified_type,
                    'classification_confidence': confidence
                },
                'context': context,  # Store context for reference
                'partial_payment': partial_terms  # Add partial payment terms
            }
            
            # Add optional fields if present
            if 'payment_date' in row and pd.notna(row['payment_date']):
                obligation['payment_date'] = cls._parse_date(row['payment_date'])
            
            if 'description' in row and pd.notna(row['description']):
                obligation['note'] = str(row['description'])
            
            # Add additional metadata
            if 'invoice_no' in row and pd.notna(row['invoice_no']):
                obligation['invoice_number'] = str(row['invoice_no'])
            
            if 'gstin' in row and pd.notna(row['gstin']):
                obligation['gstin'] = str(row['gstin'])
            
            if 'pan' in row and pd.notna(row['pan']):
                obligation['pan'] = str(row['pan'])
            
            obligations.append(obligation)
            
            # Log classification for debugging
            logger.debug(f"Classified '{counterparty_name}' as {classified_type} (confidence: {confidence:.2f})")
            logger.debug(f"Partial terms for {counterparty_name}: accepts={partial_terms['accepts_partial']}, min_pct={partial_terms['minimum_partial_pct']}%")
        
        return obligations
    
    @classmethod
    def _classify_counterparty(cls, name: str, context: str, explicit_type: Optional[str] = None) -> Tuple[str, float]:
        """
        Classify counterparty type using intelligent rules
        
        Args:
            name: Counterparty name
            context: Additional context from the row
            explicit_type: Explicit type if provided in CSV
        
        Returns:
            Tuple of (type_string, confidence_score)
        """
        # If explicit type is provided and valid, use it with high confidence
        if explicit_type:
            # Map explicit types to standard categories
            type_mapping = {
                'payable': 'vendor',
                'vendor': 'vendor',
                'supplier': 'vendor',
                'receivable': 'customer',
                'customer': 'customer',
                'client': 'customer',
                'tax': 'tax_authority',
                'gst': 'tax_authority',
                'government': 'government',
                'govt': 'government',
                'friend': 'friend',
                'family': 'family',
                'bank': 'bank',
                'utility': 'utility',
                'rent': 'rent',
                'insurance': 'insurance',
                'investment': 'investment',
                'charity': 'charity',
                'employee': 'employee'
            }
            
            if explicit_type in type_mapping:
                return type_mapping[explicit_type], 0.95
        
        # Use intelligent classification
        category, confidence = CounterpartyClassifier.classify(name, context)
        
        # Map category to string
        type_mapping = {
            CounterpartyCategory.VENDOR: 'vendor',
            CounterpartyCategory.CUSTOMER: 'customer',
            CounterpartyCategory.GOVERNMENT: 'government',
            CounterpartyCategory.TAX_AUTHORITY: 'tax_authority',
            CounterpartyCategory.EMPLOYEE: 'employee',
            CounterpartyCategory.FRIEND: 'friend',
            CounterpartyCategory.FAMILY: 'family',
            CounterpartyCategory.BANK: 'bank',
            CounterpartyCategory.UTILITY: 'utility',
            CounterpartyCategory.RENT: 'rent',
            CounterpartyCategory.INSURANCE: 'insurance',
            CounterpartyCategory.INVESTMENT: 'investment',
            CounterpartyCategory.CHARITY: 'charity',
            CounterpartyCategory.UNKNOWN: 'unknown'
        }
        
        return type_mapping.get(category, 'unknown'), confidence
    
    @classmethod
    def _parse_amount(cls, value: Any) -> float:
        """Parse amount from various formats"""
        if pd.isna(value):
            return 0.0
        
        if isinstance(value, (int, float)):
            return float(value)
        
        # Remove currency symbols and commas
        cleaned = re.sub(r'[^\d.-]', '', str(value))
        try:
            return float(cleaned)
        except ValueError:
            logger.warning(f"Could not parse amount: {value}")
            return 0.0
    
    @staticmethod
    def _parse_date(value: Any):
        """Parse date from various formats with Indian format support"""
        if pd.isna(value):
            return None
        
        if isinstance(value, (datetime, pd.Timestamp)):
            return value.date()
        
        date_str = str(value).strip()
        # Add more date formats including Indian format
        formats = [
            '%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', 
            '%d-%m-%Y', '%m-%d-%Y', '%d %b %Y', 
            '%b %d %Y', '%d %B %Y', '%B %d %Y',
            '%d/%m/%y', '%d-%m-%y'  # Two-digit year formats
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        logger.warning(f"Could not parse date: {value}")
        return None
    
    @staticmethod
    def _infer_type(row: pd.Series) -> str:
        """Legacy method - kept for backward compatibility"""
        # Check if type column exists
        if 'type' in row and pd.notna(row['type']):
            type_val = str(row['type']).lower()
            if type_val in ['payable', 'receivable']:
                return type_val
        
        # Infer from amount sign
        amount = row.get('amount', 0)
        if isinstance(amount, (int, float)):
            if amount < 0:
                return 'payable'
            elif amount > 0:
                return 'receivable'
        
        # Default to payable for safety
        return 'payable'
    
    @staticmethod
    def _extract_cash_balance(df: pd.DataFrame) -> float:
        """Extract cash balance from CSV if present"""
        # Look for a row with type 'balance' or 'cash'
        if 'type' in df.columns:
            balance_rows = df[df['type'].str.lower().isin(['balance', 'cash', 'opening_balance'])]
            if not balance_rows.empty:
                amount = balance_rows.iloc[0].get('amount', 0)
                if pd.notna(amount):
                    return float(amount)
        
        # Look for a row with 'balance' in the counterparty name
        if 'counterparty' in df.columns:
            balance_rows = df[df['counterparty'].str.lower().str.contains('balance|cash', na=False)]
            if not balance_rows.empty:
                amount = balance_rows.iloc[0].get('amount', 0)
                if pd.notna(amount):
                    return float(amount)
        
        # Alternative: look for 'balance' in column names
        for col in df.columns:
            if 'balance' in col.lower() or 'cash' in col.lower():
                if df[col].dtype in ['float64', 'int64']:
                    return float(df[col].iloc[-1])
        
        return 0.0
    
    @classmethod
    def parse_with_custom_mapping(cls, file_path: str, mapping: Dict[str, str]) -> Dict[str, Any]:
        """
        Parse CSV with custom column mapping
        
        Args:
            file_path: Path to CSV file
            mapping: Dict mapping CSV column names to standard field names
        
        Returns:
            Parsed data dictionary
        """
        return cls.parse(file_path, column_mapping=mapping)
    
    @classmethod
    def detect_column_mapping(cls, file_path: str) -> Dict[str, str]:
        """
        Automatically detect column mapping based on column names
        
        Args:
            file_path: Path to CSV file
        
        Returns:
            Suggested column mapping
        """
        df = cls._read_csv_safe(file_path)
        columns = cls._clean_column_names(df.columns)
        
        mapping = {}
        
        # Define common variations
        variations = {
            'amount': ['amount', 'amt', 'total', 'value', 'price', 'invoice_amount'],
            'due_date': ['due_date', 'duedate', 'due date', 'date', 'invoice_date', 'bill_date'],
            'counterparty': ['counterparty', 'party', 'vendor', 'customer', 'name', 'party_name'],
            'payment_date': ['payment_date', 'paymentdate', 'paid_date', 'payment date'],
            'type': ['type', 'transaction_type', 'txn_type', 'category'],
            'description': ['description', 'desc', 'notes', 'remarks', 'particulars'],
            'invoice_no': ['invoice_no', 'invoiceno', 'invoice number', 'inv_no'],
            'accepts_partial': ['accepts_partial', 'partial_allowed', 'allow_partial', 'partial_payment'],
            'min_payment_pct': ['min_payment_pct', 'min_percent', 'minimum_percent', 'partial_percent'],
            'min_payment_amount': ['min_payment_amount', 'min_amount', 'minimum_amount', 'partial_min'],
            'payment_terms': ['payment_terms', 'terms', 'payment_conditions']
        }
        
        for standard_field, possible_names in variations.items():
            for col in columns:
                if col in possible_names or any(variant in col for variant in possible_names):
                    mapping[col] = standard_field
                    break
        
        return mapping