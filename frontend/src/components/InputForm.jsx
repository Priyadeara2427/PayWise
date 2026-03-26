import React, { useState } from 'react';

const InputForm = ({ onAnalyze, loading }) => {
    const [form, setForm] = useState({
        counterparty_name: '',
        counterparty_type: 'vendor',
        amount: '',
        due_date: '',
        transaction_type: 'payable',
        status: 'pending',
        accepts_partial: true,
        minimum_partial_pct: 40
    });

    const handleSubmit = () => {
        if (!form.counterparty_name || !form.amount) {
            alert('Please fill in counterparty name and amount');
            return;
        }
        onAnalyze(form);
    };

    const handleChange = (field, value) => {
        setForm(prev => ({ ...prev, [field]: value }));
    };

    return (
        <div>
            <h2 style={{ marginBottom: '1.5rem' }}>📝 Manual Transaction Entry</h2>
            
            <div className="two-column">
                <div className="card">
                    <div className="card-title">COUNTERPARTY DETAILS</div>
                    <div className="form-group">
                        <label className="form-label">Counterparty Name *</label>
                        <input
                            className="form-input"
                            placeholder="e.g., Raj Fabrics"
                            value={form.counterparty_name}
                            onChange={e => handleChange('counterparty_name', e.target.value)}
                        />
                    </div>
                    <div className="form-group">
                        <label className="form-label">Counterparty Type</label>
                        <select
                            className="form-select"
                            value={form.counterparty_type}
                            onChange={e => handleChange('counterparty_type', e.target.value)}
                        >
                            <option value="vendor">Vendor / Supplier</option>
                            <option value="customer">Customer / Buyer</option>
                            <option value="tax_authority">Tax Authority</option>
                            <option value="government">Government</option>
                            <option value="bank">Bank</option>
                            <option value="employee">Employee</option>
                            <option value="friend">Friend</option>
                            <option value="family">Family</option>
                        </select>
                    </div>
                    <div className="form-group">
                        <label className="form-label">Transaction Type</label>
                        <select
                            className="form-select"
                            value={form.transaction_type}
                            onChange={e => handleChange('transaction_type', e.target.value)}
                        >
                            <option value="payable">Payable (You owe)</option>
                            <option value="receivable">Receivable (Owed to you)</option>
                        </select>
                    </div>
                </div>

                <div className="card">
                    <div className="card-title">TRANSACTION DETAILS</div>
                    <div className="form-group">
                        <label className="form-label">Amount (₹) *</label>
                        <input
                            type="number"
                            className="form-input"
                            placeholder="45000"
                            value={form.amount}
                            onChange={e => handleChange('amount', e.target.value)}
                        />
                    </div>
                    <div className="form-group">
                        <label className="form-label">Due Date</label>
                        <input
                            type="date"
                            className="form-input"
                            value={form.due_date}
                            onChange={e => handleChange('due_date', e.target.value)}
                        />
                    </div>
                    <div className="form-group">
                        <label className="form-label">Status</label>
                        <select
                            className="form-select"
                            value={form.status}
                            onChange={e => handleChange('status', e.target.value)}
                        >
                            <option value="pending">Pending</option>
                            <option value="overdue">Overdue</option>
                            <option value="paid">Paid</option>
                        </select>
                    </div>
                </div>
            </div>

            <div className="card" style={{ marginTop: '1rem' }}>
                <div className="card-title">PAYMENT TERMS</div>
                <div className="two-column">
                    <div>
                        <div className="form-group">
                            <label className="form-label">Accepts Partial Payment</label>
                            <select
                                className="form-select"
                                value={form.accepts_partial.toString()}
                                onChange={e => handleChange('accepts_partial', e.target.value === 'true')}
                            >
                                <option value="true">Yes</option>
                                <option value="false">No</option>
                            </select>
                        </div>
                    </div>
                    <div>
                        <div className="form-group">
                            <label className="form-label">Minimum Partial %</label>
                            <input
                                type="number"
                                className="form-input"
                                placeholder="40"
                                value={form.minimum_partial_pct}
                                onChange={e => handleChange('minimum_partial_pct', e.target.value)}
                            />
                        </div>
                    </div>
                </div>
            </div>

            <div style={{ display: 'flex', gap: '1rem', marginTop: '1.5rem' }}>
                <button className="btn btn-primary" onClick={handleSubmit} disabled={loading}>
                    {loading ? <><span className="spinner"></span> Analyzing...</> : '🔍 Analyze Transaction'}
                </button>
                <button className="btn btn-secondary" onClick={() => {
                    setForm({
                        counterparty_name: '',
                        counterparty_type: 'vendor',
                        amount: '',
                        due_date: '',
                        transaction_type: 'payable',
                        status: 'pending',
                        accepts_partial: true,
                        minimum_partial_pct: 40
                    });
                }}>
                    Reset
                </button>
            </div>
        </div>
    );
};

export default InputForm;