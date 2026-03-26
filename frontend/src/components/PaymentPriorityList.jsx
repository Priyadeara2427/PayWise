// src/components/PaymentPriorityList.js
import React, { useState } from 'react';
import PaymentStrategyCard from './PaymentStrategyCard';

const PaymentPriorityList = ({ payments, onCopyMessage }) => {
    const [filter, setFilter] = useState('all');
    const [searchTerm, setSearchTerm] = useState('');
    
    const filters = [
        { value: 'all', label: 'All', icon: '📋' },
        { value: 'must_pay', label: 'Must Pay Now', icon: '⚠️', color: '#dc3545' },
        { value: 'can_negotiate', label: 'Can Negotiate', icon: '🤝', color: '#ffc107' },
        { value: 'can_partial', label: 'Can Pay Partial', icon: '💳', color: '#17a2b8' },
        { value: 'can_delay', label: 'Can Delay', icon: '⏰', color: '#28a745' }
    ];
    
    const filteredPayments = payments.filter(payment => {
        if (filter !== 'all' && payment.payment_category !== filter) return false;
        if (searchTerm) {
            const searchLower = searchTerm.toLowerCase();
            return payment.counterparty.toLowerCase().includes(searchLower) ||
                   payment.counterparty_type.toLowerCase().includes(searchLower);
        }
        return true;
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
        return (b.urgency_score || 0) - (a.urgency_score || 0);
    });
    
    const summary = {
        total_amount: payments.reduce((sum, p) => sum + p.amount, 0),
        must_pay_amount: payments.filter(p => p.payment_category === 'must_pay').reduce((sum, p) => sum + p.amount, 0),
        can_negotiate_amount: payments.filter(p => p.payment_category === 'can_negotiate').reduce((sum, p) => sum + p.amount, 0),
        can_partial_amount: payments.filter(p => p.payment_category === 'can_partial').reduce((sum, p) => sum + p.amount, 0),
        can_delay_amount: payments.filter(p => p.payment_category === 'can_delay').reduce((sum, p) => sum + p.amount, 0)
    };
    
    return (
        <div>
            <div style={{ marginBottom: '1.5rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', flexWrap: 'wrap', gap: '1rem' }}>
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
                
                <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
                    <input
                        type="text"
                        placeholder="Search by name or type..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        style={{
                            flex: 1,
                            padding: '0.5rem',
                            borderRadius: '8px',
                            border: '1px solid var(--border)',
                            background: 'var(--bg-secondary)',
                            color: 'var(--text-primary)'
                        }}
                    />
                </div>
                
                <div className="stats-grid" style={{ marginBottom: '1.5rem' }}>
                    <div className="stat-card" style={{ background: 'rgba(220, 53, 69, 0.1)' }}>
                        <div className="stat-value" style={{ color: '#dc3545' }}>
                            {formatCurrency(summary.must_pay_amount)}
                        </div>
                        <div className="stat-label">Must Pay Now</div>
                    </div>
                    <div className="stat-card" style={{ background: 'rgba(255, 193, 7, 0.1)' }}>
                        <div className="stat-value" style={{ color: '#ffc107' }}>
                            {formatCurrency(summary.can_negotiate_amount)}
                        </div>
                        <div className="stat-label">Can Negotiate</div>
                    </div>
                    <div className="stat-card" style={{ background: 'rgba(23, 162, 184, 0.1)' }}>
                        <div className="stat-value" style={{ color: '#17a2b8' }}>
                            {formatCurrency(summary.can_partial_amount)}
                        </div>
                        <div className="stat-label">Can Pay Partial</div>
                    </div>
                    <div className="stat-card" style={{ background: 'rgba(40, 167, 69, 0.1)' }}>
                        <div className="stat-value" style={{ color: '#28a745' }}>
                            {formatCurrency(summary.can_delay_amount)}
                        </div>
                        <div className="stat-label">Can Delay</div>
                    </div>
                </div>
            </div>
            
            {sortedPayments.length === 0 ? (
                <div className="empty-state" style={{ padding: '2rem', textAlign: 'center' }}>
                    <div className="empty-icon">📭</div>
                    <div className="empty-title">No payments found</div>
                    <div className="empty-sub">Try changing your filter or search term</div>
                </div>
            ) : (
                <div>
                    {sortedPayments.map((payment, index) => (
                        <div key={payment.transaction_id || index} style={{ position: 'relative' }}>
                            <div style={{
                                position: 'absolute',
                                left: '-1rem',
                                top: '1rem',
                                background: 'var(--bg-secondary)',
                                borderRadius: '50%',
                                width: '24px',
                                height: '24px',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                fontSize: '0.75rem',
                                fontWeight: 'bold',
                                zIndex: 1
                            }}>
                                {index + 1}
                            </div>
                            <PaymentStrategyCard 
                                obligation={payment} 
                                onCopyMessage={onCopyMessage}
                            />
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

export default PaymentPriorityList;