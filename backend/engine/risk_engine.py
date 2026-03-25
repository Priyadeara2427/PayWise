"""
Enhanced Risk Engine for Financial Obligations
"""

from datetime import datetime, date, timedelta
from typing import List, Dict, Any
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np

def calculate_risk(processed_data):
    """
    Enhanced risk calculation using all factors:
    - Number of days delayed
    - Transaction amount
    - Counterparty type (with intelligent classification)
    - Payment urgency
    - Cash flow projection
    """
    
    cash = processed_data["cash_balance"]
    payables = processed_data["payables"]
    receivables = processed_data["receivables"]
    
    today = datetime.today().date()
    
    # Initialize counters
    total_payables = 0
    overdue_payables = 0
    upcoming_payables = 0
    incoming_cash = 0
    
    # Track risk by category
    risk_by_category = {}
    high_risk_items = []
    critical_items = []
    
    # ---------- Enhanced Payables Analysis ----------
    for p in payables:
        amount = p["amount"]
        due_date = p.get("due_date")
        counterparty_type = p.get("type", "unknown")
        days_late = p.get("days_late", 0)
        risk_score_individual = p.get("risk_score", 0)
        priority = p.get("priority", "medium")
        urgency = p.get("urgency", "none")
        category = p.get("category", "other")
        
        total_payables += amount
        
        # Parse due date
        if due_date:
            if isinstance(due_date, str):
                due = datetime.strptime(due_date, "%Y-%m-%d").date()
            else:
                due = due_date
            
            if due < today:
                overdue_payables += amount
                days_overdue = (today - due).days
                
                # Track high risk items
                high_risk_items.append({
                    "party": p["party"],
                    "amount": amount,
                    "type": counterparty_type,
                    "days_overdue": days_overdue,
                    "risk_score": risk_score_individual,
                    "penalty": p.get("penalty", 0)
                })
            else:
                upcoming_payables += amount
        else:
            # No due date - treat as upcoming
            upcoming_payables += amount
        
        # Track risk by category
        if category not in risk_by_category:
            risk_by_category[category] = {
                "total_amount": 0,
                "count": 0,
                "overdue_amount": 0,
                "risk_score": 0
            }
        
        risk_by_category[category]["total_amount"] += amount
        risk_by_category[category]["count"] += 1
        if days_late > 0:
            risk_by_category[category]["overdue_amount"] += amount
        risk_by_category[category]["risk_score"] += risk_score_individual
        
        # Track critical items (tax, government, etc.)
        if counterparty_type in ['tax_authority', 'government'] and days_late > 0:
            critical_items.append({
                "party": p["party"],
                "type": counterparty_type,
                "amount": amount,
                "days_late": days_late,
                "penalty": p.get("penalty", 0)
            })
    
    # Normalize risk scores by category
    for category in risk_by_category:
        if risk_by_category[category]["count"] > 0:
            risk_by_category[category]["risk_score"] /= risk_by_category[category]["count"]
    
    # ---------- Receivables Analysis ----------
    for r in receivables:
        incoming_cash += r["amount"]
        expected_date = r.get("expected_date")
        
        if expected_date:
            if isinstance(expected_date, str):
                expected = datetime.strptime(expected_date, "%Y-%m-%d").date()
            else:
                expected = expected_date
            
            # Check if receivable is overdue
            if expected < today:
                days_overdue = (today - expected).days
                # Overdue receivables increase risk
                if days_overdue > 30:
                    risk_by_category.setdefault("overdue_receivables", {
                        "total_amount": 0,
                        "count": 0,
                        "overdue_amount": 0,
                        "risk_score": 0.8
                    })
                    risk_by_category["overdue_receivables"]["total_amount"] += r["amount"]
                    risk_by_category["overdue_receivables"]["count"] += 1
    
    # ---------- Cash Flow Projection ----------
    # Calculate weighted cash flow based on urgency
    weighted_payables = 0
    for p in payables:
        amount = p["amount"]
        days_late = p.get("days_late", 0)
        priority_weight = {
            'critical': 1.0,
            'high': 0.9,
            'medium': 0.6,
            'low': 0.3
        }.get(p.get("priority", "medium"), 0.5)
        
        # Add urgency multiplier
        urgency_multiplier = 1.0
        if days_late > 30:
            urgency_multiplier = 1.5
        elif days_late > 15:
            urgency_multiplier = 1.3
        elif days_late > 7:
            urgency_multiplier = 1.1
        
        weighted_payables += amount * priority_weight * urgency_multiplier
    
    projected_cash = cash + incoming_cash - weighted_payables
    
    # ---------- Enhanced Risk Score Calculation ----------
    # Factor 1: Financial Ratio (40% weight)
    total_liabilities = total_payables
    total_assets = cash + incoming_cash
    
    if total_assets == 0:
        financial_risk = 1.0
    else:
        financial_risk = min(1.0, total_liabilities / total_assets)
    
    # Factor 2: Overdue Risk (30% weight)
    if total_payables == 0:
        overdue_risk = 0
    else:
        overdue_risk = min(1.0, overdue_payables / total_payables)
    
    # Factor 3: Counterparty Risk (20% weight)
    counterparty_risk = 0
    for p in payables:
        cp_type = p.get("type", "unknown")
        type_risk = {
            'tax_authority': 1.0,
            'government': 0.9,
            'bank': 0.85,
            'vendor': 0.7,
            'employee': 0.8,
            'utility': 0.6,
            'rent': 0.5,
            'customer': 0.3,
            'friend': 0.2,
            'family': 0.1,
            'unknown': 0.4
        }.get(cp_type, 0.5)
        
        amount_weight = p["amount"] / total_payables if total_payables > 0 else 0
        counterparty_risk += type_risk * amount_weight
    
    # Factor 4: Critical Items Risk (10% weight)
    critical_risk = min(1.0, len(critical_items) / max(len(payables), 1))
    
    # Calculate final risk score (weighted average)
    risk_score = (
        financial_risk * 0.4 +
        overdue_risk * 0.3 +
        counterparty_risk * 0.2 +
        critical_risk * 0.1
    )
    
    # ---------- Risk Level Determination ----------
    if projected_cash < 0 or risk_score > 0.7 or len(critical_items) > 0:
        risk_level = "HIGH"
        risk_summary = "Critical risk - Immediate action required"
    elif risk_score > 0.4 or overdue_payables > cash * 0.5:
        risk_level = "MEDIUM"
        risk_summary = "Moderate risk - Monitor closely"
    else:
        risk_level = "LOW"
        risk_summary = "Low risk - Stable cash position"
    
    # ---------- Days to Zero Cash ----------
    days_to_zero = None
    if projected_cash < 0:
        days_to_zero = "Immediate Risk - Cash Shortfall"
    elif cash > 0 and weighted_payables > 0:
        daily_burn = weighted_payables / 30  # Assuming 30-day cycle
        if daily_burn > 0:
            days_to_zero = int(cash / daily_burn)
        else:
            days_to_zero = "Unlimited"
    
    # ---------- Generate Recommendations ----------
    recommendations = []
    
    if len(critical_items) > 0:
        recommendations.append(f"⚠️ Critical: Pay {len(critical_items)} tax/government obligations immediately")
    
    if overdue_payables > cash * 0.3:
        recommendations.append("⚠️ High overdue payments - Negotiate extensions")
    
    if len(high_risk_items) > 0:
        recommendations.append(f"⚠️ {len(high_risk_items)} high-risk items need immediate attention")
    
    if risk_score > 0.6:
        recommendations.append("⚠️ Consider arranging additional funds or restructuring payments")
    
    # ---------- Return Enhanced Risk Report ----------
    return {
        "cash_balance": cash,
        "total_payables": total_payables,
        "overdue_payables": overdue_payables,
        "upcoming_payables": upcoming_payables,
        "incoming_cash": incoming_cash,
        "projected_cash": round(projected_cash, 2),
        "weighted_payables": round(weighted_payables, 2),
        "risk_score": round(risk_score, 2),
        "risk_level": risk_level,
        "risk_summary": risk_summary,
        "days_to_zero": days_to_zero,
        "financial_ratio": round(financial_risk, 2),
        "overdue_ratio": round(overdue_risk, 2),
        "counterparty_risk": round(counterparty_risk, 2),
        "critical_risk": round(critical_risk, 2),
        "risk_by_category": risk_by_category,
        "high_risk_items": high_risk_items[:5],  # Top 5 high risk items
        "critical_items": critical_items,
        "recommendations": recommendations,
        "summary": {
            "total_obligations": len(payables),
            "critical_count": len(critical_items),
            "high_risk_count": len(high_risk_items),
            "cash_position": "positive" if projected_cash > 0 else "negative"
        }
    }


