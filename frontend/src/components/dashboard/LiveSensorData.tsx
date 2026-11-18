"use client";

import React from "react";
import { useSensorData } from "@/hooks/useSensorData";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:5000';

const LiveSensorData = () => {
    const { readings, loading, refresh } = useSensorData();

    const handleExport = () => {
        // Trigger the backend export endpoint
        window.location.href = `${BACKEND_URL}/api/authority/export-data`;
    };

    const getProvenanceBadge = () => {
        if (loading) return '⏳ Loading sensor data...';
        if (readings.provenance === 'real') return '🟢 Live Hardware Stream (Arduino/ESP32 Node)';
        if (readings.provenance === 'simulated') return '🟡 Simulated Stream (Demo Telemetry)';
        return '⚪ Default Baseline (Sensors Inactive / Offline)';
    };

    const sensors = [
        { label: "pH Level", value: readings.ph.toFixed(2), unit: "", status: readings.ph >= 6.5 && readings.ph <= 8.5 ? 'SAFE' : 'CAUTION', color: readings.ph >= 6.5 && readings.ph <= 8.5 ? 'green' : 'orange' },
        { label: "Turbidity", value: readings.turbidity.toFixed(1), unit: "NTU", status: readings.turbidity < 10 ? 'SAFE' : readings.turbidity < 50 ? 'CAUTION' : 'UNSAFE', color: readings.turbidity < 10 ? 'green' : readings.turbidity < 50 ? 'orange' : 'red' },
        { label: "Temperature", value: readings.temperature.toFixed(1), unit: "°C", status: readings.temperature_error ? 'ERROR' : 'SAFE', color: readings.temperature_error ? 'red' : 'green' },
        { label: "Humidity", value: readings.humidity.toFixed(1), unit: "%", status: 'SAFE', color: 'green' },
        { label: "EC", value: readings.ec.toFixed(0), unit: "µS/cm", status: readings.ec > 0 ? 'SAFE' : 'ERROR', color: readings.ec > 0 ? 'green' : 'red' },
        { label: "Water Level", value: readings.water_level.toFixed(2), unit: "m", status: readings.water_level_error ? 'ERROR' : readings.water_level > 70 ? 'CAUTION' : 'SAFE', color: readings.water_level_error ? 'red' : readings.water_level > 70 ? 'orange' : 'green' },
        { label: "BOD", value: readings.bod.toFixed(1), unit: "mg/L", status: readings.bod < 30 ? 'SAFE' : 'CAUTION', color: readings.bod < 30 ? 'green' : 'orange' },
        { label: "COD", value: readings.cod.toFixed(1), unit: "mg/L", status: readings.cod < 250 ? 'SAFE' : 'CAUTION', color: readings.cod < 250 ? 'green' : 'orange' },
        { label: "DO", value: readings.do.toFixed(1), unit: "mg/L", status: readings.do > 5 ? 'SAFE' : 'CAUTION', color: readings.do > 5 ? 'green' : 'orange' },
    ];

    return (
        <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
                <div>
                    <h3>Real-Time Sensor Network</h3>
                    <div style={{ fontSize: '0.85rem', color: '#64748b', marginTop: '0.5rem' }}>
                        {getProvenanceBadge()}
                    </div>
                </div>
                <div style={{ display: 'flex', gap: '1rem' }}>
                    <button className="btn btn-secondary" style={{ fontSize: '0.85rem' }} onClick={refresh} disabled={loading}>
                        {loading ? 'Refreshing...' : 'Refresh'}
                    </button>
                    <button className="btn btn-primary" style={{ fontSize: '0.85rem' }} onClick={handleExport}>Export CSV</button>
                </div>
            </div>

            {/* Sensor Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
                {sensors.map((sensor, i) => (
                    <div key={i} className="card" style={{
                        padding: '1.5rem',
                        borderLeft: `4px solid var(--${sensor.color === 'green' ? 'success' : sensor.color === 'orange' ? 'warning' : 'danger'})`,
                        background: sensor.color === 'green' ? '#f0fdf4' : sensor.color === 'orange' ? '#fffbeb' : '#fef2f2'
                    }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
                            <div style={{ fontSize: '0.75rem', color: '#64748b', fontWeight: 600 }}>{sensor.label}</div>
                            <span className={`badge badge-${sensor.color}`} style={{ fontSize: '0.65rem' }}>{sensor.status}</span>
                        </div>
                        <div style={{ fontSize: '2rem', fontWeight: 800, color: sensor.color === 'green' ? '#10b981' : sensor.color === 'orange' ? '#f59e0b' : '#ef4444' }}>
                            {sensor.value}
                            <small style={{ fontSize: '1rem', fontWeight: 500, marginLeft: '4px', color: '#64748b' }}>{sensor.unit}</small>
                        </div>
                    </div>
                ))}
            </div>

            {/* Sensor Data Table */}
            <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                    <thead>
                        <tr style={{ borderBottom: '1px solid var(--border)', color: '#64748b', fontSize: '0.9rem' }}>
                            <th style={{ padding: '1rem' }}>Parameter</th>
                            <th style={{ padding: '1rem' }}>Current Value</th>
                            <th style={{ padding: '1rem' }}>Status</th>
                            <th style={{ padding: '1rem' }}>Safe Range</th>
                            <th style={{ padding: '1rem' }}>Updated</th>
                        </tr>
                    </thead>
                    <tbody>
                        {sensors.map((sensor, i) => (
                            <tr key={i} style={{ borderBottom: '1px solid #f1f5f9' }}>
                                <td style={{ padding: '1rem', fontWeight: 600 }}>{sensor.label}</td>
                                <td style={{ padding: '1rem', fontSize: '1.1rem', fontWeight: 700 }}>
                                    {sensor.value} {sensor.unit}
                                </td>
                                <td style={{ padding: '1rem' }}>
                                    <span className={`badge badge-${sensor.color}`}>{sensor.status}</span>
                                </td>
                                <td style={{ padding: '1rem', color: '#64748b', fontSize: '0.9rem' }}>
                                    {i === 0 && '6.5 - 8.5'}
                                    {i === 1 && '< 10 NTU'}
                                    {i === 2 && '15 - 35°C'}
                                    {i === 3 && '40 - 80%'}
                                    {i === 4 && '> 0 µS/cm'}
                                    {i === 5 && '< 70m'}
                                    {i === 6 && '< 30 mg/L'}
                                    {i === 7 && '< 250 mg/L'}
                                    {i === 8 && '> 5 mg/L'}
                                </td>
                                <td style={{ padding: '1rem', color: '#64748b', fontSize: '0.85rem' }}>Just now</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* Error Warnings */}
            {(readings.temperature_error || readings.water_level_error) && (
                <div style={{ marginTop: '1.5rem', padding: '1rem', background: '#fef2f2', border: '1px solid #fecaca', borderRadius: '0.5rem' }}>
                    <div style={{ fontWeight: 600, color: '#dc2626', marginBottom: '0.5rem' }}>⚠️ Sensor Errors Detected</div>
                    <ul style={{ margin: 0, paddingLeft: '1.5rem', color: '#991b1b', fontSize: '0.9rem' }}>
                        {readings.temperature_error && <li>Temperature sensor error (-127°C) - Check wiring and connections</li>}
                        {readings.water_level_error && <li>Water level sensor error (0.00m) - Ensure sensor is submerged</li>}
                    </ul>
                </div>
            )}
        </div>
    );
};

export default LiveSensorData;
