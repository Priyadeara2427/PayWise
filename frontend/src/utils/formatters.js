export const formatCurrency = (amount) => {
    if (amount === undefined || amount === null) return '₹0';
    return `₹${amount.toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;
};

export const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A';
    try {
        return new Date(dateStr).toLocaleDateString('en-IN');
    } catch {
        return dateStr;
    }
};

export const getRiskColor = (score) => {
    if (score >= 0.7) return '#ef4444';
    if (score >= 0.4) return '#f59e0b';
    return '#10b981';
};

export const getRiskLevel = (score) => {
    if (score >= 0.7) return 'High';
    if (score >= 0.4) return 'Medium';
    return 'Low';
};

export const getPriorityBadgeClass = (priority) => {
    const classes = {
        'Critical': 'badge-critical',
        'High': 'badge-high',
        'Medium': 'badge-medium',
        'Low': 'badge-low'
    };
    return classes[priority] || 'badge-medium';
};