def print_risk_report(report):
    """Pretty print the risk report"""
    
    print("\n" + "="*60)
    print("RISK ASSESSMENT REPORT")
    print("="*60)
    
    print(f"\n💰 Cash Balance: ₹{report['cash_balance']:,.2f}")
    print(f"📤 Total Payables: ₹{report['total_payables']:,.2f}")
    print(f"📥 Incoming Cash: ₹{report['incoming_cash']:,.2f}")
    print(f"⚠️ Overdue Payables: ₹{report['overdue_payables']:,.2f}")
    print(f"🎯 Projected Cash: ₹{report['projected_cash']:,.2f}")
    
    print(f"\n📊 Risk Score: {report['risk_score']} ({report['risk_level']})")
    print(f"📝 Risk Summary: {report['risk_summary']}")
    
    print(f"\n📈 Risk Factors:")
    print(f"   - Financial Ratio: {report['financial_ratio']}")
    print(f"   - Overdue Ratio: {report['overdue_ratio']}")
    print(f"   - Counterparty Risk: {report['counterparty_risk']}")
    print(f"   - Critical Items Risk: {report['critical_risk']}")
    
    if report['critical_items']:
        print(f"\n🚨 CRITICAL ITEMS:")
        for item in report['critical_items']:
            print(f"   - {item['party']} ({item['type']}): ₹{item['amount']:,.2f} (Late: {item['days_late']} days)")
    
    if report['high_risk_items']:
        print(f"\n⚠️ HIGH RISK ITEMS:")
        for item in report['high_risk_items'][:3]:
            print(f"   - {item['party']}: ₹{item['amount']:,.2f} (Overdue: {item['days_overdue']} days)")
    
    if report['recommendations']:
        print(f"\n💡 RECOMMENDATIONS:")
        for rec in report['recommendations']:
            print(f"   {rec}")
    
    print("\n" + "="*60)


