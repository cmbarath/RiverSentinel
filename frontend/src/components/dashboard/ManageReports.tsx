"use client";

import React, { useState } from "react";
import { supabase } from "@/lib/supabaseClient";

const ManageReports = () => {
    const [reports, setReports] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedReport, setSelectedReport] = useState<any>(null);
    const [filter, setFilter] = useState("All Status");

    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:5000';

    const getAuthHeaders = async (): Promise<Record<string, string>> => {
        try {
            const { data } = await supabase.auth.getSession();
            const token = data?.session?.access_token;
            if (token) {
                return { 'Authorization': `Bearer ${token}` };
            }
        } catch {
            // ignore session retrieval error
        }
        return {};
    };

    const fetchReports = async () => {
        setLoading(true);
        try {
            const authHeaders = await getAuthHeaders();
            const response = await fetch(`${backendUrl}/api/authority/reports`, {
                headers: authHeaders
            });
            const data = await response.json();
            setReports(Array.isArray(data) ? data : []);
        } catch (error) {
            console.error("Failed to fetch reports:", error);
        } finally {
            setLoading(false);
        }
    };

    React.useEffect(() => {
        fetchReports();
    }, []);

    const handleStatusUpdate = async (reportId: string, status: string) => {
        try {
            const authHeaders = await getAuthHeaders();
            const response = await fetch(`${backendUrl}/api/authority/reports/update`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...authHeaders
                },
                body: JSON.stringify({ reportId, status })
            });
            const data = await response.json();
            if (data.status === 'success') {
                setReports(reports.map(r => r.id === reportId ? { ...r, status } : r));
                if (selectedReport?.id === reportId) setSelectedReport({ ...selectedReport, status });
            }
        } catch (error) {
            alert("Failed to update report status");
        }
    };

    const filteredReports = reports.filter(r => 
        filter === "All Status" || r.status === filter.toUpperCase()
    );

    return (
        <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
                <h3>Citizen Pollution Reports</h3>
                <div style={{ display: 'flex', gap: '1rem' }}>
                    <button className="btn btn-secondary" style={{ fontSize: '0.8rem' }} onClick={fetchReports}>Refresh</button>
                    <select 
                        value={filter}
                        onChange={(e) => setFilter(e.target.value)}
                        style={{ padding: '0.5rem', borderRadius: '0.5rem', border: '1px solid var(--border)' }}
                    >
                        <option>All Status</option>
                        <option>Pending</option>
                        <option>Verified</option>
                        <option>Resolved</option>
                        <option>Rejected</option>
                    </select>
                </div>
            </div>

            {loading ? (
                <div style={{ textAlign: 'center', padding: '3rem' }}>Fetching reports...</div>
            ) : filteredReports.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '3rem', color: '#64748b' }}>No reports found.</div>
            ) : (
                <div style={{ overflowX: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                        <thead>
                            <tr style={{ borderBottom: '1px solid var(--border)', color: '#64748b', fontSize: '0.9rem' }}>
                                <th style={{ padding: '1rem' }}>Photo</th>
                                <th style={{ padding: '1rem' }}>Location</th>
                                <th style={{ padding: '1rem' }}>Reporter</th>
                                <th style={{ padding: '1rem' }}>AI Severity</th>
                                <th style={{ padding: '1rem' }}>Status</th>
                                <th style={{ padding: '1rem' }}>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filteredReports.map((r) => (
                                <tr key={r.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                                    <td style={{ padding: '1rem' }}>
                                        <div 
                                            onClick={() => setSelectedReport(r)}
                                            style={{ cursor: 'pointer', width: '40px', height: '40px', background: '#e2e8f0', borderRadius: '4px', display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden' }}
                                        >
                                            {r.imageUrl && r.imageUrl.startsWith('data:') ? (
                                                <img src={r.imageUrl} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                                            ) : '📸'}
                                        </div>
                                    </td>
                                    <td style={{ padding: '1rem', fontWeight: 600 }}>{r.location}</td>
                                    <td style={{ padding: '1rem' }}>{r.reporter}</td>
                                    <td style={{ padding: '1rem' }}>
                                        <span className={`badge badge-${r.pollution_level === 'Critical' || r.pollution_level === 'High' ? 'red' : r.pollution_level === 'Moderate' ? 'orange' : 'blue'}`}>
                                            {r.pollution_level || 'LOW'}
                                        </span>
                                    </td>
                                    <td style={{ padding: '1rem' }}>
                                        <span style={{ 
                                            fontSize: '0.8rem', 
                                            fontWeight: 700, 
                                            color: r.status === 'VERIFIED' ? '#10b981' : r.status === 'REJECTED' ? '#ef4444' : '#f59e0b' 
                                        }}>
                                            {r.status}
                                        </span>
                                    </td>
                                    <td style={{ padding: '1rem' }}>
                                        <div style={{ display: 'flex', gap: '0.5rem' }}>
                                            <button 
                                                className="btn btn-primary" 
                                                style={{ padding: '0.4rem 0.8rem', fontSize: '0.75rem' }}
                                                onClick={() => handleStatusUpdate(r.id, 'VERIFIED')}
                                            >
                                                Verify
                                            </button>
                                            <button 
                                                className="btn btn-secondary" 
                                                style={{ padding: '0.4rem 0.8rem', fontSize: '0.75rem' }}
                                                onClick={() => handleStatusUpdate(r.id, 'REJECTED')}
                                            >
                                                Reject
                                            </button>
                                            <button 
                                                className="btn btn-secondary" 
                                                style={{ padding: '0.4rem 0.8rem', fontSize: '0.75rem', background: 'transparent', border: '1px solid var(--border)' }}
                                                onClick={() => setSelectedReport(r)}
                                            >
                                                View
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            {/* Simple Modal for Details */}
            {selectedReport && (
                <div style={{
                    position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
                    backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: '2rem'
                }}>
                    <div className="card" style={{ maxWidth: '800px', width: '100%', maxHeight: '90vh', overflowY: 'auto', position: 'relative' }}>
                        <button 
                            onClick={() => setSelectedReport(null)}
                            style={{ position: 'absolute', top: '1rem', right: '1rem', border: 'none', background: 'none', fontSize: '1.5rem', cursor: 'pointer' }}
                        >
                            &times;
                        </button>
                        
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
                            <div>
                                {selectedReport.imageUrl && selectedReport.imageUrl.startsWith('data:') ? (
                                    <img src={selectedReport.imageUrl} style={{ width: '100%', borderRadius: '1rem', objectFit: 'contain' }} />
                                ) : (
                                    <div style={{ height: '300px', background: '#f1f5f9', borderRadius: '1rem', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>No Photo Available</div>
                                )}
                            </div>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                                <div>
                                    <h2 style={{ margin: 0 }}>{selectedReport.location}</h2>
                                    <p style={{ color: '#64748b' }}>Submitted by {selectedReport.reporter} on {new Date(selectedReport.timestamp).toLocaleString()}</p>
                                </div>
                                <div style={{ display: 'flex', gap: '1rem' }}>
                                    <span className="badge badge-primary">AI Confidence: {selectedReport.confidence}%</span>
                                    <span className={`badge badge-${selectedReport.status === 'VERIFIED' ? 'success' : selectedReport.status === 'REJECTED' ? 'danger' : 'warning'}`}>{selectedReport.status}</span>
                                </div>
                                <div style={{ background: '#f8fafc', padding: '1rem', borderRadius: '0.5rem' }}>
                                    <div style={{ fontWeight: 700, marginBottom: '0.5rem' }}>AI Assessment:</div>
                                    <p style={{ fontSize: '0.9rem', lineHeight: 1.5 }}>{selectedReport.assessment}</p>
                                </div>
                                <div>
                                    <div style={{ fontWeight: 700, marginBottom: '0.5rem' }}>Pollutants Detected:</div>
                                    <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                                        {selectedReport.pollutants?.map((p: string, i: number) => (
                                            <span key={i} style={{ background: '#fee2e2', color: '#991b1b', padding: '0.2rem 0.6rem', borderRadius: '4px', fontSize: '0.8rem' }}>{p}</span>
                                        ))}
                                    </div>
                                </div>
                                {selectedReport.description && (
                                    <div>
                                        <div style={{ fontWeight: 700, marginBottom: '0.5rem' }}>User Description:</div>
                                        <p style={{ fontSize: '0.9rem' }}>{selectedReport.description}</p>
                                    </div>
                                )}
                                <div style={{ display: 'flex', gap: '1rem', marginTop: 'auto', paddingTop: '1rem' }}>
                                    <button className="btn btn-primary" onClick={() => handleStatusUpdate(selectedReport.id, 'VERIFIED')}>Mark Verified</button>
                                    <button className="btn btn-secondary" onClick={() => handleStatusUpdate(selectedReport.id, 'REJECTED')}>Reject Report</button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default ManageReports;
