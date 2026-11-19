"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
    PieChart, Pie, Cell, ResponsiveContainer, BarChart, Bar,
    XAxis, YAxis, CartesianGrid, Tooltip, Legend
} from "recharts";
import { supabase } from "@/lib/supabaseClient";

interface AnalyticsOverview {
    status: string;
    generated_at: string;
    stations: {
        total: number;
        active: number;
        planned: number;
        maintenance: number;
        by_status: Record<string, number>;
    };
    devices: {
        total: number;
        active_online: number;
        offline: number;
        provisioned: number;
        by_status: Record<string, number>;
    };
    telemetry: {
        total_readings: number;
        readings_last_24h: number;
        by_provenance: Record<string, number>;
        real_sensor_count: number;
        simulated_count: number;
    };
    pollution_reports: {
        total: number;
        submitted: number;
        investigating: number;
        resolved: number;
        rejected: number;
        by_status: Record<string, number>;
    };
    flood_risk: {
        latest_predictions_count: number;
        by_severity: Record<string, number>;
    };
}

interface StationItem {
    id: string;
    station_code: string;
    station_name: string;
    location_name: string;
    status: string;
    latest_reading?: {
        ph?: number;
        turbidity?: number;
        water_level?: number;
        do?: number;
    };
}

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:5000';

const LIFECYCLE_COLORS: Record<string, string> = {
    active: '#10b981',
    installed: '#0284c7',
    planned: '#f59e0b',
    maintenance: '#ef4444',
    decommissioned: '#64748b'
};

const REPORT_STATUS_COLORS: Record<string, string> = {
    submitted: '#f59e0b',
    investigating: '#3b82f6',
    resolved: '#10b981',
    rejected: '#64748b'
};

