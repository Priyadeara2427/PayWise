import React from 'react';
import { formatCurrency } from '../utils/formatters';

const StatsCards = ({ stats }) => {
    if (!stats) return null;
    
    return (
        <div className="stats-grid">
            <div className="stat-card">
                <div className="stat-value">{stats.total_transactions || 0}</div>
                <div className="stat-label">Total Transactions</div>
            </div>
            <div className="stat-card">
                <div className="stat-value">{formatCurrency(stats.total_amount || 0)}</div>
                <div className="stat-label">Total Value</div>
            </div>
            <div className="stat-card">
                <div className="stat-value" style={{ color: 'var(--warning)' }}>
                    {stats.high_risk_count || 0}
                </div>
                <div className="stat-label">High Risk</div>
            </div>
            <div className="stat-card">
                <div className="stat-value" style={{ color: 'var(--danger)' }}>
                    {stats.overdue_count || 0}
                </div>
                <div className="stat-label">Overdue</div>
            </div>
            <div className="stat-card">
                <div className="stat-value">{formatCurrency(stats.total_penalties || 0)}</div>
                <div className="stat-label">Total Penalties</div>
            </div>
            <div className="stat-card">
                <div className="stat-value">{((stats.avg_risk_score || 0) * 100).toFixed(0)}%</div>
                <div className="stat-label">Avg Risk Score</div>
            </div>
        </div>
    );
};

export default StatsCards;