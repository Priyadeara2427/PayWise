// frontend/src/components/ActionList.jsx
import React from 'react';

const ActionList = ({ actions }) => {
    if (!actions || actions.length === 0) {
        return (
            <div style={{ textAlign: 'center', color: 'var(--text-tertiary)', padding: '1rem' }}>
                No recommendations available
            </div>
        );
    }
    
    return (
        <div className="action-list">
            {actions.map((action, idx) => (
                <div key={idx} className={`action-item action-urgency-${action.urgency || 'medium'}`}>
                    <div style={{ fontWeight: 600, marginBottom: '0.25rem' }}>{action.action}</div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{action.rationale}</div>
                </div>
            ))}
        </div>
    );
};

export default ActionList;