import React, { useState } from 'react';
import { useApi } from '../hooks/useApi';
import { formatCurrency } from '../utils/formatters';

const Communicate = ({ data }) => {
    const [action, setAction] = useState('request_extension');
    const [extraContext, setExtraContext] = useState('');
    const [loading, setLoading] = useState(false);
    const [draft, setDraft] = useState(null);
    const [copied, setCopied] = useState(false);
    const [error, setError] = useState('');
    const { request } = useApi();

    const generate = async () => {
        if (!data) {
            setError('Please analyze a transaction first.');
            return;
        }
        setError('');
        setLoading(true);
        try {
            const result = await request('/generate-message', {
                method: 'POST',
                body: JSON.stringify({ 
                    transaction: data, 
                    action, 
                    extra_context: extraContext 
                })
            });
            setDraft(result);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const copyToClipboard = () => {
        if (!draft) return;
        const text = `Subject: ${draft.subject}\n\n${draft.body}`;
        navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
    };

    if (!data) {
        return (
            <div className="empty-state">
                <div className="empty-icon">✉️</div>
                <div className="empty-title">No Transaction Loaded</div>
                <div className="empty-sub">Analyze a transaction first to generate communications</div>
                <button className="btn btn-primary" style={{ marginTop: '1rem' }} onClick={() => setActiveTab('input')}>
                    + New Transaction
                </button>
            </div>
        );
    }

    const messageTypes = [
        { id: 'request_extension', label: '📅 Request Deadline Extension', description: 'Politely ask for more time to pay' },
        { id: 'propose_partial', label: '💳 Propose Partial Payment', description: 'Offer to pay part now, rest later' },
        { id: 'payment_confirmation', label: '✅ Payment Confirmation', description: 'Confirm that payment has been made' },
        { id: 'apology_delay', label: '🙏 Apology for Delay', description: 'Acknowledge delay and explain situation' },
        { id: 'demand_payment', label: '⚡ Payment Demand', description: 'Firm reminder for overdue payment' },
    ];

    return (
        <div className="two-column">
            <div>
                {/* Transaction Summary Card */}
                <div className="card" style={{ marginBottom: '1rem' }}>
                    <div className="card-title">Transaction Summary</div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span style={{ color: 'var(--text3)', fontSize: '13px' }}>Counterparty</span>
                            <span style={{ fontWeight: 600 }}>{data.counterparty_name}</span>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span style={{ color: 'var(--text3)', fontSize: '13px' }}>Amount</span>
                            <span className="mono" style={{ fontWeight: 600 }}>{formatCurrency(data.amount)}</span>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span style={{ color: 'var(--text3)', fontSize: '13px' }}>Days Late</span>
                            <span style={{ color: data.days_late > 0 ? 'var(--amber)' : 'var(--green)', fontWeight: 600 }}>
                                {data.days_late}
                            </span>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span style={{ color: 'var(--text3)', fontSize: '13px' }}>Risk Level</span>
                            <span className={`badge ${data.priority === 'High' ? 'badge-high' : data.priority === 'Medium' ? 'badge-medium' : 'badge-low'}`}>
                                {data.priority}
                            </span>
                        </div>
                        {data.due_date && (
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <span style={{ color: 'var(--text3)', fontSize: '13px' }}>Due Date</span>
                                <span>{data.due_date}</span>
                            </div>
                        )}
                    </div>
                </div>

                {/* Message Type Selection Card */}
                <div className="card">
                    <div className="card-title">Message Type</div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                        {messageTypes.map(({ id, label, description }) => (
                            <label
                                key={id}
                                style={{
                                    display: 'flex',
                                    alignItems: 'flex-start',
                                    gap: '0.75rem',
                                    padding: '0.75rem',
                                    borderRadius: '8px',
                                    background: action === id ? 'var(--accent-glow)' : 'transparent',
                                    border: `1px solid ${action === id ? 'var(--accent)' : 'transparent'}`,
                                    cursor: 'pointer',
                                    transition: 'all 0.2s'
                                }}
                            >
                                <input
                                    type="radio"
                                    name="action"
                                    value={id}
                                    checked={action === id}
                                    onChange={() => setAction(id)}
                                    style={{ width: 'auto', marginTop: '2px' }}
                                />
                                <div>
                                    <div style={{ fontWeight: action === id ? 600 : 400, marginBottom: '0.25rem' }}>
                                        {label}
                                    </div>
                                    <div style={{ fontSize: '11px', color: 'var(--text3)' }}>
                                        {description}
                                    </div>
                                </div>
                            </label>
                        ))}
                    </div>

                    {/* Additional Context */}
                    <div style={{ marginTop: '1rem' }}>
                        <label style={{ display: 'block', marginBottom: '0.5rem' }}>Additional Context (Optional)</label>
                        <textarea
                            className="form-textarea"
                            rows="3"
                            placeholder="e.g., Partial payment of ₹20,000 made on March 22... or Please note the bank holiday on April 14..."
                            value={extraContext}
                            onChange={e => setExtraContext(e.target.value)}
                            style={{ width: '100%', padding: '0.75rem', borderRadius: '8px', background: 'var(--surface2)', border: '1px solid var(--border)', color: 'var(--text)' }}
                        />
                        <div style={{ fontSize: '11px', color: 'var(--text3)', marginTop: '0.25rem' }}>
                            💡 Tip: Add specific details to personalize the message
                        </div>
                    </div>

                    {/* Generate Button */}
                    <button
                        className="btn btn-primary"
                        style={{ marginTop: '1rem', width: '100%' }}
                        onClick={generate}
                        disabled={loading}
                    >
                        {loading ? (
                            <>
                                <span className="spinner" style={{ width: '16px', height: '16px', display: 'inline-block', marginRight: '0.5rem' }}></span>
                                Generating...
                            </>
                        ) : (
                            '✨ Generate Draft'
                        )}
                    </button>

                    {error && (
                        <div style={{ marginTop: '1rem', padding: '0.75rem', background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.25)', borderRadius: '8px', fontSize: '12px', color: 'var(--red)' }}>
                            ⚠️ {error}
                        </div>
                    )}
                </div>
            </div>

            <div>
                {draft ? (
                    <div className="card">
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                            <div className="card-title" style={{ margin: 0 }}>Generated Draft</div>
                            <button
                                className={`btn btn-ghost btn-sm ${copied ? 'copied' : ''}`}
                                onClick={copyToClipboard}
                                style={{ padding: '0.4rem 0.9rem' }}
                            >
                                {copied ? '✓ Copied!' : '📋 Copy'}
                            </button>
                        </div>

                        {/* Subject */}
                        <div style={{
                            fontFamily: 'var(--font-display)',
                            fontWeight: 700,
                            fontSize: '14px',
                            color: 'var(--accent2)',
                            marginBottom: '0.75rem',
                            paddingBottom: '0.75rem',
                            borderBottom: '1px solid var(--border)'
                        }}>
                            Subject: {draft.subject}
                        </div>

                        {/* Body */}
                        <div style={{
                            whiteSpace: 'pre-wrap',
                            lineHeight: 1.7,
                            fontSize: '13px',
                            color: 'var(--text2)',
                            maxHeight: '400px',
                            overflowY: 'auto',
                            fontFamily: 'var(--font-body)'
                        }}>
                            {draft.body}
                        </div>

                        {/* AI Disclaimer */}
                        <div style={{
                            marginTop: '1rem',
                            paddingTop: '0.75rem',
                            borderTop: '1px solid var(--border)',
                            fontSize: '11px',
                            color: 'var(--text3)',
                            textAlign: 'center'
                        }}>
                            🤖 AI-generated draft • Please review before sending
                        </div>
                    </div>
                ) : (
                    <div className="empty-state" style={{ background: 'var(--surface)', borderRadius: '12px', border: '1px solid var(--border)', padding: '3rem' }}>
                        <div className="empty-icon">✉️</div>
                        <div className="empty-title">Draft will appear here</div>
                        <div className="empty-sub">Select a message type and click Generate</div>
                        <div style={{ marginTop: '1rem', fontSize: '12px', color: 'var(--text3)' }}>
                            ✨ AI will create a professional email based on:
                            <ul style={{ marginTop: '0.5rem', textAlign: 'left', paddingLeft: '1.5rem' }}>
                                <li>Transaction details (amount, due date, days late)</li>
                                <li>Counterparty type and relationship</li>
                                <li>Your selected message type</li>
                                <li>Any additional context you provide</li>
                            </ul>
                        </div>
                    </div>
                )}
            </div>

            <style>{`
                .btn-ghost {
                    background: transparent;
                    color: var(--text2);
                    border: 1px solid var(--border);
                }
                .btn-ghost:hover {
                    background: var(--surface2);
                    color: var(--text);
                }
                .btn-sm {
                    padding: 0.4rem 0.9rem;
                    font-size: 12px;
                }
                .copied {
                    animation: pop 0.3s ease;
                }
                @keyframes pop {
                    0%,100%{transform:scale(1)}
                    50%{transform:scale(1.1)}
                }
                .badge-high { background: rgba(239,68,68,0.1); color: #ef4444; border: 1px solid rgba(239,68,68,0.25); }
                .badge-medium { background: rgba(245,158,11,0.1); color: #f59e0b; border: 1px solid rgba(245,158,11,0.25); }
                .badge-low { background: rgba(16,185,129,0.1); color: #10b981; border: 1px solid rgba(16,185,129,0.25); }
                .mono { font-family: var(--font-mono); }
            `}</style>
        </div>
    );
};

export default Communicate;