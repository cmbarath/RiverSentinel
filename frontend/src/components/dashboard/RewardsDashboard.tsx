"use client";

import React from "react";

export default function RewardsDashboard() {
    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            {/* Deferred Feature Notice */}
            <div style={{
                padding: '1.5rem',
                borderRadius: '0.75rem',
                background: '#f8fafc',
                border: '1px solid #e2e8f0',
                textAlign: 'center'
            }}>
                <div style={{ fontSize: '3rem', marginBottom: '0.75rem' }}>⭐</div>
                <h3 style={{ margin: '0 0 0.5rem 0', fontWeight: 800, color: '#0f172a' }}>
                    Citizen Community Rewards (Deferred)
                </h3>
                <p style={{ maxWidth: '520px', margin: '0 auto 1.5rem auto', color: '#64748b', fontSize: '0.9rem', lineHeight: 1.5 }}>
                    The gamification points and rewards subsystem is deferred to future community milestones.
                    Current engineering priority is focused on physical IoT sensor integration, real-time hydrological flood screening, and official UPPCB pollution report resolution.
                </p>
                <div style={{ display: 'flex', justifyContent: 'center', gap: '1rem' }}>
                    <a href="/citizen-dashboard?tab=report" className="btn btn-primary" style={{ padding: '0.5rem 1.25rem', fontSize: '0.875rem' }}>
                        Submit Live Pollution Report
                    </a>
                    <a href="/citizen-dashboard?tab=safety" className="btn btn-secondary" style={{ padding: '0.5rem 1.25rem', fontSize: '0.875rem' }}>
                        View Water Safety Screening
                    </a>
                </div>
            </div>
        </div>
    );
}
