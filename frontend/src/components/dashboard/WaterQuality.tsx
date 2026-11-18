"use client";

import React from "react";
import { useSensorData } from "@/hooks/useSensorData";

const WaterQuality = () => {
    const { readings } = useSensorData();

    const metrics = [
        { label: 'pH Level', value: readings.ph.toFixed(1), unit: '', status: readings.ph >= 6.5 && readings.ph <= 8.5 ? 'Good' : 'Caution', color: readings.ph >= 6.5 && readings.ph <= 8.5 ? '#10b981' : '#f59e0b' },
        { label: 'Dissolved Oxygen', value: readings.do.toFixed(1), unit: 'mg/L', status: readings.do > 5 ? 'Good' : 'Moderate', color: readings.do > 5 ? '#10b981' : '#f59e0b' },
        { label: 'Turbidity', value: readings.turbidity.toFixed(0), unit: 'NTU', status: readings.turbidity < 10 ? 'Excellent' : 'Moderate', color: readings.turbidity < 10 ? '#3b82f6' : '#f59e0b' },
        { label: 'Temperature', value: readings.temperature.toFixed(1), unit: '°C', status: readings.temperature_error ? 'Error' : 'Normal', color: readings.temperature_error ? '#ef4444' : '#6366f1' },
        { label: 'Conductivity', value: readings.ec.toFixed(0), unit: 'µS/cm', status: readings.ec < 500 ? 'Good' : 'High', color: readings.ec < 500 ? '#10b981' : '#ef4444' },
        { label: 'BOD', value: readings.bod.toFixed(1), unit: 'mg/L', status: readings.bod < 30 ? 'Good' : 'High', color: readings.bod < 30 ? '#10b981' : '#f59e0b' },
        { label: 'COD', value: readings.cod.toFixed(1), unit: 'mg/L', status: readings.cod < 250 ? 'Good' : 'High', color: readings.cod < 250 ? '#10b981' : '#f59e0b' },
        { label: 'Water Level', value: readings.water_level.toFixed(2), unit: 'm', status: readings.water_level_error ? 'Error' : readings.water_level > 70 ? 'High' : 'Normal', color: readings.water_level_error ? '#ef4444' : readings.water_level > 70 ? '#f59e0b' : '#8b5cf6' },
    ];

    const getBadgeColor = (status: string) => {
        switch (status.toLowerCase()) {
            case 'good':
            case 'excellent':
            case 'safe':
            case 'normal':
                return 'success';
            case 'moderate':
            case 'high':
                return 'warning';
            case 'critical':
            case 'error':
                return 'danger';
            default:
                return 'info';
        }
    };

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1.5rem' }}>
                {metrics.map((p, i) => (
                    <div key={i} className="card" style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <div style={{ fontWeight: 600 }}>{p.label}</div>
                            <span className={`badge badge-${getBadgeColor(p.status)}`}>{p.status}</span>
                        </div>
                        <div style={{ fontSize: '2.5rem', fontWeight: 800, color: p.color }}>{p.value}<small style={{ fontSize: '1rem', fontWeight: 500, marginLeft: '4px', color: '#64748b' }}>{p.unit}</small></div>
                    </div>
                ))}
            </div>

            <div className="card">
                <h3 style={{ marginBottom: '1.5rem' }}>Disease Risk Analysis</h3>
                <div style={{ overflowX: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                        <thead>
                            <tr style={{ borderBottom: '1px solid var(--border)', color: '#64748b', fontSize: '0.9rem' }}>
                                <th style={{ padding: '1rem' }}>Disease</th>
                                <th style={{ padding: '1rem' }}>Risk Level</th>
                                <th style={{ padding: '1rem' }}>Probability</th>
                                <th style={{ padding: '1rem' }}>Common Symptoms</th>
                            </tr>
                        </thead>
                        <tbody>
                            {[
                                { name: "Cholera", risk: "LOW", prob: 5, color: "green", symptoms: "Nausea, Dehydration" },
                                { name: "Typhoid", risk: "MODERATE", prob: 24, color: "orange", symptoms: "Fever, Headache" },
                                { name: "Dysentery", risk: "LOW", prob: 8, color: "green", symptoms: "Stomach Cramps" },
                                { name: "Skin Infections", risk: "HIGH", prob: 62, color: "red", symptoms: "Rashes, Itching" },
                            ].map((d, i) => (
                                <tr key={i} style={{ borderBottom: '1px solid #f1f5f9' }}>
                                    <td style={{ padding: '1rem', fontWeight: 600 }}>{d.name}</td>
                                    <td style={{ padding: '1rem' }}>
                                        <span className={`badge badge-${d.color}`}>{d.risk}</span>
                                    </td>
                                    <td style={{ padding: '1rem' }}>
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                                            <div style={{ flex: 1, height: '6px', background: '#e2e8f0', borderRadius: '3px', width: '100px' }}>
                                                <div style={{ width: `${d.prob}%`, height: '100%', background: `var(--${d.color === 'green' ? 'success' : d.color === 'orange' ? 'warning' : 'danger'})`, borderRadius: '3px' }}></div>
                                            </div>
                                            <span>{d.prob}%</span>
                                        </div>
                                    </td>
                                    <td style={{ padding: '1rem', color: '#64748b', fontSize: '0.9rem' }}>{d.symptoms}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};

export default WaterQuality;