def create_cash_flow_dataframe(processed_data):
    """
    Create a detailed DataFrame of cash flow events
    """
    
    cash_balance = processed_data["cash_balance"]
    payables = processed_data["payables"]
    receivables = processed_data["receivables"]
    
    # Create events list
    events = []
    
    # Initial cash balance
    events.append({
        'date': datetime.today().date(),
        'type': 'starting_balance',
        'party': 'Opening Balance',
        'amount': cash_balance,
        'running_balance': cash_balance,
        'description': f'Initial Cash Balance'
    })
    
    # Add all payables
    for p in payables:
        due_date = p.get("due_date")
        if due_date:
            if isinstance(due_date, str):
                due = datetime.strptime(due_date, "%Y-%m-%d").date()
            else:
                due = due_date
            
            events.append({
                'date': due,
                'type': 'payable',
                'party': p['party'],
                'amount': -p['amount'],
                'running_balance': None,  # Will calculate later
                'description': f"Payment to {p['party']} - ₹{p['amount']:,.2f}"
            })
    
    # Add all receivables
    for r in receivables:
        expected_date = r.get("expected_date")
        if expected_date:
            if isinstance(expected_date, str):
                expected = datetime.strptime(expected_date, "%Y-%m-%d").date()
            else:
                expected = expected_date
            
            events.append({
                'date': expected,
                'type': 'receivable',
                'party': r['party'],
                'amount': r['amount'],
                'running_balance': None,  # Will calculate later
                'description': f"Receipt from {r['party']} - ₹{r['amount']:,.2f}"
            })
    
    # Sort by date
    events.sort(key=lambda x: x['date'])
    
    # Calculate running balance
    running = cash_balance
    for event in events:
        if event['type'] != 'starting_balance':
            running += event['amount']
            event['running_balance'] = running
    
    # Convert to DataFrame
    df = pd.DataFrame(events)
    
    # Add day of week
    df['day_of_week'] = df['date'].apply(lambda x: x.strftime('%A'))
    
    return df


