// frontend/src/components/Results.jsx
import React, { useState } from 'react';
import { formatCurrency, getPriorityBadgeClass } from '../utils/formatters';
import RiskMeter from './RiskMeter';
import ActionList from './ActionList';

const Results = ({ data }) => {
    const [viewMode, setViewMode] = useState('single');
    
    if (!data) {
        return (
            <div className="empty-state">
                <div className="empty-icon">📊</div>
                <div className="empty-title">No Analysis Yet</div>
                <div className="empty-sub">Enter transaction details or upload a document to see analysis</div>
            </div>
        );
    }

    const hasMultipleObligations = data.payments && data.payments.length > 0;
    const obligation = hasMultipleObligations && data.payments.length === 1 ? data.payments[0] : data;
    
    // Dashboard view for multiple payments
    if (hasMultipleObligations && viewMode === 'dashboard') {
        return (
            <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '1rem' }}>
                    <button 
                        onClick={() => setViewMode('single')}
                        className="btn btn-outline"
                        style={{ fontSize: '0.8rem', padding: '0.5rem 1rem' }}
                    >
                        ← Back to Single View
                    </button>
                    <div style={{
                        background: data.cash_balance >= 0 ? 'rgba(40, 167, 69, 0.1)' : 'rgba(220, 53, 69, 0.1)',
                        padding: '0.5rem 1rem',
                        borderRadius: '8px',
                        borderLeft: `3px solid ${data.cash_balance >= 0 ? '#28a745' : '#dc3545'}`
                    }}>
                        <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>Current Cash Balance</div>
                        <div style={{ fontSize: '1.25rem', fontWeight: 'bold', color: data.cash_balance >= 0 ? '#28a745' : '#dc3545' }}>
                            {formatCurrency(data.cash_balance)}
                        </div>
                    </div>
                </div>
                <PaymentStrategyDashboard payments={data.payments} />
            </div>
        );
    }

    // Single obligation view
    return (
        <div>
            {hasMultipleObligations && (
                <div style={{ marginBottom: '1rem', textAlign: 'right' }}>
                    <button 
                        onClick={() => setViewMode('dashboard')}
                        className="btn btn-primary"
                        style={{ fontSize: '0.8rem', padding: '0.5rem 1rem' }}
                    >
                        📊 View Dashboard ({data.payments.length} payments)
                    </button>
                </div>
            )}
            
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
                <div>
                    <h2 style={{ marginBottom: '0.25rem' }}>{obligation.counterparty_name || obligation.counterparty || 'Unknown'}</h2>
                    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                        <span className={`badge ${getPriorityBadgeClass(obligation.priority)}`}>{obligation.priority || 'medium'}</span>
                        <span className="badge badge-medium">{obligation.counterparty_type || 'unknown'}</span>
                        <span className={`badge ${obligation.days_late > 0 ? 'badge-critical' : 'badge-medium'}`}>
                            {obligation.days_late > 0 ? `${obligation.days_late} days overdue` : 'On time'}
                        </span>
                        {obligation.payment_category && (
                            <span className={`badge ${getCategoryBadgeClass(obligation.payment_category)}`}>
                                {getCategoryLabel(obligation.payment_category)}
                            </span>
                        )}
                    </div>
                </div>
                <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: obligation.days_late > 0 ? '#dc3545' : '#28a745' }}>
                    {formatCurrency(obligation.amount)}
                </div>
            </div>

            {/* Stats Grid */}
            <div className="stats-grid">
                <div className="stat-card">
                    <div className="stat-value" style={{ color: obligation.days_late > 0 ? '#ffc107' : '#28a745' }}>
                        {obligation.days_late || 0}
                    </div>
                    <div className="stat-label">Days Late</div>
                </div>
                <div className="stat-card">
                    <div className="stat-value" style={{ color: '#dc3545' }}>
                        {formatCurrency(obligation.penalty_analysis?.total_penalty || 0)}
                    </div>
                    <div className="stat-label">Total Penalty</div>
                </div>
                <div className="stat-card">
                    <div className="stat-value">{formatCurrency(obligation.penalty_analysis?.total_effective_cost || obligation.amount)}</div>
                    <div className="stat-label">Total Cost</div>
                </div>
                <div className="stat-card">
                    <div className="stat-value">{obligation.risk_score ? `${(obligation.risk_score * 100).toFixed(0)}%` : 'N/A'}</div>
                    <div className="stat-label">Risk Score</div>
                </div>
            </div>

            {/* Payment Strategy Section */}
            {(obligation.payment_category || obligation.recommendation || obligation.message_template) && (
                <div className="card" style={{ marginBottom: '1.5rem', background: 'rgba(102, 126, 234, 0.05)' }}>
                    <div className="card-title">🎯 PAYMENT STRATEGY</div>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '1rem' }}>
                        {obligation.payment_category && (
                            <div>
                                <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>Category</div>
                                <div style={{ fontWeight: 'bold' }}>{getCategoryLabel(obligation.payment_category)}</div>
                            </div>
                        )}
                        <div>
                            <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>Can Negotiate</div>
                            <div>{obligation.can_negotiate ? '✅ Yes' : '❌ No'}</div>
                        </div>
                        <div>
                            <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>Can Delay</div>
                            <div>{obligation.can_delay ? '✅ Yes' : '❌ No'}</div>
                        </div>
                        <div>
                            <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>Can Pay Partial</div>
                            <div>{obligation.can_partial ? '✅ Yes' : '❌ No'}</div>
                        </div>
                        {obligation.grace_days > 0 && (
                            <div>
                                <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>Grace Period</div>
                                <div>{obligation.grace_days} days</div>
                            </div>
                        )}
                    </div>
                    
                    {obligation.recommendation && (
                        <div style={{ 
                            background: 'rgba(102, 126, 234, 0.1)', 
                            padding: '0.75rem', 
                            borderRadius: '8px',
                            marginBottom: '0.75rem'
                        }}>
                            <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>💡 Recommendation</div>
                            <div>{obligation.recommendation}</div>
                        </div>
                    )}
                    
                    {obligation.message_template && (
                        <div>
                            <button 
                                onClick={() => {
                                    navigator.clipboard.writeText(obligation.message_template);
                                    alert('Message copied to clipboard!');
                                }}
                                className="btn btn-outline"
                                style={{ fontSize: '0.75rem', padding: '0.25rem 0.75rem' }}
                            >
                                📋 Copy Message Template
                            </button>
                        </div>
                    )}
                </div>
            )}

            <div className="two-column">
                {/* Risk Analysis */}
                <div className="card">
                    <div className="card-title">RISK ANALYSIS</div>
                    <RiskMeter score={obligation.risk_score || 0} />
                    {obligation.risks && obligation.risks.length > 0 && (
                        <div style={{ marginTop: '1rem', borderTop: '1px solid var(--border)', paddingTop: '0.75rem' }}>
                            <div style={{ fontSize: '0.7rem', color: '#dc3545' }}>⚠️ Specific Risks</div>
                            {obligation.risks.map((risk, i) => (
                                <div key={i} style={{ fontSize: '0.7rem', marginTop: '0.25rem' }}>• {risk}</div>
                            ))}
                        </div>
                    )}
                </div>

                {/* Recommended Actions */}
                <div className="card">
                    <div className="card-title">RECOMMENDED ACTIONS</div>
                    <ActionList actions={obligation.recommended_actions || []} />
                    {obligation.payment_action && (
                        <div style={{ marginTop: '0.75rem', padding: '0.5rem', background: 'rgba(102, 126, 234, 0.1)', borderRadius: '8px' }}>
                            <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>Primary Strategy</div>
                            <div style={{ fontWeight: 'bold' }}>{getStrategyLabel(obligation.payment_action)}</div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

// Helper Functions
const getCategoryLabel = (category) => {
    const labels = {
        'must_pay': '⚠️ Must Pay Now',
        'can_negotiate': '🤝 Can Negotiate',
        'can_partial': '💳 Can Pay Partial',
        'can_delay': '⏰ Can Delay'
    };
    return labels[category] || category;
};

const getCategoryBadgeClass = (category) => {
    const classes = {
        'must_pay': 'badge-critical',
        'can_negotiate': 'badge-warning',
        'can_partial': 'badge-info',
        'can_delay': 'badge-success'
    };
    return classes[category] || 'badge-medium';
};

const getStrategyLabel = (action) => {
    const labels = {
        'PAY_IMMEDIATELY': 'Pay Immediately',
        'NEGOTIATE_EXTENSION': 'Negotiate Extension',
        'COMMUNICATE_AND_DELAY': 'Communicate and Delay',
        'PAY_PARTIAL_OR_DELAY': 'Pay Partial or Delay',
        'PREPARE_FOR_PAYMENT': 'Prepare for Payment'
    };
    return labels[action] || action;
};

// PaymentStrategyDashboard Component
const PaymentStrategyDashboard = ({ payments }) => {
    const [filter, setFilter] = useState('all');
    
    const filters = [
        { value: 'all', label: 'All', icon: '📋' },
        { value: 'must_pay', label: 'Must Pay Now', icon: '⚠️' },
        { value: 'can_negotiate', label: 'Can Negotiate', icon: '🤝' },
        { value: 'can_partial', label: 'Can Pay Partial', icon: '💳' },
        { value: 'can_delay', label: 'Can Delay', icon: '⏰' }
    ];
    
    const filteredPayments = payments.filter(payment => {
        if (filter === 'all') return true;
        return payment.payment_category === filter;
    });
    
    const categoryOrder = {
        'must_pay': 1,
        'can_negotiate': 2,
        'can_partial': 3,
        'can_delay': 4
    };
    
    const sortedPayments = [...filteredPayments].sort((a, b) => {
        const orderDiff = (categoryOrder[a.payment_category] || 5) - (categoryOrder[b.payment_category] || 5);
        if (orderDiff !== 0) return orderDiff;
        return (b.days_late || 0) - (a.days_late || 0);
    });
    
    const summary = {
        must_pay_amount: payments.filter(p => p.payment_category === 'must_pay').reduce((sum, p) => sum + p.amount, 0),
        can_negotiate_amount: payments.filter(p => p.payment_category === 'can_negotiate').reduce((sum, p) => sum + p.amount, 0),
        can_partial_amount: payments.filter(p => p.payment_category === 'can_partial').reduce((sum, p) => sum + p.amount, 0),
        can_delay_amount: payments.filter(p => p.payment_category === 'can_delay').reduce((sum, p) => sum + p.amount, 0)
    };
    
    return (
        <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '0.5rem' }}>
                <h3 style={{ margin: 0 }}>Payment Priority Order</h3>
                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                    {filters.map(f => (
                        <button
                            key={f.value}
                            onClick={() => setFilter(f.value)}
                            className={`btn ${filter === f.value ? 'btn-primary' : 'btn-outline'}`}
                            style={{ fontSize: '0.75rem', padding: '0.25rem 0.75rem' }}
                        >
                            {f.icon} {f.label}
                        </button>
                    ))}
                </div>
            </div>
            
            <div className="stats-grid" style={{ marginBottom: '1.5rem' }}>
                <div className="stat-card" style={{ background: 'rgba(220, 53, 69, 0.1)' }}>
                    <div className="stat-value" style={{ color: '#dc3545' }}>{formatCurrency(summary.must_pay_amount)}</div>
                    <div className="stat-label">Must Pay Now</div>
                </div>
                <div className="stat-card" style={{ background: 'rgba(255, 193, 7, 0.1)' }}>
                    <div className="stat-value" style={{ color: '#ffc107' }}>{formatCurrency(summary.can_negotiate_amount)}</div>
                    <div className="stat-label">Can Negotiate</div>
                </div>
                <div className="stat-card" style={{ background: 'rgba(23, 162, 184, 0.1)' }}>
                    <div className="stat-value" style={{ color: '#17a2b8' }}>{formatCurrency(summary.can_partial_amount)}</div>
                    <div className="stat-label">Can Pay Partial</div>
                </div>
                <div className="stat-card" style={{ background: 'rgba(40, 167, 69, 0.1)' }}>
                    <div className="stat-value" style={{ color: '#28a745' }}>{formatCurrency(summary.can_delay_amount)}</div>
                    <div className="stat-label">Can Delay</div>
                </div>
            </div>
            
            {sortedPayments.map((payment, index) => (
                <PaymentCard 
                    key={payment.transaction_id || index}
                    payment={payment}
                    rank={index + 1}
                />
            ))}
        </div>
    );
};

