"use client";

import React, { useState, useEffect } from "react";
import { supabase } from "@/lib/supabaseClient";

interface UserProfile {
    id: string;
    email: string;
    full_name?: string;
    role: string;
    organization?: string;
    phone?: string;
    account_status?: string;
    created_at?: string;
}

interface CitizenReport {
    id: string;
    pollution_level: string;
    location_name: string;
    assessment: string;
    description: string;
    status: string;
    created_at: string;
}

interface UserNotificationItem {
    delivery_id: string;
    alert_id: string;
    delivery_status: string;
    title: string;
    description: string;
    is_read: boolean;
    read_at: string | null;
    created_at: string;
    alert_code: string;
    category: string;
    severity: string;
    alert_status: string;
    station_name: string;
    location_name: string;
}

interface NotificationPreferences {
    in_app_enabled: boolean;
    email_enabled: boolean;
    sms_enabled: boolean;
    preferred_severities: string[];
    preferred_categories: string[];
    phone_number_verified: boolean;
    email_verified: boolean;
    consent_timestamp: string | null;
}

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:5000";

export const Notifications = () => {
    const [notifications, setNotifications] = useState<UserNotificationItem[]>([]);
    const [publicAlerts, setPublicAlerts] = useState<any[]>([]);
    const [unreadCount, setUnreadCount] = useState<number>(0);
    const [loading, setLoading] = useState<boolean>(true);
    const [isLoggedIn, setIsLoggedIn] = useState<boolean>(false);
    const [actionLoading, setActionLoading] = useState<boolean>(false);

    const getAuthHeaders = async () => {
        const { data } = await supabase.auth.getSession();
        const token = data?.session?.access_token;
        return {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {})
        };
    };

    const fetchNotifications = async () => {
        setLoading(true);
        try {
            const { data } = await supabase.auth.getSession();
            const token = data?.session?.access_token;

            if (token) {
                setIsLoggedIn(true);
                const res = await fetch(`${BACKEND_URL}/api/v1/notifications?limit=20`, {
                    headers: { Authorization: `Bearer ${token}` }
                });
                if (res.ok) {
                    const d = await res.json();
                    setNotifications(d.notifications || []);
                    setUnreadCount(d.unread_count || 0);
                }
            } else {
                setIsLoggedIn(false);
            }

            // Also fetch active public alerts as baseline
            const alertRes = await fetch(`${BACKEND_URL}/api/v1/alerts?limit=10`);
            if (alertRes.ok) {
                const ad = await alertRes.json();
                setPublicAlerts(ad.alerts || []);
            }
        } catch (err) {
            console.error("Failed to load notifications:", err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchNotifications();
    }, []);

    const markAsRead = async (deliveryId: string) => {
        setActionLoading(true);
        try {
            const headers = await getAuthHeaders();
            const res = await fetch(`${BACKEND_URL}/api/v1/notifications/${deliveryId}/read`, {
                method: "POST",
                headers
            });
            if (res.ok) {
                setNotifications((prev) =>
                    prev.map((n) => (n.delivery_id === deliveryId ? { ...n, is_read: true, read_at: new Date().toISOString() } : n))
                );
                setUnreadCount((c) => Math.max(0, c - 1));
            }
        } catch (err) {
            console.error("Failed to mark notification read:", err);
        } finally {
            setActionLoading(false);
        }
    };

    const markAllAsRead = async () => {
        setActionLoading(true);
        try {
            const headers = await getAuthHeaders();
            const res = await fetch(`${BACKEND_URL}/api/v1/notifications/mark-all-read`, {
                method: "POST",
                headers
            });
            if (res.ok) {
                setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true, read_at: new Date().toISOString() })));
                setUnreadCount(0);
            }
        } catch (err) {
            console.error("Failed to mark all read:", err);
        } finally {
            setActionLoading(false);
        }
    };

    return (
        <div className="card">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem", flexWrap: "wrap", gap: "0.5rem" }}>
                <div>
                    <h3 style={{ margin: 0, fontWeight: 700 }}>Operational Alerts & Notification Inbox</h3>
                    <p style={{ margin: "0.25rem 0 0 0", fontSize: "0.85rem", color: "#64748b" }}>
                        Real-time notifications generated from CPCB & CWC threshold screening and citizen reports.
                    </p>
                </div>
                {isLoggedIn && unreadCount > 0 && (
                    <button
                        onClick={markAllAsRead}
                        disabled={actionLoading}
                        className="btn btn-secondary"
                        style={{ fontSize: "0.8rem", padding: "0.35rem 0.75rem" }}
                    >
                        ✓ Mark All as Read ({unreadCount})
                    </button>
                )}
            </div>

            {loading ? (
                <div style={{ padding: "2rem", textAlign: "center", color: "#64748b" }}>
                    ⏳ Loading notification feed...
                </div>
            ) : isLoggedIn && notifications.length > 0 ? (
                /* Authenticated In-App Inbox */
                <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                    {notifications.map((n) => (
                        <div
                            key={n.delivery_id}
                            style={{
                                display: "flex",
                                gap: "1rem",
                                padding: "1rem",
                                borderRadius: "0.75rem",
                                background: n.is_read ? "#f8fafc" : "#ffffff",
                                border: `1px solid ${n.is_read ? "#e2e8f0" : "#cbd5e1"}`,
                                borderLeft: `5px solid ${
                                    n.severity === "CRITICAL" ? "#ef4444" : n.severity === "HIGH" ? "#f97316" : n.severity === "MEDIUM" ? "#eab308" : "#0284c7"
                                }`
                            }}
                        >
                            <div style={{ flex: 1 }}>
                                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.25rem", alignItems: "center" }}>
                                    <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                                        <span style={{ fontWeight: 700, fontSize: "0.95rem", color: "#0f172a" }}>
                                            {n.title}
                                        </span>
                                        {!n.is_read && (
                                            <span style={{ fontSize: "0.65rem", background: "#ef4444", color: "white", padding: "0.1rem 0.4rem", borderRadius: "999px", fontWeight: 700 }}>
                                                NEW
                                            </span>
                                        )}
                                        <span style={{ fontSize: "0.7rem", color: "#64748b", fontFamily: "monospace" }}>
                                            {n.alert_code}
                                        </span>
                                    </div>
                                    <div style={{ fontSize: "0.75rem", color: "#64748b" }}>
                                        {new Date(n.created_at).toLocaleString("en-IN")}
                                    </div>
                                </div>
                                <div style={{ fontSize: "0.85rem", color: "#475569", lineHeight: 1.4, marginBottom: "0.5rem" }}>
                                    {n.description}
                                </div>
                                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "0.75rem", color: "#64748b" }}>
                                    <span>📍 {n.station_name} ({n.location_name})</span>
                                    {!n.is_read && (
                                        <button
                                            onClick={() => markAsRead(n.delivery_id)}
                                            style={{ background: "none", border: "none", color: "#0284c7", cursor: "pointer", fontWeight: 600, padding: 0 }}
                                        >
                                            Mark as read
                                        </button>
                                    )}
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            ) : publicAlerts.length > 0 ? (
                /* Public Active Alerts Feed */
                <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                    <div style={{ fontSize: "0.8rem", color: "#64748b", marginBottom: "0.25rem" }}>
                        Active Ganga River Environmental Alerts:
                    </div>
                    {publicAlerts.map((alt) => (
                        <div
                            key={alt.id}
                            style={{
                                display: "flex",
                                gap: "1rem",
                                padding: "1rem",
                                borderRadius: "0.75rem",
                                background: "#f8fafc",
                                border: "1px solid #e2e8f0",
                                borderLeft: `5px solid ${alt.severity === "CRITICAL" ? "#ef4444" : alt.severity === "HIGH" ? "#f97316" : "#0284c7"}`
                            }}
                        >
                            <div style={{ flex: 1 }}>
                                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.25rem" }}>
                                    <div style={{ fontWeight: 700, fontSize: "0.95rem", color: "#0f172a" }}>{alt.title}</div>
                                    <div style={{ fontSize: "0.75rem", color: "#64748b" }}>
                                        {new Date(alt.last_triggered_at).toLocaleString("en-IN")}
                                    </div>
                                </div>
                                <div style={{ fontSize: "0.85rem", color: "#475569", lineHeight: 1.4 }}>{alt.description}</div>
                            </div>
                        </div>
                    ))}
                </div>
            ) : (
                <div style={{ padding: "2rem", textAlign: "center", color: "#64748b" }}>
                    ✅ All Varanasi monitoring stations operating within normal regulatory thresholds.
                </div>
            )}
        </div>
    );
};

