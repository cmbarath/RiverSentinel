"use client";

import React, { useState, useEffect, useCallback } from "react";
import { supabase } from "@/lib/supabaseClient";

interface StationMeta {
    id: string;
    station_code: string;
    station_name: string;
    location_name: string;
}

interface AlertItem {
    id: string;
    alert_code: string;
    category: string;
    severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
    title: string;
    description: string;
    status: "active" | "acknowledged" | "resolved";
    occurrence_count: number;
    measured_value: number | null;
    expected_threshold: number | null;
    threshold_unit: string | null;
    provenance: string;
    quality_status: string;
    first_triggered_at: string;
    last_triggered_at: string;
    acknowledged_at?: string | null;
    resolved_at?: string | null;
    resolution_reason?: string | null;
    station?: StationMeta | null;
}

interface AlertEvent {
    id: string;
    event_type: string;
    actor_id: string | null;
    metadata: Record<string, any>;
    created_at: string;
}

interface AlertRule {
    id: string;
    rule_code: string;
    name: string;
    description: string;
    category: string;
    parameter: string;
    operator: string;
    threshold_value: number;
    threshold_unit: string;
    severity: string;
    enabled: boolean;
    cooldown_seconds: number;
}

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:5000";

export default function AuthorityAlerts() {
    const [alerts, setAlerts] = useState<AlertItem[]>([]);
    const [rules, setRules] = useState<AlertRule[]>([]);
    const [loading, setLoading] = useState<boolean>(true);
    const [tabView, setTabView] = useState<"active" | "acknowledged" | "resolved" | "rules">("active");
    
    // Filters
    const [severityFilter, setSeverityFilter] = useState<string>("ALL");
    const [categoryFilter, setCategoryFilter] = useState<string>("ALL");
    
    // Selected alert for modal inspection
    const [selectedAlert, setSelectedAlert] = useState<AlertItem | null>(null);
    const [alertEvents, setAlertEvents] = useState<AlertEvent[]>([]);
    const [deliverySummary, setDeliverySummary] = useState<Record<string, Record<string, number>> | null>(null);
    const [modalLoading, setModalLoading] = useState<boolean>(false);
    
    // Action inputs
    const [ackNotes, setAckNotes] = useState<string>("");
    const [resolveReason, setResolveReason] = useState<string>("");
    const [actionLoading, setActionLoading] = useState<boolean>(false);
    const [actionFeedback, setActionFeedback] = useState<string | null>(null);
    
    // Outbox trigger
    const [outboxRunning, setOutboxRunning] = useState<boolean>(false);
    const [outboxMessage, setOutboxMessage] = useState<string | null>(null);

    const getAuthHeaders = async () => {
        const { data } = await supabase.auth.getSession();
        const token = data?.session?.access_token;
        return {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {})
        };
    };

    const fetchAlerts = useCallback(async () => {
        setLoading(true);
        try {
            const headers = await getAuthHeaders();
            const statusParam = tabView === "rules" ? "active" : tabView;
            const queryParams = new URLSearchParams({
                status: statusParam,
                severity: severityFilter,
                category: categoryFilter,
                limit: "100"
            });

            const res = await fetch(`${BACKEND_URL}/api/v1/alerts?${queryParams.toString()}`, { headers });
            if (res.ok) {
                const data = await res.json();
                setAlerts(data.alerts || []);
            }
        } catch (err) {
            console.error("Failed to fetch alerts:", err);
        } finally {
            setLoading(false);
        }
    }, [tabView, severityFilter, categoryFilter]);

    const fetchRules = useCallback(async () => {
        try {
            const headers = await getAuthHeaders();
            const res = await fetch(`${BACKEND_URL}/api/v1/alerts/rules`, { headers });
            if (res.ok) {
                const data = await res.json();
                setRules(data.rules || []);
            }
        } catch (err) {
            console.error("Failed to fetch rules:", err);
        }
    }, []);

    useEffect(() => {
        if (tabView === "rules") {
            fetchRules();
        } else {
            fetchAlerts();
        }
    }, [tabView, fetchAlerts, fetchRules]);

    const handleInspectAlert = async (alert: AlertItem) => {
        setSelectedAlert(alert);
        setModalLoading(true);
        setActionFeedback(null);
        try {
            const headers = await getAuthHeaders();
            const res = await fetch(`${BACKEND_URL}/api/v1/alerts/${alert.id}`, { headers });
            if (res.ok) {
                const data = await res.json();
                if (data.alert) {
                    setAlertEvents(data.alert.events || []);
                    setDeliverySummary(data.alert.delivery_summary || null);
                }
            }
        } catch (err) {
            console.error("Failed to fetch alert details:", err);
        } finally {
            setModalLoading(false);
        }
    };

    const handleAcknowledge = async (alertId: string) => {
        setActionLoading(true);
        setActionFeedback(null);
        try {
            const headers = await getAuthHeaders();
            const res = await fetch(`${BACKEND_URL}/api/v1/alerts/${alertId}/acknowledge`, {
                method: "POST",
                headers,
                body: JSON.stringify({ notes: ackNotes })
            });
            const data = await res.json();
            if (res.ok) {
                setActionFeedback("Alert acknowledged successfully.");
                setAckNotes("");
                fetchAlerts();
                if (selectedAlert) {
                    handleInspectAlert({ ...selectedAlert, status: "acknowledged" });
                }
            } else {
                setActionFeedback(`Error: ${data.message || "Failed to acknowledge"}`);
            }
        } catch (err: any) {
            setActionFeedback(`Error: ${err.message}`);
        } finally {
            setActionLoading(false);
        }
    };

    const handleResolve = async (alertId: string) => {
        if (!resolveReason.trim()) {
            setActionFeedback("Resolution reason is required.");
            return;
        }
        setActionLoading(true);
        setActionFeedback(null);
        try {
            const headers = await getAuthHeaders();
            const res = await fetch(`${BACKEND_URL}/api/v1/alerts/${alertId}/resolve`, {
                method: "POST",
                headers,
                body: JSON.stringify({ reason: resolveReason })
            });
            const data = await res.json();
            if (res.ok) {
                setActionFeedback("Alert resolved and closed.");
                setResolveReason("");
                fetchAlerts();
                if (selectedAlert) {
                    handleInspectAlert({ ...selectedAlert, status: "resolved", resolution_reason: resolveReason });
                }
            } else {
                setActionFeedback(`Error: ${data.message || "Failed to resolve"}`);
            }
        } catch (err: any) {
            setActionFeedback(`Error: ${err.message}`);
        } finally {
            setActionLoading(false);
        }
    };

    const handleProcessOutbox = async () => {
        setOutboxRunning(true);
        setOutboxMessage(null);
        try {
            const headers = await getAuthHeaders();
            const res = await fetch(`${BACKEND_URL}/api/v1/notifications/process-outbox`, {
                method: "POST",
                headers
            });
            const data = await res.json();
            if (res.ok) {
                const s = data.summary;
                setOutboxMessage(`Outbox Processed: In-App Delivered: ${s.in_app_delivered}, SMS Dispatched: ${s.sms_dispatched}, Suppressed: ${s.sms_suppressed}, Errors: ${s.errors}`);
            } else {
                setOutboxMessage(`Outbox error: ${data.message}`);
            }
        } catch (err: any) {
            setOutboxMessage(`Worker invocation error: ${err.message}`);
        } finally {
            setOutboxRunning(false);
        }
    };

    const getSeverityBadge = (sev: string) => {
        switch (sev) {
            case "CRITICAL":
                return <span style={{ background: "#fee2e2", color: "#b91c1c", padding: "0.25rem 0.6rem", borderRadius: "999px", fontSize: "0.75rem", fontWeight: 700 }}>CRITICAL</span>;
            case "HIGH":
                return <span style={{ background: "#ffedd5", color: "#c2410c", padding: "0.25rem 0.6rem", borderRadius: "999px", fontSize: "0.75rem", fontWeight: 700 }}>HIGH</span>;
            case "MEDIUM":
                return <span style={{ background: "#fef9c3", color: "#854d0e", padding: "0.25rem 0.6rem", borderRadius: "999px", fontSize: "0.75rem", fontWeight: 700 }}>MEDIUM</span>;
            case "LOW":
            default:
                return <span style={{ background: "#e0f2fe", color: "#0369a1", padding: "0.25rem 0.6rem", borderRadius: "999px", fontSize: "0.75rem", fontWeight: 700 }}>LOW</span>;
        }
    };

    const getCategoryBadge = (cat: string) => {
        return (
            <span style={{ background: "#f1f5f9", color: "#475569", padding: "0.2rem 0.5rem", borderRadius: "0.375rem", fontSize: "0.75rem", fontWeight: 600 }}>
                {cat.replace("_", " ")}
            </span>
        );
    };

    return (
        <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
            {/* Header & Outbox Action */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem" }}>
                <div>
                    <h2 style={{ fontSize: "1.5rem", fontWeight: 800, color: "#0f172a", margin: 0 }}>
                        Alert Center & Notification Engine
                    </h2>
                    <p style={{ margin: "0.25rem 0 0 0", fontSize: "0.875rem", color: "#64748b" }}>
                        Database-backed real-time detection, CPCB & CWC threshold screening, lifecycle resolution, and telephony outbox.
                    </p>
                </div>

                <div style={{ display: "flex", gap: "0.75rem" }}>
                    <button
                        onClick={handleProcessOutbox}
                        disabled={outboxRunning}
                        className="btn btn-secondary"
                        style={{ fontSize: "0.85rem", padding: "0.5rem 1rem", display: "flex", alignItems: "center", gap: "0.5rem" }}
                    >
                        {outboxRunning ? "⏳ Processing..." : "⚡ Run Outbox Worker"}
                    </button>
                    <button
                        onClick={fetchAlerts}
                        className="btn btn-primary"
                        style={{ fontSize: "0.85rem", padding: "0.5rem 1rem" }}
                    >
                        🔄 Refresh
                    </button>
                </div>
            </div>

            {outboxMessage && (
                <div style={{ padding: "0.75rem 1rem", borderRadius: "0.5rem", background: "#f0fdf4", border: "1px solid #bbf7d0", color: "#166534", fontSize: "0.85rem" }}>
                    {outboxMessage}
                </div>
            )}

            {/* Navigation Tabs */}
            <div style={{ display: "flex", borderBottom: "2px solid #e2e8f0", gap: "1.5rem" }}>
                <button
                    onClick={() => setTabView("active")}
                    style={{
                        padding: "0.75rem 0.25rem",
                        background: "none",
                        border: "none",
                        borderBottom: tabView === "active" ? "3px solid #dc2626" : "3px solid transparent",
                        color: tabView === "active" ? "#dc2626" : "#64748b",
                        fontWeight: tabView === "active" ? 700 : 500,
                        cursor: "pointer",
                        fontSize: "0.95rem"
                    }}
                >
                    🚨 Active Alerts
                </button>
                <button
                    onClick={() => setTabView("acknowledged")}
                    style={{
                        padding: "0.75rem 0.25rem",
                        background: "none",
                        border: "none",
                        borderBottom: tabView === "acknowledged" ? "3px solid #d97706" : "3px solid transparent",
                        color: tabView === "acknowledged" ? "#d97706" : "#64748b",
                        fontWeight: tabView === "acknowledged" ? 700 : 500,
                        cursor: "pointer",
                        fontSize: "0.95rem"
                    }}
                >
                    👀 Acknowledged
                </button>
                <button
                    onClick={() => setTabView("resolved")}
                    style={{
                        padding: "0.75rem 0.25rem",
                        background: "none",
                        border: "none",
                        borderBottom: tabView === "resolved" ? "3px solid #16a34a" : "3px solid transparent",
                        color: tabView === "resolved" ? "#16a34a" : "#64748b",
                        fontWeight: tabView === "resolved" ? 700 : 500,
                        cursor: "pointer",
                        fontSize: "0.95rem"
                    }}
                >
                    ✅ Resolved History
                </button>
                <button
                    onClick={() => setTabView("rules")}
                    style={{
                        padding: "0.75rem 0.25rem",
                        background: "none",
                        border: "none",
                        borderBottom: tabView === "rules" ? "3px solid #2563eb" : "3px solid transparent",
                        color: tabView === "rules" ? "#2563eb" : "#64748b",
                        fontWeight: tabView === "rules" ? 700 : 500,
                        cursor: "pointer",
                        fontSize: "0.95rem"
                    }}
                >
                    ⚙️ Configured Threshold Rules
                </button>
            </div>

            {/* Filter Bar (for alerts) */}
            {tabView !== "rules" && (
                <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap", alignItems: "center", background: "#ffffff", padding: "1rem", borderRadius: "0.75rem", border: "1px solid #e2e8f0" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                        <span style={{ fontSize: "0.85rem", fontWeight: 600, color: "#475569" }}>Severity:</span>
                        <select
                            value={severityFilter}
                            onChange={(e) => setSeverityFilter(e.target.value)}
                            style={{ padding: "0.4rem 0.75rem", borderRadius: "0.375rem", border: "1px solid #cbd5e1", fontSize: "0.85rem" }}
                        >
                            <option value="ALL">All Severities</option>
                            <option value="CRITICAL">Critical</option>
                            <option value="HIGH">High</option>
                            <option value="MEDIUM">Medium</option>
                            <option value="LOW">Low</option>
                        </select>
                    </div>

                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                        <span style={{ fontSize: "0.85rem", fontWeight: 600, color: "#475569" }}>Category:</span>
                        <select
                            value={categoryFilter}
                            onChange={(e) => setCategoryFilter(e.target.value)}
                            style={{ padding: "0.4rem 0.75rem", borderRadius: "0.375rem", border: "1px solid #cbd5e1", fontSize: "0.85rem" }}
                        >
                            <option value="ALL">All Categories</option>
                            <option value="FLOOD">CWC Flood</option>
                            <option value="WATER_QUALITY">CPCB Water Quality</option>
                            <option value="DEVICE_HEALTH">IoT Node Health</option>
                            <option value="POLLUTION_REPORT">Citizen Pollution Reports</option>
                        </select>
                    </div>

                    <div style={{ marginLeft: "auto", fontSize: "0.85rem", color: "#64748b" }}>
                        Showing <strong>{alerts.length}</strong> alerts
                    </div>
                </div>
            )}

            {/* Content Area */}
            {tabView === "rules" ? (
                /* Rules Configuration View */
                <div className="card">
                    <h3 style={{ margin: "0 0 1rem 0", fontWeight: 700 }}>Active CPCB & CWC Regulatory Rules</h3>
                    <p style={{ margin: "0 0 1.5rem 0", fontSize: "0.85rem", color: "#64748b" }}>
                        Standardized threshold criteria evaluated continuously against incoming sensor observations.
                    </p>

                    <div style={{ overflowX: "auto" }}>
                        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem", textAlign: "left" }}>
                            <thead>
                                <tr style={{ borderBottom: "2px solid #e2e8f0", color: "#475569" }}>
                                    <th style={{ padding: "0.75rem" }}>Rule Code</th>
                                    <th style={{ padding: "0.75rem" }}>Name</th>
                                    <th style={{ padding: "0.75rem" }}>Category</th>
                                    <th style={{ padding: "0.75rem" }}>Condition</th>
                                    <th style={{ padding: "0.75rem" }}>Severity</th>
                                    <th style={{ padding: "0.75rem" }}>Cooldown</th>
                                    <th style={{ padding: "0.75rem" }}>Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                {rules.map((rule) => (
                                    <tr key={rule.id} style={{ borderBottom: "1px solid #f1f5f9" }}>
                                        <td style={{ padding: "0.75rem", fontFamily: "monospace", fontWeight: 700, color: "#1e293b" }}>{rule.rule_code}</td>
                                        <td style={{ padding: "0.75rem", fontWeight: 600 }}>{rule.name}</td>
                                        <td style={{ padding: "0.75rem" }}>{getCategoryBadge(rule.category)}</td>
                                        <td style={{ padding: "0.75rem", fontFamily: "monospace" }}>
                                            {rule.parameter} {rule.operator} {rule.threshold_value} {rule.threshold_unit}
                                        </td>
                                        <td style={{ padding: "0.75rem" }}>{getSeverityBadge(rule.severity)}</td>
                                        <td style={{ padding: "0.75rem", color: "#64748b" }}>{rule.cooldown_seconds}s</td>
                                        <td style={{ padding: "0.75rem" }}>
                                            <span style={{ color: rule.enabled ? "#16a34a" : "#94a3b8", fontWeight: 600 }}>
                                                {rule.enabled ? "Active" : "Disabled"}
                                            </span>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            ) : (
                /* Alerts Cards Grid */
                <div>
                    {loading ? (
                        <div className="card" style={{ padding: "3rem", textAlign: "center", color: "#64748b" }}>
                            ⏳ Loading alerts from Supabase...
                        </div>
                    ) : alerts.length === 0 ? (
                        <div className="card" style={{ padding: "3rem", textAlign: "center", color: "#64748b" }}>
                            ✅ No {tabView} alerts matching selected criteria.
                        </div>
                    ) : (
                        <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
                            {alerts.map((alt) => (
                                <div
                                    key={alt.id}
                                    className="card"
                                    style={{
                                        borderLeft: `5px solid ${
                                            alt.severity === "CRITICAL" ? "#ef4444" : alt.severity === "HIGH" ? "#f97316" : alt.severity === "MEDIUM" ? "#eab308" : "#0284c7"
                                        }`,
                                        display: "flex",
                                        flexDirection: "column",
                                        gap: "0.75rem"
                                    }}
                                >
                                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: "0.5rem" }}>
                                        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", flexWrap: "wrap" }}>
                                            <span style={{ fontFamily: "monospace", fontSize: "0.8rem", fontWeight: 700, color: "#64748b" }}>
                                                {alt.alert_code}
                                            </span>
                                            {getSeverityBadge(alt.severity)}
                                            {getCategoryBadge(alt.category)}
                                            <span style={{ fontSize: "0.75rem", padding: "0.15rem 0.4rem", borderRadius: "0.25rem", background: alt.provenance === "simulated" ? "#fef3c7" : "#e0f2fe", color: alt.provenance === "simulated" ? "#92400e" : "#0369a1", fontWeight: 600 }}>
                                                {alt.provenance}
                                            </span>
                                            {alt.occurrence_count > 1 && (
                                                <span style={{ fontSize: "0.75rem", background: "#fee2e2", color: "#991b1b", padding: "0.15rem 0.45rem", borderRadius: "999px", fontWeight: 700 }}>
                                                    {alt.occurrence_count} occurrences
                                                </span>
                                            )}
                                        </div>

                                        <div style={{ fontSize: "0.75rem", color: "#64748b" }}>
                                            Last triggered: {new Date(alt.last_triggered_at).toLocaleString("en-IN", { timeZone: "Asia/Kolkata" })}
                                        </div>
                                    </div>

                                    <div>
                                        <h4 style={{ margin: "0 0 0.35rem 0", fontSize: "1.05rem", fontWeight: 700, color: "#0f172a" }}>
                                            {alt.title}
                                        </h4>
                                        <p style={{ margin: 0, fontSize: "0.875rem", color: "#475569", lineHeight: 1.5 }}>
                                            {alt.description}
                                        </p>
                                    </div>

                                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem", paddingTop: "0.5rem", borderTop: "1px solid #f1f5f9" }}>
                                        <div style={{ fontSize: "0.8rem", color: "#64748b" }}>
                                            📍 <strong>{alt.station?.station_name || "Varanasi Ganga Station"}</strong> ({alt.station?.location_name || "Ghat Corridor"})
                                            {alt.measured_value !== null && (
                                                <span style={{ marginLeft: "1rem" }}>
                                                    Measured: <strong style={{ color: "#0f172a" }}>{alt.measured_value} {alt.threshold_unit}</strong>
                                                    {alt.expected_threshold !== null && ` (Threshold: ${alt.expected_threshold} ${alt.threshold_unit})`}
                                                </span>
                                            )}
                                        </div>

                                        <button
                                            onClick={() => handleInspectAlert(alt)}
                                            className="btn btn-secondary"
                                            style={{ fontSize: "0.8rem", padding: "0.35rem 0.8rem" }}
                                        >
                                            Inspect & Manage ➔
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            )}

            {/* Alert Inspection & Action Modal */}
            {selectedAlert && (
                <div style={{
                    position: "fixed",
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    background: "rgba(15, 23, 42, 0.6)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    padding: "1.5rem",
                    zIndex: 9999
                }}>
                    <div style={{
                        background: "#ffffff",
                        borderRadius: "1rem",
                        maxWidth: "750px",
                        width: "100%",
                        maxHeight: "90vh",
                        overflowY: "auto",
                        padding: "2rem",
                        boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1)"
                    }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "1.25rem" }}>
                            <div>
                                <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", marginBottom: "0.25rem" }}>
                                    <span style={{ fontFamily: "monospace", fontWeight: 700, color: "#64748b" }}>{selectedAlert.alert_code}</span>
                                    {getSeverityBadge(selectedAlert.severity)}
                                    {getCategoryBadge(selectedAlert.category)}
                                </div>
                                <h3 style={{ margin: 0, fontWeight: 800, fontSize: "1.25rem", color: "#0f172a" }}>{selectedAlert.title}</h3>
                            </div>
                            <button
                                onClick={() => setSelectedAlert(null)}
                                style={{ background: "none", border: "none", fontSize: "1.5rem", cursor: "pointer", color: "#94a3b8" }}
                            >
                                ✕
                            </button>
                        </div>

                        <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem", fontSize: "0.875rem" }}>
                            <div style={{ background: "#f8fafc", padding: "1rem", borderRadius: "0.5rem", border: "1px solid #e2e8f0" }}>
                                <div style={{ color: "#334155", marginBottom: "0.5rem" }}>{selectedAlert.description}</div>
                                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.5rem", fontSize: "0.8rem", color: "#64748b" }}>
                                    <div>Status: <strong style={{ color: "#0f172a", textTransform: "uppercase" }}>{selectedAlert.status}</strong></div>
                                    <div>Occurrences: <strong style={{ color: "#0f172a" }}>{selectedAlert.occurrence_count}</strong></div>
                                    <div>Station: <strong>{selectedAlert.station?.station_name || "Varanasi Station"}</strong></div>
                                    <div>Quality Status: <strong>{selectedAlert.quality_status}</strong></div>
                                    <div>First Triggered: <strong>{new Date(selectedAlert.first_triggered_at).toLocaleString("en-IN")}</strong></div>
                                    <div>Last Triggered: <strong>{new Date(selectedAlert.last_triggered_at).toLocaleString("en-IN")}</strong></div>
                                </div>
                            </div>

                            {/* Delivery Summary */}
                            {deliverySummary && (
                                <div style={{ border: "1px solid #e2e8f0", borderRadius: "0.5rem", padding: "0.75rem 1rem" }}>
                                    <div style={{ fontWeight: 700, color: "#1e293b", marginBottom: "0.5rem" }}>📢 Outbox Delivery Summary</div>
                                    <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap", fontSize: "0.8rem" }}>
                                        {Object.entries(deliverySummary).map(([channel, statuses]) => (
                                            <div key={channel} style={{ background: "#f1f5f9", padding: "0.4rem 0.75rem", borderRadius: "0.375rem" }}>
                                                <strong style={{ textTransform: "uppercase" }}>{channel}:</strong>{" "}
                                                {Object.entries(statuses).map(([st, cnt]) => `${st}=${cnt}`).join(", ")}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Actions Section */}
                            <div style={{ border: "1px solid #cbd5e1", borderRadius: "0.5rem", padding: "1rem", background: "#f8fafc" }}>
                                <h4 style={{ margin: "0 0 0.75rem 0", fontWeight: 700, color: "#1e293b" }}>Operational Response Actions</h4>

                                {actionFeedback && (
                                    <div style={{ padding: "0.5rem 0.75rem", borderRadius: "0.375rem", background: "#eff6ff", border: "1px solid #bfdbfe", color: "#1e40af", marginBottom: "0.75rem", fontSize: "0.8rem" }}>
                                        {actionFeedback}
                                    </div>
                                )}

                                {selectedAlert.status === "active" && (
                                    <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem", marginBottom: "1rem" }}>
                                        <label style={{ fontWeight: 600, color: "#475569", fontSize: "0.8rem" }}>Acknowledge Alert (Field Officer Note):</label>
                                        <div style={{ display: "flex", gap: "0.5rem" }}>
                                            <input
                                                type="text"
                                                placeholder="e.g. Field team dispatched to inspect Assi Ghat sensor."
                                                value={ackNotes}
                                                onChange={(e) => setAckNotes(e.target.value)}
                                                style={{ flex: 1, padding: "0.5rem 0.75rem", borderRadius: "0.375rem", border: "1px solid #cbd5e1", fontSize: "0.85rem" }}
                                            />
                                            <button
                                                onClick={() => handleAcknowledge(selectedAlert.id)}
                                                disabled={actionLoading}
                                                className="btn btn-secondary"
                                                style={{ fontSize: "0.8rem", padding: "0.5rem 1rem", fontWeight: 700 }}
                                            >
                                                Acknowledge
                                            </button>
                                        </div>
                                    </div>
                                )}

                                {selectedAlert.status !== "resolved" && (
                                    <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                                        <label style={{ fontWeight: 600, color: "#475569", fontSize: "0.8rem" }}>Resolve & Close Alert (Resolution Reason Required):</label>
                                        <div style={{ display: "flex", gap: "0.5rem" }}>
                                            <input
                                                type="text"
                                                placeholder="e.g. Water level normalized below warning threshold. Drain gate closed."
                                                value={resolveReason}
                                                onChange={(e) => setResolveReason(e.target.value)}
                                                style={{ flex: 1, padding: "0.5rem 0.75rem", borderRadius: "0.375rem", border: "1px solid #cbd5e1", fontSize: "0.85rem" }}
                                            />
                                            <button
                                                onClick={() => handleResolve(selectedAlert.id)}
                                                disabled={actionLoading}
                                                className="btn btn-primary"
                                                style={{ fontSize: "0.8rem", padding: "0.5rem 1rem", fontWeight: 700, background: "#16a34a", borderColor: "#16a34a" }}
                                            >
                                                Resolve Alert
                                            </button>
                                        </div>
                                    </div>
                                )}

                                {selectedAlert.status === "resolved" && (
                                    <div style={{ color: "#16a34a", fontWeight: 600, fontSize: "0.85rem" }}>
                                        ✓ This alert has been resolved. Reason: {selectedAlert.resolution_reason || "Automated threshold recovery."}
                                    </div>
                                )}
                            </div>

                            {/* Event Audit Trail */}
                            <div>
                                <h4 style={{ margin: "0 0 0.5rem 0", fontWeight: 700, color: "#1e293b" }}>Lifecycle Event Audit Trail</h4>
                                {modalLoading ? (
                                    <div style={{ color: "#64748b" }}>Loading audit events...</div>
                                ) : alertEvents.length === 0 ? (
                                    <div style={{ color: "#94a3b8" }}>No lifecycle events recorded.</div>
                                ) : (
                                    <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", maxHeight: "200px", overflowY: "auto" }}>
                                        {alertEvents.map((ev) => (
                                            <div key={ev.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "0.5rem 0.75rem", borderRadius: "0.375rem", background: "#f8fafc", border: "1px solid #e2e8f0", fontSize: "0.8rem" }}>
                                                <div>
                                                    <span style={{ fontWeight: 700, color: "#0f172a", textTransform: "uppercase" }}>{ev.event_type}</span>
                                                    {ev.metadata?.notes && <span style={{ marginLeft: "0.5rem", color: "#475569" }}>Note: {ev.metadata.notes}</span>}
                                                    {ev.metadata?.reason && <span style={{ marginLeft: "0.5rem", color: "#475569" }}>Reason: {ev.metadata.reason}</span>}
                                                </div>
                                                <div style={{ color: "#64748b" }}>
                                                    {new Date(ev.created_at).toLocaleString("en-IN")}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
