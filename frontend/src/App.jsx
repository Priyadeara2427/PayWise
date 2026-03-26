import React, { useState } from 'react';
import { useApi } from './hooks/useApi';
import Navbar from './components/Navbar';
import Dashboard from './components/Dashboard';
import InputForm from './components/InputForm';
import UploadZone from './components/UploadZone';
import Results from './components/Results';
import Communicate from './components/Communicate';
import Chat from './components/Chat';
import Festival from './components/FestivalPlanner';

const App = () => {
    const [activeTab, setActiveTab] = useState('dashboard');
    const [analysis, setAnalysis] = useState(null);
    const { request, loading } = useApi();

    const handleAnalyze = async (formData) => {
        try {
            const result = await request('/analyze', {
                method: 'POST',
                body: JSON.stringify(formData)
            });
            setAnalysis(result);
            setActiveTab('results');
        } catch (err) {
            alert(err.message);
        }
    };

    const handleUpload = async (data) => {
        setAnalysis(data);
        setActiveTab('results');
    };

    const loadDemo = async () => {
        try {
            const result = await request('/demo');
            setAnalysis(result);
            setActiveTab('results');
        } catch (err) {
            alert(err.message);
        }
    };

    return (
        <div className="app">
            <Navbar activeTab={activeTab} setActiveTab={setActiveTab} hasResult={!!analysis} />
            
            <div className="main-content">
                {activeTab === 'dashboard' && <Dashboard setActiveTab={setActiveTab} />}
                {activeTab === 'input' && <InputForm onAnalyze={handleAnalyze} loading={loading} />}
                {activeTab === 'upload' && <UploadZone onUpload={handleUpload} loading={loading} />}
                {activeTab === 'results' && <Results data={analysis} />}
                {activeTab === 'communicate' && <Communicate data={analysis} />}
                {activeTab === 'chat' && <Chat data={analysis} />}
                {activeTab === 'festival' && <Festival data={analysis} />}
            </div>
            
            {activeTab !== 'dashboard' && (
                <div style={{ position: 'fixed', bottom: '20px', right: '20px' }}>
                    <button 
                        className="btn btn-secondary" 
                        onClick={loadDemo}
                        style={{ fontSize: '0.8rem', padding: '0.5rem 1rem' }}
                    >
                        🎯 Load Demo
                    </button>
                </div>
            )}
        </div>
    );
};

export default App;