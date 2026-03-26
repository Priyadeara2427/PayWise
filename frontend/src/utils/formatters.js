// src/utils/formatters.js
export const formatCurrency = (amount) => {
    if (amount === undefined || amount === null) return '₹0';
    return new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(amount);
};

export const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-IN', {
        day: '2-digit',
        month: 'short',
        year: 'numeric'
    });
};

export const getPriorityBadgeClass = (priority) => {
    const classes = {
        'critical': 'badge-critical',
        'high': 'badge-high',
        'medium': 'badge-medium',
        'low': 'badge-low'
    };
    return classes[priority] || 'badge-medium';
};

// Add this missing function
export const getRiskColor = (score) => {
    if (score >= 0.7) return '#dc3545';
    if (score >= 0.4) return '#ffc107';
    return '#28a745';
};