def print_cash_flow_table(df):
    """
    Print a formatted cash flow table
    """
    
    print("\n" + "="*100)
    print("CASH FLOW SCHEDULE")
    print("="*100)
    
    # Separate into future and past
    today = datetime.today().date()
    future_events = df[df['date'] >= today].copy()
    past_events = df[df['date'] < today].copy()
    
    if not past_events.empty:
        print("\n📜 PAST TRANSACTIONS:")
        print("-"*100)
        for _, row in past_events.iterrows():
            if row['type'] != 'starting_balance':
                arrow = "↓" if row['amount'] < 0 else "↑"
                color = "🔴" if row['amount'] < 0 else "🟢"
                print(f"   {row['date']} ({row['day_of_week']}) | {color} {arrow} {row['party']:<30} | "
                      f"₹{row['amount']:>12,.2f} | Balance: ₹{row['running_balance']:>12,.2f}")
    
    if not future_events.empty:
        print("\n📅 FUTURE TRANSACTIONS:")
        print("-"*100)
        for _, row in future_events.iterrows():
            if row['type'] != 'starting_balance':
                arrow = "↓" if row['amount'] < 0 else "↑"
                color = "🔴" if row['amount'] < 0 else "🟢"
                days_until = (row['date'] - today).days
                print(f"   {row['date']} ({row['day_of_week']}) | {color} {arrow} {row['party']:<30} | "
                      f"₹{row['amount']:>12,.2f} | Balance: ₹{row['running_balance']:>12,.2f} "
                      f"| Days: {days_until}")
    
    print("\n" + "="*100)


