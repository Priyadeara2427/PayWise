import re
from typing import Dict, List, Tuple, Optional
from enum import Enum

class CounterpartyCategory(Enum):
    """Comprehensive counterparty categories"""
    VENDOR = "vendor"           # Suppliers, service providers
    CUSTOMER = "customer"        # Clients, buyers
    GOVERNMENT = "government"    # Tax authorities, government agencies
    TAX_AUTHORITY = "tax_authority"  # GST, Income Tax, etc.
    EMPLOYEE = "employee"        # Salary, reimbursements
    FRIEND = "friend"           # Personal loans, informal
    FAMILY = "family"           # Family transactions
    BANK = "bank"               # Bank, financial institutions
    UTILITY = "utility"         # Electricity, water, internet
    RENT = "rent"               # Landlord, rent payments
    INSURANCE = "insurance"     # Insurance companies
    INVESTMENT = "investment"    # Investment firms
    CHARITY = "charity"         # Donations, NGOs
    UNKNOWN = "unknown"         # Can't determine

class CounterpartyClassifier:
    """Intelligent counterparty classification based on context"""
    
    # Keywords and patterns for classification
    CLASSIFICATION_RULES = {
        CounterpartyCategory.GOVERNMENT: {
            'keywords': [
                'government', 'govt', 'municipal', 'corporation', 'municipality',
                'income tax', 'gst', 'sales tax', 'property tax', 'customs',
                'ministry', 'department', 'public works', 'pwd', 'mcd', 'ndmc'
            ],
            'patterns': [
                r'govt\s*\.?\s*of\s*india',
                r'income\s*tax\s*department',
                r'central\s*bureau',
                r'municipal\s*corporation'
            ]
        },
        
        CounterpartyCategory.TAX_AUTHORITY: {
            'keywords': [
                'gst', 'gstin', 'tax', 'income tax', 'tds', 'vat', 'service tax',
                'central tax', 'state tax', 'tax department', 'tax authority'
            ],
            'patterns': [
                r'\b[A-Z0-9]{15}\b',  # GSTIN pattern
                r'gst\s*in',
                r'tax\s*invoice'
            ]
        },
        
        CounterpartyCategory.VENDOR: {
            'keywords': [
                'vendor', 'supplier', 'seller', 'merchant', 'store', 'shop',
                'enterprises', 'industries', 'trading', 'traders', 'wholesale',
                'retailer', 'distributor', 'dealer', 'agency', 'services',
                'solutions', 'technologies', 'pvt ltd', 'ltd', 'llp', 'private limited'
            ],
            'patterns': [
                r'\b\w+\s+(?:enterprises|industries|trading|traders)\b',
                r'\b\w+\s+(?:pvt|private)\s+(?:ltd|limited)\b',
                r'invoice\s*(?:no|number)',
                r'supplier\s*(?:name|details)'
            ]
        },
        
        CounterpartyCategory.CUSTOMER: {
            'keywords': [
                'customer', 'client', 'buyer', 'purchaser', 'consumer',
                'retail', 'store', 'mart', 'supermarket', 'outlet'
            ],
            'patterns': [
                r'bill\s*to',
                r'ship\s*to',
                r'customer\s*(?:name|id|code)'
            ]
        },
        
        CounterpartyCategory.UTILITY: {
            'keywords': [
                'electricity', 'water', 'gas', 'broadband', 'internet', 'phone',
                'mobile', 'telephone', 'utility', 'bill', 'meter'
            ],
            'patterns': [
                r'(?:electricity|water|gas)\s*bill',
                r'meter\s*(?:no|number)',
                r'consumer\s*(?:no|number)'
            ]
        },
        
        CounterpartyCategory.RENT: {
            'keywords': [
                'rent', 'lease', 'landlord', 'property', 'apartment', 'flat',
                'office space', 'commercial space'
            ],
            'patterns': [
                r'rent\s*agreement',
                r'lease\s*agreement',
                r'rent\s*receipt'
            ]
        },
        
        CounterpartyCategory.BANK: {
            'keywords': [
                'bank', 'hdfc', 'sbi', 'icici', 'axis', 'kotak', 'yes bank',
                'financial', 'loan', 'emi', 'mortgage', 'credit card'
            ],
            'patterns': [
                r'\b\w+\s+bank\b',
                r'loan\s*account',
                r'credit\s*card\s*statement'
            ]
        },
        
        CounterpartyCategory.EMPLOYEE: {
            'keywords': [
                'salary', 'wages', 'employee', 'staff', 'payroll', 'compensation',
                'reimbursement', 'allowance', 'bonus'
            ],
            'patterns': [
                r'salary\s*(?:slip|statement)',
                r'payroll\s*statement',
                r'employee\s*(?:id|code)'
            ]
        },
        
        CounterpartyCategory.INSURANCE: {
            'keywords': [
                'insurance', 'policy', 'premium', 'icici prudential', 'lic',
                'health insurance', 'life insurance', 'general insurance'
            ],
            'patterns': [
                r'policy\s*(?:no|number)',
                r'insurance\s*premium',
                r'insurance\s*company'
            ]
        },
        
        CounterpartyCategory.INVESTMENT: {
            'keywords': [
                'investment', 'mutual fund', 'stock', 'share', 'broker',
                'demate', 'trading', 'portfolio', 'dividend'
            ],
            'patterns': [
                r'mutual\s*fund',
                r'demat\s*account',
                r'stock\s*broke'
            ]
        },
        
        CounterpartyCategory.CHARITY: {
            'keywords': [
                'donation', 'charity', 'ngo', 'foundation', 'trust',
                'non-profit', 'not-for-profit', 'philanthropy'
            ],
            'patterns': [
                r'charitable\s*trust',
                r'non\s*profit\s*organization'
            ]
        },
        
        CounterpartyCategory.FRIEND: {
            'keywords': [
                'friend', 'personal loan', 'borrow', 'lend', 'settlement',
                'upi', 'google pay', 'phonepe', 'paytm'
            ],
            'patterns': [
                r'upi\s*transfer',
                r'friend\s*request',
                r'personal\s*payment'
            ]
        },
        
        CounterpartyCategory.FAMILY: {
            'keywords': [
                'family', 'relative', 'brother', 'sister', 'parent', 'son', 'daughter',
                'spouse', 'husband', 'wife', 'home'
            ],
            'patterns': [
                r'family\s*member',
                r'relative\s*payment'
            ]
        }
    }
    
    # Domain-specific keywords
    DOMAIN_KEYWORDS = {
        'tax': ['gst', 'tax', 'tds', 'vat', 'gstin', 'tax invoice'],
        'government': ['govt', 'government', 'municipal', 'corporation'],
        'business': ['pvt', 'ltd', 'llp', 'enterprises', 'industries'],
        'personal': ['friend', 'family', 'personal', 'home'],
        'utility': ['electricity', 'water', 'gas', 'internet', 'broadband']
    }
    
    @classmethod
    def classify(cls, counterparty_name: str, context: str = "") -> Tuple[CounterpartyCategory, float]:
        """
        Classify counterparty type based on name and context
        
        Args:
            counterparty_name: Name of the counterparty
            context: Additional context from the document (invoice text, description)
        
        Returns:
            Tuple of (category, confidence score)
        """
        combined_text = f"{counterparty_name} {context}".lower()
        
        scores = {}
        
        # Score each category based on keyword matches
        for category, rules in cls.CLASSIFICATION_RULES.items():
            score = 0.0
            
            # Check keywords
            for keyword in rules['keywords']:
                if keyword in combined_text:
                    score += 1.0
            
            # Check patterns
            for pattern in rules['patterns']:
                if re.search(pattern, combined_text, re.IGNORECASE):
                    score += 2.0  # Patterns are stronger indicators
            
            # Normalize score
            score = min(score / 5.0, 1.0)  # Cap at 1.0
            
            # Boost for certain categories based on additional rules
            if category == CounterpartyCategory.VENDOR:
                if any(word in combined_text for word in ['invoice', 'supplier']):
                    score = min(score + 0.3, 1.0)
            
            elif category == CounterpartyCategory.CUSTOMER:
                if any(word in combined_text for word in ['customer', 'client']):
                    score = min(score + 0.3, 1.0)
            
            elif category == CounterpartyCategory.TAX_AUTHORITY:
                # Check for GSTIN pattern (15 characters alphanumeric)
                if re.search(r'\b[A-Z0-9]{15}\b', combined_text):
                    score = min(score + 0.5, 1.0)
                if 'gst' in combined_text or 'tax' in combined_text:
                    score = min(score + 0.4, 1.0)
            
            elif category == CounterpartyCategory.GOVERNMENT:
                if any(word in combined_text for word in ['govt', 'department']):
                    score = min(score + 0.4, 1.0)
            
            scores[category] = score
        
        # Get best match
        if scores:
            best_category = max(scores, key=scores.get)
            best_score = scores[best_category]
            
            # If best score is too low, return unknown
            if best_score < 0.2:
                return CounterpartyCategory.UNKNOWN, best_score
            
            return best_category, best_score
        else:
            return CounterpartyCategory.UNKNOWN, 0.0
    
    @classmethod
    def get_category_details(cls, category: CounterpartyCategory) -> Dict:
        """Get details about a category for decision making"""
        details = {
            CounterpartyCategory.VENDOR: {
                'priority': 'high',
                'action_suggestion': 'pay_immediately',
                'risk_factor': 0.8,
                'relationship_importance': 'critical'
            },
            CounterpartyCategory.TAX_AUTHORITY: {
                'priority': 'critical',
                'action_suggestion': 'pay_immediately',
                'risk_factor': 1.0,
                'relationship_importance': 'legal_obligation'
            },
            CounterpartyCategory.GOVERNMENT: {
                'priority': 'critical',
                'action_suggestion': 'pay_immediately',
                'risk_factor': 0.9,
                'relationship_importance': 'compliance'
            },
            CounterpartyCategory.EMPLOYEE: {
                'priority': 'high',
                'action_suggestion': 'pay_immediately',
                'risk_factor': 0.85,
                'relationship_importance': 'critical'
            },
            CounterpartyCategory.UTILITY: {
                'priority': 'high',
                'action_suggestion': 'pay_immediately',
                'risk_factor': 0.7,
                'relationship_importance': 'essential_services'
            },
            CounterpartyCategory.RENT: {
                'priority': 'high',
                'action_suggestion': 'pay_immediately',
                'risk_factor': 0.75,
                'relationship_importance': 'contractual'
            },
            CounterpartyCategory.BANK: {
                'priority': 'critical',
                'action_suggestion': 'pay_immediately',
                'risk_factor': 0.95,
                'relationship_importance': 'financial_health'
            },
            CounterpartyCategory.CUSTOMER: {
                'priority': 'medium',
                'action_suggestion': 'negotiate_payment',
                'risk_factor': 0.5,
                'relationship_importance': 'business_relationship'
            },
            CounterpartyCategory.INSURANCE: {
                'priority': 'medium',
                'action_suggestion': 'pay_before_deadline',
                'risk_factor': 0.6,
                'relationship_importance': 'coverage_continuity'
            },
            CounterpartyCategory.INVESTMENT: {
                'priority': 'medium',
                'action_suggestion': 'pay_on_time',
                'risk_factor': 0.55,
                'relationship_importance': 'investment_growth'
            },
            CounterpartyCategory.FRIEND: {
                'priority': 'low',
                'action_suggestion': 'communicate_and_pay',
                'risk_factor': 0.3,
                'relationship_importance': 'personal'
            },
            CounterpartyCategory.FAMILY: {
                'priority': 'low',
                'action_suggestion': 'inform_and_pay',
                'risk_factor': 0.25,
                'relationship_importance': 'personal'
            },
            CounterpartyCategory.CHARITY: {
                'priority': 'low',
                'action_suggestion': 'pay_when_possible',
                'risk_factor': 0.2,
                'relationship_importance': 'goodwill'
            }
        }
        return details.get(category, {
            'priority': 'medium',
            'action_suggestion': 'review',
            'risk_factor': 0.5,
            'relationship_importance': 'unknown'
        })