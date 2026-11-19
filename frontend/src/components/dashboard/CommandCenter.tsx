"use client";

import React, { useState, useEffect, useCallback } from "react";
import { supabase } from "@/lib/supabaseClient";
import { BACKEND_URL } from "@/lib/apiConfig";

interface StationData {
    id: string;
    station_code: string;
    station_name: string;
    location_name: string;
    status: string;
    is_online: boolean;
    warning_water_level_m?: number | null;
    danger_water_level_m?: number | null;
    latest_reading?: {
        ph?: number;
        turbidity?: number;
        water_level?: number;
        do?: number;
        temperature?: number;
        observed_at?: string;
    };
    device?: {
        runtime_status?: string;
    };
}

interface AlertItem {
    priority: 'HIGH' | 'MEDIUM' | 'LOW';
    station: string;
    issue: string;
    time: string;
    color: 'red' | 'orange' | 'blue';
}


export default function CommandCenter() {
    const [status, setStatus] = useState<{ type: 'success' | 'error' | 'info' | null, msg: string }>({ type: null, msg: '' });
    const [loading, setLoading] = useState<string | null>(null);
    const [stations, setStations] = useState<StationData[]>([]);
    const [pendingReportsCount, setPendingReportsCount] = useState<number>(0);
    const [totalReadingsCount, setTotalReadingsCount] = useState<number>(0);
    const [fetchingData, setFetchingData] = useState<boolean>(true);

    const getAuthHeaders = useCallback(async (): Promise<Record<string, string>> => {
        try {
            const { data } = await supabase.auth.getSession();
            const token = data?.session?.access_token;
            if (token) return { 'Authorization': `Bearer ${token}` };
        } catch {
            // Ignore
        }
        return {};
    }, []);

    const fetchDashboardMetrics = useCallback(async () => {
        setFetchingData(true);
        try {
            const authHeaders = await getAuthHeaders();

            // 1. Fetch Station Directory & Live Readings
            const stnRes = await fetch(`${BACKEND_URL}/api/v1/stations`);
            if (stnRes.ok) {
                const stnData = await stnRes.json();
                setStations(stnData.stations || []);
            }

            // 2. Try fetching overview or reports count
            const overviewRes = await fetch(`${BACKEND_URL}/api/v1/analytics/overview`, {
                headers: authHeaders
            });
            if (overviewRes.ok) {
                const ovData = await overviewRes.json();
                const pending = (ovData.pollution_reports?.submitted || 0) + (ovData.pollution_reports?.investigating || 0);
                setPendingReportsCount(pending);
                setTotalReadingsCount(ovData.telemetry?.total_readings || 0);
            } else {
                // Fallback: fetch reports directly if overview denied
                const repRes = await fetch(`${BACKEND_URL}/api/authority/reports`, { headers: authHeaders });
                if (repRes.ok) {
                    const repData = await repRes.json();
                    if (Array.isArray(repData)) {
                        const pending = repData.filter((r: { status?: string }) => ['pending', 'submitted', 'investigating'].includes(r.status?.toLowerCase() || '')).length;
                        setPendingReportsCount(pending);
                    }
                }
            }
        } catch (err) {
            console.error("Error fetching command center data:", err);
        } finally {
            setFetchingData(false);
        }
    }, [getAuthHeaders]);

    useEffect(() => {
        fetchDashboardMetrics();
    }, [fetchDashboardMetrics]);

    // Compute dynamic alerts based on live sensor deviations
    const criticalAlerts: AlertItem[] = React.useMemo(() => {
        const alerts: AlertItem[] = [];
        stations.forEach(stn => {
            const lr = stn.latest_reading;
            if (!lr) return;

            // Flood Stage Alert
            if (lr.water_level && stn.warning_water_level_m && lr.water_level >= stn.warning_water_level_m) {
                const isDanger = stn.danger_water_level_m && lr.water_level >= stn.danger_water_level_m;
                alerts.push({
                    priority: isDanger ? 'HIGH' : 'MEDIUM',
                    station: stn.station_name,
                    issue: isDanger ? `Danger Stage Exceeded (${lr.water_level.toFixed(2)}m MSL)` : `Warning Stage Exceeded (${lr.water_level.toFixed(2)}m MSL)`,
                    time: lr.observed_at ? new Date(lr.observed_at).toLocaleTimeString() : 'Recent',
                    color: isDanger ? 'red' : 'orange'
                });
            }

            // Dissolved Oxygen Depletion Alert
            if (lr.do !== null && lr.do !== undefined && lr.do < 5.0) {
                alerts.push({
                    priority: lr.do < 4.0 ? 'HIGH' : 'MEDIUM',
                    station: stn.station_name,
                    issue: `Low Dissolved Oxygen (${lr.do.toFixed(1)} mg/L < CPCB 5.0)`,
                    time: lr.observed_at ? new Date(lr.observed_at).toLocaleTimeString() : 'Active',
                    color: lr.do < 4.0 ? 'red' : 'orange'
                });
            }

            // Severe Turbidity Alert
            if (lr.turbidity !== null && lr.turbidity !== undefined && lr.turbidity > 50) {
                alerts.push({
                    priority: 'MEDIUM',
                    station: stn.station_name,
                    issue: `Elevated Turbidity (${lr.turbidity.toFixed(0)} NTU)`,
                    time: lr.observed_at ? new Date(lr.observed_at).toLocaleTimeString() : 'Active',
                    color: 'orange'
                });
            }
        });
        return alerts;
    }, [stations]);

    const activeStationsCount = stations.filter(s => s.status === 'active').length;
    const totalStationsCount = stations.length;
    const onlineDevicesCount = stations.filter(s => s.is_online).length;

    const handleAction = async (action: string) => {
        setLoading(action);
        setStatus({ type: 'info', msg: `Processing ${action}...` });

        try {
            const authHeaders = await getAuthHeaders();

            if (action === 'export') {
                window.location.href = `${BACKEND_URL}/api/v1/export/sensor-data`;
                setStatus({ type: 'success', msg: 'System sensor telemetry export started.' });
                setLoading(null);
                return;
            }

            if (action === 'sms') {
                setStatus({
                    type: 'info',
                    msg: 'Notice: Cellular SMS Gateway runs in simulated outbox mode. Configure carrier credentials for live telecom dispatch.'
                });
                setLoading(null);
                return;
            }

            const endpoints: Record<string, string> = {
                'notice': '/api/authority/generate-notice',
                'alert': '/api/authority/trigger-alert'
            };

            if (action === 'alert') {
                if (!window.confirm("CRITICAL: Are you sure you want to trigger a system-wide FLOOD ALERT? This will log an official alert.")) {
                    setLoading(null);
                    setStatus({ type: null, msg: '' });
                    return;
                }
            }

            const response = await fetch(`${BACKEND_URL}${endpoints[action]}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...authHeaders
                },
                body: JSON.stringify({})
            });

            const data = await response.json();

            if (data.status === 'success') {
                setStatus({ type: 'success', msg: data.message || 'Action completed successfully!' });

                if (action === 'notice' && data.content) {
                    const blob = new Blob([data.content], { type: 'text/plain' });
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = `Draft_Notice_${data.notice_id || 'Review'}.txt`;
                    a.click();
                    setStatus({ type: 'success', msg: `Draft Notice ${data.notice_id || ''} generated for authorized review.` });
                }
            } else {
                throw new Error(data.message || 'Action failed');
            }
        } catch (error: unknown) {
            const msg = error instanceof Error ? error.message : 'Failed to connect to backend.';
            setStatus({ type: 'error', msg });
        } finally {
            setLoading(null);
            setTimeout(() => setStatus({ type: null, msg: '' }), 6000);
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

            {/* Live Database-Backed KPI Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1.5rem' }}>
                <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', padding: '1.25rem' }}>
                    <div style={{ fontSize: '0.8rem', color: '#64748b', fontWeight: 600 }}>ACTIVE STATIONS</div>
                    <div style={{ fontSize: '2.2rem', fontWeight: 800, color: '#0284c7' }}>
                        {activeStationsCount}
                        <span style={{ fontSize: '1.1rem', color: '#94a3b8', fontWeight: 500 }}> / {totalStationsCount}</span>
                    </div>
                    <span className="badge badge-success" style={{ width: 'fit-content', fontSize: '0.75rem' }}>
                        {activeStationsCount} DEPLOYED IN VARANASI
                    </span>
                </div>

                <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', padding: '1.25rem' }}>
                    <div style={{ fontSize: '0.8rem', color: '#64748b', fontWeight: 600 }}>IOT NODES ONLINE</div>
                    <div style={{ fontSize: '2.2rem', fontWeight: 800, color: onlineDevicesCount > 0 ? '#10b981' : '#f59e0b' }}>
                        {onlineDevicesCount}
                        <span style={{ fontSize: '1.1rem', color: '#94a3b8', fontWeight: 500 }}> / {totalStationsCount}</span>
                    </div>
                    <span className={`badge ${onlineDevicesCount > 0 ? 'badge-success' : 'badge-warning'}`} style={{ width: 'fit-content', fontSize: '0.75rem' }}>
                        {onlineDevicesCount > 0 ? 'ESP32 STREAMING' : 'NODES SIMULATED / OFFLINE'}
                    </span>
                </div>

                <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', padding: '1.25rem' }}>
                    <div style={{ fontSize: '0.8rem', color: '#64748b', fontWeight: 600 }}>ACTIVE THRESHOLD ALERTS</div>
                    <div style={{ fontSize: '2.2rem', fontWeight: 800, color: criticalAlerts.length > 0 ? '#ef4444' : '#10b981' }}>
                        {criticalAlerts.length}
                    </div>
                    <span className={`badge ${criticalAlerts.length > 0 ? 'badge-danger' : 'badge-success'}`} style={{ width: 'fit-content', fontSize: '0.75rem' }}>
                        {criticalAlerts.length > 0 ? 'DEVIATIONS DETECTED' : 'ALL NOMINAL'}
                    </span>
                </div>

                <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', padding: '1.25rem' }}>
                    <div style={{ fontSize: '0.8rem', color: '#64748b', fontWeight: 600 }}>PENDING POLLUTION REPORTS</div>
                    <div style={{ fontSize: '2.2rem', fontWeight: 800, color: pendingReportsCount > 0 ? '#d97706' : '#10b981' }}>
                        {pendingReportsCount}
                    </div>
                    <span className="badge badge-warning" style={{ width: 'fit-content', fontSize: '0.75rem' }}>
                        AWAITING FIELD INSPECTION
                    </span>
                </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1.2fr', gap: '2rem' }}>
                {/* Active Alerts Table */}
                <div className="card">
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
                        <div>
                            <h3 style={{ margin: 0, fontWeight: 700, fontSize: '1.1rem' }}>Active Hydrological & Water Quality Alerts</h3>
                            <p style={{ margin: '0.2rem 0 0 0', fontSize: '0.8rem', color: '#64748b' }}>
                                Dynamic threshold screening from latest monitoring station observations.
                            </p>
                        </div>
                        <button onClick={fetchDashboardMetrics} disabled={fetchingData} className="btn btn-secondary" style={{ fontSize: '0.75rem', padding: '0.35rem 0.75rem' }}>
                            {fetchingData ? '⏳ Syncing...' : `🔄 Refresh (${totalReadingsCount} logs)`}
                        </button>
                    </div>

                    {criticalAlerts.length === 0 ? (
                        <div style={{ padding: '2.5rem', textAlign: 'center', color: '#166534', background: '#f0fdf4', borderRadius: '0.5rem', border: '1px solid #bbf7d0' }}>
                            <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>✅</div>
                            <div style={{ fontWeight: 700, fontSize: '1rem' }}>All Stations Operating Within CPCB / CWC Limits</div>
                            <p style={{ fontSize: '0.8rem', margin: '0.25rem 0 0 0', color: '#15803d' }}>
                                No active river stage warnings or critical dissolved oxygen depletions detected.
                            </p>
                        </div>
                    ) : (
                        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                            <thead>
                                <tr style={{ borderBottom: '1px solid #e2e8f0', color: '#64748b', fontSize: '0.8rem' }}>
                                    <th style={{ padding: '0.75rem' }}>Priority</th>
                                    <th style={{ padding: '0.75rem' }}>Station</th>
                                    <th style={{ padding: '0.75rem' }}>Issue & Condition</th>
                                    <th style={{ padding: '0.75rem' }}>Time</th>
                                </tr>
                            </thead>
                            <tbody>
                                {criticalAlerts.map((a, i) => (
                                    <tr key={i} style={{ borderBottom: '1px solid #f1f5f9' }}>
                                        <td style={{ padding: '0.75rem' }}>
                                            <span className={`badge ${a.color === 'red' ? 'badge-danger' : a.color === 'orange' ? 'badge-warning' : 'badge-blue'}`} style={{ fontSize: '0.75rem' }}>
                                                {a.priority}
                                            </span>
                                        </td>
                                        <td style={{ padding: '0.75rem', fontWeight: 600, color: '#0f172a' }}>{a.station}</td>
                                        <td style={{ padding: '0.75rem', fontSize: '0.85rem', color: '#334155' }}>{a.issue}</td>
                                        <td style={{ padding: '0.75rem', fontSize: '0.8rem', color: '#64748b' }}>{a.time}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    )}
                </div>

                {/* Quick Authority Actions */}
                <div className="card">
                    <h3 style={{ margin: '0 0 0.5rem 0', fontWeight: 700, fontSize: '1.1rem' }}>Operational Actions</h3>
                    <p style={{ margin: '0 0 1.25rem 0', fontSize: '0.8rem', color: '#64748b' }}>
                        Official authority workflows and compliance export.
                    </p>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
                        <button
                            className="btn btn-secondary"
                            style={{ width: '100%', justifyContent: 'flex-start', gap: '0.75rem', fontSize: '0.85rem', padding: '0.65rem 1rem' }}
                            onClick={() => handleAction('export')}
                            disabled={!!loading}
                        >
                            <span>📥</span> {loading === 'export' ? 'Exporting...' : 'Export Filtered Sensor CSV'}
                        </button>
                        <button
                            className="btn btn-secondary"
                            style={{ width: '100%', justifyContent: 'flex-start', gap: '0.75rem', fontSize: '0.85rem', padding: '0.65rem 1rem' }}
                            onClick={() => handleAction('notice')}
                            disabled={!!loading}
                        >
                            <span>📄</span> {loading === 'notice' ? 'Generating...' : 'Generate Draft Notice (For Review)'}
                        </button>
                        <button
                            className="btn btn-secondary"
                            style={{ width: '100%', justifyContent: 'flex-start', gap: '0.75rem', fontSize: '0.85rem', padding: '0.65rem 1rem' }}
                            onClick={() => handleAction('alert')}
                            disabled={!!loading}
                        >
                            <span>🌊</span> {loading === 'alert' ? 'Triggering...' : 'Trigger Official Flood Alert'}
                        </button>
                        <button
                            className="btn btn-secondary"
                            style={{ width: '100%', justifyContent: 'flex-start', gap: '0.75rem', fontSize: '0.85rem', padding: '0.65rem 1rem', opacity: 0.6 }}
                            onClick={() => handleAction('sms')}
                            disabled={!!loading}
                        >
                            <span>📢</span> Cellular SMS Broadcast
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
