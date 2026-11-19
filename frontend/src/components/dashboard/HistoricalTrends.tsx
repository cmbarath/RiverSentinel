"use client";

import React, { useState, useEffect, useMemo } from "react";
import { BACKEND_URL } from "@/lib/apiConfig";
import {
    AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
    LineChart, Line, Legend, ReferenceLine
} from "recharts";

interface Station {
    id: string;
    station_code: string;
    station_name: string;
    location_name: string;
    status: string;
    is_online: boolean;
    warning_water_level_m?: number | null;
    danger_water_level_m?: number | null;
}

interface ReadingItem {
    id: number;
    timestamp: string;
    ph: number | null;
    turbidity: number | null;
    temperature: number | null;
    humidity: number | null;
    ec: number | null;
    water_level: number | null;
    do: number | null;
    provenance: string;
    quality_status: string;
}

interface StatSummary {
    min: number;
    max: number;
    avg: number;
}

interface ReadingsResponse {
    status: string;
    station_id: string;
    station_code: string;
    station_name: string;
    timeframe: string;
    count: number;
    readings: ReadingItem[];
    summary_statistics: {
        count: number;
        ph?: StatSummary;
        turbidity?: StatSummary;
        temperature?: StatSummary;
        water_level?: StatSummary;
        ec?: StatSummary;
        do?: StatSummary;
        [key: string]: StatSummary | number | undefined;
    };
    provenance_breakdown: {
        real_sensor?: number;
        simulated?: number;
        default?: number;
    };
}


const PARAMETERS = [
    { key: "all", label: "Overview (All Key Parameters)", unit: "" },
    { key: "ph", label: "pH Level", unit: "pH", minSafe: 6.5, maxSafe: 8.5 },
    { key: "turbidity", label: "Turbidity", unit: "NTU", maxSafe: 10 },
    { key: "temperature", label: "Water Temperature", unit: "°C" },
    { key: "water_level", label: "River Stage / Level", unit: "m MSL", warningLevel: 70.26, dangerLevel: 71.26 },
    { key: "ec", label: "Electrical Conductivity", unit: "µS/cm" },
    { key: "do", label: "Dissolved Oxygen (DO)", unit: "mg/L", minSafe: 5.0 },
];

