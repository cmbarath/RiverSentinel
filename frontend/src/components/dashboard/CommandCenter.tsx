"use client";

import React from "react";

const CommandCenter = () => {
    const [status, setStatus] = React.useState<{type: 'success' | 'error' | 'info' | null, msg: string}>({type: null, msg: ''});
    const [loading, setLoading] = React.useState<string | null>(null);

    const handleAction = async (action: string) => {
        setLoading(action);
        setStatus({type: 'info', msg: `Processing ${action}...`});
        
        const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:5000';

        try {
            if (action === 'export') {
                // Handle file download for export
                window.location.href = `${backendUrl}/api/authority/export-data`;
                setStatus({type: 'success', msg: 'System data export started.'});
                setLoading(null);
                return;
            }

            const endpoints: Record<string, string> = {
                'sms': '/api/authority/send-sms',
                'notice': '/api/authority/generate-notice',
                'alert': '/api/authority/trigger-alert'
            };

            if (action === 'alert') {
                if (!window.confirm("CRITICAL: Are you sure you want to trigger a system-wide FLOOD ALERT? This will notify all agencies.")) {
                    setLoading(null);
                    setStatus({type: null, msg: ''});
                    return;
                }
            }

            const response = await fetch(`${backendUrl}${endpoints[action]}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({})
            });

            const data = await response.json();

            if (data.status === 'success') {
                setStatus({type: 'success', msg: data.message || 'Action completed successfully!'});
                
                // If it's a legal notice, trigger download of the content
                if (action === 'notice' && data.content) {
                    const blob = new Blob([data.content], { type: 'text/plain' });
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `Legal_Notice_${data.notice_id}.txt`;
                    a.click();
                    setStatus({type: 'success', msg: `Legal Notice ${data.notice_id} generated and downloaded.`});
                }
            } else {
                throw new Error(data.message || 'Action failed');
            }
        } catch (error: any) {
            setStatus({type: 'error', msg: error.message || 'Failed to connect to backend.'});
        } finally {
            setLoading(null);
            setTimeout(() => setStatus({type: null, msg: ''}), 5000);
        }
    };

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            {status.type && (
                <div style={{ 
                    padding: '1rem', 
                    borderRadius: '8px', 
                    background: status.type === 'success' ? '#dcfce7' : status.type === 'error' ? '#fee2e2' : '#dbeafe',
                    color: status.type === 'success' ? '#166534' : status.type === 'error' ? '#991b1b' : '#1e40af',
                    border: `1px solid ${status.type === 'success' ? '#bbf7d0' : status.type === 'error' ? '#fecaca' : '#bfdbfe'}`,
                    fontWeight: 500
                }}>
                    {status.type === 'info' && '⏳ '}
                    {status.type === 'success' && '✅ '}
                    {status.type === 'error' && '❌ '}
                    {status.msg}
                </div>
            )}
            
            {/* KPI Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1.5rem' }}>
                {[
                    { label: "Active Stations", value: "11/12", badge: "ONLINE", color: "success" },
                    { label: "Critical Alerts", value: "03", badge: "HIGH PRIORITY", color: "danger" },
                    { label: "Pending Reports", value: "14", badge: "NEEDS REVIEW", color: "warning" },
                    { label: "System Health", value: "98.5%", badge: "OPTIMAL", color: "success" },
                ].map((kpi, i) => (
                    <div key={i} className="card" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                        <div style={{ fontSize: '0.85rem', color: '#64748b', fontWeight: 600 }}>{kpi.label}</div>
                        <div style={{ fontSize: '2.5rem', fontWeight: 800 }}>{kpi.value}</div>
                        <span className={`badge badge-${kpi.color}`} style={{ width: 'fit-content' }}>{kpi.badge}</span>
                    </div>
                ))}
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1.2fr', gap: '2rem' }}>
                {/* Active Alerts Table */}
                <div className="card">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                        <h3>Critical Alerts</h3>
                        <button className="btn btn-secondary" style={{ fontSize: '0.8rem', padding: '0.4rem 0.8rem' }}>View All</button>
                    </div>
                    <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                        <thead>
                            <tr style={{ borderBottom: '1px solid var(--border)', color: '#64748b', fontSize: '0.8rem' }}>
                                <th style={{ padding: '0.75rem' }}>Priority</th>
                                <th style={{ padding: '0.75rem' }}>Station</th>
                                <th style={{ padding: '0.75rem' }}>Issue</th>
                                <th style={{ padding: '0.75rem' }}>Time</th>
                            </tr>
                        </thead>
                        <tbody>
                            {[
                                { p: "HIGH", s: "Assi Ghat", i: "Low Dissolved Oxygen", t: "10m ago", c: "red" },
                                { p: "MEDIUM", s: "Manikarnika", i: "High Turbidity Peaks", t: "45m ago", c: "orange" },
                                { p: "LOW", s: "Scindia", i: "Sensor Maintenance", t: "2h ago", c: "blue" },
                            ].map((a, i) => (
                                <tr key={i} style={{ borderBottom: '1px solid #f1f5f9' }}>
                                    <td style={{ padding: '0.75rem' }}><span className={`badge badge-${a.c}`}>{a.p}</span></td>
                                    <td style={{ padding: '0.75rem', fontWeight: 600 }}>{a.s}</td>
                                    <td style={{ padding: '0.75rem', fontSize: '0.9rem' }}>{a.i}</td>
                                    <td style={{ padding: '0.75rem', fontSize: '0.8rem', color: '#64748b' }}>{a.t}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>

                {/* Quick Actions */}
                <div className="card">
                    <h3>Quick Actions</h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginTop: '1.5rem' }}>
                        <button 
                            className="btn btn-primary" 
                            style={{ width: '100%', justifyContent: 'flex-start', gap: '0.75rem', opacity: loading === 'sms' ? 0.7 : 1 }}
                            onClick={() => handleAction('sms')}
                            disabled={!!loading}
                        >
                            <span>📢</span> {loading === 'sms' ? 'Sending...' : 'Send Emergency SMS'}
                        </button>
                        <button 
                            className="btn btn-secondary" 
                            style={{ width: '100%', justifyContent: 'flex-start', gap: '0.75rem', opacity: loading === 'notice' ? 0.7 : 1 }}
                            onClick={() => handleAction('notice')}
                            disabled={!!loading}
                        >
                            <span>📄</span> {loading === 'notice' ? 'Generating...' : 'Generate Legal Notice'}
                        </button>
                        <button 
                            className="btn btn-secondary" 
                            style={{ width: '100%', justifyContent: 'flex-start', gap: '0.75rem', opacity: loading === 'alert' ? 0.7 : 1 }}
                            onClick={() => handleAction('alert')}
                            disabled={!!loading}
                        >
                            <span>🌊</span> {loading === 'alert' ? 'Triggering...' : 'Trigger Flood Alert'}
                        </button>
                        <button 
                            className="btn btn-secondary" 
                            style={{ width: '100%', justifyContent: 'flex-start', gap: '0.75rem', opacity: loading === 'export' ? 0.7 : 1 }}
                            onClick={() => handleAction('export')}
                            disabled={!!loading}
                        >
                            <span>📥</span> {loading === 'export' ? 'Exporting...' : 'Export System Data'}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default CommandCenter;
