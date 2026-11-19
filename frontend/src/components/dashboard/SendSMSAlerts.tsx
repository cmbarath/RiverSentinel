"use client";

import React, { useState } from "react";
import { supabase } from "@/lib/supabaseClient";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:5000";

export default function SendSMSAlerts() {
    const [alertType, setAlertType] = useState("Flood Warning");
    const [message, setMessage] = useState("URGENT: CWC Warning Stage exceeded at Dashashwamedh Ghat (70.26m MSL). Low-lying steps evacuated. Emergency Helpline: 1077.");
    const [recipientPhone, setRecipientPhone] = useState("+91 98765 43210");
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<any>(null);
    const [outboxRunning, setOutboxRunning] = useState(false);
    const [outboxResult, setOutboxResult] = useState<any>(null);

    const getAuthHeaders = async () => {
        const { data } = await supabase.auth.getSession();
        const token = data?.session?.access_token;
        return {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {})
        };
    };

    const handleSendTestSMS = async () => {
        setLoading(true);
        setResult(null);
        try {
            const headers = await getAuthHeaders();
            const res = await fetch(`${BACKEND_URL}/api/authority/send-sms`, {
                method: "POST",
                headers,
                body: JSON.stringify({
                    message,
                    phone_number: recipientPhone,
                    category: alertType
                })
            });
            const data = await res.json();
            setResult(data);
        } catch (err: any) {
            setResult({ status: "error", message: err.message });
        } finally {
            setLoading(false);
        }
    };

    const handleRunWorker = async () => {
        setOutboxRunning(true);
        setOutboxResult(null);
        try {
            const headers = await getAuthHeaders();
            const res = await fetch(`${BACKEND_URL}/api/v1/notifications/process-outbox`, {
                method: "POST",
                headers
            });
            const data = await res.json();
            setOutboxResult(data);
        } catch (err: any) {
            setOutboxResult({ status: "error", message: err.message });
        } finally {
            setOutboxRunning(false);
        }
    };

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            {/* Status Guardrail Card */}
            <div style={{
                padding: '1.25rem',
                borderRadius: '0.75rem',
                background: '#f0fdf4',
                border: '1px solid #bbf7d0',
                color: '#166534',
                fontSize: '0.9rem',
                lineHeight: 1.5
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 700, fontSize: '0.95rem', marginBottom: '0.25rem' }}>
                    ✅ Telephony Subsystem & Outbox Engine (Phase 5 Active)
                </div>
                The transactional notification outbox and telephony interface are active. By default, <code>SMS_ENABLED=false</code> protects external telephony budgets, running safely in <strong>MockSMSProvider</strong> mode. 
                Simulated sensor telemetry is strictly suppressed from sending live cellular SMS.
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(320px, 1fr) 320px', gap: '2rem' }}>
                <div className="card">
                    <h3 style={{ margin: '0 0 1.25rem 0', fontWeight: 700 }}>Compose Emergency Cellular Alert</h3>
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
                            <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: '#475569', marginBottom: '0.5rem' }}>Target Authority Recipient</label>
                            <input
                                type="text"
                                value={recipientPhone}
                                onChange={(e) => setRecipientPhone(e.target.value)}
                                placeholder="+91 XXXXX XXXXX"
                                style={{ width: '100%', padding: '0.6rem 0.75rem', borderRadius: '0.5rem', border: '1px solid #cbd5e1', fontSize: '0.875rem' }}
                            />
                            <span style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.25rem', display: 'block' }}>
                                Standard E.164 format with +91 country code (Varanasi/UP circle).
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
                            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: message.length > 160 ? '#ef4444' : '#64748b', marginTop: '0.25rem' }}>
                                <span>GSM 7-bit Encoding standard</span>
                                <span>{message.length} / 160 characters ({Math.ceil(message.length / 160) || 1} SMS segment)</span>
                            </div>
                        </div>

                        <div>
                            <button
                                onClick={handleSendTestSMS}
                                disabled={loading}
                                className="btn btn-primary"
                                style={{
                                    width: '100%',
                                    padding: '0.75rem',
                                    display: 'flex',
                                    justifyContent: 'center',
                                    alignItems: 'center',
                                    gap: '0.5rem',
                                    fontWeight: 700,
                                    background: '#dc2626',
                                    borderColor: '#dc2626'
                                }}
                            >
                                {loading ? "⏳ Dispatching..." : "🚨 Dispatch Authority Test Alert"}
                            </button>
                        </div>

                        {result && (
                            <div style={{
                                padding: '1rem',
                                borderRadius: '0.5rem',
                                background: result.status === 'success' ? '#f0fdf4' : '#fef2f2',
                                border: `1px solid ${result.status === 'success' ? '#bbf7d0' : '#fecaca'}`,
                                fontSize: '0.85rem'
                            }}>
                                <strong>Status:</strong> {result.status}<br />
                                <strong>Message:</strong> {result.message}<br />
                                {result.note && <span style={{ color: '#64748b', fontSize: '0.8rem' }}>{result.note}</span>}
                            </div>
                        )}
                    </div>
                </div>

                {/* Outbox & Gateway Specifications */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                    <div className="card" style={{ padding: '1.25rem' }}>
                        <h4 style={{ margin: '0 0 0.75rem 0', fontSize: '0.95rem', fontWeight: 700, color: '#0f172a' }}>
                            Outbox Dispatch Engine
                        </h4>
                        <p style={{ fontSize: '0.8rem', color: '#64748b', lineHeight: 1.5, margin: '0 0 1rem 0' }}>
                            Process pending queued notifications from the <code>notification_deliveries</code> table with exponential backoff and rate limits.
                        </p>
                        <button
                            onClick={handleRunWorker}
                            disabled={outboxRunning}
                            className="btn btn-secondary"
                            style={{ width: '100%', fontSize: '0.85rem', padding: '0.5rem' }}
                        >
                            {outboxRunning ? "⏳ Running..." : "⚡ Trigger Outbox Worker"}
                        </button>

                        {outboxResult && (
                            <div style={{ marginTop: '0.75rem', padding: '0.5rem', background: '#f8fafc', borderRadius: '0.375rem', fontSize: '0.75rem', border: '1px solid #e2e8f0' }}>
                                <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{JSON.stringify(outboxResult.summary || outboxResult, null, 2)}</pre>
                            </div>
                        )}
                    </div>

                    <div className="card" style={{ padding: '1.25rem' }}>
                        <h4 style={{ margin: '0 0 0.75rem 0', fontSize: '0.95rem', fontWeight: 700, color: '#0f172a' }}>
                            Gateway Specifications
                        </h4>
                        <div style={{ fontSize: '0.8rem', color: '#475569', lineHeight: 1.6 }}>
                            <div>Provider: <strong>MockSMSProvider (Active)</strong></div>
                            <div>HTTP Gateway: <strong>Configurable (CDAC / Twilio)</strong></div>
                            <div>Rate Limit: <strong>100 msg/sec burst, 10/min per target</strong></div>
                            <div>Fallback: <strong>District Disaster Helpline (1077)</strong></div>
                            <div>SMS Enabled Flag: <strong>false (Safe Dev Mode)</strong></div>
                        </div>
                    </div>

                    <div className="card" style={{ padding: '1.25rem', background: '#f8fafc', border: '1px solid #e2e8f0' }}>
                        <h4 style={{ margin: '0 0 0.5rem 0', fontSize: '0.9rem', fontWeight: 700, color: '#0f172a' }}>
                            Regulatory Notice (TRAI/CDAC)
                        </h4>
                        <div style={{ fontSize: '0.75rem', color: '#64748b', lineHeight: 1.5 }}>
                            All SMS broadcasts must adhere to TRAI Telecom Commercial Communications Customer Preference Regulations (TCCCPR, 2018). External delivery requires explicit user consent timestamping and verified Indian cellular numbers.
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
