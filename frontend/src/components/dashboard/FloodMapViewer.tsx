"use client";

import React, { useState } from 'react';

const FloodMapViewer = () => {
    const [showLegend, setShowLegend] = useState(true);

    const legendItems = [
        { range: '≤ 4.6', risk: 'Very Low', color: '#ed8b58', desc: 'High land, steep slope, far from river — safest areas' },
        { range: '4.6 – 6.2', risk: 'Low', color: '#f7d692', desc: 'Slight chance of water accumulation' },
        { range: '6.2 – 7.8', risk: 'Moderate', color: '#d9f99d', desc: 'Water may collect during heavy rain' },
        { range: '7.8 – 9.4', risk: 'High', color: '#4ade80', desc: 'Low, flat land near river — flood prone' },
        { range: '> 9.4', risk: 'Very High', color: '#2563eb', desc: 'Very low elevation and dense river influence — highest flood risk' },
    ];

    return (
        <div className="card" style={{ padding: 0, overflow: 'hidden', height: '600px', display: 'flex', flexDirection: 'column', position: 'relative' }}>
            <div style={{ padding: '1.5rem', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'white', zIndex: 10 }}>
                <div>
                    <h3 style={{ marginBottom: '0.25rem' }}>Flood Susceptibility Map (Varanasi)</h3>
                    <p style={{ color: '#64748b', fontSize: '0.9rem' }}>
                        Geospatial analysis combining elevation, slope, and river proximity.
                    </p>
                </div>
                <button
                    className="btn btn-secondary"
                    onClick={() => setShowLegend(!showLegend)}
                    style={{ fontSize: '0.85rem' }}
                >
                    {showLegend ? 'Hide Legend' : 'Show Legend'}
                </button>
            </div>

            <div style={{ flex: 1, position: 'relative' }}>
                <iframe
                    src="/flood-map/index.html"
                    style={{ width: '100%', height: '100%', border: 'none' }}
                    title="Flood Susceptibility Map"
                />

                {/* Legend Overlay */}
                {showLegend && (
                    <div className="glass" style={{
                        position: 'absolute',
                        bottom: '20px',
                        right: '20px',
                        width: '480px',
                        padding: '1.25rem',
                        borderRadius: '0.75rem',
                        boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)',
                        zIndex: 1000,
                        maxHeight: '400px',
                        overflowY: 'auto'
                    }}>
                        <h4 style={{ fontSize: '1rem', marginBottom: '1rem', fontWeight: 700, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            Meaning of Valid Values
                            <button onClick={() => setShowLegend(false)} style={{ fontSize: '0.8rem', color: '#ef4444' }}>✕</button>
                        </h4>
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
                            <thead>
                                <tr style={{ borderBottom: '1px solid #e2e8f0', color: '#64748b' }}>
                                    <th style={{ textAlign: 'left', padding: '0.5rem' }}>Value Range</th>
                                    <th style={{ textAlign: 'left', padding: '0.5rem' }}>Flood Risk</th>
                                    <th style={{ textAlign: 'left', padding: '0.5rem' }}>Meaning</th>
                                </tr>
                            </thead>
                            <tbody>
                                {legendItems.map((item, index) => (
                                    <tr key={index} style={{ borderBottom: '1px solid #f1f5f9' }}>
                                        <td style={{ padding: '0.75rem 0.5rem', whiteSpace: 'nowrap', fontWeight: 500 }}>{item.range}</td>
                                        <td style={{ padding: '0.75rem 0.5rem' }}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                <div style={{ width: '12px', height: '12px', borderRadius: '3px', background: item.color, flexShrink: 0 }}></div>
                                                <span style={{ fontWeight: 600 }}>{item.risk}</span>
                                            </div>
                                        </td>
                                        <td style={{ padding: '0.75rem 0.5rem', color: '#475569', lineHeight: 1.4 }}>{item.desc}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
};

export default FloodMapViewer;
