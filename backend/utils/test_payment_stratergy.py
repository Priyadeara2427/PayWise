# test_payment_strategy.py
"""
Test Payment Strategy Analyzer
"""

from datetime import datetime, date, timedelta
from backend.engine.payment_strategy_analyzer import PaymentStrategyAnalyzer, analyze_payment_batch
from backend.engine.decision_engine import DecisionEngine
from backend.models.obligation import Obligation
from backend.utils.json_updater import update_all_json_files

def test_payment_strategy():
    """Test payment strategy with sample data (money you owe)"""
    
    obligations = [
        {
            "transaction_id": "1",
            "counterparty": {"name": "Income Tax Department", "type": "tax_authority"},
            "amount": 50000,
            "due_date": (date.today() - timedelta(days=5)).isoformat(),
            "days_late": 5
        },
        {
            "transaction_id": "2",
            "counterparty": {"name": "Raj Fabrics", "type": "vendor"},
            "amount": 25000,
            "due_date": date.today().isoformat(),
            "days_late": 0
        },
        {
            "transaction_id": "3",
            "counterparty": {"name": "HDFC Bank", "type": "bank"},
            "amount": 15000,
            "due_date": (date.today() + timedelta(days=3)).isoformat(),
            "days_late": 0
        },
        {
            "transaction_id": "4",
            "counterparty": {"name": "Friend - Rajesh", "type": "friend"},
            "amount": 10000,
            "due_date": (date.today() + timedelta(days=15)).isoformat(),
            "days_late": 0
        },
        {
            "transaction_id": "5",
            "counterparty": {"name": "Electricity Board", "type": "utility"},
            "amount": 3500,
            "due_date": (date.today() + timedelta(days=10)).isoformat(),
            "days_late": 0
        },
        {
            "transaction_id": "6",
            "counterparty": {"name": "Office Rent", "type": "rent"},
            "amount": 20000,
            "due_date": (date.today() + timedelta(days=5)).isoformat(),
            "days_late": 0
        },
        {
            "transaction_id": "7",
            "counterparty": {"name": "Employee Salary", "type": "employee"},
            "amount": 45000,
            "due_date": (date.today() + timedelta(days=2)).isoformat(),
            "days_late": 0
        }
    ]
    
    cash_balance = 50000
    
    print("=" * 80)
    print("PAYMENT STRATEGY ANALYZER - Money You Owe")
    print("=" * 80)
    print(f"Current Cash Balance: ₹{cash_balance:,.2f}")
    print()
    
    analyzed = analyze_payment_batch(obligations, cash_balance)
    
    for ob in analyzed:
        analysis = ob.get('payment_strategy_analysis', {})
        print(f"\n{'='*60}")
        print(f"📋 {ob['counterparty']['name']} ({ob['counterparty']['type']})")
        print(f"   Amount Owed: ₹{ob['amount']:,.2f}")
        print(f"   Due Date: {ob['due_date']}")
        print(f"   Days Late: {ob.get('days_late', 0)}")
        print(f"\n   🏷️  Category: {analysis.get('category', 'unknown').upper()}")
        print(f"   📞 Can Negotiate: {'✅ YES' if analysis.get('can_negotiate') else '❌ NO'}")
        print(f"   ⏰ Can Delay: {'✅ YES' if analysis.get('can_delay') else '❌ NO'}")
        print(f"   💰 Can Pay Partial: {'✅ YES' if analysis.get('can_partial') else '❌ NO'}")
        print(f"   🎁 Grace Days: {analysis.get('grace_days', 0)}")
        print(f"   ⚠️  Penalty Rate: {analysis.get('penalty_rate', 0)*100:.0f}%")
        print(f"   🔥 Urgency Score: {analysis.get('urgency_score', 0):.2f}")
        print(f"\n   💡 STRATEGY: {analysis.get('strategy', 'UNKNOWN')}")
        print(f"\n   📝 RECOMMENDATION: {analysis.get('recommendation', 'N/A')}")
        if analysis.get('risks'):
            print(f"\n   ⚠️  RISKS:")
            for risk in analysis.get('risks', []):
                print(f"      - {risk}")
        if analysis.get('message_template'):
            print(f"\n   💬 MESSAGE TEMPLATE:")
            print(f"      \"{analysis.get('message_template')}\"")
    
    print("\n" + "=" * 80)
    print("GENERATING PAYMENT DECISIONS")
    print("=" * 80)
    
    decisions = []
    for ob in analyzed:
        due_date = ob.get('due_date')
        if due_date and isinstance(due_date, str):
            due_date = datetime.strptime(due_date, '%Y-%m-%d').date()
        
        obligation = Obligation(
            transaction_id=ob.get('transaction_id'),
            counterparty=ob.get('counterparty', {}),
            amount=ob.get('amount', 0),
            due_date=due_date,
            days_late=ob.get('days_late', 0),
            risk_score=ob.get('risk_score', 0)
        )
        
        decision = DecisionEngine.make_decision(obligation, cash_balance)
        decisions.append({
            "transaction_id": obligation.transaction_id,
            "counterparty": obligation.counterparty.get('name'),
            "counterparty_type": obligation.counterparty.get('type'),
            "amount": obligation.amount,
            "due_date": obligation.due_date.isoformat() if obligation.due_date else None,
            "days_late": obligation.days_late,
            "priority": decision.priority.value,
            "action": decision.action.value,
            "reason": decision.reason,
            "payment_category": ob.get('payment_category'),
            "can_negotiate": ob.get('can_negotiate', False),
            "can_delay": ob.get('can_delay', False),
            "can_partial": ob.get('can_partial', False),
            "message_template": ob.get('payment_strategy_analysis', {}).get('message_template', '')
        })
    
    print("\n📊 PAYMENT DECISIONS SUMMARY:")
    for d in decisions:
        print(f"\n   {d['counterparty']}:")
        print(f"      Action: {d['action'].replace('_', ' ').upper()}")
        print(f"      Priority: {d['priority'].upper()}")
        print(f"      Reason: {d['reason']}")
    
    print("\n" + "=" * 80)
    print("PAYMENT PRIORITY ORDER (Who to Pay First)")
    print("=" * 80)
    
    category_order = {'must_pay': 1, 'can_negotiate': 2, 'can_partial': 3, 'can_delay': 4}
    sorted_decisions = sorted(decisions, key=lambda x: (
        category_order.get(x.get('payment_category', 'can_delay'), 4),
        -x.get('days_late', 0)
    ))
    
    for idx, d in enumerate(sorted_decisions, 1):
        print(f"\n{idx}. {d['counterparty']} - ₹{d['amount']:,.2f}")
        print(f"   Category: {d.get('payment_category', 'unknown').upper()}")
        print(f"   Action: {d['action'].replace('_', ' ').upper()}")
        print(f"   {d['reason']}")
    
    print("\n" + "=" * 80)
    print("UPDATING JSON FILES")
    print("=" * 80)
    
    results = update_all_json_files(analyzed, decisions)
    
    for file_type, filepath in results.items():
        if filepath:
            print(f"✅ {file_type}: {filepath}")
        else:
            print(f"❌ {file_type}: Failed to update")
    
    print("\n✅ Test complete! Check the 'data' folder for JSON files.")
    return analyzed, decisions

if __name__ == "__main__":
    test_payment_strategy()