export const Profile = () => {
    const [profile, setProfile] = useState<UserProfile | null>(null);
    const [reports, setReports] = useState<CitizenReport[]>([]);
    const [loading, setLoading] = useState<boolean>(true);
    const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
    
    // Notification Preferences
    const [prefs, setPrefs] = useState<NotificationPreferences>({
        in_app_enabled: true,
        email_enabled: false,
        sms_enabled: false,
        preferred_severities: ["CRITICAL", "HIGH"],
        preferred_categories: ["FLOOD", "WATER_QUALITY", "POLLUTION_REPORT"],
        phone_number_verified: false,
        email_verified: false,
        consent_timestamp: null
    });
    const [savingPrefs, setSavingPrefs] = useState<boolean>(false);
    const [prefsMessage, setPrefsMessage] = useState<string | null>(null);

    useEffect(() => {
        let isMounted = true;

        async function fetchUserData() {
            setLoading(true);
            try {
                const { data: sessionData } = await supabase.auth.getSession();
                const token = sessionData?.session?.access_token;

                if (!token) {
                    if (isMounted) {
                        setIsAuthenticated(false);
                        setLoading(false);
                    }
                    return;
                }

                setIsAuthenticated(true);

                // Fetch current user profile
                const meRes = await fetch(`${BACKEND_URL}/api/auth/me`, {
                    headers: { Authorization: `Bearer ${token}` }
                });

                if (meRes.ok) {
                    const meData = await meRes.json();
                    if (isMounted) {
                        const userObj = meData.user || {};
                        const profObj = meData.profile || {};
                        setProfile({
                            id: userObj.id,
                            email: userObj.email,
                            full_name: profObj.full_name || userObj.email?.split("@")[0] || "Citizen Contributor",
                            role: meData.role || "citizen",
                            organization: profObj.organization || "General Public",
                            account_status: profObj.account_status || "active",
                            created_at: userObj.created_at,
                            phone: userObj.phone
                        });
                    }
                }

                // Fetch user notification preferences
                const prefRes = await fetch(`${BACKEND_URL}/api/v1/notifications/preferences`, {
                    headers: { Authorization: `Bearer ${token}` }
                });
                if (prefRes.ok) {
                    const prefData = await prefRes.json();
                    if (isMounted && prefData.preferences) {
                        setPrefs(prefData.preferences);
                    }
                }

                // Fetch citizen's submitted reports
                const repRes = await fetch(`${BACKEND_URL}/api/citizen/my-reports`, {
                    headers: { Authorization: `Bearer ${token}` }
                });

                if (repRes.ok) {
                    const repData = await repRes.json();
                    if (isMounted && Array.isArray(repData.reports)) {
                        setReports(repData.reports);
                    }
                }
            } catch (err) {
                console.error("Error loading user profile:", err);
            } finally {
                if (isMounted) setLoading(false);
            }
        }

        fetchUserData();
        return () => {
            isMounted = false;
        };
    }, []);

    const handleSavePreferences = async () => {
        setSavingPrefs(true);
        setPrefsMessage(null);
        try {
            const { data } = await supabase.auth.getSession();
            const token = data?.session?.access_token;
            if (!token) return;

            const res = await fetch(`${BACKEND_URL}/api/v1/notifications/preferences`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`
                },
                body: JSON.stringify(prefs)
            });
            const d = await res.json();
            if (res.ok) {
                setPrefsMessage("✓ Notification preferences updated successfully.");
            } else {
                setPrefsMessage(`Error: ${d.message || "Failed to save preferences"}`);
            }
        } catch (err: any) {
            setPrefsMessage(`Error: ${err.message}`);
        } finally {
            setSavingPrefs(false);
        }
    };

    if (loading) {
        return (
            <div className="card" style={{ padding: "3rem", textAlign: "center", color: "#64748b" }}>
                ⏳ Loading authenticated citizen profile...
            </div>
        );
    }

    if (!isAuthenticated || !profile) {
        return (
            <div className="card" style={{ padding: "3rem", textAlign: "center" }}>
                <div style={{ fontSize: "2.5rem", marginBottom: "0.5rem" }}>🔒</div>
                <h3 style={{ margin: "0 0 0.5rem 0", color: "#1e293b", fontWeight: 700 }}>Authentication Required</h3>
                <p style={{ margin: "0 0 1.5rem 0", color: "#64748b", fontSize: "0.9rem" }}>
                    Please sign in with your verified credentials to access your citizen profile, pollution report history, and alert preferences.
                </p>
                <a href="/login" className="btn btn-primary" style={{ display: "inline-block" }}>
                    Sign In to River Sentinel
                </a>
            </div>
        );
    }

    return (
        <div style={{ display: "flex", flexDirection: "column", gap: "2rem" }}>
            {/* Citizen Identity & Stats */}
            <div style={{ display: "grid", gridTemplateColumns: "minmax(300px, 1fr) minmax(280px, 1fr)", gap: "1.5rem" }}>
                <div className="card">
                    <h3 style={{ margin: "0 0 1.25rem 0", fontWeight: 700, fontSize: "1.1rem" }}>Citizen Identity</h3>
                    <div style={{ display: "flex", alignItems: "center", gap: "1.25rem", marginBottom: "1.5rem" }}>
                        <div style={{
                            width: "60px",
                            height: "60px",
                            borderRadius: "50%",
                            background: "#0284c7",
                            color: "white",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            fontSize: "1.5rem",
                            fontWeight: 800
                        }}>
                            {(profile.full_name || profile.email).charAt(0).toUpperCase()}
                        </div>
                        <div>
                            <div style={{ fontSize: "1.15rem", fontWeight: 700, color: "#0f172a" }}>
                                {profile.full_name}
                            </div>
                            <div style={{ fontSize: "0.85rem", color: "#64748b" }}>
                                {profile.email}
                            </div>
                            <span className="badge badge-blue" style={{ marginTop: "0.35rem", display: "inline-block", fontSize: "0.75rem" }}>
                                {profile.role.toUpperCase()}
                            </span>
                        </div>
                    </div>

                    <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem", fontSize: "0.85rem", borderTop: "1px solid #f1f5f9", paddingTop: "1rem" }}>
                        <div style={{ display: "flex", justifyContent: "space-between" }}>
                            <span style={{ color: "#64748b" }}>Affiliation</span>
                            <span style={{ fontWeight: 600, color: "#1e293b" }}>{profile.organization}</span>
                        </div>
                        <div style={{ display: "flex", justifyContent: "space-between" }}>
                            <span style={{ color: "#64748b" }}>Account Status</span>
                            <span style={{ fontWeight: 600, color: "#16a34a" }}>Active</span>
                        </div>
                    </div>
                </div>

                <div className="card">
                    <h3 style={{ margin: "0 0 1.25rem 0", fontWeight: 700, fontSize: "1.1rem" }}>Citizen Activity Summary</h3>
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
                        <div style={{ padding: "1rem", background: "#f8fafc", borderRadius: "0.5rem", border: "1px solid #e2e8f0" }}>
                            <div style={{ fontSize: "0.8rem", color: "#64748b", fontWeight: 600 }}>Reports Filed</div>
                            <div style={{ fontSize: "2.2rem", fontWeight: 800, color: "#0284c7", margin: "0.25rem 0" }}>
                                {reports.length}
                            </div>
                            <div style={{ fontSize: "0.75rem", color: "#64748b" }}>Ganga Watch</div>
                        </div>

                        <div style={{ padding: "1rem", background: "#f8fafc", borderRadius: "0.5rem", border: "1px solid #e2e8f0" }}>
                            <div style={{ fontSize: "0.8rem", color: "#64748b", fontWeight: 600 }}>Action Rate</div>
                            <div style={{ fontSize: "2.2rem", fontWeight: 800, color: "#16a34a", margin: "0.25rem 0" }}>
                                {reports.filter((r) => (r.status || "").toLowerCase() === "resolved").length}
                            </div>
                            <div style={{ fontSize: "0.75rem", color: "#16a34a" }}>Resolved by UPPCB</div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Notification Preferences Card (Phase 5) */}
            <div className="card">
                <h3 style={{ margin: "0 0 0.5rem 0", fontWeight: 700, fontSize: "1.1rem" }}>
                    Notification & Alert Preferences (Phase 5)
                </h3>
                <p style={{ margin: "0 0 1.5rem 0", fontSize: "0.85rem", color: "#64748b" }}>
                    Configure dispatch channels for environmental alerts. Under TRAI regulations, cellular SMS dispatch requires verified phone ownership and explicit opt-in consent.
                </p>

                {prefsMessage && (
                    <div style={{ padding: "0.75rem 1rem", borderRadius: "0.5rem", background: prefsMessage.startsWith("✓") ? "#f0fdf4" : "#fef2f2", border: `1px solid ${prefsMessage.startsWith("✓") ? "#bbf7d0" : "#fecaca"}`, fontSize: "0.85rem", marginBottom: "1rem" }}>
                        {prefsMessage}
                    </div>
                )}

                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "1.5rem", marginBottom: "1.5rem" }}>
                    <div style={{ padding: "1rem", borderRadius: "0.5rem", border: "1px solid #e2e8f0", background: "#f8fafc" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
                            <strong>In-App Notifications</strong>
                            <input
                                type="checkbox"
                                checked={prefs.in_app_enabled}
                                onChange={(e) => setPrefs({ ...prefs, in_app_enabled: e.target.checked })}
                                style={{ width: "18px", height: "18px", cursor: "pointer" }}
                            />
                        </div>
                        <p style={{ margin: 0, fontSize: "0.8rem", color: "#64748b" }}>
                            Real-time alert banner and notifications inbox inside the River Sentinel web application.
                        </p>
                    </div>

                    <div style={{ padding: "1rem", borderRadius: "0.5rem", border: "1px solid #e2e8f0", background: "#f8fafc" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
                            <strong>Email Alerts</strong>
                            <input
                                type="checkbox"
                                checked={prefs.email_enabled}
                                onChange={(e) => setPrefs({ ...prefs, email_enabled: e.target.checked })}
                                style={{ width: "18px", height: "18px", cursor: "pointer" }}
                            />
                        </div>
                        <p style={{ margin: 0, fontSize: "0.8rem", color: "#64748b" }}>
                            Receive daily digests and critical environmental warnings at {profile.email}.
                        </p>
                    </div>

                    <div style={{ padding: "1rem", borderRadius: "0.5rem", border: "1px solid #e2e8f0", background: "#f8fafc" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
                            <strong>SMS Cellular Broadcast</strong>
                            <input
                                type="checkbox"
                                checked={prefs.sms_enabled}
                                onChange={(e) => setPrefs({ ...prefs, sms_enabled: e.target.checked })}
                                style={{ width: "18px", height: "18px", cursor: "pointer" }}
                            />
                        </div>
                        <p style={{ margin: "0 0 0.5rem 0", fontSize: "0.8rem", color: "#64748b" }}>
                            Emergency CWC flood level alerts transmitted directly to your mobile phone via SMS gateway.
                        </p>
                        <div style={{ fontSize: "0.75rem", color: prefs.phone_number_verified ? "#16a34a" : "#b45309", fontWeight: 600 }}>
                            {prefs.phone_number_verified ? "✓ Phone Number Verified" : "⚠️ Phone verification required for cellular broadcast"}
                        </div>
                    </div>
                </div>

                <button
                    onClick={handleSavePreferences}
                    disabled={savingPrefs}
                    className="btn btn-primary"
                    style={{ fontSize: "0.85rem", padding: "0.5rem 1.25rem" }}
                >
                    {savingPrefs ? "Saving..." : "Save Preferences"}
                </button>
            </div>

            {/* My Submitted Reports Table */}
            <div className="card">
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.25rem" }}>
                    <div>
                        <h3 style={{ margin: 0, fontWeight: 700, fontSize: "1.1rem" }}>My Pollution Reports</h3>
                        <p style={{ margin: "0.25rem 0 0 0", fontSize: "0.85rem", color: "#64748b" }}>
                            Real reports submitted to the Uttar Pradesh Pollution Control Board database.
                        </p>
                    </div>
                    <a href="/citizen-dashboard?tab=report" className="btn btn-secondary" style={{ fontSize: "0.8rem", padding: "0.4rem 0.8rem" }}>
                        + New Report
                    </a>
                </div>

                {reports.length === 0 ? (
                    <div style={{ padding: "2.5rem", textAlign: "center", color: "#64748b", background: "#f8fafc", borderRadius: "0.5rem" }}>
                        <div style={{ fontSize: "2rem", marginBottom: "0.5rem" }}>📝</div>
                        <div style={{ fontWeight: 600, color: "#334155" }}>No Reports Submitted Yet</div>
                        <p style={{ fontSize: "0.85rem", maxWidth: "380px", margin: "0.35rem auto 1rem auto" }}>
                            Help protect the Ganga by submitting pollution observations or pipe discharges through the Report Pollution tool.
                        </p>
                    </div>
                ) : (
                    <div style={{ overflowX: "auto" }}>
                        <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: "0.85rem" }}>
                            <thead>
                                <tr style={{ borderBottom: "1px solid #e2e8f0", color: "#64748b" }}>
                                    <th style={{ padding: "0.75rem" }}>Date</th>
                                    <th style={{ padding: "0.75rem" }}>Location</th>
                                    <th style={{ padding: "0.75rem" }}>Severity</th>
                                    <th style={{ padding: "0.75rem" }}>Status</th>
                                    <th style={{ padding: "0.75rem" }}>Summary</th>
                                </tr>
                            </thead>
                            <tbody>
                                {reports.map((r) => {
                                    const st = (r.status || "PENDING").toUpperCase();
                                    const badgeClass = st === "RESOLVED" ? "badge-green" : st === "INVESTIGATING" ? "badge-blue" : st === "REJECTED" ? "badge-red" : "badge-orange";
                                    return (
                                        <tr key={r.id} style={{ borderBottom: "1px solid #f1f5f9" }}>
                                            <td style={{ padding: "0.75rem", color: "#64748b" }}>
                                                {new Date(r.created_at).toLocaleDateString()}
                                            </td>
                                            <td style={{ padding: "0.75rem", fontWeight: 600, color: "#0f172a" }}>
                                                {r.location_name || "Varanasi Ghat"}
                                            </td>
                                            <td style={{ padding: "0.75rem" }}>
                                                <span className={`badge ${r.pollution_level === "High" ? "badge-red" : "badge-orange"}`} style={{ fontSize: "0.75rem" }}>
                                                    {r.pollution_level}
                                                </span>
                                            </td>
                                            <td style={{ padding: "0.75rem" }}>
                                                <span className={`badge ${badgeClass}`} style={{ fontSize: "0.75rem" }}>
                                                    {st}
                                                </span>
                                            </td>
                                            <td style={{ padding: "0.75rem", color: "#475569", maxWidth: "280px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                                                {r.assessment || r.description || "Pollution observation"}
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
};
