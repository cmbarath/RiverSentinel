"use client";

import React from "react";

export const Notifications = () => (
    <div className="card">
        <h3>Recent Alerts</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginTop: '1.5rem' }}>
            {[
                { title: "Flood Alert", msg: "Moderate risk detected at Dashashwamedh. Expected peak at 04:00 AM.", type: "red", time: "2h ago" },
                { title: "Report Verified", msg: "Your pollution report at Assi Ghat has been verified. +35 pts earned!", type: "green", time: "5h ago" },
                { title: "Water Quality Update", msg: "Ganga water quality in Varanasi has improved by 12% this week.", type: "blue", time: "1d ago" },
            ].map((n, i) => (
                <div key={i} style={{ display: 'flex', gap: '1rem', padding: '1rem', borderRadius: '0.75rem', border: `1px solid var(--border)`, borderLeft: `5px solid var(--${n.type === 'red' ? 'danger' : n.type === 'green' ? 'success' : 'primary'})` }}>
                    <div style={{ flex: 1 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                            <div style={{ fontWeight: 700 }}>{n.title}</div>
                            <div style={{ fontSize: '0.75rem', color: '#64748b' }}>{n.time}</div>
                        </div>
                        <div style={{ fontSize: '0.9rem', color: '#475569' }}>{n.msg}</div>
                    </div>
                </div>
            ))}
        </div>
    </div>
);

export const Profile = () => (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '2rem' }}>
        <div className="card" style={{ textAlign: 'center' }}>
            <div style={{ width: '100px', height: '100px', borderRadius: '50%', background: 'var(--primary)', color: 'white', fontSize: '3rem', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 1.5rem', fontWeight: 800 }}>A</div>
            <h2>Aviral Sharma</h2>
            <p style={{ color: '#64748b' }}>Member since Dec 2025</p>
            <div className="badge badge-blue" style={{ marginTop: '1rem' }}>RIVER GUARDIAN</div>
            <button className="btn btn-secondary" style={{ marginTop: '2rem', width: '100%' }}>Edit Profile</button>
        </div>
        <div className="card">
            <h3>Account Statistics</h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem', marginTop: '2rem' }}>
                <div>
                    <div style={{ fontSize: '0.85rem', color: '#64748b' }}>Reports Submitted</div>
                    <div style={{ fontSize: '2rem', fontWeight: 800 }}>25</div>
                </div>
                <div>
                    <div style={{ fontSize: '0.85rem', color: '#64748b' }}>Lives Impacted</div>
                    <div style={{ fontSize: '2rem', fontWeight: 800 }}>1.2k</div>
                </div>
                <div>
                    <div style={{ fontSize: '0.85rem', color: '#64748b' }}>Sensors Verified</div>
                    <div style={{ fontSize: '2rem', fontWeight: 800 }}>12</div>
                </div>
                <div>
                    <div style={{ fontSize: '0.85rem', color: '#64748b' }}>Rewards Claimed</div>
                    <div style={{ fontSize: '2rem', fontWeight: 800 }}>3</div>
                </div>
            </div>
        </div>
    </div>
);
