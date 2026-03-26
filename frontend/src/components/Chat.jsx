import React, { useState, useRef, useEffect } from 'react';
import { useApi } from '../hooks/useApi';
import { formatCurrency } from '../utils/formatters';

const Chat = ({ data }) => {
    const [messages, setMessages] = useState([
        { role: 'assistant', content: 'Hello! I\'m PayWise AI. I can help you understand risk, penalties, payment strategies, and more. What would you like to know?' }
    ]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const { request } = useApi();
    const messagesEndRef = useRef(null);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const sendMessage = async () => {
        if (!input.trim() || loading) return;
        const userMsg = { role: 'user', content: input };
        setMessages(prev => [...prev, userMsg]);
        setInput('');
        setLoading(true);

        try {
            const result = await request('/chat', {
                method: 'POST',
                body: JSON.stringify({ messages: [...messages, userMsg], transaction: data })
            });
            setMessages(prev => [...prev, { role: 'assistant', content: result.reply }]);
        } catch (err) {
            setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${err.message}` }]);
        } finally {
            setLoading(false);
        }
    };

    const quickQuestions = data ? [
        'What is my risk level?',
        'How can I reduce penalties?',
        'Should I pay now or negotiate?',
        'What are partial payment options?'
    ] : [
        'How does risk scoring work?',
        'What is a partial payment?',
        'When to request extension?',
        'How are penalties calculated?'
    ];

    return (
        <div>
            <h2 style={{ marginBottom: '1.5rem' }}>💬 AI Assistant</h2>
            
            {data && (
                <div style={{ 
                    background: 'var(--accent-glow)', 
                    padding: '0.75rem', 
                    borderRadius: '8px', 
                    marginBottom: '1rem',
                    fontSize: '0.85rem',
                    border: '1px solid var(--accent)'
                }}>
                    📌 Transaction context loaded: <strong>{data.counterparty_name}</strong> — {formatCurrency(data.amount)} · {data.days_late} days late · {data.priority} risk
                </div>
            )}

            <div className="chat-container">
                <div className="chat-messages">
                    {messages.map((msg, i) => (
                        <div key={i} className={`chat-message ${msg.role}`}>
                            <div className="chat-bubble">{msg.content}</div>
                        </div>
                    ))}
                    {loading && (
                        <div className="chat-message assistant">
                            <div className="chat-bubble">
                                <span className="spinner"></span> Thinking...
                            </div>
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>
                <div className="chat-input">
                    <input 
                        className="form-input" 
                        placeholder="Ask about risk, penalties, strategy..." 
                        value={input} 
                        onChange={e => setInput(e.target.value)} 
                        onKeyPress={e => e.key === 'Enter' && sendMessage()} 
                    />
                    <button className="btn btn-primary" onClick={sendMessage} disabled={loading || !input.trim()}>
                        Send
                    </button>
                </div>
            </div>

            <div style={{ marginTop: '1rem', display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                {quickQuestions.map((q, i) => (
                    <button 
                        key={i} 
                        className="btn btn-secondary" 
                        style={{ fontSize: '0.7rem', padding: '0.3rem 0.7rem' }} 
                        onClick={() => setInput(q)}
                    >
                        {q}
                    </button>
                ))}
            </div>
        </div>
    );
};

export default Chat;