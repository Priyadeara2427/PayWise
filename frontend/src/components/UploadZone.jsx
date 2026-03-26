import React, { useState, useRef } from 'react';

const UploadZone = ({ onUpload, loading }) => {
    const [dragOver, setDragOver] = useState(false);
    const [filename, setFilename] = useState('');
    const fileRef = useRef();

    const handleFile = async (file) => {
        if (!file) return;
        setFilename(file.name);
        
        const formData = new FormData();
        formData.append('file', file);
        
        try {
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error);
            onUpload(data);
        } catch (err) {
            alert(err.message);
        }
    };

    const onDrop = (e) => {
        e.preventDefault();
        setDragOver(false);
        handleFile(e.dataTransfer.files[0]);
    };

    return (
        <div>
            <h2 style={{ marginBottom: '1.5rem' }}>📄 Upload Document</h2>
            
            <div
                className={`upload-zone ${dragOver ? 'dragover' : ''}`}
                onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                onDrop={onDrop}
                onClick={() => fileRef.current.click()}
            >
                <input
                    ref={fileRef}
                    type="file"
                    style={{ display: 'none' }}
                    accept=".csv,.pdf,.png,.jpg,.jpeg"
                    onChange={e => handleFile(e.target.files[0])}
                />
                {loading ? (
                    <>
                        <div className="spinner" style={{ width: '30px', height: '30px', margin: '0 auto 1rem' }}></div>
                        <div className="upload-text">Processing {filename}...</div>
                        <div className="upload-sub">OCR extraction + AI parsing in progress</div>
                    </>
                ) : (
                    <>
                        <div className="upload-icon">📎</div>
                        <div className="upload-text">Drop file here or click to browse</div>
                        <div className="upload-sub">Supports CSV, PDF, PNG, JPG</div>
                    </>
                )}
            </div>

            <div className="card" style={{ marginTop: '1.5rem' }}>
                <div className="card-title">HOW IT WORKS</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', fontSize: '0.85rem' }}>
                    <div>1. OCR extracts text from images/PDFs</div>
                    <div>2. AI parses unstructured text into structured data</div>
                    <div>3. Smart defaults infer missing fields</div>
                    <div>4. Full risk analysis and recommendations generated</div>
                </div>
            </div>
        </div>
    );
};

export default UploadZone;