export default function HistoricalTrends() {
    const [stations, setStations] = useState<Station[]>([]);
    const [selectedStationId, setSelectedStationId] = useState<string>("");
    const [selectedParam, setSelectedParam] = useState<string>("all");
    const [timeframe, setTimeframe] = useState<string>("24h");
    const [readingsData, setReadingsData] = useState<ReadingsResponse | null>(null);
    const [loadingStations, setLoadingStations] = useState<boolean>(true);
    const [loadingReadings, setLoadingReadings] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);

    // 1. Fetch Station Directory
    useEffect(() => {
        let isMounted = true;
        async function fetchStations() {
            setLoadingStations(true);
            try {
                const res = await fetch(`${BACKEND_URL}/api/v1/stations`);
                if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch stations`);
                const data = await res.json();
                if (isMounted && data.stations && data.stations.length > 0) {
                    setStations(data.stations);
                    // Select first active station or first in list
                    const activeStn = data.stations.find((s: Station) => s.status === 'active') || data.stations[0];
                    setSelectedStationId(activeStn.id);
                }
            } catch (err: unknown) {
                console.error("Error loading stations:", err);
                if (isMounted) setError("Failed to load station directory from backend.");
            } finally {
                if (isMounted) setLoadingStations(false);
            }
        }
        fetchStations();
        return () => { isMounted = false; };
    }, []);

    // 2. Fetch Historical Readings when station, timeframe, or param changes
    useEffect(() => {
        if (!selectedStationId) return;

        let isMounted = true;
        async function fetchReadings() {
            setLoadingReadings(true);
            setError(null);
            try {
                const url = `${BACKEND_URL}/api/v1/stations/${selectedStationId}/readings?timeframe=${timeframe}&parameter=${selectedParam}&limit=500`;
                const res = await fetch(url);
                if (!res.ok) {
                    const errData = await res.json().catch(() => ({}));
                    throw new Error(errData.message || `HTTP ${res.status}: Failed to fetch readings`);
                }
                const data: ReadingsResponse = await res.json();
                if (isMounted) {
                    setReadingsData(data);
                }
            } catch (err: unknown) {
                console.error("Error loading readings:", err);
                if (isMounted) {
                    const msg = err instanceof Error ? err.message : "Failed to load telemetry data.";
                    setError(msg);
                    setReadingsData(null);
                }
            } finally {
                if (isMounted) setLoadingReadings(false);
            }
        }
        fetchReadings();
        return () => { isMounted = false; };
    }, [selectedStationId, selectedParam, timeframe]);

    // Format chart points
    const chartData = useMemo(() => {
        if (!readingsData || !readingsData.readings || readingsData.readings.length === 0) return [];
        return readingsData.readings.map((r) => {
            const date = new Date(r.timestamp);
            const timeLabel = timeframe === '24h'
                ? date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false })
                : `${date.getMonth() + 1}/${date.getDate()} ${date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false })}`;

            return {
                timestamp: r.timestamp,
                timeLabel,
                ph: r.ph,
                turbidity: r.turbidity,
                temperature: r.temperature,
                water_level: r.water_level,
                ec: r.ec,
                do: r.do,
                provenance: r.provenance,
                quality_status: r.quality_status,
                is_real: r.provenance === 'real_sensor'
            };
        });
    }, [readingsData, timeframe]);

    const currentStation = stations.find(s => s.id === selectedStationId);
    const stats = readingsData?.summary_statistics;
    const paramStat = stats && selectedParam in stats ? (stats[selectedParam] as StatSummary | undefined) : undefined;
    const provenanceCounts = readingsData?.provenance_breakdown;

    const handleExportCSV = () => {
        if (!selectedStationId) return;
        window.location.href = `${BACKEND_URL}/api/v1/export/sensor-data?station_id=${selectedStationId}&timeframe=${timeframe}&parameter=${selectedParam}`;
    };

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.75rem' }}>
            {/* Header & Controls Bar */}
            <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '1rem' }}>
                <div>
                    <h3 style={{ margin: 0, fontWeight: 700 }}>Water Quality & Hydrological Historical Trends</h3>
                    <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.85rem', color: '#64748b' }}>
                        Database-verified sensor telemetry across Ganga River monitoring stations in Varanasi.
                    </p>
                </div>

                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', alignItems: 'center' }}>
                    {/* Station Selector */}
                    <div style={{ display: 'flex', flexDirection: 'column' }}>
                        <label style={{ fontSize: '0.75rem', fontWeight: 600, color: '#475569', marginBottom: '0.25rem' }}>Station</label>
                        <select
                            value={selectedStationId}
                            onChange={(e) => setSelectedStationId(e.target.value)}
                            disabled={loadingStations || stations.length === 0}
                            style={{ padding: '0.45rem 0.75rem', borderRadius: '0.5rem', border: '1px solid #cbd5e1', fontSize: '0.875rem', background: '#fff', fontWeight: 500 }}
                        >
                            {stations.map(stn => (
                                <option key={stn.id} value={stn.id}>
                                    {stn.station_name} ({stn.station_code}) - {stn.status.toUpperCase()}
                                </option>
                            ))}
                        </select>
                    </div>

                    {/* Parameter Selector */}
                    <div style={{ display: 'flex', flexDirection: 'column' }}>
                        <label style={{ fontSize: '0.75rem', fontWeight: 600, color: '#475569', marginBottom: '0.25rem' }}>Parameter</label>
                        <select
                            value={selectedParam}
                            onChange={(e) => setSelectedParam(e.target.value)}
                            style={{ padding: '0.45rem 0.75rem', borderRadius: '0.5rem', border: '1px solid #cbd5e1', fontSize: '0.875rem', background: '#fff', fontWeight: 500 }}
                        >
                            {PARAMETERS.map(p => (
                                <option key={p.key} value={p.key}>
                                    {p.label} {p.unit ? `(${p.unit})` : ''}
                                </option>
                            ))}
                        </select>
                    </div>

                    {/* Timeframe Selector */}
                    <div style={{ display: 'flex', flexDirection: 'column' }}>
                        <label style={{ fontSize: '0.75rem', fontWeight: 600, color: '#475569', marginBottom: '0.25rem' }}>Timeframe</label>
                        <select
                            value={timeframe}
                            onChange={(e) => setTimeframe(e.target.value)}
                            style={{ padding: '0.45rem 0.75rem', borderRadius: '0.5rem', border: '1px solid #cbd5e1', fontSize: '0.875rem', background: '#fff', fontWeight: 500 }}
                        >
                            <option value="24h">Last 24 Hours</option>
                            <option value="7d">Last 7 Days</option>
                            <option value="30d">Last 30 Days</option>
                        </select>
                    </div>

                    {/* Export Button */}
                    <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'flex-end' }}>
                        <label style={{ fontSize: '0.75rem', opacity: 0, marginBottom: '0.25rem' }}>Action</label>
                        <button
                            onClick={handleExportCSV}
                            disabled={!selectedStationId || loadingReadings || (readingsData?.count || 0) === 0}
                            className="btn btn-secondary"
                            style={{ fontSize: '0.85rem', padding: '0.45rem 0.9rem', display: 'flex', alignItems: 'center', gap: '0.35rem' }}
                        >
                            📥 Export CSV
                        </button>
                    </div>
                </div>
            </div>

            {/* Station Status & Provenance Bar */}
            {currentStation && (
                <div style={{
                    display: 'flex',
                    flexWrap: 'wrap',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '0.75rem 1rem',
                    borderRadius: '0.5rem',
                    background: '#f8fafc',
                    border: '1px solid #e2e8f0',
                    fontSize: '0.85rem'
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <span style={{ fontWeight: 600, color: '#1e293b' }}>
                            📍 {currentStation.location_name}
                        </span>
                        <span style={{
                            padding: '0.2rem 0.5rem',
                            borderRadius: '9999px',
                            fontSize: '0.75rem',
                            fontWeight: 700,
                            background: currentStation.status === 'active' ? '#dcfce7' : '#fef9c3',
                            color: currentStation.status === 'active' ? '#15803d' : '#854d0e',
                            border: `1px solid ${currentStation.status === 'active' ? '#86efac' : '#fde047'}`
                        }}>
                            Lifecycle: {currentStation.status.toUpperCase()}
                        </span>
                        <span style={{
                            padding: '0.2rem 0.5rem',
                            borderRadius: '9999px',
                            fontSize: '0.75rem',
                            fontWeight: 600,
                            background: currentStation.is_online ? '#eff6ff' : '#f1f5f9',
                            color: currentStation.is_online ? '#1d4ed8' : '#64748b'
                        }}>
                            Hardware: {currentStation.is_online ? 'ONLINE' : 'OFFLINE / UNCONNECTED'}
                        </span>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', color: '#64748b' }}>
                        <span>
                            Total Observations: <strong style={{ color: '#0f172a' }}>{readingsData?.count || 0}</strong>
                        </span>
                        <span>
                            Real Hardware: <strong style={{ color: '#15803d' }}>{provenanceCounts?.real_sensor || 0}</strong>
                        </span>
                        <span>
                            Simulated: <strong style={{ color: '#b45309' }}>{provenanceCounts?.simulated || 0}</strong>
                        </span>
                    </div>
                </div>
            )}

            {/* Error Message */}
            {error && (
                <div style={{ padding: '1rem', borderRadius: '0.5rem', background: '#fef2f2', border: '1px solid #fecaca', color: '#b91c1c', fontSize: '0.9rem' }}>
                    ⚠️ {error}
                </div>
            )}

            {/* Main Time-Series Chart */}
            <div className="card" style={{ height: '420px', width: '100%', padding: '1.5rem 1rem 1rem 0', position: 'relative' }}>
                {loadingReadings && (
                    <div style={{
                        position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
                        background: 'rgba(255,255,255,0.7)', display: 'flex', alignItems: 'center',
                        justifyContent: 'center', zIndex: 10, fontSize: '0.95rem', fontWeight: 600, color: '#475569'
                    }}>
                        ⏳ Querying database time-series...
                    </div>
                )}

                {chartData.length === 0 && !loadingReadings ? (
                    <div style={{
                        height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center',
                        justifyContent: 'center', color: '#64748b', padding: '2rem', textAlign: 'center'
                    }}>
                        <div style={{ fontSize: '2.5rem', marginBottom: '0.5rem' }}>📊</div>
                        <div style={{ fontWeight: 700, fontSize: '1.1rem', color: '#334155' }}>
                            No Telemetry Records Found
                        </div>
                        <p style={{ maxWidth: '420px', fontSize: '0.85rem', margin: '0.5rem 0 0 0' }}>
                            {currentStation?.status === 'planned'
                                ? `Station "${currentStation.station_name}" is currently in PLANNED status. Physical sensor nodes have not yet been deployed or simulated for this location.`
                                : `No observations were logged for ${currentStation?.station_name || 'this station'} during the selected ${timeframe} timeframe.`}
                        </p>
                    </div>
                ) : (
                    <ResponsiveContainer width="100%" height="100%">
                        {selectedParam === 'all' ? (
                            <LineChart data={chartData} margin={{ top: 10, right: 30, left: 10, bottom: 0 }}>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                                <XAxis dataKey="timeLabel" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#64748b' }} />
                                <YAxis yAxisId="left" orientation="left" stroke="#0284c7" tick={{ fontSize: 11 }} />
                                <YAxis yAxisId="right" orientation="right" stroke="#d97706" tick={{ fontSize: 11 }} />
                                <Tooltip
                                    content={({ active, payload, label }) => {
                                        if (active && payload && payload.length) {
                                            const dataPt = payload[0].payload;
                                            return (
                                                <div style={{ background: '#fff', padding: '0.75rem 1rem', borderRadius: '0.5rem', border: '1px solid #cbd5e1', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' }}>
                                                    <div style={{ fontWeight: 700, fontSize: '0.85rem', marginBottom: '0.35rem', color: '#0f172a' }}>
                                                        {label} ({new Date(dataPt.timestamp).toLocaleTimeString()})
                                                    </div>
                                                    <div style={{ fontSize: '0.8rem', color: '#0284c7' }}>pH: <strong>{dataPt.ph ?? 'N/A'}</strong></div>
                                                    <div style={{ fontSize: '0.8rem', color: '#d97706' }}>Turbidity: <strong>{dataPt.turbidity ?? 'N/A'} NTU</strong></div>
                                                    <div style={{ fontSize: '0.8rem', color: '#059669' }}>DO: <strong>{dataPt.do ?? 'N/A'} mg/L</strong></div>
                                                    <div style={{ fontSize: '0.8rem', color: '#6366f1' }}>Temp: <strong>{dataPt.temperature ?? 'N/A'} °C</strong></div>
                                                    <div style={{ fontSize: '0.8rem', color: '#64748b' }}>Stage: <strong>{dataPt.water_level ?? 'N/A'} m</strong></div>
                                                    <div style={{ marginTop: '0.5rem', paddingTop: '0.35rem', borderTop: '1px solid #f1f5f9', fontSize: '0.75rem' }}>
                                                        <span style={{ color: dataPt.is_real ? '#15803d' : '#b45309', fontWeight: 600 }}>
                                                            {dataPt.is_real ? '🟢 Real ESP32 Sensor' : '🟡 Simulated Sensor Stream'}
                                                        </span>
                                                    </div>
                                                </div>
                                            );
                                        }
                                        return null;
                                    }}
                                />
                                <Legend verticalAlign="top" height={36} />
                                <Line yAxisId="left" type="monotone" dataKey="ph" name="pH (pH units)" stroke="#0284c7" strokeWidth={2.5} dot={false} />
                                <Line yAxisId="right" type="monotone" dataKey="turbidity" name="Turbidity (NTU)" stroke="#d97706" strokeWidth={2} dot={false} />
                                <Line yAxisId="left" type="monotone" dataKey="do" name="Dissolved Oxygen (mg/L)" stroke="#059669" strokeWidth={2} dot={false} />
                                <Line yAxisId="left" type="monotone" dataKey="temperature" name="Temp (°C)" stroke="#8b5cf6" strokeWidth={1.5} dot={false} strokeDasharray="4 4" />
                            </LineChart>
                        ) : (
                            <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 10, bottom: 0 }}>
                                <defs>
                                    <linearGradient id="paramGradient" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#0284c7" stopOpacity={0.35} />
                                        <stop offset="95%" stopColor="#0284c7" stopOpacity={0.0} />
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                                <XAxis dataKey="timeLabel" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#64748b' }} />
                                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#64748b' }} domain={['auto', 'auto']} />
                                <Tooltip
                                    content={({ active, payload, label }) => {
                                        if (active && payload && payload.length) {
                                            const dataPt = payload[0].payload;
                                            const val = dataPt[selectedParam];
                                            const paramDef = PARAMETERS.find(p => p.key === selectedParam);
                                            return (
                                                <div style={{ background: '#fff', padding: '0.75rem 1rem', borderRadius: '0.5rem', border: '1px solid #cbd5e1', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' }}>
                                                    <div style={{ fontWeight: 700, fontSize: '0.85rem', marginBottom: '0.35rem', color: '#0f172a' }}>
                                                        {label}
                                                    </div>
                                                    <div style={{ fontSize: '0.9rem', color: '#0284c7', fontWeight: 700 }}>
                                                        {paramDef?.label}: {val !== null ? `${val} ${paramDef?.unit}` : 'Missing / Invalid'}
                                                    </div>
                                                    <div style={{ marginTop: '0.4rem', fontSize: '0.75rem', color: dataPt.is_real ? '#15803d' : '#b45309', fontWeight: 600 }}>
                                                        {dataPt.is_real ? '🟢 Real ESP32 Sensor' : '🟡 Simulated Sensor Stream'} ({dataPt.quality_status})
                                                    </div>
                                                </div>
                                            );
                                        }
                                        return null;
                                    }}
                                />
                                {selectedParam === 'ph' && (
                                    <>
                                        <ReferenceLine y={6.5} stroke="#10b981" strokeDasharray="3 3" label={{ value: "CPCB Min (6.5)", fill: "#10b981", fontSize: 10 }} />
                                        <ReferenceLine y={8.5} stroke="#10b981" strokeDasharray="3 3" label={{ value: "CPCB Max (8.5)", fill: "#10b981", fontSize: 10 }} />
                                    </>
                                )}
                                {selectedParam === 'do' && (
                                    <ReferenceLine y={5.0} stroke="#10b981" strokeDasharray="3 3" label={{ value: "CPCB Bathing Min (5.0 mg/L)", fill: "#10b981", fontSize: 10 }} />
                                )}
                                {selectedParam === 'water_level' && (
                                    <>
                                        <ReferenceLine y={70.26} stroke="#f59e0b" strokeDasharray="4 4" label={{ value: "CWC Warning (70.26m)", fill: "#f59e0b", fontSize: 10 }} />
                                        <ReferenceLine y={71.26} stroke="#ef4444" strokeDasharray="4 4" label={{ value: "CWC Danger (71.26m)", fill: "#ef4444", fontSize: 10 }} />
                                    </>
                                )}
                                <Area
                                    type="monotone"
                                    dataKey={selectedParam}
                                    stroke="#0284c7"
                                    strokeWidth={3}
                                    fillOpacity={1}
                                    fill="url(#paramGradient)"
                                />
                            </AreaChart>
                        )}
                    </ResponsiveContainer>
                )}
            </div>

            {/* Dynamic Summary Metric Cards */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: '1.25rem' }}>
                {selectedParam === 'all' ? (
                    <>
                        <div className="card" style={{ textAlign: 'center', padding: '1.25rem' }}>
                            <div style={{ fontSize: '0.8rem', color: '#64748b', fontWeight: 600 }}>pH (Avg / Range)</div>
                            <div style={{ fontSize: '1.6rem', fontWeight: 800, margin: '0.25rem 0', color: '#0284c7' }}>
                                {stats?.ph ? stats.ph.avg.toFixed(2) : '—'}
                            </div>
                            <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
                                {stats?.ph ? `Min: ${stats.ph.min.toFixed(2)} | Max: ${stats.ph.max.toFixed(2)}` : 'No valid readings'}
                            </div>
                        </div>

                        <div className="card" style={{ textAlign: 'center', padding: '1.25rem' }}>
                            <div style={{ fontSize: '0.8rem', color: '#64748b', fontWeight: 600 }}>Turbidity (Avg / Range)</div>
                            <div style={{ fontSize: '1.6rem', fontWeight: 800, margin: '0.25rem 0', color: '#d97706' }}>
                                {stats?.turbidity ? `${stats.turbidity.avg.toFixed(1)} NTU` : '—'}
                            </div>
                            <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
                                {stats?.turbidity ? `Min: ${stats.turbidity.min.toFixed(1)} | Max: ${stats.turbidity.max.toFixed(1)}` : 'No valid readings'}
                            </div>
                        </div>

                        <div className="card" style={{ textAlign: 'center', padding: '1.25rem' }}>
                            <div style={{ fontSize: '0.8rem', color: '#64748b', fontWeight: 600 }}>Dissolved Oxygen (Avg / Range)</div>
                            <div style={{ fontSize: '1.6rem', fontWeight: 800, margin: '0.25rem 0', color: '#059669' }}>
                                {stats?.do ? `${stats.do.avg.toFixed(1)} mg/L` : '—'}
                            </div>
                            <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
                                {stats?.do ? `Min: ${stats.do.min.toFixed(1)} | Max: ${stats.do.max.toFixed(1)}` : 'No valid readings'}
                            </div>
                        </div>

                        <div className="card" style={{ textAlign: 'center', padding: '1.25rem' }}>
                            <div style={{ fontSize: '0.8rem', color: '#64748b', fontWeight: 600 }}>Water Temp (Avg / Range)</div>
                            <div style={{ fontSize: '1.6rem', fontWeight: 800, margin: '0.25rem 0', color: '#8b5cf6' }}>
                                {stats?.temperature ? `${stats.temperature.avg.toFixed(1)} °C` : '—'}
                            </div>
                            <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
                                {stats?.temperature ? `Min: ${stats.temperature.min.toFixed(1)} | Max: ${stats.temperature.max.toFixed(1)}` : 'No valid readings'}
                            </div>
                        </div>
                    </>
                ) : (
                    <>
                        <div className="card" style={{ textAlign: 'center', padding: '1.25rem' }}>
                            <div style={{ fontSize: '0.8rem', color: '#64748b', fontWeight: 600 }}>Parameter Average</div>
                            <div style={{ fontSize: '1.75rem', fontWeight: 800, margin: '0.25rem 0', color: '#0284c7' }}>
                                {paramStat?.avg !== undefined
                                    ? `${paramStat.avg.toFixed(2)} ${PARAMETERS.find(p => p.key === selectedParam)?.unit}`
                                    : '—'}
                            </div>
                            <div style={{ fontSize: '0.75rem', color: '#64748b' }}>Computed from {stats?.count || 0} observations</div>
                        </div>

                        <div className="card" style={{ textAlign: 'center', padding: '1.25rem' }}>
                            <div style={{ fontSize: '0.8rem', color: '#64748b', fontWeight: 600 }}>Minimum Recorded</div>
                            <div style={{ fontSize: '1.75rem', fontWeight: 800, margin: '0.25rem 0', color: '#059669' }}>
                                {paramStat?.min !== undefined
                                    ? `${paramStat.min.toFixed(2)} ${PARAMETERS.find(p => p.key === selectedParam)?.unit}`
                                    : '—'}
                            </div>
                            <div style={{ fontSize: '0.75rem', color: '#64748b' }}>Lowest valid observation in timeframe</div>
                        </div>

                        <div className="card" style={{ textAlign: 'center', padding: '1.25rem' }}>
                            <div style={{ fontSize: '0.8rem', color: '#64748b', fontWeight: 600 }}>Maximum Recorded</div>
                            <div style={{ fontSize: '1.75rem', fontWeight: 800, margin: '0.25rem 0', color: '#d97706' }}>
                                {paramStat?.max !== undefined
                                    ? `${paramStat.max.toFixed(2)} ${PARAMETERS.find(p => p.key === selectedParam)?.unit}`
                                    : '—'}
                            </div>
                            <div style={{ fontSize: '0.75rem', color: '#64748b' }}>Peak observation in timeframe</div>
                        </div>

                        <div className="card" style={{ textAlign: 'center', padding: '1.25rem' }}>
                            <div style={{ fontSize: '0.8rem', color: '#64748b', fontWeight: 600 }}>Telemetry Stream Provenance</div>
                            <div style={{ fontSize: '1.2rem', fontWeight: 800, margin: '0.45rem 0', color: '#1e293b' }}>
                                {provenanceCounts?.real_sensor ? '🟢 Live Hardware' : '🟡 Simulation'}
                            </div>
                            <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
                                {provenanceCounts?.real_sensor || 0} physical / {provenanceCounts?.simulated || 0} synthetic
                            </div>
                        </div>
                    </>
                )}
            </div>

            {/* Scientific Standards & Regulatory Benchmark Card */}
            <div className="card" style={{ background: '#f8fafc', border: '1px solid #e2e8f0' }}>
                <h4 style={{ color: '#0f172a', marginBottom: '0.5rem', fontWeight: 700, fontSize: '0.95rem' }}>
                    📋 Regulatory & Scientific Benchmarks (CPCB & CWC)
                </h4>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem', fontSize: '0.85rem', color: '#475569' }}>
                    <div>
                        <strong style={{ color: '#0369a1' }}>Outdoor Bathing (CPCB Class B):</strong>
                        <ul style={{ margin: '0.25rem 0 0 1.25rem', padding: 0 }}>
                            <li>pH: 6.5 to 8.5</li>
                            <li>Dissolved Oxygen (DO): ≥ 5.0 mg/L</li>
                            <li>BOD (5 days at 20°C): ≤ 3.0 mg/L</li>
                        </ul>
                    </div>
                    <div>
                        <strong style={{ color: '#b45309' }}>CWC Varanasi Reference Gauge (MSL):</strong>
                        <ul style={{ margin: '0.25rem 0 0 1.25rem', padding: 0 }}>
                            <li>Warning Level: 70.26 m</li>
                            <li>Danger Level: 71.26 m</li>
                            <li>High Flood Level (HFL 1978): 73.90 m</li>
                        </ul>
                    </div>
                </div>
                <div style={{ marginTop: '0.75rem', paddingTop: '0.5rem', borderTop: '1px solid #e2e8f0', fontSize: '0.75rem', color: '#64748b' }}>
                    <em>Note: In-situ electronic probes measure physical and chemical indicators. Full drinking water certification requires certified laboratory bacteriological (fecal coliform) and heavy metal testing.</em>
                </div>
            </div>
        </div>
    );
}
