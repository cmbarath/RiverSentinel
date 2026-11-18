"use client";

import React, { useState, useEffect } from "react";

const DownloadReport = () => {
    const [data, setData] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    const fetchHealthStatus = async () => {
        setLoading(true);
        try {
            const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:5000';
            const response = await fetch(`${backendUrl}/api/citizen/health-status`);
            const result = await response.json();
            if (result.status === 'success') {
                setData(result);
            }
        } catch (error) {
            console.error("Fetch error:", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchHealthStatus();
    }, []);

    const handleDownload = () => {
        window.print();
    };

    if (loading) return <div style={{ textAlign: 'center', padding: '5rem' }}>Preparing your River Health Card...</div>;

    if (!data) return <div style={{ textAlign: 'center', padding: '5rem', color: '#ef4444' }}>Error: Could not retrieve health data.</div>;

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem', maxWidth: '900px', margin: '0 auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                    <h2 style={{ margin: 0 }}>River Health Card</h2>
                    <p style={{ color: '#64748b' }}>Latest official safety update for your river section</p>
                </div>
                <button className="btn btn-primary" onClick={handleDownload} style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
                    <span>📜</span> Save Health Certificate
                </button>
            </div>

            {/* Certificate UI */}
            <div id="health-certificate" style={{
                background: 'white',
                padding: '3rem',
                borderRadius: '1.5rem',
                boxShadow: '0 10px 30px rgba(0,0,0,0.1)',
                border: '12px double #e2e8f0',
                position: 'relative',
                overflow: 'hidden'
            }}>
                {/* Background Watermark/Pattern */}
                <div style={{ position: 'absolute', top: '-10%', right: '-10%', fontSize: '20rem', opacity: 0.03, pointerEvents: 'none' }}>🌊</div>
                <div style={{ position: 'absolute', bottom: '-5%', left: '-5%', fontSize: '15rem', opacity: 0.03, pointerEvents: 'none', transform: 'rotate(45deg)' }}>🕉️</div>

                {/* Branding Header */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '3rem', borderBottom: '1px solid #f1f5f9', paddingBottom: '1.5rem' }}>
                    <div style={{ textAlign: 'center', flex: 1 }}>
                        <div style={{ fontSize: '0.8rem', fontWeight: 800, color: '#64748b', letterSpacing: '0.1em' }}>GOVERNMENT OF UTTAR PRADESH</div>
                        <div style={{ fontSize: '1.25rem', fontWeight: 900, color: '#1e293b' }}>VARANASI NAGAR NIGAM</div>
                        <div style={{ fontSize: '0.9rem', color: '#0ea5e9', fontWeight: 700 }}>NAMAMI GANGE MISSION</div>
                    </div>
                </div>

                <div style={{ textAlign: 'center', marginBottom: '3rem' }}>
                    <div style={{ display: 'inline-block', padding: '0.5rem 1.5rem', background: '#f0f9ff', borderRadius: '999px', fontSize: '0.85rem', fontWeight: 800, color: '#0369a1', marginBottom: '1rem' }}>
                        CERTIFICATE OF RIVER HEALTH
                    </div>
                    <h1 style={{ fontSize: '2.5rem', fontWeight: 900, marginBottom: '0.5rem' }}>{data.location}</h1>
                    <p style={{ color: '#64748b' }}>Verified monitoring status as of {data.timestamp}</p>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '3rem', marginBottom: '3rem' }}>
                    {/* Gauge/Score Side */}
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', background: '#f8fafc', borderRadius: '2rem', padding: '2rem' }}>
                        <div style={{ fontSize: '0.9rem', fontWeight: 700, color: '#64748b', marginBottom: '1rem' }}>RIVER HEALTH INDEX</div>
                        <div style={{ position: 'relative', width: '160px', height: '160px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                            <svg viewBox="0 0 36 36" style={{ width: '100%', height: '100%', transform: 'rotate(-90deg)' }}>
                                <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="#e2e8f0" strokeWidth="3" />
                                <path d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" fill="none" stroke="var(--primary)" strokeWidth="3" strokeDasharray={`${data.health_score}, 100`} />
                            </svg>
                            <div style={{ position: 'absolute', textAlign: 'center' }}>
                                <div style={{ fontSize: '2.5rem', fontWeight: 900, color: 'var(--primary)' }}>{data.health_score}</div>
                                <div style={{ fontSize: '0.75rem', fontWeight: 700, marginTop: '-5px' }}>BOP SCORE</div>
                            </div>
                        </div>
                        <div style={{ marginTop: '1.5rem', fontSize: '1.5rem', fontWeight: 800, color: '#10b981' }}>{data.grade} GRADE</div>
                    </div>

                    {/* Stats Side */}
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '1rem', borderBottom: '1px solid #f1f5f9' }}>
                            <span style={{ fontWeight: 600, color: '#64748b' }}>Safety Status</span>
                            <span className={`badge badge-${data.safety_status === 'EXCELLENT' || data.safety_status === 'SAFE' ? 'green' : 'orange'}`} style={{ fontSize: '0.9rem' }}>
                                {data.safety_status}
                            </span>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '1rem', borderBottom: '1px solid #f1f5f9' }}>
                            <span style={{ fontWeight: 600, color: '#64748b' }}>Water Purity</span>
                            <span style={{ fontWeight: 800, color: '#1e293b' }}>{Math.round(data.metrics.purity)}%</span>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '1rem', borderBottom: '1px solid #f1f5f9' }}>
                            <span style={{ fontWeight: 600, color: '#64748b' }}>pH Balance</span>
                            <span style={{ fontWeight: 800, color: '#1e293b' }}>{data.metrics.ph}</span>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '1rem', borderBottom: '1px solid #f1f5f9' }}>
                            <span style={{ fontWeight: 600, color: '#64748b' }}>Oxygen Level</span>
                            <span style={{ fontWeight: 800, color: '#1e293b' }}>{data.metrics.do} mg/L</span>
                        </div>
                    </div>
                </div>

                <div style={{ background: '#fffbeb', border: '1px solid #fef3c7', padding: '1.5rem', borderRadius: '1rem', marginBottom: '3rem' }}>
                    <div style={{ display: 'flex', gap: '1rem' }}>
                        <span style={{ fontSize: '1.5rem' }}>💡</span>
                        <p style={{ fontSize: '0.9rem', color: '#92400e', margin: 0, lineHeight: 1.5 }}>
                            <strong>Authority Advisory:</strong> Current conditions are favorable for ritual bathing and ecological support. Please maintain cleanliness at the ghats and report any visible pollution via the dashboard.
                        </p>
                    </div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', paddingTop: '2rem' }}>
                    <div style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: '0.8rem', fontWeight: 700, opacity: 0.3, marginBottom: '0.5rem' }}>QR-AUTH-CERT</div>
                        <div style={{ width: '60px', height: '60px', background: '#1e293b', padding: '4px', borderRadius: '4px' }}>
                            <div style={{ width: '100%', height: '100%', border: '2px solid white' }}></div>
                        </div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                        <div style={{ fontSize: '0.8rem', fontWeight: 800 }}>RIVERSENTINEL AI VALIDATED</div>
                        <div style={{ fontSize: '0.75rem', color: '#64748b' }}>Citizen Awareness Initiative</div>
                    </div>
                </div>
            </div>

            <style>{`
                @media print {
                    body * { visibility: hidden; }
                    #health-certificate, #health-certificate * { visibility: visible; }
                    #health-certificate { 
                        position: absolute; 
                        left: 0; 
                        top: 0; 
                        width: 100%; 
                        padding: 1rem; 
                        box-shadow: none !important;
                        border: 6px double #334155;
                    }
                }
            `}</style>
        </div>
    );
};

export default DownloadReport;
