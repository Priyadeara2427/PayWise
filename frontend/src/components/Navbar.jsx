import React from 'react';

const Navbar = ({ activeTab, setActiveTab, hasResult }) => {
  const tabs = [
    { id: "dashboard", label: "📊 Dashboard" },
    { id: "input", label: "📝 Input" },
    { id: "upload", label: "📄 Upload" },
    { id: "results", label: "📈 Results" },
    { id: "communicate", label: "✉️ Communicate" },
    { id: "chat", label: "💬 AI Chat" },
    { id: "festival", label: "✨ Festival Planning" },
  ];

    return (
        <nav className="navbar">
            <div className="nav-container">
                <div className="logo">
                    <div className="logo-dot"></div>
                    PayWise
                </div>
                <div className="nav-tabs">
                    {tabs.map(tab => (
                        <button
                            key={tab.id}
                            className={`nav-tab ${activeTab === tab.id ? 'active' : ''}`}
                            onClick={() => setActiveTab(tab.id)}
                        >
                            {tab.label}
                            {tab.id === 'results' && hasResult && (
                                <span style={{
                                    marginLeft: '5px',
                                    width: '6px',
                                    height: '6px',
                                    borderRadius: '50%',
                                    background: 'var(--success)',
                                    display: 'inline-block'
                                }} />
                            )}
                        </button>
                    ))}
                </div>
            </div>
        </nav>
    );
};

export default Navbar;