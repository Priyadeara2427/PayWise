// src/components/PaymentStrategyDashboard.js
import React, { useState, useEffect } from 'react';
import PaymentPriorityList from './PaymentPriorityList';
import { formatCurrency } from '../utils/formatters';

const PaymentStrategyDashboard = ({ initialData, onRefresh }) => {
    const [data, setData] = useState(initialData || null);
    const [loading, setLoading] = useState(!initialData);
    const [error, setError] = useState(null);
    
    useEffect(() => {
        if (!initialData) {
            fetchDashboardData();
        }
    }, []);
    
    const fetchDashboardData = async () => {
        setLoading(true);
        try {
            const response = await fetch('/api/dashboard-data');
            const result = await response.json();
            if (result.status === 'success') {
                setData(result);
            } else {
                setError(result.message);
            }
        } catch (err) {
            setError('Failed to load dashboard data');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };
    
    const handleCopyMessage = (message) => {
        navigator.clipboard.writeText(message);
        alert('Message copied to clipboard!');
    };
    
    if (loading) {
        return (
            <div className="loading-container" style={{ textAlign: 'center', padding: '3rem' }}>
                <div className="spinner"></div>
                <p>Analyzing payment strategies...</p>
            </div>
        );
    }
    
    if (error) {
        return (
            <div className="error-container" style={{ textAlign: 'center', padding: '3rem', color: 'var(--danger)' }}>
                <div className="error-icon">⚠️</div>
                <p>{error}</p>
                <button onClick={fetchDashboardData} className="btn btn-primary">Try Again</button>
            </div>
        );
    }
    
    if (!data || !data.payments || data.payments.length === 0) {
        return (
            <div className="empty-state">
                <div className="empty-icon">💰</div>
                <div className="empty-title">No Payment Obligations</div>
                <div className="empty-sub">
                    Upload a document or add transactions to see payment strategies
                </div>
            </div>
        );
    }
    
    return (
        <div>
            <div className="dashboard-header" style={{ 
                display: 'flex', 
                justifyContent: 'space-between', 
                alignItems: 'center',
                marginBottom: '1.5rem',
                flexWrap: 'wrap',
                gap: '1rem'
            }}>
                <div>
                    <h1 style={{ margin: 0 }}>Payment Strategy Dashboard</h1>
                    <p style={{ margin: '0.25rem 0 0', color: 'var(--text-secondary)' }}>
                        Analysis based on who you owe money to
                    </p>
                </div>
                <div className="cash-balance" style={{
                    background: data.cash_balance >= 0 ? 'rgba(40, 167, 69, 0.1)' : 'rgba(220, 53, 69, 0.1)',
                    padding: '0.5rem 1rem',
                    borderRadius: '8px',
                    borderLeft: `3px solid ${data.cash_balance >= 0 ? '#28a745' : '#dc3545'}`
                }}>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
                        Current Cash Balance
                    </div>
                    <div style={{ fontSize: '1.25rem', fontWeight: 'bold', color: data.cash_balance >= 0 ? '#28a745' : '#dc3545' }}>
                        {formatCurrency(data.cash_balance)}
                    </div>
                </div>
            </div>
            
            <PaymentPriorityList 
                payments={data.payments} 
                onCopyMessage={handleCopyMessage}
            />
            
            {onRefresh && (
                <div style={{ textAlign: 'center', marginTop: '1.5rem' }}>
                    <button onClick={onRefresh} className="btn btn-outline">
                        🔄 Refresh Analysis
                    </button>
                </div>
            )}
        </div>
    );
};

export default PaymentStrategyDashboard;