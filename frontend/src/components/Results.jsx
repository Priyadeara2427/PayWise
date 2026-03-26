import React from 'react';
import { formatCurrency, formatDate, getPriorityBadgeClass } from '../utils/formatters';
import RiskMeter from './RiskMeter';
import ActionList from './ActionList';

const Results = ({ data }) => {
    if (!data) {
        return (
            <div className="empty-state">
                <div className="empty-icon">📊</div>
                <div className="empty-title">No Analysis Yet</div>
                <div className="empty-sub">Enter transaction details or upload a document to see analysis</div>
            </div>
        );
    }

    return (
        <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
                <div>
                    <h2 style={{ marginBottom: '0.25rem' }}>{data.counterparty_name}</h2>
                    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                        <span className={`badge ${getPriorityBadgeClass(data.priority)}`}>{data.priority}</span>
                        <span className="badge badge-medium">{data.counterparty_type}</span>
                        <span className="badge badge-medium">{data.transaction_type}</span>
                        <span className={`badge ${data.status === 'overdue' ? 'badge-critical' : 'badge-medium'}`}>{data.status}</span>
                    </div>
                </div>
                <div style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>{formatCurrency(data.amount)}</div>
            </div>

            {/* Stats Grid */}
            <div className="stats-grid">
                <div className="stat-card">
                    <div className="stat-value" style={{ color: data.days_late > 0 ? 'var(--warning)' : 'var(--success)' }}>
                        {data.days_late}
                    </div>
                    <div className="stat-label">Days Late</div>
                </div>
                <div className="stat-card">
                    <div className="stat-value" style={{ color: 'var(--danger)' }}>
                        {formatCurrency(data.penalty_analysis?.total_penalty || 0)}
                    </div>
                    <div className="stat-label">Total Penalty</div>
                </div>
                <div className="stat-card">
                    <div className="stat-value">{formatCurrency(data.penalty_analysis?.total_effective_cost || data.amount)}</div>
                    <div className="stat-label">Total Cost</div>
                </div>
                <div className="stat-card">
                    <div className="stat-value">{data.risk_score ? `${(data.risk_score * 100).toFixed(0)}%` : 'N/A'}</div>
                    <div className="stat-label">Risk Score</div>
                </div>
            </div>

            <div className="two-column">
                {/* Risk Analysis */}
                <div className="card">
                    <div className="card-title">RISK ANALYSIS</div>
                    <RiskMeter score={data.risk_score || 0} />
                    {data.risk_factors && data.risk_factors.length > 0 && (
                        <div style={{ marginTop: '1rem' }}>
                            {data.risk_factors.map((factor, i) => (
                                <div key={i} style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>⚠️ {factor}</div>
                            ))}
                        </div>
                    )}
                </div>

                {/* Recommended Actions */}
                <div className="card">
                    <div className="card-title">RECOMMENDED ACTIONS</div>
                    <ActionList actions={data.recommended_actions} />
                </div>
            </div>

            {/* Penalty Breakdown */}
            {data.penalty_analysis?.penalty_breakdown && data.penalty_analysis.penalty_breakdown.length > 0 && (
                <div className="card" style={{ marginTop: '1.5rem' }}>
                    <div className="card-title">PENALTY BREAKDOWN</div>
                    <table className="data-table">
                        <thead>
                            <tr>
                                <th>Type</th>
                                <th>Calculation</th>
                                <th style={{ textAlign: 'right' }}>Amount</th>
                            </tr>
                        </thead>
                        <tbody>
                            {data.penalty_analysis.penalty_breakdown.map((item, i) => (
                                <tr key={i}>
                                    <td>{item.type}</td>
                                    <td style={{ fontFamily: 'monospace', fontSize: '0.7rem' }}>{item.calculation}</td>
                                    <td style={{ textAlign: 'right' }}>{formatCurrency(item.amount)}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            {/* Assumptions */}
            {data.assumptions_made && data.assumptions_made.length > 0 && (
                <div className="card" style={{ marginTop: '1rem', background: 'rgba(245, 158, 11, 0.1)', borderColor: 'var(--warning)' }}>
                    <div className="card-title">📌 ASSUMPTIONS MADE</div>
                    {data.assumptions_made.map((assumption, i) => (
                        <div key={i} style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>⚠️ {assumption}</div>
                    ))}
                </div>
            )}
        </div>
    );
};

export default Results;