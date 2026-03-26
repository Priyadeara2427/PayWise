# backend/utils/json_updater.py
"""
JSON File Updater for Payment Strategy and Decisions
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path


class JSONUpdater:
    """
    Updates JSON files with payment strategy analysis and decisions
    """
    
    def __init__(self, base_path: str = None):
        self.base_path = base_path or os.getcwd()
        self.data_dir = os.path.join(self.base_path, 'data')
        os.makedirs(self.data_dir, exist_ok=True)
    
    def update_obligations_json(self, obligations: List[Dict], filename: str = 'obligations.json') -> str:
        """Update obligations JSON with payment strategy analysis"""
        filepath = os.path.join(self.data_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(obligations, f, indent=2, default=str, ensure_ascii=False)
            
            print(f"✅ Updated obligations JSON: {filepath}")
            return filepath
        except Exception as e:
            print(f"❌ Failed to update obligations JSON: {e}")
            return None
    
    def update_decisions_json(self, decisions: List[Dict], filename: str = 'decisions.json') -> str:
        """Update decisions JSON with payment strategy"""
        filepath = os.path.join(self.data_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(decisions, f, indent=2, default=str, ensure_ascii=False)
            
            print(f"✅ Updated decisions JSON: {filepath}")
            return filepath
        except Exception as e:
            print(f"❌ Failed to update decisions JSON: {e}")
            return None
    
    def update_payment_priority_json(self, decisions: List[Dict], filename: str = 'payment_priorities.json') -> str:
        """Update payment priority order based on strategy"""
        filepath = os.path.join(self.data_dir, filename)
        
        try:
            category_order = {
                'must_pay': 1,
                'critical': 2,
                'can_negotiate': 3,
                'can_partial': 4,
                'can_delay': 5
            }
            
            sorted_decisions = sorted(decisions, key=lambda x: (
                category_order.get(x.get('payment_category', 'can_delay'), 5),
                -x.get('urgency_score', 0),
                -x.get('days_late', 0)
            ))
            
            priority_data = {
                'generated_at': datetime.now().isoformat(),
                'total_obligations': len(sorted_decisions),
                'priority_order': [],
                'summary': {
                    'must_pay_count': sum(1 for d in sorted_decisions if d.get('payment_category') == 'must_pay'),
                    'can_negotiate_count': sum(1 for d in sorted_decisions if d.get('payment_category') == 'can_negotiate'),
                    'can_partial_count': sum(1 for d in sorted_decisions if d.get('payment_category') == 'can_partial'),
                    'can_delay_count': sum(1 for d in sorted_decisions if d.get('payment_category') == 'can_delay'),
                    'total_amount': sum(d.get('amount', 0) for d in sorted_decisions)
                }
            }
            
            for idx, d in enumerate(sorted_decisions, 1):
                priority_data['priority_order'].append({
                    'rank': idx,
                    'transaction_id': d.get('transaction_id'),
                    'counterparty': d.get('counterparty'),
                    'counterparty_type': d.get('counterparty_type'),
                    'amount': d.get('amount'),
                    'due_date': d.get('due_date'),
                    'days_late': d.get('days_late'),
                    'payment_category': d.get('payment_category'),
                    'can_negotiate': d.get('can_negotiate', False),
                    'can_delay': d.get('can_delay', False),
                    'can_partial': d.get('can_partial', False),
                    'action': d.get('action'),
                    'reason': d.get('reason'),
                    'message_template': d.get('message_template', '')
                })
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(priority_data, f, indent=2, default=str, ensure_ascii=False)
            
            print(f"✅ Updated payment priorities JSON: {filepath}")
            return filepath
        except Exception as e:
            print(f"❌ Failed to update payment priorities JSON: {e}")
            return None
    
    def update_strategy_summary_json(self, obligations: List[Dict], filename: str = 'payment_strategy_summary.json') -> str:
        """Update payment strategy summary by category"""
        filepath = os.path.join(self.data_dir, filename)
        
        try:
            must_pay = []
            can_negotiate = []
            can_partial = []
            can_delay = []
            
            for ob in obligations:
                analysis = ob.get('payment_strategy_analysis', {})
                category = analysis.get('category', 'can_delay')
                
                summary = {
                    'counterparty': ob.get('counterparty', {}).get('name'),
                    'counterparty_type': ob.get('counterparty', {}).get('type'),
                    'amount': ob.get('amount'),
                    'due_date': ob.get('due_date'),
                    'days_late': ob.get('days_late', 0),
                    'can_negotiate': analysis.get('can_negotiate', False),
                    'can_delay': analysis.get('can_delay', False),
                    'can_partial': analysis.get('can_partial', False),
                    'grace_days': analysis.get('grace_days', 0),
                    'recommendation': analysis.get('recommendation'),
                    'risks': analysis.get('risks', []),
                    'message_template': analysis.get('message_template', '')
                }
                
                if category == 'must_pay':
                    must_pay.append(summary)
                elif category == 'can_negotiate':
                    can_negotiate.append(summary)
                elif category == 'can_partial':
                    can_partial.append(summary)
                else:
                    can_delay.append(summary)
            
            summary_data = {
                'generated_at': datetime.now().isoformat(),
                'total_obligations': len(obligations),
                'categories': {
                    'must_pay': {
                        'count': len(must_pay),
                        'total_amount': sum(o['amount'] for o in must_pay),
                        'description': 'Must pay on time - no negotiation possible (Tax, Government, Bank, Salary)',
                        'obligations': must_pay
                    },
                    'can_negotiate': {
                        'count': len(can_negotiate),
                        'total_amount': sum(o['amount'] for o in can_negotiate),
                        'description': 'Can negotiate extension or payment terms (Vendors, Suppliers)',
                        'obligations': can_negotiate
                    },
                    'can_partial': {
                        'count': len(can_partial),
                        'total_amount': sum(o['amount'] for o in can_partial),
                        'description': 'Can pay partially to avoid service disruption (Utilities, Rent)',
                        'obligations': can_partial
                    },
                    'can_delay': {
                        'count': len(can_delay),
                        'total_amount': sum(o['amount'] for o in can_delay),
                        'description': 'Can delay payment - flexible relationships (Friends, Family)',
                        'obligations': can_delay
                    }
                }
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, indent=2, default=str, ensure_ascii=False)
            
            print(f"✅ Updated strategy summary JSON: {filepath}")
            return filepath
        except Exception as e:
            print(f"❌ Failed to update strategy summary JSON: {e}")
            return None


def update_all_json_files(obligations: List[Dict], decisions: List[Dict], base_path: str = None) -> Dict[str, str]:
    """Update all JSON files with latest data"""
    updater = JSONUpdater(base_path)
    
    results = {
        'obligations': updater.update_obligations_json(obligations),
        'decisions': updater.update_decisions_json(decisions),
        'payment_priorities': updater.update_payment_priority_json(decisions),
        'strategy_summary': updater.update_strategy_summary_json(obligations)
    }
    
    return results