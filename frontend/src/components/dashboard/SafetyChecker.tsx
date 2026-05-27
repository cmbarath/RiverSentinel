"use client";

import React, { useState } from "react";

const ghats = [
    "Dashashwamedh", "Assi", "Manikarnika", "Harishchandra", "Rajendra Prasad",
    "Tulsi", "Kedar", "Shivala", "Darbhanga", "Panchganga", "Scindia", "Munshi"
];

import { useSensorData } from "@/hooks/useSensorData";

const SafetyChecker = () => {
    const [selectedGhat, setSelectedGhat] = useState(ghats[0]);
    const { readings } = useSensorData();

    // Determine Status Logic (Simple Example)
    const isBathingSafe = readings.ph >= 6.5 && readings.ph <= 8.5 && readings.turbidity < 10;
    const isDrinkingSafe = readings.ph >= 6.5 && readings.ph <= 8.5 && readings.turbidity < 5 && readings.ec < 500;

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                    <h1 style={{ marginBottom: '0.5rem' }}>Safety Checker</h1>
                    <p style={{ color: '#64748b' }}>Real-time water safety assessments for your favorite ghats.</p>
                </div>
                <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                    <select
                        value={selectedGhat}
                        onChange={(e) => setSelectedGhat(e.target.value)}
                        style={{ padding: '0.75rem 1.5rem', borderRadius: '0.75rem', border: '1px solid var(--border)', background: 'white', fontWeight: 600 }}
                    >
                        {ghats.map(g => <option key={g} value={g}>{g} Ghat</option>)}
                    </select>
                    <div style={{ fontSize: '0.85rem', color: '#64748b' }}>
                        {readings.status === 'live' ? '🟢 Live Data' : '⚠️ Default Values'}
                    </div>
                </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1.5rem' }}>
                {/* Bathing Safety */}
                <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <h3 style={{ margin: 0 }}>Bathing Safety 🏊</h3>
                        <span className={`badge ${isBathingSafe ? 'badge-green' : 'badge-red'}`}>{isBathingSafe ? 'SAFE' : 'UNSAFE'}</span>
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem', margin: '0.5rem 0' }}>
                        <div style={{ textAlign: 'center' }}>
                            <div style={{ fontSize: '0.8rem', color: '#64748b' }}>pH</div>
                            <div style={{ fontWeight: 700 }}>{readings.ph.toFixed(1)}</div>
                        </div>
                        <div style={{ textAlign: 'center' }}>
                            <div style={{ fontSize: '0.8rem', color: '#64748b' }}>Turbidity</div>
                            <div style={{ fontWeight: 700 }}>{readings.turbidity.toFixed(0)} NTU</div>
                        </div>
                        <div style={{ textAlign: 'center' }}>
                            <div style={{ fontSize: '0.8rem', color: '#64748b' }}>Temp</div>
                            <div style={{ fontWeight: 700 }}>{readings.temperature.toFixed(1)}°C</div>
                        </div>
                    </div>
                    <div style={{ fontSize: '0.9rem', color: '#64748b', background: '#f8fafc', padding: '0.75rem', borderRadius: '0.5rem' }}>
                        {isBathingSafe ? "✓ Water quality is within safe limits for religious bathing." : "⚠️ Water quality unsafe for bathing."}
                    </div>
                </div>

                {/* Drinking Safety */}
                <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <h3 style={{ margin: 0 }}>Drinking Safety 🚰</h3>
                        <span className={`badge ${isDrinkingSafe ? 'badge-green' : 'badge-orange'}`}>{isDrinkingSafe ? 'SAFE' : 'CAUTION'}</span>
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem', margin: '0.5rem 0' }}>
                        <div style={{ textAlign: 'center' }}>
                            <div style={{ fontSize: '0.8rem', color: '#64748b' }}>pH</div>
                            <div style={{ fontWeight: 700 }}>{readings.ph.toFixed(1)}</div>
                        </div>
                        <div style={{ textAlign: 'center' }}>
                            <div style={{ fontSize: '0.8rem', color: '#64748b' }}>EC</div>
                            <div style={{ fontWeight: 700 }}>{readings.ec.toFixed(0)}</div>
                        </div>
                        <div style={{ textAlign: 'center' }}>
                            <div style={{ fontSize: '0.8rem', color: '#64748b' }}>DO</div>
                            <div style={{ fontWeight: 700 }}>{readings.do.toFixed(1)} mg/L</div>
                        </div>
                    </div>
                    <div style={{ fontSize: '0.9rem', color: '#9a3412', background: '#fff7ed', padding: '0.75rem', borderRadius: '0.5rem' }}>
                        {isDrinkingSafe ? "✓ Safe for drinking after filtration." : "⚠️ Boil before drinking. Contamination detected."}
                    </div>
                </div>

                {/* Livestock Safety */}
                <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <h3 style={{ margin: 0 }}>Livestock Safety 🐄</h3>
                        <span className="badge badge-green">SAFE</span>
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', margin: '0.5rem 0' }}>
                        <div style={{ textAlign: 'center' }}>
                            <div style={{ fontSize: '0.8rem', color: '#64748b' }}>EC</div>
                            <div style={{ fontWeight: 700 }}>{readings.ec.toFixed(0)} µS/cm</div>
                        </div>
                        <div style={{ textAlign: 'center' }}>
                            <div style={{ fontSize: '0.8rem', color: '#64748b' }}>Temp</div>
                            <div style={{ fontWeight: 700 }}>{readings.temperature.toFixed(1)}°C</div>
                        </div>
                    </div>
                    <div style={{ fontSize: '0.9rem', color: '#64748b', background: '#f8fafc', padding: '0.75rem', borderRadius: '0.5rem' }}>
                        ✓ Water is likely safe for cattle.
                    </div>
                </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '1rem' }}>
                {[
                    { label: "pH", value: readings.ph.toFixed(1), unit: "", status: "green" },
                    { label: "Turbidity", value: readings.turbidity.toFixed(0), unit: "NTU", status: "green" },
                    { label: "Temp", value: readings.temperature.toFixed(1), unit: "°C", status: "green" },
                    { label: "EC", value: readings.ec.toFixed(0), unit: "µS", status: "green" },
                    { label: "BOD", value: readings.bod.toFixed(1), unit: "mg/L", status: "green" },
                    { label: "COD", value: readings.cod.toFixed(1), unit: "mg/L", status: "green" },
                ].map((sensor, i) => (
                    <div key={i} className="card" style={{ padding: '1rem', display: 'flex', borderLeft: `4px solid var(--${sensor.status === 'green' ? 'success' : 'warning'})` }}>
                        <div>
                            <div style={{ fontSize: '0.75rem', color: '#64748b', fontWeight: 600 }}>{sensor.label}</div>
                            <div style={{ fontSize: '1.25rem', fontWeight: 800 }}>{sensor.value}<small style={{ fontSize: '0.8rem', fontWeight: 500, marginLeft: '2px' }}>{sensor.unit}</small></div>
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};

export default SafetyChecker;
