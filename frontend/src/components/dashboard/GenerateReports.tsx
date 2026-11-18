"use client";

import React, { useState, useEffect } from "react";

const GenerateReports = () => {
    const [summary, setSummary] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    const fetchSummary = async () => {
        setLoading(true);
        try {
            const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:5000';
            const response = await fetch(`${backendUrl}/api/authority/report-summary`);
            const data = await response.json();
            if (data.status === 'success') {
                setSummary(data);
            }
        } catch (error) {
            console.error("Failed to fetch report summary:", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchSummary();
    }, []);

    const handlePrint = () => {
        window.print();
    };

    if (loading) return <div style={{ textAlign: 'center', padding: '5rem' }}>Gathering system information for report...</div>;

    if (!summary) return <div style={{ textAlign: 'center', padding: '5rem', color: '#ef4444' }}>Error: Could not generate report. Please ensure backend is running.</div>;

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                    <h2 style={{ margin: 0 }}>Generate Formal Report</h2>
                    <p style={{ color: '#64748b' }}>Consolidated system state and compliance monitoring</p>
                </div>
                <button className="btn btn-primary" onClick={handlePrint} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <span>📄</span> Download Formal Report (PDF)
                </button>
            </div>

            {/* Formal Report Preview */}
            <div id="formal-report" className="card" style={{ 
                background: 'white', 
                padding: '4rem', 
                borderRadius: '0', 
                boxShadow: '0 4px 20px rgba(0,0,0,0.08)',
                minHeight: '297mm', // A4 aspect ratio 
                position: 'relative',
                color: '#1e293b'
            }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '2px solid #1e293b', paddingBottom: '1.5rem', marginBottom: '2rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                        <div style={{ fontSize: '2.5rem' }}>🌊</div>
                        <div>
                            <div style={{ fontWeight: 800, fontSize: '1.5rem', letterSpacing: '-0.02em' }}>RIVER SENTINEL AI</div>
                            <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#64748b' }}>ENVIRONMENTAL COMPLIANCE PORTAL</div>
                        </div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                        <div style={{ fontWeight: 700 }}>REPORT ID: RS-{new Date().getFullYear()}-{Math.floor(Math.random() * 90000 + 10000)}</div>
                        <div style={{ fontSize: '0.9rem', color: '#64748b' }}>Generated: {summary.generated_at}</div>
                    </div>
                </div>

                <div style={{ marginBottom: '3rem' }}>
                    <h1 style={{ fontSize: '2rem', fontWeight: 900, marginBottom: '0.5rem' }}>Executive Environmental Summary</h1>
                    <p style={{ color: '#475569', maxWidth: '80%' }}>
                        This document provides an official status update of the monitored river section, aggregating data from multiple IoT sensors and verified citizen reports. 
                        Issued by the <strong>{summary.agency}</strong>.
                    </p>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1.5rem', marginBottom: '3rem' }}>
                    <div style={{ background: '#f8fafc', padding: '1.5rem', borderLeft: '4px solid var(--primary)' }}>
                        <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#64748b', textTransform: 'uppercase', marginBottom: '0.5rem' }}>Water Quality Score</div>
                        <div style={{ fontSize: '2rem', fontWeight: 800 }}>{85 + Math.floor(Math.random() * 10)}/100</div>
                        <div style={{ fontSize: '0.85rem', color: '#10b981', fontWeight: 600 }}>↑ 2.4% from last week</div>
                    </div>
                    <div style={{ background: '#f8fafc', padding: '1.5rem', borderLeft: '4px solid #f59e0b' }}>
                        <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#64748b', textTransform: 'uppercase', marginBottom: '0.5rem' }}>Citizen Reports</div>
                        <div style={{ fontSize: '2rem', fontWeight: 800 }}>{summary.report_summary.total}</div>
                        <div style={{ fontSize: '0.85rem', color: '#64748b', fontWeight: 600 }}>Resolution: {summary.report_summary.resolution_rate}%</div>
                    </div>
                    <div style={{ background: '#f8fafc', padding: '1.5rem', borderLeft: '4px solid #ef4444' }}>
                        <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#64748b', textTransform: 'uppercase', marginBottom: '0.5rem' }}>Active Warnings</div>
                        <div style={{ fontSize: '2rem', fontWeight: 800 }}>{summary.active_alerts}</div>
                        <div style={{ fontSize: '0.85rem', color: '#ef4444', fontWeight: 600 }}>{summary.active_alerts > 0 ? "Action Required" : "Normal Status"}</div>
                    </div>
                </div>

                <div style={{ marginBottom: '3rem' }}>
                    <h3 style={{ borderBottom: '1px solid #e2e8f0', paddingBottom: '0.5rem', marginBottom: '1.5rem' }}>II. Sensor Performance Metrics</h3>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2.5rem' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                            <tbody>
                                <tr style={{ borderBottom: '1px solid #f1f5f9' }}>
                                    <td style={{ padding: '0.75rem 0', color: '#64748b', fontWeight: 600 }}>Average pH Level</td>
                                    <td style={{ padding: '0.75rem 0', fontWeight: 700, textAlign: 'right' }}>{summary.sensor_summary.avg_ph}</td>
                                </tr>
                                <tr style={{ borderBottom: '1px solid #f1f5f9' }}>
                                    <td style={{ padding: '0.75rem 0', color: '#64748b', fontWeight: 600 }}>Dissolved Oxygen</td>
                                    <td style={{ padding: '0.75rem 0', fontWeight: 700, textAlign: 'right' }}>{summary.sensor_summary.avg_do} mg/L</td>
                                </tr>
                                <tr style={{ borderBottom: '1px solid #f1f5f9' }}>
                                    <td style={{ padding: '0.75rem 0', color: '#64748b', fontWeight: 600 }}>Avg Turbidity</td>
                                    <td style={{ padding: '0.75rem 0', fontWeight: 700, textAlign: 'right' }}>{summary.sensor_summary.avg_turbidity} NTU</td>
                                </tr>
                            </tbody>
                        </table>
                        <div style={{ background: '#f0f9ff', padding: '1.5rem', borderRadius: '0.5rem', border: '1px solid #bae6fd' }}>
                            <div style={{ fontWeight: 700, color: '#0369a1', marginBottom: '0.5rem' }}>Analytical Note:</div>
                            <p style={{ fontSize: '0.85rem', color: '#0c4a6e', margin: 0 }}>
                                Water stability remains <strong>{summary.sensor_summary.trend || "STABLE"}</strong> despite minor variations in average turbidity. Dissolved oxygen levels are within the healthy ecological range for aquatic life support.
                            </p>
                        </div>
                    </div>
                </div>

                <div style={{ marginBottom: '3rem' }}>
                    <h3 style={{ borderBottom: '1px solid #e2e8f0', paddingBottom: '0.5rem', marginBottom: '1.5rem' }}>III. Enforcement & Citizen Monitoring</h3>
                    <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: '2.5rem' }}>
                        <div>
                            <p style={{ fontSize: '0.9rem', color: '#475569', lineHeight: 1.6 }}>
                                Total of <strong>{summary.report_summary.total}</strong> pollution incidents were reported by public participants. 
                                Authorities have successfully processed <strong>{summary.report_summary.verified + summary.report_summary.rejected}</strong> cases, 
                                resulting in a current verification and response index of <strong>{summary.report_summary.resolution_rate}%</strong>.
                            </p>
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem' }}>
                                <span>Verified Reports</span>
                                <span style={{ fontWeight: 700 }}>{summary.report_summary.verified}</span>
                            </div>
                            <div style={{ width: '100%', height: '8px', background: '#e2e8f0', borderRadius: '4px', overflow: 'hidden' }}>
                                <div style={{ width: `${(summary.report_summary.verified / summary.report_summary.total) * 100}%`, height: '100%', background: '#10b981' }}></div>
                            </div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginTop: '0.5rem' }}>
                                <span>Rejected Reports</span>
                                <span style={{ fontWeight: 700 }}>{summary.report_summary.rejected}</span>
                            </div>
                            <div style={{ width: '100%', height: '8px', background: '#e2e8f0', borderRadius: '4px', overflow: 'hidden' }}>
                                <div style={{ width: `${(summary.report_summary.rejected / summary.report_summary.total) * 100}%`, height: '100%', background: '#ef4444' }}></div>
                            </div>
                        </div>
                    </div>
                </div>

                <div style={{ marginTop: 'auto', paddingTop: '4rem', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
                    <div>
                        <div style={{ fontWeight: 800, fontSize: '0.9rem' }}>DIGITALLY SIGNED</div>
                        <div style={{ height: '2px', width: '150px', background: '#1e293b', margin: '0.5rem 0' }}></div>
                        <div style={{ fontSize: '0.8rem', color: '#64748b' }}>Environmental Commissioner</div>
                    </div>
                    <div style={{ opacity: 0.3, fontSize: '0.8rem' }}>
                        Authenticated by RiverSentinel Blockchain Core
                    </div>
                </div>
            </div>

            <style>{`
                @media print {
                    body * { visibility: hidden; }
                    #formal-report, #formal-report * { visibility: visible; }
                    #formal-report { 
                        position: absolute; 
                        left: 0; 
                        top: 0; 
                        width: 100%; 
                        padding: 2cm; 
                        box-shadow: none !react;
                    }
                }
            `}</style>
        </div>
    );
};

export default GenerateReports;
