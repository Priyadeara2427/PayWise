// frontend/src/components/RiskMeter.jsx
import React from 'react';
import { getRiskColor } from '../utils/formatters';

const RiskMeter = ({ score }) => {
    const percentage = ((score || 0) * 100).toFixed(1);
    const color = getRiskColor(score || 0);
    
    return (
        <div className="risk-meter">
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                <span style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)' }}>RISK SCORE</span>
                <span style={{ fontWeight: 'bold', color }}>{percentage}%</span>
            </div>
            <div className="risk-bar-container">
                <div className="risk-bar" style={{ width: `${percentage}%`, background: color }}></div>
            </div>
        </div>
    );
};

export default RiskMeter;