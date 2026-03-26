"""
Context-Aware Action Preparation Engine
Generates tailored communications for different counterparty types
"""

import json
import requests
import time
import random
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
import os

logger = logging.getLogger(__name__)

class CommunicationEngine:
    """
    Generates context-aware communications for financial decisions
    """
    
    def __init__(self, api_key: str = None, model: str = None):
        """
        Initialize the communication engine
        """
        self.api_key = api_key or os.getenv('OPENROUTER_API_KEY')
        # Verified working models as of March 2026
        self.models_to_try = [
            model or os.getenv('OPENROUTER_MODEL', 'openai/gpt-4o-mini'),
            "openai/gpt-4o-mini",
            "anthropic/claude-3-haiku",
            "meta-llama/llama-3.2-3b-instruct",
            "microsoft/phi-3-mini-128k-instruct"
        ]
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        
    def _call_llm(self, prompt: str, system_prompt: str = None, max_retries: int = 2) -> str:
        """Call LLM API with fallback models"""
        if not self.api_key:
            return self._generate_template_based(prompt, {})
        
        # Try each model in order
        for model in self.models_to_try:
            print(f"  Trying model: {model}")
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            payload = {
                "model": model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 500
            }
            
            for attempt in range(max_retries):
                try:
                    response = requests.post(self.base_url, headers=headers, json=payload, timeout=30)
                    
                    if response.status_code == 200:
                        result = response.json()
                        return result['choices'][0]['message']['content'].strip()
                        
                    elif response.status_code == 429:
                        wait_time = (attempt + 1) * 2 + random.uniform(0, 1)
                        print(f"    Rate limited. Waiting {wait_time:.1f}s...")
                        time.sleep(wait_time)
                        continue
                        
                    elif response.status_code in [401, 403]:
                        print(f"    API key error: {response.status_code}")
                        return self._generate_template_based(prompt, {})
                        
                    else:
                        if attempt == max_retries - 1:
                            print(f"    Model {model} failed: {response.status_code}")
                            break
                        time.sleep(1)
                        
                except requests.exceptions.Timeout:
                    print(f"    Timeout, retrying...")
                    if attempt == max_retries - 1:
                        break
                    time.sleep(2)
                except Exception as e:
                    print(f"    Error: {e}")
                    if attempt == max_retries - 1:
                        break
                    time.sleep(1)
        
        # All models failed, use template
        return self._generate_template_based(prompt, {})
    
    def _generate_template_based(self, prompt: str, data: Dict) -> str:
        """Fallback template with actual data"""
        # Extract data from prompt
        party_name = "Vendor"
        amount = "0"
        due_date = ""
        days_late = 0
        
        lines = prompt.split('\n')
        for line in lines:
            if "Recipient:" in line:
                party_name = line.split("Recipient:")[-1].strip()
            elif "Amount:" in line:
                amount = line.split("Amount:")[-1].strip()
            elif "Due Date:" in line:
                due_date = line.split("Due Date:")[-1].strip()
            elif "Days Overdue:" in line:
                try:
                    days_late = int(line.split("Days Overdue:")[-1].strip())
                except:
                    pass
        
        prompt_lower = prompt.lower()
        
        if "tax_authority" in prompt_lower or "government" in prompt_lower:
            return f"""Respected Officer,

Subject: Request for Extension - Tax Payment

I am writing regarding our tax obligation of {amount}. Due to temporary cash flow constraints, we respectfully request an extension of 15 days to make this payment.

We are committed to fulfilling our tax obligations and will ensure payment by the requested date.

Thank you for your understanding.

Yours faithfully,
Authorized Signatory"""
        
        elif "vendor" in prompt_lower or "supplier" in prompt_lower:
            return f"""Dear {party_name},

I hope this message finds you well.

We are writing to discuss payment for our outstanding invoice of {amount} due on {due_date}. Due to temporary cash flow challenges, we would appreciate the opportunity to arrange a partial payment or extension.

We value our partnership and are committed to resolving this promptly. Please let us know what arrangement would work best for you.

Best regards,
Accounts Team"""
        
        elif "friend" in prompt_lower:
            return f"""Hey {party_name},

I'm reaching out regarding the loan. I'm facing a temporary cash flow situation and wanted to be transparent. Would it be possible to discuss a short extension? Happy to work out a plan.

Let me know when you're free to chat.

Cheers"""
        
        elif "customer" in prompt_lower or "client" in prompt_lower:
            return f"""Dear {party_name},

This is a friendly reminder about the outstanding payment of {amount}. If you have any questions or need assistance, please don't hesitate to reach out.

Thank you for your business.

Best regards,
Finance Team"""
        
        else:
            return f"""Dear {party_name},

We need to discuss the pending payment of {amount}. Please let us know your availability to connect.

Regards,
Team"""
    
    def get_relationship_profile(self, counterparty_type: str, relationship_score: float = 0.5) -> Dict:
        """Get relationship profile based on counterparty type"""
        profiles = {
            'tax_authority': {
                'tone': 'formal',
                'greeting': 'Respected Officer',
                'closing': 'Yours faithfully',
                'signature': 'Authorized Signatory'
            },
            'government': {
                'tone': 'formal',
                'greeting': 'Respected Sir/Madam',
                'closing': 'Yours faithfully',
                'signature': 'Authorized Representative'
            },
            'vendor': {
                'tone': 'professional',
                'greeting': 'Dear [Name]',
                'closing': 'Best regards',
                'signature': 'Accounts Team'
            },
            'customer': {
                'tone': 'polite',
                'greeting': 'Dear [Name]',
                'closing': 'Thank you for your business',
                'signature': 'Finance Team'
            },
            'friend': {
                'tone': 'casual',
                'greeting': 'Hey [Name]',
                'closing': 'Cheers',
                'signature': ''
            },
            'family': {
                'tone': 'warm',
                'greeting': 'Hi [Name]',
                'closing': 'Love',
                'signature': ''
            },
            'default': {
                'tone': 'professional',
                'greeting': 'Dear Sir/Madam',
                'closing': 'Regards',
                'signature': 'Team'
            }
        }
        return profiles.get(counterparty_type, profiles['default'])
    
    def generate_payment_extension_request(self, obligation: Dict, profile: Dict, 
                                            suggested_days: int = 15) -> str:
        """Generate email requesting payment extension"""
        party_name = obligation.get('party', 'Vendor')
        amount = obligation.get('amount', 0)
        due_date = obligation.get('due_date', '')
        days_late = obligation.get('days_late', 0)
        
        greeting = profile.get('greeting', 'Dear Sir/Madam').replace('[Name]', party_name)
        closing = profile.get('closing', 'Regards')
        signature = profile.get('signature', '')
        tone = profile.get('tone', 'professional')
        
        prompt = f"""
        Write a {tone} email requesting payment extension.
        
        Details:
        - Recipient: {party_name}
        - Amount: ₹{amount:,.2f}
        - Original Due Date: {due_date}
        - Days Overdue: {days_late}
        - Requested Extension: {suggested_days} days
        
        Greeting: {greeting}
        Closing: {closing}
        
        Write a concise, professional email.
        """
        
        system_prompt = f"You are a {tone} business communication expert."
        email_content = self._call_llm(prompt, system_prompt)
        
        if not email_content.startswith(greeting.split()[0] if greeting else 'Dear'):
            email_content = f"{greeting},\n\n{email_content}"
        if not email_content.endswith(closing):
            email_content = f"{email_content}\n\n{closing},\n{signature}" if signature else f"{email_content}\n\n{closing}"
        
        return email_content
    
    def generate_payment_reminder(self, receivable: Dict, profile: Dict, 
                                   days_overdue: int = 0) -> str:
        """Generate payment reminder for receivables"""
        party_name = receivable.get('party', 'Customer')
        amount = receivable.get('amount', 0)
        due_date = receivable.get('expected_date', '')
        
        greeting = profile.get('greeting', 'Dear Sir/Madam').replace('[Name]', party_name)
        closing = profile.get('closing', 'Regards')
        signature = profile.get('signature', '')
        tone = profile.get('tone', 'professional')
        
        prompt = f"""
        Write a {tone} payment reminder email.
        
        Details:
        - Customer: {party_name}
        - Amount Due: ₹{amount:,.2f}
        - Due Date: {due_date}
        - Days Overdue: {days_overdue}
        
        Greeting: {greeting}
        Closing: {closing}
        
        Be polite but firm. Keep it short.
        """
        
        system_prompt = f"You are a {tone} accounts receivable professional."
        email_content = self._call_llm(prompt, system_prompt)
        
        if not email_content.startswith(greeting.split()[0] if greeting else 'Dear'):
            email_content = f"{greeting},\n\n{email_content}"
        if not email_content.endswith(closing):
            email_content = f"{email_content}\n\n{closing},\n{signature}" if signature else f"{email_content}\n\n{closing}"
        
        return email_content
    
    def generate_partial_payment_proposal(self, obligation: Dict, profile: Dict,
                                           proposed_pct: float, remaining_plan: Dict) -> str:
        """Generate partial payment proposal email"""
        party_name = obligation.get('party', 'Vendor')
        amount = obligation.get('amount', 0)
        proposed_amount = amount * proposed_pct / 100
        remaining_amount = amount - proposed_amount
        installments = remaining_plan.get('installments', 1)
        days = remaining_plan.get('days', 15)
        
        greeting = profile.get('greeting', 'Dear Sir/Madam').replace('[Name]', party_name)
        closing = profile.get('closing', 'Regards')
        tone = profile.get('tone', 'professional')
        
        prompt = f"""
        Write a {tone} email proposing a partial payment arrangement.
        
        Details:
        - Vendor: {party_name}
        - Total Amount: ₹{amount:,.2f}
        - Immediate Payment: {proposed_pct}% (₹{proposed_amount:,.2f})
        - Remaining Balance: ₹{remaining_amount:,.2f}
        - Proposed Schedule: {installments} installments over {days} days
        
        Greeting: {greeting}
        Closing: {closing}
        
        Keep it professional and concise.
        """
        
        system_prompt = f"You are a {tone} business negotiator."
        email_content = self._call_llm(prompt, system_prompt)
        
        if not email_content.startswith(greeting.split()[0] if greeting else 'Dear'):
            email_content = f"{greeting},\n\n{email_content}"
        
        return email_content


