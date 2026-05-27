"use client";

import React, { useState } from "react";

const SendSMSAlerts = () => {
    const [alertType, setAlertType] = useState("Flood Warning");
    const [message, setMessage] = useState("URGENT: Moderate flood risk detected at Dashashwamedh Ghat. Please evacuate the low-lying steps immediately. Helpline: 1077.");
    const [sending, setSending] = useState(false);

    const handleSend = () => {
        setSending(true);
        setTimeout(() => {
            setSending(false);
            alert("SMS Alert sent to 45,230 residents in the Varanasi Ghat area.");
        }, 2500);
    };

    return (
        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(300px, 1fr) 250px', gap: '2rem' }}>
            <div className="card">
                <h3>Broadcast SMS Alert</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', marginTop: '1.5rem' }}>
                    <div>
                        <label style={{ display: 'block', fontSize: '0.9rem', fontWeight: 600, marginBottom: '0.5rem' }}>Alert Type</label>
                        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                            {["Flood Warning", "Water Quality", "Emergency Evacuation", "General Info"].map(t => (
                                <button
                                    key={t}
                                    onClick={() => setAlertType(t)}
                                    className={`btn ${alertType === t ? 'btn-primary' : 'btn-secondary'}`}
                                    style={{ fontSize: '0.8rem', padding: '0.5rem 1rem' }}
                                >
                                    {t}
                                </button>
                            ))}
                        </div>
                    </div>

                    <div>
                        <label style={{ display: 'block', fontSize: '0.9rem', fontWeight: 600, marginBottom: '0.5rem' }}>Target Audience</label>
                        <select style={{ width: '100%', padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid var(--border)' }}>
                            <option>All Citizens (Varanasi)</option>
                            <option>Residents within 5km of Ganga</option>
                            <option>Verified Contributors Only</option>
                            <option>Authority Personnel</option>
                        </select>
                    </div>

                    <div>
                        <label style={{ display: 'block', fontSize: '0.9rem', fontWeight: 600, marginBottom: '0.5rem' }}>Message (Max 1600 chars)</label>
                        <textarea
                            value={message}
                            onChange={(e) => setMessage(e.target.value)}
                            rows={5}
                            style={{ width: '100%', padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid var(--border)', fontFamily: 'inherit' }}
                        />
                    </div>

                    <button
                        className="btn btn-primary"
                        style={{ padding: '1rem', background: '#ef4444' }}
                        disabled={sending}
                        onClick={handleSend}
                    >
                        {sending ? "Sending SMS Broadcast..." : "🚨 Send Emergency Alert"}
                    </button>
                </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                <div className="card" style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: '0.8rem', color: '#64748b', fontWeight: 600 }}>ESTIMATED REACH</div>
                    <div style={{ fontSize: '2rem', fontWeight: 800 }}>45.2k</div>
                    <div style={{ fontSize: '0.75rem', color: '#64748b' }}>Active Subscribers</div>
                </div>
                <div className="card" style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: '0.8rem', color: '#64748b', fontWeight: 600 }}>ESTIMATED COST</div>
                    <div style={{ fontSize: '2rem', fontWeight: 800 }}>₹6,750</div>
                    <div style={{ fontSize: '0.75rem', color: '#64748b' }}>₹0.15 per SMS</div>
                </div>
            </div>
        </div>
    );
};

export default SendSMSAlerts;