export default function AuthorityAnalytics() {
    const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
    const [stations, setStations] = useState<StationItem[]>([]);
    const [loading, setLoading] = useState<boolean>(true);
    const [authError, setAuthError] = useState<string | null>(null);

    const getAuthHeaders = useCallback(async (): Promise<Record<string, string>> => {
        try {
            const { data } = await supabase.auth.getSession();
            const token = data?.session?.access_token;
            if (token) {
                return { 'Authorization': `Bearer ${token}` };
            }
        } catch {
            // Ignore session retrieval error
        }
        return {};
    }, []);

    const fetchAnalyticsData = useCallback(async () => {
        setLoading(true);
        setAuthError(null);
        try {
            const authHeaders = await getAuthHeaders();

            // 1. Fetch Overview (RBAC Protected)
            const overviewRes = await fetch(`${BACKEND_URL}/api/v1/analytics/overview`, {
                headers: authHeaders
            });

            if (overviewRes.status === 401 || overviewRes.status === 403) {
                const errJson = await overviewRes.json().catch(() => ({}));
                setAuthError(errJson.message || "Authority authorization required to view live system analytics.");
                setLoading(false);
                return;
            }

            if (!overviewRes.ok) {
                throw new Error(`HTTP ${overviewRes.status}: Failed to fetch analytics overview`);
            }

            const overviewData: AnalyticsOverview = await overviewRes.json();
            setOverview(overviewData);

            // 2. Fetch Station Telemetry for Cross-Station Comparisons
            const stnRes = await fetch(`${BACKEND_URL}/api/v1/stations`);
            if (stnRes.ok) {
                const stnData = await stnRes.json();
                setStations(stnData.stations || []);
            }
        } catch (err: unknown) {
            console.error("Error fetching authority analytics:", err);
            const msg = err instanceof Error ? err.message : "Failed to load authority analytics.";
            setAuthError(msg);
        } finally {
            setLoading(false);
        }
    }, [getAuthHeaders]);

    useEffect(() => {
        fetchAnalyticsData();
    }, [fetchAnalyticsData]);

    // Format Station Status Distribution for Pie Chart
    const stationPieData = React.useMemo(() => {
        if (!overview?.stations?.by_status) return [];
        return Object.entries(overview.stations.by_status).map(([key, val]) => ({
            name: key.charAt(0).toUpperCase() + key.slice(1),
            value: val,
            color: LIFECYCLE_COLORS[key] || '#94a3b8'
        }));
    }, [overview]);

    // Format Pollution Report Status for Bar Chart
    const reportBarData = React.useMemo(() => {
        if (!overview?.pollution_reports?.by_status) return [];
        return Object.entries(overview.pollution_reports.by_status).map(([key, val]) => ({
            status: key.charAt(0).toUpperCase() + key.slice(1),
            count: val,
            fill: REPORT_STATUS_COLORS[key] || '#0284c7'
        }));
    }, [overview]);

    // Format Station Telemetry (pH vs Turbidity) from live station readings
    const stationTelemetryData = React.useMemo(() => {
        return stations
            .filter(s => s.latest_reading && (s.latest_reading.ph !== null || s.latest_reading.turbidity !== null))
            .map(s => ({
                name: s.location_name ? s.location_name.split(',')[0] : s.station_name,
                ph: s.latest_reading?.ph ?? 0,
                turbidity: s.latest_reading?.turbidity ?? 0,
                water_level: s.latest_reading?.water_level ?? 0
            }));
    }, [stations]);

    if (loading) {
        return (
            <div className="card" style={{ padding: '3rem', textAlign: 'center', color: '#64748b' }}>
                <div style={{ fontSize: '2rem', marginBottom: '0.75rem' }}>⏳</div>
                <div style={{ fontWeight: 600 }}>Loading Authority System Analytics from Supabase PostgreSQL...</div>
            </div>
        );
    }

    if (authError) {
        return (
            <div className="card" style={{ padding: '2.5rem', textAlign: 'center', background: '#f8fafc', border: '1px solid #e2e8f0' }}>
                <div style={{ fontSize: '2.5rem', marginBottom: '0.75rem' }}>🔒</div>
                <h3 style={{ color: '#0f172a', fontWeight: 700, margin: '0 0 0.5rem 0' }}>
                    Authority Authentication Required
                </h3>
                <p style={{ maxWidth: '500px', margin: '0 auto 1.5rem auto', color: '#64748b', fontSize: '0.9rem', lineHeight: 1.5 }}>
                    {authError}
                    <br /><br />
                    System-wide analytics aggregations contain operational telemetry counts, hardware inventory status, and official pollution report audit trails restricted to UPPCB Authority Administrators and Field Officers.
                </p>
                <div style={{ display: 'flex', justifyContent: 'center', gap: '1rem' }}>
                    <a href="/login" className="btn btn-primary" style={{ padding: '0.5rem 1.25rem' }}>
                        Log In with Authority Account
                    </a>
                    <button onClick={fetchAnalyticsData} className="btn btn-secondary" style={{ padding: '0.5rem 1.25rem' }}>
                        Retry
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            {/* Header & Controls */}
            <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '1rem' }}>
                <div>
                    <h3 style={{ margin: 0, fontWeight: 700 }}>UPPCB & CWC Operational Analytics Overview</h3>
                    <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.85rem', color: '#64748b' }}>
                        Live PostgreSQL aggregations across monitoring stations, IoT hardware nodes, and citizen reports.
                    </p>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <span style={{ fontSize: '0.75rem', color: '#64748b' }}>
                        Updated: {overview?.generated_at ? new Date(overview.generated_at).toLocaleTimeString() : 'Just now'}
                    </span>
                    <button onClick={fetchAnalyticsData} className="btn btn-secondary" style={{ fontSize: '0.85rem', padding: '0.4rem 0.8rem' }}>
                        🔄 Refresh
                    </button>
                </div>
            </div>

            {/* Key Operational KPI Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1.25rem' }}>
                <div className="card" style={{ padding: '1.25rem' }}>
                    <div style={{ fontSize: '0.8rem', color: '#64748b', fontWeight: 600 }}>MONITORING STATIONS</div>
                    <div style={{ fontSize: '2rem', fontWeight: 800, margin: '0.25rem 0', color: '#0284c7' }}>
                        {overview?.stations.total || 0}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: '#10b981', fontWeight: 600 }}>
                        {overview?.stations.active || 0} Active / {overview?.stations.planned || 0} Planned
                    </div>
                </div>

                <div className="card" style={{ padding: '1.25rem' }}>
                    <div style={{ fontSize: '0.8rem', color: '#64748b', fontWeight: 600 }}>IOT HARDWARE NODES</div>
                    <div style={{ fontSize: '2rem', fontWeight: 800, margin: '0.25rem 0', color: '#10b981' }}>
                        {overview?.devices.active_online || 0}
                        <span style={{ fontSize: '1rem', fontWeight: 500, color: '#64748b' }}> / {overview?.devices.total || 0}</span>
                    </div>
                    <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
                        {overview?.devices.offline || 0} Offline / {overview?.devices.provisioned || 0} Provisioned
                    </div>
                </div>

                <div className="card" style={{ padding: '1.25rem' }}>
                    <div style={{ fontSize: '0.8rem', color: '#64748b', fontWeight: 600 }}>TELEMETRY OBSERVATIONS</div>
                    <div style={{ fontSize: '2rem', fontWeight: 800, margin: '0.25rem 0', color: '#059669' }}>
                        {overview?.telemetry.total_readings || 0}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
                        {overview?.telemetry.real_sensor_count || 0} Hardware / {overview?.telemetry.simulated_count || 0} Simulated
                    </div>
                </div>

                <div className="card" style={{ padding: '1.25rem' }}>
                    <div style={{ fontSize: '0.8rem', color: '#64748b', fontWeight: 600 }}>POLLUTION INCIDENTS</div>
                    <div style={{ fontSize: '2rem', fontWeight: 800, margin: '0.25rem 0', color: '#d97706' }}>
                        {overview?.pollution_reports.total || 0}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: '#10b981', fontWeight: 600 }}>
                        {overview?.pollution_reports.resolved || 0} Resolved ({overview?.pollution_reports.investigating || 0} Investigating)
                    </div>
                </div>
            </div>

            {/* Visual Analytics Charts Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '1.75rem' }}>
                {/* Station Lifecycle Distribution */}
                <div className="card" style={{ padding: '1.5rem' }}>
                    <h4 style={{ margin: '0 0 1rem 0', fontWeight: 700, fontSize: '0.95rem', color: '#0f172a' }}>
                        Station Lifecycle Distribution
                    </h4>
                    <div style={{ height: '280px' }}>
                        {stationPieData.length > 0 ? (
                            <ResponsiveContainer width="100%" height="100%">
                                <PieChart>
                                    <Pie
                                        data={stationPieData}
                                        innerRadius={65}
                                        outerRadius={85}
                                        paddingAngle={5}
                                        dataKey="value"
                                    >
                                        {stationPieData.map((entry, index) => (
                                            <Cell key={`cell-${index}`} fill={entry.color} />
                                        ))}
                                    </Pie>
                                    <Tooltip />
                                    <Legend verticalAlign="bottom" height={36} />
                                </PieChart>
                            </ResponsiveContainer>
                        ) : (
                            <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#64748b' }}>
                                No station records found
                            </div>
                        )}
                    </div>
                </div>

                {/* Pollution Incident Resolution Status */}
                <div className="card" style={{ padding: '1.5rem' }}>
                    <h4 style={{ margin: '0 0 1rem 0', fontWeight: 700, fontSize: '0.95rem', color: '#0f172a' }}>
                        Citizen Pollution Reports by Status
                    </h4>
                    <div style={{ height: '280px' }}>
                        {reportBarData.length > 0 ? (
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={reportBarData} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
                                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                                    <XAxis dataKey="status" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#64748b' }} />
                                    <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#64748b' }} allowDecimals={false} />
                                    <Tooltip />
                                    <Bar dataKey="count" name="Reports" radius={[4, 4, 0, 0]}>
                                        {reportBarData.map((entry, index) => (
                                            <Cell key={`cell-bar-${index}`} fill={entry.fill} />
                                        ))}
                                    </Bar>
                                </BarChart>
                            </ResponsiveContainer>
                        ) : (
                            <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#64748b' }}>
                                No pollution reports lodged
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Station Water Quality Comparison Bar Chart */}
            <div className="card" style={{ padding: '1.5rem' }}>
                <h4 style={{ margin: '0 0 0.5rem 0', fontWeight: 700, fontSize: '0.95rem', color: '#0f172a' }}>
                    Latest Water Quality Telemetry Comparison by Ghat
                </h4>
                <p style={{ margin: '0 0 1.25rem 0', fontSize: '0.8rem', color: '#64748b' }}>
                    Comparing current pH (CPCB standard 6.5–8.5) and Turbidity (NTU) across stations with logged telemetry.
                </p>
                <div style={{ height: '320px' }}>
                    {stationTelemetryData.length > 0 ? (
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={stationTelemetryData} margin={{ top: 10, right: 20, left: -10, bottom: 20 }}>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                                <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#64748b' }} />
                                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#64748b' }} />
                                <Tooltip />
                                <Legend verticalAlign="top" height={36} />
                                <Bar dataKey="ph" name="pH Level (Units)" fill="#0284c7" radius={[4, 4, 0, 0]} />
                                <Bar dataKey="turbidity" name="Turbidity (NTU)" fill="#d97706" radius={[4, 4, 0, 0]} />
                            </BarChart>
                        </ResponsiveContainer>
                    ) : (
                        <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#64748b' }}>
                            No live station readings available for comparison
                        </div>
                    )}
                </div>
            </div>

            {/* Flood Risk & Hydrological Status Summary */}
            <div className="card" style={{ background: '#f8fafc', border: '1px solid #e2e8f0', padding: '1.25rem' }}>
                <h4 style={{ color: '#0f172a', margin: '0 0 0.75rem 0', fontWeight: 700, fontSize: '0.9rem' }}>
                    🌊 CWC Hydrological Alert Status & Flood Screening
                </h4>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '1rem', textAlign: 'center' }}>
                    <div style={{ padding: '0.75rem', borderRadius: '0.5rem', background: '#dcfce7', border: '1px solid #86efac' }}>
                        <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#15803d' }}>LOW RISK</div>
                        <div style={{ fontSize: '1.5rem', fontWeight: 800, color: '#15803d', marginTop: '0.25rem' }}>
                            {overview?.flood_risk.by_severity['LOW'] || 0}
                        </div>
                        <div style={{ fontSize: '0.7rem', color: '#166534' }}>Safe River Stage</div>
                    </div>

                    <div style={{ padding: '0.75rem', borderRadius: '0.5rem', background: '#fef9c3', border: '1px solid #fde047' }}>
                        <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#854d0e' }}>MODERATE RISK</div>
                        <div style={{ fontSize: '1.5rem', fontWeight: 800, color: '#854d0e', marginTop: '0.25rem' }}>
                            {overview?.flood_risk.by_severity['MODERATE'] || 0}
                        </div>
                        <div style={{ fontSize: '0.7rem', color: '#713f12' }}>Approaching Warning</div>
                    </div>

                    <div style={{ padding: '0.75rem', borderRadius: '0.5rem', background: '#ffedd5', border: '1px solid #fdba74' }}>
                        <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#c2410c' }}>HIGH RISK</div>
                        <div style={{ fontSize: '1.5rem', fontWeight: 800, color: '#c2410c', marginTop: '0.25rem' }}>
                            {overview?.flood_risk.by_severity['HIGH'] || 0}
                        </div>
                        <div style={{ fontSize: '0.7rem', color: '#9a3412' }}>Above Warning (70.26m)</div>
                    </div>

                    <div style={{ padding: '0.75rem', borderRadius: '0.5rem', background: '#fee2e2', border: '1px solid #fca5a5' }}>
                        <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#b91c1c' }}>CRITICAL RISK</div>
                        <div style={{ fontSize: '1.5rem', fontWeight: 800, color: '#b91c1c', marginTop: '0.25rem' }}>
                            {overview?.flood_risk.by_severity['CRITICAL'] || 0}
                        </div>
                        <div style={{ fontSize: '0.7rem', color: '#991b1b' }}>Danger Stage (71.26m)</div>
                    </div>
                </div>
            </div>
        </div>
    );
}