// PaymentCard Component
const PaymentCard = ({ payment, rank }) => {
    const [showMessage, setShowMessage] = useState(false);
    
    const getCategoryColor = (category) => {
        const colors = {
            'must_pay': '#dc3545',
            'can_negotiate': '#ffc107',
            'can_partial': '#17a2b8',
            'can_delay': '#28a745'
        };
        return colors[category] || '#6c757d';
    };
    
    return (
        <div 
            className="payment-card" 
            style={{ 
                borderLeft: `5px solid ${getCategoryColor(payment.payment_category)}`,
                marginBottom: '1rem',
                position: 'relative',
                background: 'var(--bg-secondary)',
                borderRadius: '12px',
                padding: '1.25rem',
                transition: 'all 0.3s'
            }}
        >
            <div style={{
                position: 'absolute',
                left: '-12px',
                top: '20px',
                background: '#667eea',
                borderRadius: '50%',
                width: '24px',
                height: '24px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '0.75rem',
                fontWeight: 'bold',
                color: 'white',
                zIndex: 1
            }}>
                {rank}
            </div>
            
            <div style={{ paddingLeft: '20px' }}>
                <div style={{ 
                    display: 'flex', 
                    justifyContent: 'space-between', 
                    alignItems: 'flex-start',
                    flexWrap: 'wrap',
                    gap: '1rem',
                    marginBottom: '1rem'
                }}>
                    <div>
                        <h4 style={{ margin: '0 0 0.5rem 0' }}>{payment.counterparty}</h4>
                        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                            <span className="badge badge-medium">{payment.counterparty_type}</span>
                            <span className={`badge ${payment.days_late > 0 ? 'badge-critical' : 'badge-medium'}`}>
                                {payment.days_late > 0 ? `${payment.days_late} days overdue` : 'On time'}
                            </span>
                        </div>
                    </div>
                    <div style={{ fontSize: '1.25rem', fontWeight: 'bold' }}>
                        {formatCurrency(payment.amount)}
                    </div>
                </div>
                
                <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', marginBottom: '0.75rem' }}>
                    {payment.can_negotiate && <span className="badge badge-warning">🤝 Can Negotiate</span>}
                    {payment.can_delay && <span className="badge badge-success">⏰ Can Delay</span>}
                    {payment.can_partial && <span className="badge badge-info">💳 Can Pay Partial</span>}
                    {payment.grace_days > 0 && <span className="badge badge-medium">🎁 Grace: {payment.grace_days} days</span>}
                </div>
                
                {payment.recommendation && (
                    <div style={{ 
                        background: 'rgba(102, 126, 234, 0.1)', 
                        padding: '0.5rem', 
                        borderRadius: '8px',
                        marginBottom: '0.75rem',
                        fontSize: '0.8rem'
                    }}>
                        💡 {payment.recommendation}
                    </div>
                )}
                
                {payment.message_template && (
                    <div>
                        <button 
                            onClick={() => setShowMessage(!showMessage)}
                            className="btn btn-outline"
                            style={{ fontSize: '0.7rem', padding: '0.25rem 0.5rem' }}
                        >
                            {showMessage ? 'Hide Message' : '📧 Show Message Template'}
                        </button>
                        
                        {showMessage && (
                            <div style={{
                                background: '#f8f9fa',
                                padding: '0.75rem',
                                borderRadius: '8px',
                                marginTop: '0.5rem',
                                fontSize: '0.75rem',
                                color: '#333'
                            }}>
                                {payment.message_template}
                                <button 
                                    onClick={() => {
                                        navigator.clipboard.writeText(payment.message_template);
                                        alert('Message copied to clipboard!');
                                    }}
                                    className="btn btn-primary"
                                    style={{ fontSize: '0.7rem', padding: '0.25rem 0.5rem', marginLeft: '0.5rem' }}
                                >
                                    Copy
                                </button>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
};

export default Results;