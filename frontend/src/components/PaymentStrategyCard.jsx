// src/components/PaymentStrategyCard.js
import React, { useState } from 'react';
import { formatCurrency, formatDate, getPriorityBadgeClass } from '../utils/formatters';

const PaymentStrategyCard = ({ obligation, onCopyMessage }) => {
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
    
    const getStrategyBadge = (action) => {
        const badges = {
            'PAY_IMMEDIATELY': { text: '⚠️ PAY IMMEDIATELY', class: 'badge-critical' },
            'NEGOTIATE_EXTENSION': { text: '🤝 NEGOTIATE EXTENSION', class: 'badge-warning' },
            'COMMUNICATE_AND_DELAY': { text: '💬 COMMUNICATE & DELAY', class: 'badge-info' },
            'PAY_PARTIAL_OR_DELAY': { text: '💳 PAY PARTIAL', class: 'badge-info' },
            'PREPARE_FOR_PAYMENT': { text: '📅 PREPARE FOR PAYMENT', class: 'badge-medium' }
        };
        return badges[action] || { text: 'REVIEW', class: 'badge-medium' };
    };
    
    const handleCopyMessage = () => {
        if (onCopyMessage && obligation.message_template) {
            onCopyMessage(obligation.message_template);
        }
    };
    
    return (
        <div 
            className="payment-card" 
            style={{ 
                borderLeft: `5px solid ${getCategoryColor(obligation.payment_category)}`,
                marginBottom: '1rem',
                transition: 'all 0.3s'
            }}
        >
            <div className="payment-header" style={{ 
                display: 'flex', 
                justifyContent: 'space-between', 
                alignItems: 'flex-start',
                flexWrap: 'wrap',
                gap: '1rem',
                marginBottom: '1rem'
            }}>
                <div>
                    <h3 style={{ margin: '0 0 0.5rem 0', fontSize: '1.1rem' }}>
                        {obligation.counterparty}
                    </h3>
                    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                        <span className="badge badge-medium">{obligation.counterparty_type}</span>
                        <span className={`badge ${getStrategyBadge(obligation.payment_action).class}`}>
                            {getStrategyBadge(obligation.payment_action).text}
                        </span>
                        <span className={`badge ${obligation.days_late > 0 ? 'badge-critical' : 'badge-medium'}`}>
                            {obligation.days_late > 0 ? `${obligation.days_late} days overdue` : 
                             obligation.days_until_due > 0 ? `${obligation.days_until_due} days left` : 'Due today'}
                        </span>
                    </div>
                </div>
                <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: obligation.days_late > 0 ? 'var(--warning)' : 'var(--success)' }}>
                    {formatCurrency(obligation.amount)}
                </div>
            </div>
            
            <div className="payment-details" style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                gap: '1rem',
                marginBottom: '1rem'
            }}>
                <div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
                        Due Date
                    </div>
                    <div style={{ fontWeight: '500' }}>
                        {obligation.due_date ? formatDate(obligation.due_date) : 'Not specified'}
                    </div>
                </div>
                <div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
                        Flexibility
                    </div>
                    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginTop: '0.25rem' }}>
                        {obligation.can_negotiate && (
                            <span className="badge badge-success">Can Negotiate</span>
                        )}
                        {obligation.can_delay && (
                            <span className="badge badge-success">Can Delay</span>
                        )}
                        {obligation.can_partial && (
                            <span className="badge badge-info">Can Pay Partial</span>
                        )}
                        {!obligation.can_negotiate && !obligation.can_delay && !obligation.can_partial && (
                            <span className="badge badge-critical">Must Pay Full</span>
                        )}
                    </div>
                </div>
                {obligation.grace_days > 0 && (
                    <div>
                        <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
                            Grace Period
                        </div>
                        <div style={{ fontWeight: '500' }}>
                            {obligation.grace_days} days
                        </div>
                    </div>
                )}
                {obligation.penalty_rate > 0 && (
                    <div>
                        <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
                            Penalty Rate
                        </div>
                        <div style={{ fontWeight: '500', color: 'var(--warning)' }}>
                            {obligation.penalty_rate * 100}% per day
                        </div>
                    </div>
                )}
            </div>
            
            <div className="recommendation" style={{
                background: 'rgba(102, 126, 234, 0.1)',
                padding: '0.75rem',
                borderRadius: '8px',
                marginBottom: '0.75rem'
            }}>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>
                    💡 RECOMMENDATION
                </div>
                <div style={{ fontSize: '0.85rem' }}>
                    {obligation.recommendation || obligation.reason || 'No specific recommendation'}
                </div>
            </div>
            
            {obligation.risks && obligation.risks.length > 0 && (
                <div style={{
                    background: 'rgba(220, 53, 69, 0.1)',
                    padding: '0.75rem',
                    borderRadius: '8px',
                    marginBottom: '0.75rem',
                    borderLeft: '3px solid var(--danger)'
                }}>
                    <div style={{ fontSize: '0.7rem', color: 'var(--danger)', marginBottom: '0.25rem' }}>
                        ⚠️ RISKS OF DELAY
                    </div>
                    {obligation.risks.map((risk, idx) => (
                        <div key={idx} style={{ fontSize: '0.75rem', marginBottom: '0.25rem' }}>
                            • {risk}
                        </div>
                    ))}
                </div>
            )}
            
            {obligation.message_template && (
                <div>
                    <button 
                        onClick={() => setShowMessage(!showMessage)}
                        className="btn btn-outline"
                        style={{ fontSize: '0.8rem', marginBottom: showMessage ? '0.75rem' : 0 }}
                    >
                        {showMessage ? 'Hide Message Template' : '📧 Show Message Template'}
                    </button>
                    
                    {showMessage && (
                        <div style={{
                            background: '#f8f9fa',
                            padding: '0.75rem',
                            borderRadius: '8px',
                            marginTop: '0.5rem',
                            fontStyle: 'italic'
                        }}>
                            <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                                Suggested Message:
                            </div>
                            <div style={{ fontSize: '0.8rem', marginBottom: '0.5rem', whiteSpace: 'pre-wrap' }}>
                                {obligation.message_template}
                            </div>
                            <button 
                                onClick={handleCopyMessage}
                                className="btn btn-primary"
                                style={{ fontSize: '0.75rem', padding: '0.25rem 0.75rem' }}
                            >
                                📋 Copy Message
                            </button>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

export default PaymentStrategyCard;