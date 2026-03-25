import anthropic

client = anthropic.Anthropic()  # uses ANTHROPIC_API_KEY env variable

def generate_negotiation_email(obligation: dict, decision: dict) -> str:
    prompt = f"""
You are a professional financial assistant for a small business.
Generate a polite, professional email to negotiate a payment extension.

Vendor: {obligation['party']}
Amount due: ₹{obligation['amount']}
Due date: {obligation['due_date']}
Reason for request: {decision['reasoning']}
Tone: respectful, business-formal

Write only the email body. No subject line.
"""
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=400,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text

def generate_chain_of_thought(decisions: list) -> str:
    summary = "\n".join([f"- {d['obligation_id']}: {d['action']} — {d['reasoning']}" for d in decisions])
    prompt = f"""
Summarize the following payment decisions in 3–4 clear sentences for a small business owner.
Be direct, use simple language, explain the priority logic.

Decisions:
{summary}
"""
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}]
    )
    return message.content[0].text