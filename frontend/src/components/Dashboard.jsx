import React, { useState, useEffect, useCallback } from 'react';
import { useApi } from '../hooks/useApi';
import { formatCurrency, getRiskColor } from '../utils/formatters';
import {
  LineChart, Line, PieChart, Pie, Cell, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  ReferenceLine, Scatter
} from 'recharts';

const Dashboard = ({ setActiveTab }) => {
    const { request, loading } = useApi();
    const [stats, setStats] = useState(null);
    const [recentTransactions, setRecentTransactions] = useState([]);
    const [showEditModal, setShowEditModal] = useState(false);
    const [parsedData, setParsedData] = useState(null);
    const [editableData, setEditableData] = useState(null);
    
    // State for predictive features
    const [predictiveData, setPredictiveData] = useState(null);
    const [showPredictive, setShowPredictive] = useState(true);
    const [selectedTransaction, setSelectedTransaction] = useState(null);
    const [showPartialModal, setShowPartialModal] = useState(false);
    const [partialPercentage, setPartialPercentage] = useState(50);
    const [borrowingRecommendations, setBorrowingRecommendations] = useState([]);
    const [cascadingRisks, setCascadingRisks] = useState([]);
    const [reorderMode, setReorderMode] = useState(false);
    const [reorderList, setReorderList] = useState([]);
    const [originalOrder, setOriginalOrder] = useState([]);
    const [savedOrder, setSavedOrder] = useState([]);
    const [cashBalance, setCashBalance] = useState(100000);
    const [showCashModal, setShowCashModal] = useState(false);
    const [newCashBalance, setNewCashBalance] = useState('');
    const [showBorrowingModal, setShowBorrowingModal] = useState(false);
    const [selectedBorrowing, setSelectedBorrowing] = useState(null);
    const [realTimeProjection, setRealTimeProjection] = useState(null);
    const [isCalculating, setIsCalculating] = useState(false);
    const [showRestoreConfirm, setShowRestoreConfirm] = useState(false);
    const [activeLocalTab, setLocalActiveTab] = useState('overview');
    const [sortType, setSortType] = useState('ai');
    const [riskAnalysis, setRiskAnalysis] = useState(null);
    const [cashFlowData, setCashFlowData] = useState([]);
    const [partialPaymentMap, setPartialPaymentMap] = useState({});

    useEffect(() => {
        loadDashboard();
        loadPredictiveAnalysis();
        loadRiskAnalysis();
        loadPartialPayments();
    }, []);

    // Real-time calculation when order changes
    useEffect(() => {
        if (reorderList.length > 0 && reorderMode) {
            calculateRealTimeProjection(reorderList);
            generateCashFlowChart(reorderList);
        } else if (savedOrder.length > 0 && !reorderMode) {
            calculateRealTimeProjection(savedOrder);
            generateCashFlowChart(savedOrder);
        } else if (predictiveData?.current_order && !reorderMode && savedOrder.length === 0) {
            calculateRealTimeProjection(predictiveData.current_order);
            generateCashFlowChart(predictiveData.current_order);
        }
    }, [reorderList, cashBalance, reorderMode, savedOrder, predictiveData, partialPaymentMap]);

    const loadPartialPayments = async () => {
        try {
            const result = await request('/get-partial-payments');
            if (result && result.success) {
                setPartialPaymentMap(result.payments || {});
            }
        } catch (err) {
            console.error('Failed to load partial payments:', err);
        }
    };

    const generateCashFlowChart = (orderList) => {
        if (!orderList || orderList.length === 0) return;
        
        // Sort by due date
        const sorted = [...orderList].sort((a, b) => {
            const dateA = a.due_date ? new Date(a.due_date) : new Date();
            const dateB = b.due_date ? new Date(b.due_date) : new Date();
            return dateA - dateB;
        });
        
        let runningCash = cashBalance;
        const flow = [];
        let depletionPoint = null;
        
        sorted.forEach((tx, index) => {
            const paid = partialPaymentMap[tx.transaction_id]?.paid_amount || 0;
            const remaining = tx.amount - paid;
            
            // Calculate cash after this transaction
            if (tx.type === 'payable' || tx.counterparty_type === 'payable') {
                runningCash -= remaining;
            } else {
                runningCash += remaining;
            }
            
            const date = tx.due_date ? new Date(tx.due_date).toLocaleDateString() : `Day ${index + 1}`;
            
            flow.push({
                date: date,
                rawDate: tx.due_date,
                cash: runningCash,
                type: tx.type || 'payable',
                party: tx.party,
                amount: remaining,
                originalAmount: tx.amount,
                paidAmount: paid,
                isPartial: paid > 0
            });
            
            // Track first time cash goes negative
            if (depletionPoint === null && runningCash < 0) {
                depletionPoint = {
                    date: date,
                    cash: runningCash,
                    index: flow.length - 1
                };
            }
        });
        
        setCashFlowData(flow);
        setCashFlowDepletion(depletionPoint);
    };

    const loadRiskAnalysis = async () => {
        try {
            const result = await request('/risk-analysis');
            if (result && result.success) {
                setRiskAnalysis(result.data);
            }
        } catch (err) {
            console.error('Failed to load risk analysis:', err);
        }
    };

    const loadSavedOrder = async () => {
        try {
            const result = await request('/get-saved-order');
            if (result && result.success && result.order && result.order.length > 0) {
                return result.order;
            }
        } catch (err) {
            console.error('Failed to load saved order:', err);
        }
        return [];
    };

    const loadDashboard = async () => {
        try {
            const statsData = await request('/dashboard/stats');
            setStats(statsData);
            
            const transactionsData = await request('/transactions');
            setRecentTransactions(transactionsData.transactions?.slice(0, 10) || []);
            
            try {
                const cashData = await request('/get-cash');
                if (cashData && cashData.success) {
                    setCashBalance(cashData.cash_balance);
                } else if (statsData && statsData.cash_balance) {
                    setCashBalance(statsData.cash_balance);
                }
            } catch (err) {
                console.error('Failed to get cash balance:', err);
                setCashBalance(100000);
            }
        } catch (err) {
            console.error('Failed to load dashboard:', err);
        }
    };

    const loadPredictiveAnalysis = async () => {
        try {
            const result = await request('/predictive-analysis');
            if (result && result.custom_scenario) {
                setPredictiveData(result);
                setBorrowingRecommendations(result.borrowing_recommendations || []);
                setCascadingRisks(Object.entries(result.cascading_risk_summary || {})
                    .filter(([_, count]) => count > 0)
                    .map(([level, count]) => ({ 
                        level: level.replace(/_/g, ' ').toUpperCase(), 
                        count,
                        icon: getRiskIcon(level)
                    })));
                
                const aiOrder = result.current_order || [];
                const savedIds = await loadSavedOrder();
                if (savedIds.length > 0) {
                    const idToItem = {};
                    aiOrder.forEach(item => { idToItem[item.transaction_id] = item; });
                    const hydratedOrder = savedIds
                        .map(id => idToItem[id])
                        .filter(Boolean);
                    if (hydratedOrder.length > 0) {
                        setSavedOrder(hydratedOrder);
                        setReorderList(hydratedOrder);
                        setOriginalOrder(hydratedOrder);
                        generateCashFlowChart(hydratedOrder);
                        return;
                    }
                }
                setReorderList(aiOrder);
                setOriginalOrder(aiOrder);
                generateCashFlowChart(aiOrder);
            }
        } catch (err) {
            console.error('Failed to load predictive analysis:', err);
        }
    };

    const getRiskIcon = (level) => {
        if (level.includes('STATUTORY')) return '⚖️';
        if (level.includes('OPERATIONAL')) return '⚡';
        if (level.includes('PEOPLE')) return '👥';
        if (level.includes('KEY_SUPPLY')) return '🏭';
        if (level.includes('STANDARD')) return '📄';
        if (level.includes('INFORMAL')) return '💝';
        return '⚠️';
    };

    const calculateRealTimeProjection = async (orderList) => {
        if (!orderList || orderList.length === 0) return;
        
        setIsCalculating(true);
        try {
            // Include partial payment info
            const orderWithPartials = orderList.map(item => ({
                ...item,
                paid_amount: partialPaymentMap[item.transaction_id]?.paid_amount || 0
            }));
            
            const result = await request('/calculate-projection', {
                method: 'POST',
                body: JSON.stringify({
                    order: orderWithPartials.map(item => ({
                        transaction_id: item.transaction_id,
                        amount: item.amount - (item.paid_amount || 0)
                    })),
                    cash_balance: cashBalance
                })
            });
            
            if (result && result.success) {
                setRealTimeProjection(result.projection);
            }
        } catch (err) {
            console.error('Failed to calculate projection:', err);
        } finally {
            setIsCalculating(false);
        }
    };

    const handleFileUpload = async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        
        const formData = new FormData();
        formData.append('file', file);
        
        try {
            const result = await request('/upload', {
                method: 'POST',
                body: formData
            });
            
            setParsedData(result.data);
            setEditableData(result.data);
            setShowEditModal(true);
        } catch (err) {
            alert('Error parsing file: ' + err.message);
        }
    };

    const handleConfirmUpload = async () => {
        try {
            const result = await request('/confirm-upload', {
                method: 'POST',
                body: JSON.stringify(editableData)
            });
            
            alert(`Successfully processed ${result.results.length} transactions`);
            setShowEditModal(false);
            setParsedData(null);
            loadDashboard();
            loadPredictiveAnalysis();
            loadRiskAnalysis();
            setActiveTab('results');
        } catch (err) {
            alert('Error processing: ' + err.message);
        }
    };

    const handleEditData = (index, field, value) => {
        const newData = { ...editableData };
        
        if (field.includes('.')) {
            const parts = field.split('.');
            let current = newData;
            for (let i = 0; i < parts.length - 1; i++) {
                current = current[parts[i]];
            }
            current[parts[parts.length - 1]] = value;
        } else if (newData.obligations[index]) {
            newData.obligations[index][field] = value;
        }
        
        setEditableData(newData);
    };

    const handleApplyPartialPayment = async () => {
        if (!selectedTransaction || !partialPercentage) return;
        
        const originalAmount = selectedTransaction.amount;
        const paidSoFar = partialPaymentMap[selectedTransaction.transaction_id]?.paid_amount || 0;
        const remainingAmount = originalAmount - paidSoFar;
        const partialAmount = remainingAmount * partialPercentage / 100;
        
        try {
            const result = await request('/apply-partial', {
                method: 'POST',
                body: JSON.stringify({
                    transaction_id: selectedTransaction.transaction_id,
                    percentage: partialPercentage,
                    current_paid: paidSoFar
                })
            });
            
            if (result.success) {
                // 🔥 Update cash balance instantly
                setCashBalance(prev => prev - partialAmount);
                
                // Update partial payment map
                const newPaidAmount = paidSoFar + partialAmount;
                setPartialPaymentMap(prev => ({
                    ...prev,
                    [selectedTransaction.transaction_id]: {
                        paid_amount: newPaidAmount,
                        original_amount: originalAmount,
                        percentage: ((newPaidAmount / originalAmount) * 100).toFixed(0),
                        last_payment: partialPercentage,
                        last_payment_amount: partialAmount
                    }
                }));
                
                alert(`✅ Applied ${partialPercentage}% partial payment (₹${formatCurrency(partialAmount)}). Remaining: ₹${formatCurrency(remainingAmount - partialAmount)}`);
                setShowPartialModal(false);
                
                // Refresh all data
                const currentOrder = getCurrentOrder();
                generateCashFlowChart(currentOrder);
                calculateRealTimeProjection(currentOrder);
                loadRiskAnalysis();
            } else {
                alert(result.error);
            }
        } catch (err) {
            alert('Error applying partial payment: ' + err.message);
        }
    };

    const handleSaveOrder = async () => {
        try {
            const order = reorderList.map(item => item.transaction_id);
            const result = await request('/reorder-payments', {
                method: 'POST',
                body: JSON.stringify({ order })
            });
            
            if (result.success) {
                setSavedOrder([...reorderList]);
                setOriginalOrder([...reorderList]);
                setReorderMode(false);
                alert('Payment order saved successfully!');
                calculateRealTimeProjection(reorderList);
                generateCashFlowChart(reorderList);
            } else {
                alert(result.error);
            }
        } catch (err) {
            alert('Error saving order: ' + err.message);
        }
    };

    const handleRestoreOriginal = () => {
        setShowRestoreConfirm(true);
    };

    const confirmRestore = () => {
        const original = predictiveData?.current_order || [];
        setReorderList([...original]);
        setSavedOrder([]);
        setOriginalOrder([...original]);
        calculateRealTimeProjection(original);
        generateCashFlowChart(original);
        setShowRestoreConfirm(false);
        
        request('/clear-saved-order', { method: 'POST' }).catch(console.error);
        
        alert('Order restored to original AI-optimized sequence');
    };

    const handleUpdateCashBalance = async () => {
        try {
            const amount = parseFloat(newCashBalance);
            if (isNaN(amount)) {
                alert('Please enter a valid amount');
                return;
            }
            
            const result = await request('/update-cash', {
                method: 'POST',
                body: JSON.stringify({ cash_balance: amount })
            });
            
            if (result.success) {
                setCashBalance(amount);
                setShowCashModal(false);
                setNewCashBalance('');
                const currentOrder = getCurrentOrder();
                calculateRealTimeProjection(currentOrder);
                generateCashFlowChart(currentOrder);
                loadRiskAnalysis();
                alert('Cash balance updated successfully!');
            } else {
                alert(result.error);
            }
        } catch (err) {
            alert('Error updating cash balance: ' + err.message);
        }
    };

    const handleInitializeCash = async (amount) => {
        try {
            const result = await request('/initialize-cash', {
                method: 'POST',
                body: JSON.stringify({ cash_balance: amount })
            });
            
            if (result.success) {
                setCashBalance(amount);
                const currentOrder = getCurrentOrder();
                calculateRealTimeProjection(currentOrder);
                generateCashFlowChart(currentOrder);
                loadRiskAnalysis();
                alert(`Cash balance set to ${formatCurrency(amount)}`);
            } else {
                alert(result.error);
            }
        } catch (err) {
            alert('Error initializing cash: ' + err.message);
        }
    };

    const handleDragStart = (e, index) => {
        e.dataTransfer.setData('text/plain', index);
        e.target.style.opacity = '0.5';
    };

    const handleDragEnd = (e) => {
        e.target.style.opacity = '1';
    };

    const handleDragOver = (e) => {
        e.preventDefault();
    };

    const handleDrop = (e, dropIndex) => {
        e.preventDefault();
        const dragIndex = parseInt(e.dataTransfer.getData('text/plain'));
        const newList = [...reorderList];
        const [draggedItem] = newList.splice(dragIndex, 1);
        newList.splice(dropIndex, 0, draggedItem);
        setReorderList(newList);
    };

    const handleBorrowingSelect = (option) => {
        setSelectedBorrowing(option);
        setShowBorrowingModal(true);
    };

    const getCurrentOrder = () => {
        if (reorderMode) return reorderList;
        if (savedOrder.length > 0) return savedOrder;
        return predictiveData?.current_order || [];
    };

    const isOrderChanged = () => {
        const current = getCurrentOrder();
        const aiOriginal = predictiveData?.current_order || [];
        if (current.length !== aiOriginal.length) return false;
        return JSON.stringify(current.map(i => i.transaction_id)) !== 
               JSON.stringify(aiOriginal.map(i => i.transaction_id));
    };

    const displayedPayments = getCurrentOrder();
    const [cashFlowDepletion, setCashFlowDepletion] = useState(null);

    // Calculate summary stats
    const cashFlowSummary = {
        finalCash: cashFlowData.length > 0 ? cashFlowData[cashFlowData.length - 1]?.cash || 0 : 0,
        totalPayables: displayedPayments.reduce((sum, p) => {
            const paid = partialPaymentMap[p.transaction_id]?.paid_amount || 0;
            return sum + (p.amount - paid);
        }, 0),
        totalReceivables: riskAnalysis?.receivables?.reduce((sum, r) => sum + r.amount, 0) || 0,
        depletionDate: cashFlowDepletion?.date || null,
        netPosition: (riskAnalysis?.receivables?.reduce((sum, r) => sum + r.amount, 0) || 0) - 
                     displayedPayments.reduce((sum, p) => {
                        const paid = partialPaymentMap[p.transaction_id]?.paid_amount || 0;
                        return sum + (p.amount - paid);
                     }, 0)
    };

    if (loading && !stats) {
        return (
            <div className="empty-state">
                <div className="spinner"></div>
                <div className="empty-title">Loading dashboard...</div>
            </div>
        );
    }

    if (!stats || stats.total_transactions === 0) {
        return (
            <div className="empty-state">
                <div className="empty-icon">📊</div>
                <div className="empty-title">No Data Yet</div>
                <div className="empty-sub">Upload a file or add transactions to see your financial dashboard</div>
                <div style={{ marginTop: '1rem' }}>
                    <input 
                        type="file" 
                        accept=".csv,.pdf,.png,.jpg,.jpeg"
                        onChange={handleFileUpload}
                        style={{ display: 'none' }}
                        id="file-upload"
                    />
                    <button 
                        className="btn btn-primary" 
                        onClick={() => document.getElementById('file-upload').click()}
                    >
                        📁 Upload File
                    </button>
                    <button 
                        className="btn btn-secondary" 
                        style={{ marginLeft: '1rem' }}
                        onClick={() => setActiveTab('input')}
                    >
                        + Add Manually
                    </button>
                </div>
            </div>
        );
    }

    const riskDistribution = [
        { name: 'High Risk', value: stats.high_risk_count || 0, color: '#ef4444' },
        { name: 'Medium Risk', value: stats.medium_risk_count || 0, color: '#f59e0b' },
        { name: 'Low Risk', value: stats.low_risk_count || 0, color: '#10b981' }
    ];

    const statusDistribution = [
        { name: 'Overdue', value: stats.overdue_count || 0, color: '#ef4444' },
        { name: 'Pending', value: stats.pending_count || 0, color: '#f59e0b' },
        { name: 'Paid', value: stats.paid_count || 0, color: '#10b981' }
    ];

    const typeDistribution = [
        { name: 'Payables', value: stats.payables_count || 0, color: '#3b82f6' },
        { name: 'Receivables', value: stats.receivables_count || 0, color: '#10b981' }
    ];

    return (
        <div>
            {/* Restore Confirmation Modal */}
            {showRestoreConfirm && (
                <div className="modal-overlay" onClick={() => setShowRestoreConfirm(false)}>
                    <div className="modal-content" onClick={e => e.stopPropagation()}>
                        <h3>🔄 Restore Original Order</h3>
                        <p>Are you sure you want to restore the original AI-optimized payment order?</p>
                        <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
                            This will discard your current custom order.
                        </p>
                        <div style={{ display: 'flex', gap: '1rem', marginTop: '1.5rem' }}>
                            <button className="btn btn-primary" onClick={confirmRestore}>
                                Yes, Restore
                            </button>
                            <button className="btn btn-secondary" onClick={() => setShowRestoreConfirm(false)}>
                                Cancel
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Partial Payment Modal */}
            {showPartialModal && selectedTransaction && (
                <div className="modal-overlay" onClick={() => setShowPartialModal(false)}>
                    <div className="modal-content" onClick={e => e.stopPropagation()}>
                        <h3>💳 Partial Payment</h3>
                        <p><strong>{selectedTransaction.party}</strong></p>
                        <div className="partial-payment-info">
                            <div className="info-row">
                                <span>Original Amount:</span>
                                <span className="amount">{formatCurrency(selectedTransaction.amount)}</span>
                            </div>
                            {partialPaymentMap[selectedTransaction.transaction_id] && (
                                <>
                                    <div className="info-row">
                                        <span>Already Paid:</span>
                                        <span className="paid">{formatCurrency(partialPaymentMap[selectedTransaction.transaction_id].paid_amount)}</span>
                                    </div>
                                    <div className="info-row">
                                        <span>Remaining:</span>
                                        <span className="remaining">{formatCurrency(selectedTransaction.amount - partialPaymentMap[selectedTransaction.transaction_id].paid_amount)}</span>
                                    </div>
                                </>
                            )}
                            <div className="info-row">
                                <span>Minimum Partial %:</span>
                                <span>{selectedTransaction.partial_min_pct || 50}%</span>
                            </div>
                        </div>
                        
                        <div className="form-group">
                            <label className="form-label">Payment Percentage (%)</label>
                            <input 
                                type="range"
                                min={selectedTransaction.partial_min_pct || 20}
                                max={100}
                                step={5}
                                value={partialPercentage}
                                onChange={e => setPartialPercentage(parseInt(e.target.value))}
                                className="form-input"
                            />
                            <div style={{ textAlign: 'center', marginTop: '0.5rem' }}>
                                {partialPercentage}% = {formatCurrency((selectedTransaction.amount - (partialPaymentMap[selectedTransaction.transaction_id]?.paid_amount || 0)) * partialPercentage / 100)}
                            </div>
                        </div>
                        
                        <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
                            <button className="btn btn-primary" onClick={handleApplyPartialPayment}>
                                Apply Payment
                            </button>
                            <button className="btn btn-secondary" onClick={() => setShowPartialModal(false)}>
                                Cancel
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Cash Balance Modal */}
            {showCashModal && (
                <div className="modal-overlay" onClick={() => setShowCashModal(false)}>
                    <div className="modal-content" onClick={e => e.stopPropagation()}>
                        <h3>💰 Update Cash Balance</h3>
                        <div className="form-group">
                            <label className="form-label">Current Cash Balance: {formatCurrency(cashBalance)}</label>
                            <input 
                                type="number"
                                className="form-input"
                                placeholder="Enter new cash balance"
                                value={newCashBalance}
                                onChange={e => setNewCashBalance(e.target.value)}
                            />
                        </div>
                        <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
                            <button className="btn btn-primary" onClick={handleUpdateCashBalance}>
                                Update
                            </button>
                            <button className="btn btn-secondary" onClick={() => setShowCashModal(false)}>
                                Cancel
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Borrowing Recommendations Modal */}
            {showBorrowingModal && selectedBorrowing && (
                <div className="modal-overlay" onClick={() => setShowBorrowingModal(false)}>
                    <div className="modal-content" onClick={e => e.stopPropagation()}>
                        <h3>💰 {selectedBorrowing.source}</h3>
                        <div className="borrowing-details">
                            <p><strong>Amount:</strong> {formatCurrency(selectedBorrowing.amount)}</p>
                            <p><strong>Interest Rate:</strong> {selectedBorrowing.interest_rate}%</p>
                            <p><strong>Repayment:</strong> {selectedBorrowing.repayment_days} days</p>
                            <p><strong>Feasibility:</strong> {(selectedBorrowing.feasibility * 100).toFixed(0)}%</p>
                            
                            {selectedBorrowing.pros && selectedBorrowing.pros.length > 0 && (
                                <div style={{ marginTop: '1rem' }}>
                                    <strong>✅ Pros:</strong>
                                    <ul>
                                        {selectedBorrowing.pros.map((pro, i) => <li key={i}>{pro}</li>)}
                                    </ul>
                                </div>
                            )}
                            
                            {selectedBorrowing.cons && selectedBorrowing.cons.length > 0 && (
                                <div style={{ marginTop: '1rem' }}>
                                    <strong>⚠️ Cons:</strong>
                                    <ul>
                                        {selectedBorrowing.cons.map((con, i) => <li key={i}>{con}</li>)}
                                    </ul>
                                </div>
                            )}
                            
                            <div className="info-box" style={{ marginTop: '1rem', padding: '1rem', background: 'rgba(59, 130, 246, 0.1)', borderRadius: '8px' }}>
                                <strong>💡 Recommendation:</strong> {selectedBorrowing.message}
                            </div>
                        </div>
                        <button className="btn btn-primary" style={{ marginTop: '1rem', width: '100%' }} onClick={() => setShowBorrowingModal(false)}>
                            Close
                        </button>
                    </div>
                </div>
            )}

            {/* Edit Modal */}
            {showEditModal && editableData && (
                <div className="modal-overlay" onClick={() => setShowEditModal(false)}>
                    <div className="modal-content" onClick={e => e.stopPropagation()} style={{ maxWidth: '900px', width: '90%' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem' }}>
                            <h3>📝 Edit Parsed Data</h3>
                            <button onClick={() => setShowEditModal(false)} style={{ background: 'none', border: 'none', fontSize: '1.5rem', cursor: 'pointer' }}>✕</button>
                        </div>
                        
                        <p style={{ marginBottom: '1rem', color: 'var(--text-secondary)' }}>
                            Review and edit the parsed transactions before confirming
                        </p>
                        
                        {editableData.obligations && editableData.obligations.map((ob, idx) => (
                            <div key={idx} className="card" style={{ marginBottom: '1rem' }}>
                                <div className="card-title">Transaction {idx + 1}</div>
                                <div className="form-group">
                                    <label className="form-label">Counterparty Name</label>
                                    <input 
                                        className="form-input"
                                        value={ob.counterparty?.name || ''}
                                        onChange={(e) => handleEditData(idx, 'counterparty.name', e.target.value)}
                                    />
                                </div>
                                <div className="form-group">
                                    <label className="form-label">Counterparty Type</label>
                                    <select 
                                        className="form-select"
                                        value={ob.counterparty?.type || 'unknown'}
                                        onChange={(e) => handleEditData(idx, 'counterparty.type', e.target.value)}
                                    >
                                        <option value="vendor">Vendor</option>
                                        <option value="tax_authority">Tax Authority</option>
                                        <option value="government">Government</option>
                                        <option value="bank">Bank</option>
                                        <option value="employee">Employee</option>
                                        <option value="utility">Utility</option>
                                        <option value="customer">Customer</option>
                                    </select>
                                </div>
                                <div className="two-column">
                                    <div className="form-group">
                                        <label className="form-label">Amount (₹)</label>
                                        <input 
                                            type="number"
                                            className="form-input"
                                            value={ob.amount || 0}
                                            onChange={(e) => handleEditData(idx, 'amount', parseFloat(e.target.value))}
                                        />
                                    </div>
                                    <div className="form-group">
                                        <label className="form-label">Due Date</label>
                                        <input 
                                            type="date"
                                            className="form-input"
                                            value={ob.due_date || ''}
                                            onChange={(e) => handleEditData(idx, 'due_date', e.target.value)}
                                        />
                                    </div>
                                </div>
                                <div className="two-column">
                                    <div className="form-group">
                                        <label className="form-label">
                                            <input 
                                                type="checkbox"
                                                checked={ob.partial_payment?.accepts_partial !== false}
                                                onChange={(e) => handleEditData(idx, 'partial_payment.accepts_partial', e.target.checked)}
                                            />
                                            Accepts Partial Payment
                                        </label>
                                    </div>
                                    <div className="form-group">
                                        <label className="form-label">Minimum Partial %</label>
                                        <input 
                                            type="number"
                                            className="form-input"
                                            value={ob.partial_payment?.minimum_pct || 40}
                                            onChange={(e) => handleEditData(idx, 'partial_payment.minimum_pct', parseFloat(e.target.value))}
                                        />
                                    </div>
                                </div>
                            </div>
                        ))}
                        
                        <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
                            <button className="btn btn-primary" onClick={handleConfirmUpload}>
                                ✅ Confirm & Process
                            </button>
                            <button className="btn btn-secondary" onClick={() => setShowEditModal(false)}>
                                Cancel
                            </button>
                        </div>
                    </div>
                </div>
            )}
            
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
                <h2 style={{ margin: 0 }}>📊 Financial Dashboard</h2>
                <div>
                    <button 
                        className="btn btn-secondary" 
                        onClick={() => setShowCashModal(true)}
                        style={{ marginRight: '1rem' }}
                    >
                        💰 Update Cash
                    </button>
                    <button 
                        className="btn btn-primary" 
                        onClick={() => setShowPredictive(!showPredictive)}
                        style={{ marginRight: '1rem' }}
                    >
                        {showPredictive ? 'Hide' : 'Show'} AI Analysis
                    </button>
                    <input 
                        type="file" 
                        accept=".csv,.pdf,.png,.jpg,.jpeg"
                        onChange={handleFileUpload}
                        style={{ display: 'none' }}
                        id="file-upload-dashboard"
                    />
                    <button 
                        className="btn btn-primary" 
                        onClick={() => document.getElementById('file-upload-dashboard').click()}
                    >
                        📁 Upload
                    </button>
                    <button 
                        className="btn btn-secondary" 
                        style={{ marginLeft: '1rem' }}
                        onClick={() => setActiveTab('input')}
                    >
                        + Add
                    </button>
                </div>
            </div>
            
            {/* Stats Cards */}
            <div className="stats-grid">
                <div className="stat-card">
                    <div className="stat-value">{stats.total_transactions}</div>
                    <div className="stat-label">Total Transactions</div>
                </div>
                <div className="stat-card">
                    <div className="stat-value">{formatCurrency(stats.total_amount)}</div>
                    <div className="stat-label">Total Value</div>
                </div>
                <div className="stat-card">
                    <div className="stat-value" style={{ color: 'var(--danger)' }}>
                        {formatCurrency(stats.total_penalties)}
                    </div>
                    <div className="stat-label">Total Penalties</div>
                </div>
                <div className="stat-card">
                    <div className="stat-value">{((stats.avg_risk_score || 0) * 100).toFixed(0)}%</div>
                    <div className="stat-label">Avg Risk Score</div>
                </div>
                <div className="stat-card">
                    <div className="stat-value">{stats.accepts_partial_count || 0}</div>
                    <div className="stat-label">Accept Partial</div>
                </div>
                <div className="stat-card">
                    <div className="stat-value">{stats.overdue_count || 0}</div>
                    <div className="stat-label">Overdue</div>
                </div>
            </div>
            
            {/* Cash Balance Display */}
            <div className={`cash-card ${cashBalance >= 0 ? 'positive' : 'negative'}`} style={{ marginBottom: '1.5rem', background: 'linear-gradient(135deg, var(--bg-secondary), var(--bg-primary))', borderRadius: '12px', padding: '1rem', border: `1px solid ${cashBalance >= 0 ? 'var(--success)' : 'var(--danger)'}` }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
                    <div>
                        <div className="card-title" style={{ marginBottom: '0.5rem' }}>💰 Current Cash Position</div>
                        <div style={{ fontSize: '2rem', fontWeight: 'bold', color: cashBalance >= 0 ? 'var(--success)' : 'var(--danger)' }}>
                            {formatCurrency(cashBalance)}
                        </div>
                        <div className="text-secondary">Available for payments</div>
                    </div>
                    {cashBalance <= 0 && (
                        <div>
                            <button 
                                className="btn-primary-small"
                                onClick={() => handleInitializeCash(100000)}
                                style={{ marginRight: '0.5rem' }}
                            >
                                Set ₹1L
                            </button>
                            <button 
                                className="btn-primary-small"
                                onClick={() => handleInitializeCash(50000)}
                            >
                                Set ₹50K
                            </button>
                        </div>
                    )}
                </div>
            </div>

            {/* Risk Score Card */}
            {riskAnalysis && (
                <div className="risk-score-card" style={{ marginBottom: '1.5rem', padding: '1rem', borderRadius: '12px', background: `linear-gradient(135deg, ${getRiskColor(riskAnalysis.risk_score)}, rgba(0,0,0,0.1))` }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
                        <div>
                            <div className="card-title" style={{ marginBottom: '0.25rem' }}>📊 Overall Risk Score</div>
                            <div style={{ fontSize: '2rem', fontWeight: 'bold' }}>{(riskAnalysis.risk_score * 100).toFixed(0)}%</div>
                            <div className={`risk-level ${riskAnalysis.risk_level.toLowerCase()}`} style={{ fontWeight: 'bold', marginTop: '0.25rem' }}>
                                {riskAnalysis.risk_level} RISK
                            </div>
                        </div>
                        <div style={{ flex: 1, maxWidth: '300px' }}>
                            <div style={{ marginBottom: '0.5rem' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem' }}>
                                    <span>Financial Risk</span>
                                    <span>{(riskAnalysis.financial_ratio * 100).toFixed(0)}%</span>
                                </div>
                                <div style={{ background: 'var(--bg-tertiary)', borderRadius: '4px', overflow: 'hidden' }}>
                                    <div style={{ width: `${riskAnalysis.financial_ratio * 100}%`, height: '4px', background: '#ef4444' }}></div>
                                </div>
                            </div>
                            <div style={{ marginBottom: '0.5rem' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem' }}>
                                    <span>Overdue Risk</span>
                                    <span>{(riskAnalysis.overdue_ratio * 100).toFixed(0)}%</span>
                                </div>
                                <div style={{ background: 'var(--bg-tertiary)', borderRadius: '4px', overflow: 'hidden' }}>
                                    <div style={{ width: `${riskAnalysis.overdue_ratio * 100}%`, height: '4px', background: '#f59e0b' }}></div>
                                </div>
                            </div>
                            <div>
                                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem' }}>
                                    <span>Counterparty Risk</span>
                                    <span>{(riskAnalysis.counterparty_risk * 100).toFixed(0)}%</span>
                                </div>
                                <div style={{ background: 'var(--bg-tertiary)', borderRadius: '4px', overflow: 'hidden' }}>
                                    <div style={{ width: `${riskAnalysis.counterparty_risk * 100}%`, height: '4px', background: '#8b5cf6' }}></div>
                                </div>
                            </div>
                        </div>
                        <div>
                            <div className="text-secondary" style={{ fontSize: '0.7rem' }}>Risk Summary</div>
                            <div style={{ maxWidth: '250px', fontSize: '0.8rem' }}>{riskAnalysis.risk_summary}</div>
                        </div>
                    </div>
                </div>
            )}

            {/* Enhanced Cash Flow Graph with Step Line */}
            {cashFlowData.length > 0 && (
                <div className="card cashflow-card" style={{ marginBottom: '1.5rem' }}>
                    <div className="card-title" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span>📈 Cash Flow Projection</span>
                        {reorderMode && (
                            <span className="live-badge">🟢 Live - Updates on drag</span>
                        )}
                    </div>
                    
                    <ResponsiveContainer width="100%" height={400}>
                        <LineChart data={cashFlowData} margin={{ top: 20, right: 30, left: 20, bottom: 10 }}>
                            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                            <XAxis 
                                dataKey="date" 
                                stroke="var(--text-tertiary)"
                                label={{ value: 'Transaction Date', position: 'insideBottom', offset: -5 }}
                                angle={-45}
                                textAnchor="end"
                                height={60}
                            />
                            <YAxis 
                                stroke="var(--text-tertiary)" 
                                tickFormatter={(value) => `₹${(value / 1000).toFixed(0)}K`}
                                label={{ value: 'Cash Balance (₹)', angle: -90, position: 'insideLeft' }}
                            />
                            <Tooltip 
                                formatter={(value, name, props) => {
                                    const data = props.payload;
                                    return [
                                        <>
                                            {formatCurrency(value)}
                                            {data.isPartial && <span style={{ color: 'var(--warning)' }}> (Partial payment applied)</span>}
                                            {data.paidAmount > 0 && <span style={{ color: 'var(--success)' }}> - ₹{formatCurrency(data.paidAmount)} paid</span>}
                                        </>,
                                        'Cash Balance'
                                    ];
                                }}
                                labelFormatter={(label, payload) => {
                                    const data = payload[0]?.payload;
                                    return (
                                        <div>
                                            <div>{label}</div>
                                            {data && data.type === 'payable' && (
                                                <div style={{ color: 'var(--danger)', fontSize: '0.7rem' }}>
                                                    💸 Payment to {data.party}: -{formatCurrency(data.amount)}
                                                </div>
                                            )}
                                            {data && data.type === 'receivable' && (
                                                <div style={{ color: 'var(--success)', fontSize: '0.7rem' }}>
                                                    💰 Receipt from {data.party}: +{formatCurrency(data.amount)}
                                                </div>
                                            )}
                                        </div>
                                    );
                                }}
                            />
                            <Legend />
                            
                            {/* 🔥 STEP LINE - sharp drops exactly at payment dates */}
                            <Line 
                                type="stepAfter" 
                                dataKey="cash" 
                                stroke="var(--primary)" 
                                strokeWidth={3}
                                dot={{ r: 4, fill: 'var(--primary)', strokeWidth: 2 }}
                                name="Cash Balance"
                                isAnimationActive={false}
                            />
                            
                            {/* 🔴 ZERO CASH LINE */}
                            <ReferenceLine 
                                y={0} 
                                stroke="red" 
                                strokeDasharray="5 5" 
                                strokeWidth={2}
                                label={{ value: "Zero Cash Line", position: "right", fill: "red", fontSize: 10 }}
                            />
                            
                            {/* 🟠 DEPLETION MARKER - vertical line at cash negative point */}
                            {cashFlowDepletion && (
                                <ReferenceLine 
                                    x={cashFlowDepletion.date} 
                                    stroke="orange" 
                                    strokeDasharray="5 5" 
                                    strokeWidth={2}
                                    label={{ value: "Cash Depleted", position: "top", fill: "orange", fontSize: 10 }}
                                />
                            )}
                            
                            {/* 🔴 RED DOWNWARD TRIANGLES for payables */}
                            <Scatter
                                data={cashFlowData.filter(d => d.type === 'payable')}
                                dataKey="cash"
                                shape={(props) => {
                                    const { cx, cy, payload } = props;
                                    return (
                                        <g>
                                            <polygon
                                                points={`${cx},${cy - 10} ${cx - 6},${cy + 4} ${cx + 6},${cy + 4}`}
                                                fill="#ef4444"
                                                stroke="none"
                                            />
                                            <title>{`Payment to ${payload.party}: -${formatCurrency(payload.amount)}${payload.isPartial ? ' (Partial)' : ''}`}</title>
                                        </g>
                                    );
                                }}
                                name="Payments"
                            />
                            
                            {/* 🟢 GREEN UPWARD TRIANGLES for receivables */}
                            <Scatter
                                data={cashFlowData.filter(d => d.type === 'receivable')}
                                dataKey="cash"
                                shape={(props) => {
                                    const { cx, cy, payload } = props;
                                    return (
                                        <g>
                                            <polygon
                                                points={`${cx - 6},${cy - 4} ${cx + 6},${cy - 4} ${cx},${cy + 10}`}
                                                fill="#10b981"
                                                stroke="none"
                                            />
                                            <title>{`Receipt from ${payload.party}: +${formatCurrency(payload.amount)}`}</title>
                                        </g>
                                    );
                                }}
                                name="Receipts"
                            />
                        </LineChart>
                    </ResponsiveContainer>
                    
                    {/* Cash Flow Summary Strip */}
                    <div className="cashflow-summary">
                        <div className="summary-item">
                            <span className="summary-label">Final Cash</span>
                            <span className={`summary-value ${cashFlowSummary.finalCash >= 0 ? 'positive' : 'negative'}`}>
                                {formatCurrency(cashFlowSummary.finalCash)}
                            </span>
                        </div>
                        <div className="summary-divider"></div>
                        <div className="summary-item">
                            <span className="summary-label">Total Payables</span>
                            <span className="summary-value negative">{formatCurrency(cashFlowSummary.totalPayables)}</span>
                        </div>
                        <div className="summary-divider"></div>
                        <div className="summary-item">
                            <span className="summary-label">Total Receivables</span>
                            <span className="summary-value positive">{formatCurrency(cashFlowSummary.totalReceivables)}</span>
                        </div>
                        <div className="summary-divider"></div>
                        <div className="summary-item">
                            <span className="summary-label">Net Position</span>
                            <span className={`summary-value ${cashFlowSummary.netPosition >= 0 ? 'positive' : 'negative'}`}>
                                {formatCurrency(cashFlowSummary.netPosition)}
                            </span>
                        </div>
                        {cashFlowSummary.depletionDate && (
                            <>
                                <div className="summary-divider"></div>
                                <div className="summary-item">
                                    <span className="summary-label">Cash Depletion</span>
                                    <span className="summary-value warning">{cashFlowSummary.depletionDate}</span>
                                </div>
                            </>
                        )}
                    </div>
                    
                    {/* Warning message if depletion is near */}
                    {cashFlowDepletion && cashFlowDepletion.cash < 0 && (
                        <div style={{ marginTop: '0.75rem', padding: '0.5rem', background: 'rgba(245, 158, 11, 0.1)', borderRadius: '6px', fontSize: '0.75rem', textAlign: 'center' }}>
                            ⚠️ Cash becomes negative after <strong>{cashFlowDepletion.date}</strong>. Consider partial payments or additional funding.
                        </div>
                    )}
                </div>
            )}

            {/* Predictive Analysis Section */}
            {showPredictive && predictiveData && predictiveData.custom_scenario && (
                <div>
                    {/* Real-time Projection Display */}
                    {realTimeProjection && (
                        <div className="card" style={{ 
                            marginBottom: '1.5rem', 
                            background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.15), rgba(59, 130, 246, 0.05))', 
                            borderLeft: '4px solid var(--primary)',
                            animation: 'fadeIn 0.3s ease'
                        }}>
                            <div className="card-title" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                    <span style={{ 
                                        display: 'inline-block', 
                                        width: '10px', 
                                        height: '10px', 
                                        background: reorderMode ? '#10b981' : 'var(--text-secondary)', 
                                        borderRadius: '50%',
                                        animation: reorderMode ? 'pulse 1.5s infinite' : 'none'
                                    }}></span>
                                    <span>{ reorderMode ? 'Live Projection' : 'Projection' }</span>
                                </div>
                                {isCalculating ? (
                                    <span style={{ fontSize: '0.7rem', color: 'var(--warning)' }}>⟳ Calculating...</span>
                                ) : (
                                    <span style={{ fontSize: '0.7rem', color: 'var(--success)' }}>✓ Real-time</span>
                                )}
                            </div>
                            
                            {cashBalance <= 0 && (
                                <div style={{ 
                                    marginBottom: '1rem', 
                                    padding: '0.75rem', 
                                    background: 'rgba(239, 68, 68, 0.2)', 
                                    borderRadius: '8px',
                                    borderLeft: '3px solid var(--danger)'
                                }}>
                                    <strong>⚠️ Insufficient Cash!</strong>
                                    <div style={{ fontSize: '0.8rem', marginTop: '0.25rem' }}>
                                        Current cash: {formatCurrency(cashBalance)}. You need {formatCurrency(Math.abs(realTimeProjection.shortfall || 0))} more to cover all payments.
                                    </div>
                                </div>
                            )}
                            
                            <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)', marginBottom: '1rem' }}>
                                <div className="stat-card" style={{ padding: '0.75rem' }}>
                                    <div className="stat-value" style={{ fontSize: '1.2rem', color: realTimeProjection.final_cash >= 0 ? 'var(--success)' : 'var(--danger)' }}>
                                        {formatCurrency(realTimeProjection.final_cash)}
                                    </div>
                                    <div className="stat-label">Final Cash</div>
                                </div>
                                <div className="stat-card" style={{ padding: '0.75rem' }}>
                                    <div className="stat-value" style={{ fontSize: '1.2rem', color: 'var(--warning)' }}>
                                        {formatCurrency(realTimeProjection.total_penalties)}
                                    </div>
                                    <div className="stat-label">Total Penalties</div>
                                </div>
                                <div className="stat-card" style={{ padding: '0.75rem' }}>
                                    <div className="stat-value" style={{ fontSize: '1.2rem' }}>
                                        {realTimeProjection.obligations_fulfilled?.toFixed(1)}/{realTimeProjection.total_obligations}
                                    </div>
                                    <div className="stat-label">Fulfilled</div>
                                </div>
                                <div className="stat-card" style={{ padding: '0.75rem' }}>
                                    <div className="stat-value" style={{ fontSize: '1.2rem' }}>
                                        {(realTimeProjection.efficiency * 100).toFixed(0)}%
                                    </div>
                                    <div className="stat-label">Efficiency</div>
                                </div>
                            </div>
                            
                            <div style={{ marginBottom: '1rem' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', marginBottom: '0.25rem' }}>
                                    <span>Payment Progress</span>
                                    <span>{realTimeProjection.obligations_fulfilled?.toFixed(1)} of {realTimeProjection.total_obligations} obligations</span>
                                </div>
                                <div style={{ background: 'var(--bg-tertiary)', borderRadius: '4px', overflow: 'hidden' }}>
                                    <div style={{ 
                                        width: `${realTimeProjection.efficiency * 100}%`, 
                                        background: 'linear-gradient(90deg, var(--primary), var(--success))', 
                                        padding: '0.25rem', 
                                        textAlign: 'center', 
                                        color: 'white',
                                        fontSize: '0.7rem',
                                        transition: 'width 0.3s ease'
                                    }}>
                                        {(realTimeProjection.efficiency * 100).toFixed(0)}%
                                    </div>
                                </div>
                            </div>
                            
                            {realTimeProjection.partial_payments_used > 0 && (
                                <div style={{ 
                                    marginBottom: '0.75rem', 
                                    padding: '0.5rem', 
                                    background: 'rgba(16, 185, 129, 0.1)', 
                                    borderRadius: '6px', 
                                    fontSize: '0.75rem' 
                                }}>
                                    💳 <strong>Partial payments used:</strong> {realTimeProjection.partial_payments_used} 
                                    (Saved {formatCurrency(realTimeProjection.partial_payments_saved)})
                                </div>
                            )}
                            
                            {realTimeProjection.risk_exposure > 0 && (
                                <div style={{ 
                                    padding: '0.5rem', 
                                    background: 'rgba(239, 68, 68, 0.1)', 
                                    borderRadius: '6px', 
                                    fontSize: '0.75rem' 
                                }}>
                                    ⚠️ <strong>Unpaid risk exposure:</strong> {formatCurrency(realTimeProjection.risk_exposure)}
                                    {realTimeProjection.shortfall > 0 && (
                                        <span> (Shortfall: {formatCurrency(realTimeProjection.shortfall)})</span>
                                    )}
                                </div>
                            )}
                            
                            {realTimeProjection.payment_plan && (
                                <details style={{ marginTop: '1rem' }}>
                                    <summary style={{ cursor: 'pointer', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                                        📋 View payment details
                                    </summary>
                                    <div style={{ marginTop: '0.5rem', maxHeight: '300px', overflow: 'auto' }}>
                                        {realTimeProjection.payment_plan.map((payment, idx) => (
                                            <div key={idx} style={{ 
                                                padding: '0.5rem', 
                                                marginBottom: '0.25rem', 
                                                background: 'var(--bg-tertiary)', 
                                                borderRadius: '4px',
                                                fontSize: '0.7rem',
                                                borderLeft: `3px solid ${
                                                    payment.payment_status === 'paid_full' ? 'var(--success)' :
                                                    payment.payment_status === 'paid_partial' ? 'var(--warning)' :
                                                    'var(--danger)'
                                                }`
                                            }}>
                                                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                                    <strong>{payment.rank}. {payment.party}</strong>
                                                    <span>{formatCurrency(payment.amount)}</span>
                                                </div>
                                                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.25rem' }}>
                                                    <span>
                                                        {payment.payment_status === 'paid_full' && '✅ Fully paid'}
                                                        {payment.payment_status === 'paid_partial' && `💳 Partially paid: ${formatCurrency(payment.paid_amount)}`}
                                                        {payment.payment_status === 'unpaid_min_required' && `⚠️ Needs min ${payment.min_partial_pct}% (${formatCurrency(payment.min_partial_amount)})`}
                                                        {payment.payment_status === 'unpaid_no_partial' && '❌ No partial payment option'}
                                                        {payment.payment_status === 'unpaid_insufficient' && '⚠️ Insufficient funds for min partial'}
                                                        {payment.payment_status === 'unpaid' && '❌ Unpaid'}
                                                    </span>
                                                    {payment.accepts_partial && (
                                                        <span style={{ color: 'var(--success)' }}>Partial OK</span>
                                                    )}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </details>
                            )}
                        </div>
                    )}

                    {/* Cascading Risk Summary */}
                    {cascadingRisks.length > 0 && (
                        <div className="card" style={{ marginBottom: '1.5rem', borderLeft: '4px solid var(--danger)' }}>
                            <div className="card-title">🚨 CASCADING RISK ALERT</div>
                            <div className="risk-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
                                {cascadingRisks.map((risk, idx) => (
                                    <div key={idx} style={{ padding: '0.75rem', background: 'rgba(239, 68, 68, 0.1)', borderRadius: '8px' }}>
                                        <strong>{risk.icon} {risk.level}</strong>
                                        <div>{risk.count} obligation(s)</div>
                                    </div>
                                ))}
                            </div>
                            {predictiveData.regulatory_warning?.has_critical_obligations && (
                                <div style={{ marginTop: '1rem', padding: '0.75rem', background: 'rgba(239, 68, 68, 0.2)', borderRadius: '8px' }}>
                                    ⚠️ {predictiveData.regulatory_warning.message}
                                </div>
                            )}
                        </div>
                    )}

                    {/* Payment Order with Drag & Drop */}
                    <div className="card" style={{ marginBottom: '1.5rem' }}>
                        <div className="card-title">
                            📋 Payment Priority Order
                            {!reorderMode && (
                                <button 
                                    className="btn btn-secondary" 
                                    style={{ marginLeft: '1rem', fontSize: '0.7rem' }}
                                    onClick={() => {
                                        setReorderMode(true);
                                        setReorderList(getCurrentOrder());
                                    }}
                                >
                                    🔧 Reorder
                                </button>
                            )}
                            {reorderMode && (
                                <span style={{ float: 'right', display: 'flex', gap: '0.5rem' }}>
                                    {isOrderChanged() && (
                                        <button 
                                            className="btn-warning-small" 
                                            style={{ fontSize: '0.7rem', background: 'var(--warning)', color: 'white', border: 'none', padding: '0.25rem 0.75rem', borderRadius: '4px', cursor: 'pointer' }}
                                            onClick={handleRestoreOriginal}
                                        >
                                            🔄 Restore Original
                                        </button>
                                    )}
                                    <button className="btn btn-primary" style={{ fontSize: '0.7rem' }} onClick={handleSaveOrder}>
                                        💾 Save Order
                                    </button>
                                    <button className="btn btn-secondary" style={{ fontSize: '0.7rem' }} onClick={() => {
                                        setReorderMode(false);
                                        setReorderList(getCurrentOrder());
                                    }}>
                                        ✕ Cancel
                                    </button>
                                </span>
                            )}
                        </div>
                        {reorderMode && (
                            <div style={{ marginBottom: '1rem', padding: '0.5rem', background: 'rgba(59, 130, 246, 0.1)', borderRadius: '8px', fontSize: '0.8rem' }}>
                                💡 Drag and drop to reorder payment priority. Live projections and cash flow chart update in real-time!
                            </div>
                        )}
                        <div className="payment-order-list">
                            {displayedPayments.map((item, idx) => {
                                const partialInfo = partialPaymentMap[item.transaction_id];
                                const paidAmount = partialInfo?.paid_amount || 0;
                                const remainingAmount = item.amount - paidAmount;
                                const isPartiallyPaid = paidAmount > 0;
                                
                                return (
                                    <div 
                                        key={item.transaction_id}
                                        draggable={reorderMode}
                                        onDragStart={(e) => handleDragStart(e, idx)}
                                        onDragEnd={handleDragEnd}
                                        onDragOver={handleDragOver}
                                        onDrop={(e) => handleDrop(e, idx)}
                                        style={{
                                            padding: '1rem',
                                            marginBottom: '0.5rem',
                                            border: `1px solid ${reorderMode ? 'var(--primary)' : 'var(--border)'}`,
                                            borderRadius: '8px',
                                            cursor: reorderMode ? 'move' : 'default',
                                            background: item.risk_level?.includes('CRITICAL') ? 'rgba(239, 68, 68, 0.1)' : 'transparent',
                                            transition: 'all 0.2s ease',
                                            opacity: remainingAmount <= 0 ? 0.6 : 1
                                        }}
                                    >
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                                            <div style={{ flex: 1 }}>
                                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem', flexWrap: 'wrap' }}>
                                                    <span style={{ background: reorderMode ? 'var(--primary)' : 'var(--bg-tertiary)', color: 'white', padding: '0.25rem 0.5rem', borderRadius: '4px', fontSize: '0.7rem' }}>
                                                        #{idx + 1}
                                                    </span>
                                                    <strong>{item.party}</strong>
                                                    {item.accepts_partial && (
                                                        <span style={{ background: 'var(--success)', color: 'white', padding: '0.2rem 0.4rem', borderRadius: '4px', fontSize: '0.6rem' }}>Partial OK</span>
                                                    )}
                                                    {item.regulatory_risk > 0.8 && (
                                                        <span style={{ background: 'var(--danger)', color: 'white', padding: '0.2rem 0.4rem', borderRadius: '4px', fontSize: '0.6rem' }}>🚨 Critical</span>
                                                    )}
                                                    {isPartiallyPaid && (
                                                        <span style={{ background: 'var(--warning)', color: 'white', padding: '0.2rem 0.4rem', borderRadius: '4px', fontSize: '0.6rem' }}>
                                                            💳 {formatCurrency(paidAmount)} paid
                                                        </span>
                                                    )}
                                                    {remainingAmount <= 0 && (
                                                        <span style={{ background: 'var(--success)', color: 'white', padding: '0.2rem 0.4rem', borderRadius: '4px', fontSize: '0.6rem' }}>
                                                            ✅ Fully paid
                                                        </span>
                                                    )}
                                                </div>
                                                <div className="text-secondary" style={{ fontSize: '0.8rem' }}>
                                                    {formatCurrency(remainingAmount)} / {formatCurrency(item.amount)} | {item.type} | Level: {item.level_name}
                                                    {isPartiallyPaid && ` | ${partialInfo.percentage}% paid`}
                                                </div>
                                                {item.consequences && (
                                                    <div className="text-secondary" style={{ fontSize: '0.7rem', marginTop: '0.25rem' }}>
                                                        ⚠️ {item.consequences.substring(0, 80)}...
                                                    </div>
                                                )}
                                            </div>
                                            <div style={{ textAlign: 'right' }}>
                                                <div style={{ color: getRiskColor(item.risk_score) }}>
                                                    Risk: {(item.risk_score * 100).toFixed(0)}%
                                                </div>
                                                {item.days_late > 0 && (
                                                    <div style={{ color: 'var(--danger)', fontSize: '0.7rem' }}>
                                                        {item.days_late} days late
                                                    </div>
                                                )}
                                                {item.accepts_partial && !reorderMode && remainingAmount > 0 && (
                                                    <button 
                                                        className="btn btn-secondary" 
                                                        style={{ marginTop: '0.5rem', fontSize: '0.7rem', padding: '0.25rem 0.5rem' }}
                                                        onClick={() => {
                                                            setSelectedTransaction(item);
                                                            setPartialPercentage(item.suggested_pct || 50);
                                                            setShowPartialModal(true);
                                                        }}
                                                    >
                                                        💳 Partial
                                                    </button>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>

                    {/* Projected Outcome */}
                    <div className="card" style={{ marginBottom: '1.5rem' }}>
                        <div className="card-title">📊 Projected Outcome</div>
                        <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
                            <div className="stat-card">
                                <div className="stat-value" style={{ color: predictiveData.custom_scenario.final_cash >= 0 ? 'var(--success)' : 'var(--danger)' }}>
                                    {formatCurrency(predictiveData.custom_scenario.final_cash)}
                                </div>
                                <div className="stat-label">Final Cash</div>
                            </div>
                            <div className="stat-card">
                                <div className="stat-value">{formatCurrency(predictiveData.custom_scenario.total_penalties)}</div>
                                <div className="stat-label">Total Penalties</div>
                            </div>
                            <div className="stat-card">
                                <div className="stat-value">{(predictiveData.custom_scenario.efficiency_score * 100).toFixed(0)}%</div>
                                <div className="stat-label">Efficiency</div>
                            </div>
                        </div>
                        <div style={{ marginTop: '1rem', background: 'var(--bg-secondary)', borderRadius: '4px', overflow: 'hidden' }}>
                            <div style={{ width: `${predictiveData.custom_scenario.efficiency_score * 100}%`, background: 'var(--success)', padding: '0.25rem', textAlign: 'center', color: 'white' }}>
                                {predictiveData.custom_scenario.obligations_fulfilled?.toFixed(1)} / {predictiveData.summary?.total_obligations} obligations
                            </div>
                        </div>
                        {predictiveData.custom_scenario.partial_payments_used > 0 && (
                            <div style={{ marginTop: '1rem', padding: '0.75rem', background: 'rgba(16, 185, 129, 0.1)', borderRadius: '8px' }}>
                                💳 Partial payments used: {predictiveData.custom_scenario.partial_payments_used} (Saved {formatCurrency(predictiveData.custom_scenario.partial_payments_saved)})
                            </div>
                        )}
                    </div>

                    {/* Borrowing Recommendations */}
                    {borrowingRecommendations.length > 0 && (
                        <div className="card" style={{ marginBottom: '1.5rem' }}>
                            <div className="card-title">💰 Borrowing Recommendations</div>
                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
                                {borrowingRecommendations.slice(0, 3).map((rec, idx) => (
                                    <div key={idx} style={{ padding: '1rem', border: '1px solid var(--border)', borderRadius: '8px', cursor: 'pointer' }} onClick={() => handleBorrowingSelect(rec)}>
                                        <h4 style={{ margin: '0 0 0.5rem 0' }}>{rec.source}</h4>
                                        <div style={{ fontSize: '1.2rem', fontWeight: 'bold' }}>{formatCurrency(rec.amount)}</div>
                                        <div style={{ fontSize: '0.8rem', marginTop: '0.5rem' }}>
                                            <div>Interest: {rec.interest_rate}%</div>
                                            <div>Repayment: {rec.repayment_days} days</div>
                                            <div>Feasibility: {(rec.feasibility * 100).toFixed(0)}%</div>
                                        </div>
                                        <button className="btn btn-secondary" style={{ marginTop: '0.5rem', width: '100%', fontSize: '0.7rem' }}>
                                            View Details
                                        </button>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            )}
            
            {/* Charts Section */}
            <div className="two-column">
                <div className="card">
                    <div className="card-title">RISK DISTRIBUTION</div>
                    <ResponsiveContainer width="100%" height={250}>
                        <PieChart>
                            <Pie
                                data={riskDistribution}
                                cx="50%"
                                cy="50%"
                                innerRadius={60}
                                outerRadius={80}
                                paddingAngle={5}
                                dataKey="value"
                                label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
                            >
                                {riskDistribution.map((entry, index) => (
                                    <Cell key={`cell-${index}`} fill={entry.color} />
                                ))}
                            </Pie>
                            <Tooltip />
                            <Legend />
                        </PieChart>
                    </ResponsiveContainer>
                </div>
                
                <div className="card">
                    <div className="card-title">STATUS DISTRIBUTION</div>
                    <ResponsiveContainer width="100%" height={250}>
                        <PieChart>
                            <Pie
                                data={statusDistribution}
                                cx="50%"
                                cy="50%"
                                innerRadius={60}
                                outerRadius={80}
                                paddingAngle={5}
                                dataKey="value"
                                label={({ name, percent }) => `${name} (${(percent * 100).toFixed(0)}%)`}
                            >
                                {statusDistribution.map((entry, index) => (
                                    <Cell key={`cell-${index}`} fill={entry.color} />
                                ))}
                            </Pie>
                            <Tooltip />
                            <Legend />
                        </PieChart>
                    </ResponsiveContainer>
                </div>
            </div>
            
            <div className="two-column">
                <div className="card">
                    <div className="card-title">TRANSACTION TYPE</div>
                    <ResponsiveContainer width="100%" height={250}>
                        <BarChart data={typeDistribution}>
                            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                            <XAxis dataKey="name" stroke="var(--text-tertiary)" />
                            <YAxis stroke="var(--text-tertiary)" />
                            <Tooltip />
                            <Bar dataKey="value" fill="#3b82f6" />
                        </BarChart>
                    </ResponsiveContainer>
                </div>
                
                <div className="card">
                    <div className="card-title">FINANCIAL OVERVIEW</div>
                    <div style={{ padding: '1rem' }}>
                        <div style={{ marginBottom: '1rem' }}>
                            <div style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)' }}>Total Payables</div>
                            <div style={{ fontSize: '1.2rem', fontWeight: 'bold', color: 'var(--danger)' }}>
                                {formatCurrency(stats.total_payables_amount)}
                            </div>
                        </div>
                        <div style={{ marginBottom: '1rem' }}>
                            <div style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)' }}>Total Receivables</div>
                            <div style={{ fontSize: '1.2rem', fontWeight: 'bold', color: 'var(--success)' }}>
                                {formatCurrency(stats.total_receivables_amount)}
                            </div>
                        </div>
                        <div>
                            <div style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)' }}>Net Position</div>
                            <div style={{ fontSize: '1.2rem', fontWeight: 'bold', color: (stats.total_receivables_amount - stats.total_payables_amount) >= 0 ? 'var(--success)' : 'var(--danger)' }}>
                                {formatCurrency(stats.total_receivables_amount - stats.total_payables_amount)}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            {/* Recent Transactions */}
            <div className="card" style={{ marginTop: '1.5rem' }}>
                <div className="card-title">RECENT TRANSACTIONS</div>
                {recentTransactions.length > 0 ? (
                    <div style={{ overflowX: 'auto' }}>
                        <table className="data-table" style={{ width: '100%', minWidth: '600px' }}>
                            <thead>
                                <tr>
                                    <th>Counterparty</th>
                                    <th>Amount</th>
                                    <th>Type</th>
                                    <th>Status</th>
                                    <th>Risk</th>
                                    <th>Days Late</th>
                                    <th>Partial</th>
                                </tr>
                            </thead>
                            <tbody>
                                {recentTransactions.map(t => {
                                    const partialInfo = partialPaymentMap[t.id];
                                    const paidAmount = partialInfo?.paid_amount || 0;
                                    const remainingAmount = t.amount - paidAmount;
                                    
                                    return (
                                        <tr key={t.id}>
                                            <td>{t.counterparty_name}</td>
                                            <td className="mono">
                                                {remainingAmount < t.amount ? (
                                                    <>
                                                        <span style={{ textDecoration: 'line-through', color: 'var(--text-tertiary)' }}>{formatCurrency(t.amount)}</span>
                                                        <br/>
                                                        <span style={{ color: 'var(--warning)' }}>{formatCurrency(remainingAmount)}</span>
                                                    </>
                                                ) : (
                                                    formatCurrency(t.amount)
                                                )}
                                            </td>
                                            <td><span className="badge badge-medium">{t.transaction_type}</span></td>
                                            <td>
                                                <span className={`badge ${t.status === 'overdue' ? 'badge-critical' : t.status === 'paid' ? 'badge-low' : 'badge-medium'}`}>
                                                    {t.status}
                                                </span>
                                            </td>
                                            <td>
                                                <span className={`badge ${t.priority === 'High' ? 'badge-high' : t.priority === 'Medium' ? 'badge-medium' : 'badge-low'}`}>
                                                    {t.priority}
                                                </span>
                                            </td>
                                            <td style={{ color: t.days_late > 0 ? 'var(--danger)' : 'var(--success)' }}>
                                                {t.days_late}
                                            </td>
                                            <td>
                                                {partialInfo ? (
                                                    <span style={{ color: 'var(--warning)' }}>
                                                        💳 {partialInfo.percentage}% paid
                                                    </span>
                                                ) : (
                                                    t.accepts_partial ? '✅' : '❌'
                                                )}
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                ) : (
                    <div className="empty-state" style={{ padding: '2rem' }}>
                        <div className="empty-icon">📭</div>
                        <div className="empty-sub">No transactions yet</div>
                    </div>
                )}
            </div>
            
            {/* Quick Actions */}
            <div className="two-column" style={{ marginTop: '1.5rem' }}>
                <div className="card">
                    <div className="card-title">🚨 CRITICAL ACTIONS</div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                        <div style={{ background: 'rgba(239, 68, 68, 0.1)', padding: '0.75rem', borderRadius: '8px' }}>
                            <div style={{ fontWeight: 600, color: 'var(--danger)' }}>High Risk Items</div>
                            <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
                                {stats.high_risk_count} obligations need immediate attention
                            </div>
                            <button className="btn btn-primary" style={{ marginTop: '0.5rem', fontSize: '0.7rem', padding: '0.25rem 0.5rem' }} onClick={() => setActiveTab('results')}>
                                Review Now
                            </button>
                        </div>
                        <div style={{ background: 'rgba(245, 158, 11, 0.1)', padding: '0.75rem', borderRadius: '8px' }}>
                            <div style={{ fontWeight: 600, color: 'var(--warning)' }}>Overdue Payments</div>
                            <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
                                {stats.overdue_count} payments are overdue
                            </div>
                            <button className="btn btn-secondary" style={{ marginTop: '0.5rem', fontSize: '0.7rem', padding: '0.25rem 0.5rem' }} onClick={() => setActiveTab('communicate')}>
                                Send Reminders
                            </button>
                        </div>
                    </div>
                </div>
                
                <div className="card">
                    <div className="card-title">💡 AI INSIGHTS</div>
                    <div style={{ fontSize: '0.8rem', lineHeight: 1.6 }}>
                        <div>• {stats.high_risk_count} high-risk transactions need attention</div>
                        <div>• {stats.accepts_partial_count} obligations accept partial payments</div>
                        <div>• Total penalties: {formatCurrency(stats.total_penalties)}</div>
                        <div>• Average risk score: {(stats.avg_risk_score * 100).toFixed(0)}%</div>
                        <div>• {stats.overdue_count} overdue payments - consider negotiation</div>
                        {cashFlowDepletion && (
                            <div>• Cash becomes negative after {cashFlowDepletion.date} - consider partial payments</div>
                        )}
                        {predictiveData?.custom_scenario?.shortfall > 0 && (
                            <div>• Cash shortfall: {formatCurrency(predictiveData.custom_scenario.shortfall)} - consider borrowing</div>
                        )}
                    </div>
                    <button className="btn btn-primary" style={{ marginTop: '1rem', width: '100%' }} onClick={() => setActiveTab('chat')}>
                        💬 Ask AI for Strategy
                    </button>
                </div>
            </div>

            <style>{`
                @keyframes spin {
                    to { transform: rotate(360deg); }
                }
                @keyframes fadeIn {
                    from { opacity: 0; transform: translateY(-10px); }
                    to { opacity: 1; transform: translateY(0); }
                }
                @keyframes pulse {
                    0% { opacity: 1; transform: scale(1); }
                    50% { opacity: 0.5; transform: scale(1.2); }
                    100% { opacity: 1; transform: scale(1); }
                }
                .spinner {
                    width: 40px;
                    height: 40px;
                    border: 3px solid var(--border);
                    border-top-color: var(--primary);
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                    margin: 0 auto 1rem;
                }
                .modal-overlay {
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: rgba(0,0,0,0.7);
                    z-index: 1000;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }
                .modal-content {
                    background: var(--bg-primary);
                    border-radius: 12px;
                    padding: 1.5rem;
                    max-width: 500px;
                    width: 90%;
                    max-height: 80vh;
                    overflow: auto;
                }
                .text-secondary {
                    color: var(--text-secondary);
                }
                .risk-level.high { color: var(--danger); }
                .risk-level.medium { color: var(--warning); }
                .risk-level.low { color: var(--success); }
                .live-badge {
                    font-size: 0.7rem;
                    background: rgba(16, 185, 129, 0.2);
                    padding: 0.25rem 0.5rem;
                    border-radius: 12px;
                    color: var(--success);
                }
                .btn-primary-small {
                    background: var(--primary);
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 0.25rem 0.75rem;
                    cursor: pointer;
                    font-size: 0.7rem;
                    transition: all 0.2s;
                }
                .btn-primary-small:hover {
                    opacity: 0.9;
                }
                .btn-warning-small {
                    background: var(--warning);
                    color: white;
                    border: none;
                    padding: 0.25rem 0.75rem;
                    border-radius: 4px;
                    cursor: pointer;
                    font-size: 0.7rem;
                }
                .btn-warning-small:hover {
                    opacity: 0.9;
                }
                .btn {
                    padding: 0.5rem 1rem;
                    border: none;
                    border-radius: 6px;
                    cursor: pointer;
                    font-size: 0.9rem;
                    transition: all 0.2s;
                }
                .btn-primary {
                    background: var(--primary);
                    color: white;
                }
                .btn-primary:hover {
                    opacity: 0.9;
                }
                .btn-secondary {
                    background: var(--bg-secondary);
                    color: var(--text-primary);
                    border: 1px solid var(--border);
                }
                .btn-secondary:hover {
                    background: var(--border);
                }
                .badge {
                    padding: 0.25rem 0.5rem;
                    border-radius: 4px;
                    font-size: 0.7rem;
                    font-weight: 500;
                }
                .badge-high { background: var(--danger); color: white; }
                .badge-medium { background: var(--warning); color: white; }
                .badge-low { background: var(--success); color: white; }
                .badge-critical { background: var(--danger); color: white; }
                .form-group { margin-bottom: 1rem; }
                .form-label { display: block; margin-bottom: 0.25rem; font-size: 0.8rem; color: var(--text-secondary); }
                .form-input { width: 100%; padding: 0.5rem; border: 1px solid var(--border); border-radius: 4px; background: var(--bg-primary); color: var(--text-primary); }
                .form-select { width: 100%; padding: 0.5rem; border: 1px solid var(--border); border-radius: 4px; background: var(--bg-primary); color: var(--text-primary); }
                .two-column { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-bottom: 1.5rem; }
                .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }
                .stat-card { background: var(--bg-secondary); padding: 1rem; border-radius: 8px; text-align: center; }
                .stat-value { font-size: 1.5rem; font-weight: bold; margin-bottom: 0.25rem; }
                .stat-label { font-size: 0.7rem; color: var(--text-secondary); }
                .card { background: var(--bg-secondary); border-radius: 8px; padding: 1rem; margin-bottom: 0; border: 1px solid var(--border); }
                .card-title { font-weight: bold; margin-bottom: 1rem; font-size: 1rem; }
                .empty-state { text-align: center; padding: 3rem; }
                .empty-icon { font-size: 3rem; margin-bottom: 1rem; }
                .empty-title { font-size: 1.2rem; font-weight: bold; margin-bottom: 0.5rem; }
                .empty-sub { color: var(--text-secondary); }
                .mono { font-family: monospace; }
                .cash-card.positive { border-left: 4px solid var(--success); }
                .cash-card.negative { border-left: 4px solid var(--danger); }
                .risk-score-card { color: white; }
                .cashflow-card {
                    overflow: visible;
                }
                .cashflow-summary {
                    display: flex;
                    justify-content: space-around;
                    align-items: center;
                    margin-top: 1rem;
                    padding-top: 1rem;
                    border-top: 1px solid var(--border);
                    flex-wrap: wrap;
                    gap: 0.5rem;
                }
                .summary-item {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    padding: 0.5rem;
                }
                .summary-label {
                    font-size: 0.7rem;
                    color: var(--text-secondary);
                    margin-bottom: 0.25rem;
                }
                .summary-value {
                    font-size: 1rem;
                    font-weight: bold;
                }
                .summary-value.positive { color: var(--success); }
                .summary-value.negative { color: var(--danger); }
                .summary-value.warning { color: var(--warning); }
                .summary-divider {
                    width: 1px;
                    height: 30px;
                    background: var(--border);
                }
                .custom-tooltip {
                    background: var(--bg-primary);
                    border: 1px solid var(--border);
                    border-radius: 8px;
                    padding: 0.75rem;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                    min-width: 200px;
                }
                .partial-payment-info {
                    background: var(--bg-tertiary);
                    border-radius: 8px;
                    padding: 0.75rem;
                    margin-bottom: 1rem;
                }
                .info-row {
                    display: flex;
                    justify-content: space-between;
                    padding: 0.25rem 0;
                }
                .info-row .paid { color: var(--success); }
                .info-row .remaining { color: var(--warning); }
                details summary {
                    transition: all 0.2s;
                }
                details summary:hover {
                    color: var(--primary);
                }
                @media (max-width: 768px) {
                    .two-column { grid-template-columns: 1fr; }
                    .stats-grid { grid-template-columns: repeat(2, 1fr); }
                    .cashflow-summary { flex-direction: column; align-items: stretch; }
                    .summary-divider { display: none; }
                }
            `}</style>
        </div>
    );
};

export default Dashboard;