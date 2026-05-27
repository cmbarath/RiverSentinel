"use client";

import React, { useState } from "react";

const ReportPollution = () => {
    const [analyzing, setAnalyzing] = useState(false);
    const [reportData, setReportData] = useState<any>(null);
    const [image, setImage] = useState<string | null>(null);

    const [location, setLocation] = useState("");
    const [description, setDescription] = useState("");
    const [submitting, setSubmitting] = useState(false);

    const handleImageUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = () => {
                setImage(reader.result as string);
                analyzeWithAI(file); 
            };
            reader.readAsDataURL(file);
        }
    };

    const analyzeWithAI = (file: File) => {
        setAnalyzing(true);
        setReportData(null);

        const formData = new FormData();
        formData.append('image', file);

        fetch(`http://127.0.0.1:5000/api/ai/analyze-image`, {
            method: 'POST',
            body: formData 
        })
            .then(res => res.json())
            .then(data => {
                setAnalyzing(false);
                if (data.error) {
                    alert("AI Error: " + data.error);
                    return;
                }
                setReportData({
                    pollution: data.pollution_level?.toUpperCase().includes('LOW') ? 'NO' : 'YES',
                    types: data.pollutants || [],
                    severity: data.pollution_level || "LOW",
                    confidence: (data.confidence || 0) + "%",
                    description: data.assessment || "No detailed insight available."
                });
            })
            .catch(err => {
                console.error(err);
                setAnalyzing(false);
                alert("Failed to connect to AI server.");
            });
    };

    const handleSubmit = async () => {
        if (!image || !reportData) {
            alert("Please upload and analyze an image first.");
            return;
        }

        setSubmitting(true);
        try {
            const response = await fetch('http://127.0.0.1:5000/api/reports/submit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    imageUrl: image,
                    location: location || "Near Dashashwamedh Ghat",
                    description: description,
                    pollution_level: reportData.severity,
                    pollutants: reportData.types,
                    assessment: reportData.description,
                    reporter: "Citizen App"
                })
            });

            const data = await response.json();
            if (data.status === 'success') {
                alert("Report submitted successfully to Authority!");
                // Reset form
                setImage(null);
                setReportData(null);
                setLocation("");
                setDescription("");
            } else {
                throw new Error(data.message);
            }
        } catch (err: any) {
            alert("Submission failed: " + err.message);
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(300px, 1fr) 1.5fr', gap: '2rem' }}>
            <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                <h3>Submit Report</h3>
                <div
                    style={{
                        height: '250px',
                        border: '2px dashed var(--border)',
                        borderRadius: '1rem',
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        justifyContent: 'center',
                        cursor: 'pointer',
                        overflow: 'hidden',
                        position: 'relative',
                        background: '#f8fafc',
                        opacity: submitting ? 0.6 : 1
                    }}
                    onClick={() => !submitting && document.getElementById('upload')?.click()}
                >
                    {image ? (
                        <img src={image} style={{ width: '100%', height: '100%', objectFit: 'cover' }} alt="Upload" />
                    ) : (
                        <>
                            <span style={{ fontSize: '3rem' }}>📸</span>
                            <p style={{ color: '#64748b', marginTop: '0.5rem' }}>Click to upload or drag photo</p>
                        </>
                    )}
                    <input type="file" id="upload" hidden onChange={handleImageUpload} accept="image/*" disabled={submitting} />
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    <div>
                        <label style={{ display: 'block', fontSize: '0.9rem', fontWeight: 600, marginBottom: '0.5rem' }}>Location</label>
                        <input 
                            type="text" 
                            placeholder="Near Dashashwamedh Ghat..." 
                            value={location}
                            onChange={(e) => setLocation(e.target.value)}
                            style={{ width: '100%', padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid var(--border)' }} 
                            disabled={submitting}
                        />
                    </div>
                    <div>
                        <label style={{ display: 'block', fontSize: '0.9rem', fontWeight: 600, marginBottom: '0.5rem' }}>Description</label>
                        <textarea 
                            placeholder="Describe what you observed..." 
                            value={description}
                            onChange={(e) => setDescription(e.target.value)}
                            rows={3} 
                            style={{ width: '100%', padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid var(--border)', fontFamily: 'inherit' }} 
                            disabled={submitting}
                        />
                    </div>
                    <button 
                        className="btn btn-primary" 
                        style={{ padding: '1rem', opacity: (submitting || !reportData) ? 0.7 : 1 }}
                        onClick={handleSubmit}
                        disabled={submitting || !reportData}
                    >
                        {submitting ? 'Submitting...' : 'Submit Report'}
                    </button>
                </div>
            </div>

            <div>
                {analyzing ? (
                    <div className="card" style={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '1.5rem' }}>
                        <div style={{ width: '50px', height: '50px', border: '4px solid #f3f3f3', borderTop: '4px solid var(--primary)', borderRadius: '50%', animation: 'spin 1s linear infinite' }}></div>
                        <style>{`@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }`}</style>
                        <h3>AI Analyzing Image...</h3>
                        <p style={{ color: '#64748b' }}>Deep Analysis by Groq Llama 3.2 Vision</p>
                    </div>
                ) : reportData ? (
                    <div className="card" style={{ height: '100%', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <h3 style={{ margin: 0 }}>AI Analysis Result</h3>
                            <span className={`badge ${reportData.pollution === 'YES' ? 'badge-red' : 'badge-green'}`}>
                                SEVERITY: {reportData.severity}
                            </span>
                        </div>

                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
                            <div style={{ background: '#f8fafc', padding: '1rem', borderRadius: '0.75rem' }}>
                                <div style={{ fontSize: '0.8rem', color: '#64748b', fontWeight: 600 }}>POLLUTION DETECTED</div>
                                <div style={{ fontSize: '1.5rem', fontWeight: 800, color: reportData.pollution === 'YES' ? 'var(--danger)' : '#10b981' }}>{reportData.pollution}</div>
                            </div>
                            <div style={{ background: '#f8fafc', padding: '1rem', borderRadius: '0.75rem' }}>
                                <div style={{ fontSize: '0.8rem', color: '#64748b', fontWeight: 600 }}>AI CONFIDENCE</div>
                                <div style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--primary)' }}>{reportData.confidence}</div>
                            </div>
                        </div>

                        <div>
                            <div style={{ fontWeight: 600, marginBottom: '0.5rem' }}>Details Detected:</div>
                            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                                {reportData.types.length > 0 ? reportData.types.map((t: string, i: number) => (
                                    <span key={i} style={{ background: '#e0f2fe', color: '#0369a1', padding: '0.4rem 0.8rem', borderRadius: '0.5rem', fontSize: '0.85rem', fontWeight: 600 }}>{t}</span>
                                )) : <span style={{ color: '#64748b' }}>None identified</span>}
                            </div>
                        </div>

                        <div style={{ background: '#f0f9ff', padding: '1.5rem', borderRadius: '1rem', border: '1px solid #bae6fd' }}>
                            <div style={{ fontWeight: 700, color: 'var(--primary)', marginBottom: '0.5rem' }}>Groq AI Insight:</div>
                            <p style={{ color: '#0369a1', fontSize: '0.95rem' }}>{reportData.description}</p>
                        </div>
                    </div>
                ) : (
                    <div className="card" style={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', opacity: 0.5, border: '2px dashed #cbd5e1' }}>
                        <span style={{ fontSize: '4rem', marginBottom: '1rem' }}>🤖</span>
                        <p>Upload a photo to see AI analysis magic</p>
                    </div>
                )}
            </div>
        </div>
    );
};

export default ReportPollution;
