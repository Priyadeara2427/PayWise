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
    """Enhanced CSV parser with validation, flexible column mapping, and intelligent classification"""
    
    REQUIRED_COLUMNS = ['amount', 'due_date']
    OPTIONAL_COLUMNS = ['counterparty', 'payment_date', 'type', 'description', 'invoice_no', 'gstin', 'pan']
    
    @classmethod
    def parse(cls, file_path: str, column_mapping: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Parse CSV file and extract obligations with intelligent classification
        
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
    def _parse_obligations(cls, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Parse each row into an obligation dictionary with context for classification"""
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
            
            obligations.append(obligation)
            
            # Log classification for debugging
            logger.debug(f"Classified '{counterparty_name}' as {classified_type} (confidence: {confidence:.2f})")
        
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
                'govt': 'government'
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
            'invoice_no': ['invoice_no', 'invoiceno', 'invoice number', 'inv_no']
        }
        
        for standard_field, possible_names in variations.items():
            for col in columns:
                if col in possible_names or any(variant in col for variant in possible_names):
                    mapping[col] = standard_field
                    break
        
        return mapping