def create_cash_flow_graph(processed_data, risk_report):
    """
    Create a cash flow graph showing how money is deducted and increased
    """
    
    cash_balance = processed_data["cash_balance"]
    payables = processed_data["payables"]
    receivables = processed_data["receivables"]
    
    # Create timeline
    today = datetime.today().date()
    days_to_project = 90  # Project 90 days ahead
    
    # Create date range
    dates = [today + timedelta(days=i) for i in range(days_to_project)]
    
    # Initialize cash balance array
    cash_flow = [cash_balance]
    
    # Create events list for annotations
    events = []
    
    # Track cash flow day by day
    for i in range(1, days_to_project):
        current_date = dates[i]
        previous_balance = cash_flow[-1]
        daily_change = 0
        
        # Add incoming cash from receivables
        for r in receivables:
            expected_date = r.get("expected_date")
            if expected_date:
                if isinstance(expected_date, str):
                    expected = datetime.strptime(expected_date, "%Y-%m-%d").date()
                else:
                    expected = expected_date
                
                if expected == current_date:
                    daily_change += r["amount"]
                    events.append({
                        "date": current_date,
                        "type": "receivable",
                        "amount": r["amount"],
                        "party": r["party"]
                    })
        
        # Subtract payables
        for p in payables:
            due_date = p.get("due_date")
            if due_date:
                if isinstance(due_date, str):
                    due = datetime.strptime(due_date, "%Y-%m-%d").date()
                else:
                    due = due_date
                
                if due == current_date:
                    daily_change -= p["amount"]
                    events.append({
                        "date": current_date,
                        "type": "payable",
                        "amount": p["amount"],
                        "party": p["party"]
                    })
        
        new_balance = previous_balance + daily_change
        cash_flow.append(new_balance)
    
    # Create the graph
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
    fig.suptitle('Cash Flow Analysis', fontsize=16, fontweight='bold')
    
    # Graph 1: Cash Flow Over Time
    ax1.plot(dates, cash_flow, 'b-', linewidth=2, label='Cash Balance')
    ax1.axhline(y=0, color='r', linestyle='--', linewidth=1, label='Zero Cash Line')
    
    # Add events as markers
    for event in events:
        if event["date"] in dates:
            idx = dates.index(event["date"])
            color = 'green' if event["type"] == "receivable" else 'red'
            marker = '^' if event["type"] == "receivable" else 'v'
            ax1.plot(event["date"], cash_flow[idx], marker, color=color, 
                    markersize=10, markeredgewidth=2)
            
            # Add annotation
            annotation = f"{event['party']}\n₹{event['amount']:,.0f}"
            ax1.annotate(annotation, 
                        xy=(event["date"], cash_flow[idx]),
                        xytext=(10, 10), textcoords='offset points',
                        fontsize=8, alpha=0.7,
                        bbox=dict(boxstyle="round,pad=0.3", facecolor=color, alpha=0.2))
    
    # Formatting
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Cash Balance (₹)')
    ax1.set_title('Cash Flow Projection')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    # Graph 2: Cash Flow Waterfall (Weekly)
    # Group by week
    weekly_data = []
    for i in range(0, len(dates), 7):
        week_dates = dates[i:min(i+7, len(dates))]
        week_cash = cash_flow[i:min(i+7, len(cash_flow))]
        weekly_data.append({
            'week_start': week_dates[0],
            'end_balance': week_cash[-1] if week_cash else cash_flow[i]
        })
    
    weeks = [w['week_start'] for w in weekly_data]
    balances = [w['end_balance'] for w in weekly_data]
    
    colors = ['green' if b > 0 else 'red' for b in balances]
    ax2.bar(weeks, balances, color=colors, alpha=0.7, edgecolor='black')
    ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    
    ax2.set_xlabel('Week')
    ax2.set_ylabel('Cash Balance (₹)')
    ax2.set_title('Weekly Cash Position')
    ax2.grid(True, alpha=0.3, axis='y')
    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    # Add zero cash line annotation
    if min(cash_flow) < 0:
        # Find when cash goes negative
        for i, balance in enumerate(cash_flow):
            if balance < 0:
                zero_date = dates[i]
                ax1.axvline(x=zero_date, color='orange', linestyle=':', 
                           linewidth=2, alpha=0.7, label='Cash Depletion Date')
                ax1.annotate(f'Cash Depletion\n{zero_date.strftime("%Y-%m-%d")}',
                           xy=(zero_date, 0), xytext=(10, 20),
                           textcoords='offset points', fontsize=9,
                           bbox=dict(boxstyle="round,pad=0.3", facecolor='orange', alpha=0.3))
                break
    
    plt.tight_layout()
    return fig


def create_cash_flow_analysis(processed_data, risk_report):
    """
    Create comprehensive cash flow analysis with graph and table
    """
    
    # Create DataFrame
    df = create_cash_flow_dataframe(processed_data)
    
    # Print table
    print_cash_flow_table(df)
    
    # Create and show graph
    fig = create_cash_flow_graph(processed_data, risk_report)
    plt.show()
    
    # Return statistics
    today = datetime.today().date()
    future_events = df[df['date'] > today]
    
    upcoming_payments = future_events[future_events['type'] == 'payable']['amount'].sum()
    upcoming_receipts = future_events[future_events['type'] == 'receivable']['amount'].sum()
    
    # Find days to zero
    days_to_zero = None
    for _, row in df.iterrows():
        if row['running_balance'] < 0:
            days_to_zero = (row['date'] - today).days
            break
    
    return {
        'df': df,
        'upcoming_payments': -upcoming_payments,
        'upcoming_receipts': upcoming_receipts,
        'net_future_cashflow': upcoming_receipts + upcoming_payments,
        'days_to_zero': days_to_zero,
        'lowest_cash': df['running_balance'].min(),
        'highest_cash': df['running_balance'].max()
    }