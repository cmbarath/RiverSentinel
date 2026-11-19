"use client";

import React, { useState } from "react";

export default function SendSMSAlerts() {
    const [alertType, setAlertType] = useState("Flood Warning");
    const [message, setMessage] = useState("URGENT: CWC Warning Stage exceeded at Dashashwamedh Ghat (70.26m MSL). Low-lying steps are being evacuated. Emergency Helpline: 1077.");

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            {/* Phase 5 Hardware/Gateway Notice */}
            <div style={{
                padding: '1.25rem',
                borderRadius: '0.75rem',
                background: '#fffbeb',
                border: '1px solid #fde68a',
                color: '#92400e',
                fontSize: '0.9rem',
                lineHeight: 1.5
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 700, fontSize: '0.95rem', marginBottom: '0.25rem' }}>
                    ⚠️ Telephony SMS Gateway Notice (Phase 5 Feature)
                </div>
                The production SMS broadcasting engine (Twilio / Government CDAC SMS Gateway) is scheduled for deployment in <strong>Phase 5 (Alerting & Notification Subsystems)</strong>.
                Direct cellular broadcasts are currently disabled in this development environment to prevent unauthenticated message transmission.
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(320px, 1fr) 300px', gap: '2rem' }}>
                <div className="card">
                    <h3 style={{ margin: '0 0 1.25rem 0', fontWeight: 700 }}>Compose Emergency Alert</h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                        <div>
                            <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: '#475569', marginBottom: '0.5rem' }}>Alert Category</label>
                            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                                {["Flood Warning", "Water Quality", "Emergency Evacuation", "General Info"].map(t => (
                                    <button
                                        key={t}
                                        type="button"
                                        onClick={() => setAlertType(t)}
                                        className={`btn ${alertType === t ? 'btn-primary' : 'btn-secondary'}`}
                                        style={{ fontSize: '0.8rem', padding: '0.45rem 0.9rem' }}
                                    >
                                        {t}
                                    </button>
                                ))}
                            </div>
                        </div>

                        <div>
                            <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: '#475569', marginBottom: '0.5rem' }}>Geographic Target Audience</label>
                            <select
                                disabled
                                style={{ width: '100%', padding: '0.6rem 0.75rem', borderRadius: '0.5rem', border: '1px solid #cbd5e1', background: '#f8fafc', color: '#64748b', fontSize: '0.875rem' }}
                            >
                                <option>Varanasi Urban Riparian Zones (Ganga Ghat Corridor)</option>
                                <option>Residents within 500m of Assi / Varuna Inflows</option>
                                <option>Registered UPPCB Field Volunteers</option>
                                <option>CWC & Disaster Management Officers</option>
                            </select>
                            <span style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '0.25rem', display: 'block' }}>
                                Recipient geo-fencing will be activated upon gateway provisioning.
                            </span>
                        </div>

                        <div>
                            <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: '#475569', marginBottom: '0.5rem' }}>Broadcast Message Text</label>
                            <textarea
                                rows={4}
                                value={message}
                                onChange={(e) => setMessage(e.target.value)}
                                style={{ width: '100%', padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid #cbd5e1', fontSize: '0.875rem', fontFamily: 'inherit' }}
                            />
                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: '#64748b', marginTop: '0.25rem' }}>
                                <span>GSM 7-bit Encoding standard</span>
                                <span>{message.length} / 160 characters (1 SMS segment)</span>
                            </div>
                        </div>

                        <div>
                            <button
                                disabled
                                className="btn btn-secondary"
                                style={{
                                    width: '100%',
                                    padding: '0.75rem',
                                    opacity: 0.6,
                                    cursor: 'not-allowed',
                                    display: 'flex',
                                    justifyContent: 'center',
                                    alignItems: 'center',
                                    gap: '0.5rem',
                                    fontWeight: 700
                                }}
                            >
                                🔒 Gateway Offline (Disabled Until Phase 5)
                            </button>
                        </div>
                    </div>
                </div>

                {/* Gateway Specifications & Integration Roadmap */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                    <div className="card" style={{ padding: '1.25rem' }}>
                        <h4 style={{ margin: '0 0 0.75rem 0', fontSize: '0.95rem', fontWeight: 700, color: '#0f172a' }}>
                            Gateway Specifications
                        </h4>
                        <div style={{ fontSize: '0.8rem', color: '#475569', lineHeight: 1.6 }}>
                            <div>Provider: <strong>Scheduled Phase 5</strong></div>
                            <div>Shortcode: <strong>Pending UP-DIPR</strong></div>
                            <div>Max Throughput: <strong>100 msg/sec</strong></div>
                            <div>Fallback: <strong>District Disaster Helpline (1077)</strong></div>
                        </div>
                    </div>

                    <div className="card" style={{ padding: '1.25rem', background: '#f8fafc', border: '1px solid #e2e8f0' }}>
                        <h4 style={{ margin: '0 0 0.5rem 0', fontSize: '0.9rem', fontWeight: 700, color: '#0f172a' }}>
                            Emergency Contact Protocols
                        </h4>
                        <div style={{ fontSize: '0.8rem', color: '#64748b', lineHeight: 1.5 }}>
                            In the event of an immediate hydrological emergency, field officers must contact:
                            <ul style={{ margin: '0.5rem 0 0 1rem', padding: 0 }}>
                                <li>Varanasi Flood Control Room</li>
                                <li>NDRF 11th Battalion, Varanasi</li>
                                <li>UP Jal Nigam Ghat Division</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