def create_action_communications(cash_balance: float, 
                                 payables: List[Dict], 
                                 receivables: List[Dict],
                                 decisions: List[Dict],
                                 api_key: str = None) -> Dict[str, Any]:
    """Create all necessary communications based on decisions"""
    engine = CommunicationEngine(api_key)
    
    communications = {
        "payables": [],
        "receivables": [],
        "summary": {"total_communications": 0}
    }
    
    print("\n📧 Generating communications...")
    
    for i, (payable, decision) in enumerate(zip(payables, decisions)):
        print(f"  [{i+1}/{len(payables)}] {payable.get('party')}")
        profile = engine.get_relationship_profile(payable.get('type', 'unknown'))
        
        if decision.get('action') == 'negotiate_deadline_extension':
            email = engine.generate_payment_extension_request(
                payable, profile, 
                suggested_days=decision.get('suggested_terms', {}).get('requested_days', 15)
            )
            communications["payables"].append({
                "party": payable['party'],
                "type": "extension_request",
                "email": email
            })
        elif decision.get('action') == 'pay_partially':
            suggested_pct = decision.get('suggested_terms', {}).get('percentage', 50)
            email = engine.generate_partial_payment_proposal(
                payable, profile, suggested_pct, {"installments": 2, "days": 15}
            )
            communications["payables"].append({
                "party": payable['party'],
                "type": "partial_payment_proposal",
                "email": email
            })
        
        if i < len(payables) - 1:
            time.sleep(1)
    
    for i, receivable in enumerate(receivables):
        if receivable.get('days_late', 0) > 0:
            print(f"  Reminder for {receivable.get('party')}")
            profile = engine.get_relationship_profile(receivable.get('type', 'customer'))
            email = engine.generate_payment_reminder(
                receivable, profile, receivable.get('days_late', 0)
            )
            communications["receivables"].append({
                "party": receivable['party'],
                "type": "payment_reminder",
                "email": email
            })
            time.sleep(1)
    
    communications["summary"]["total_communications"] = len(communications["payables"]) + len(communications["receivables"])
    
    return communications