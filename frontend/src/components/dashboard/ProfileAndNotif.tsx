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

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:5000';

export const Notifications = () => {
    const [stationAlerts, setStationAlerts] = useState<any[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        let isMounted = true;
        async function fetchSystemNotifications() {
            try {
                const res = await fetch(`${BACKEND_URL}/api/v1/stations`);
                if (res.ok) {
                    const data = await res.json();
                    if (isMounted && data.stations) {
                        const notificationsList: any[] = [];
                        
                        data.stations.forEach((stn: any) => {
                            if (stn.latest_reading?.water_level && stn.warning_water_level_m && stn.latest_reading.water_level >= stn.warning_water_level_m) {
                                notificationsList.push({
                                    title: `Flood Warning: ${stn.station_name}`,
                                    msg: `Water level (${stn.latest_reading.water_level.toFixed(2)}m) has reached or exceeded the CWC Warning stage (${stn.warning_water_level_m}m MSL).`,
                                    type: "red",
                                    time: "Recent"
                                });
                            }
                            if (stn.latest_reading?.ph && (stn.latest_reading.ph < 6.5 || stn.latest_reading.ph > 8.5)) {
                                notificationsList.push({
                                    title: `Water Quality Deviation: ${stn.station_name}`,
                                    msg: `pH value (${stn.latest_reading.ph.toFixed(2)}) is outside CPCB Class B standard (6.5–8.5).`,
                                    type: "orange",
                                    time: "Active"
                                });
                            }
                        });

                        // Add general network notification
                        notificationsList.push({
                            title: "Varanasi Sensor Network Status",
                            msg: `${data.stations.length} river monitoring stations registered in database (Assi, Dashashwamedh, Namo Ghat, Rajghat).`,
                            type: "blue",
                            time: "Operational"
                        });

                        setStationAlerts(notificationsList);
                    }
                }
            } catch (err) {
                console.error("Failed to load notifications:", err);
            } finally {
                if (isMounted) setLoading(false);
            }
        }
        fetchSystemNotifications();
        return () => { isMounted = false; };
    }, []);

    return (
        <div className="card">
            <h3 style={{ margin: '0 0 1rem 0', fontWeight: 700 }}>Operational Alerts & System Updates</h3>
            <p style={{ margin: '0 0 1.5rem 0', fontSize: '0.85rem', color: '#64748b' }}>
                Automated threshold notifications based on live sensor telemetry and CPCB / CWC regulatory benchmarks.
            </p>

            {loading ? (
                <div style={{ padding: '2rem', textAlign: 'center', color: '#64748b' }}>
                    ⏳ Checking telemetry thresholds...
                </div>
            ) : stationAlerts.length === 0 ? (
                <div style={{ padding: '2rem', textAlign: 'center', color: '#64748b' }}>
                    ✅ All monitoring stations operating within normal regulatory thresholds.
                </div>
            ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    {stationAlerts.map((n, i) => (
                        <div
                            key={i}
                            style={{
                                display: 'flex',
                                gap: '1rem',
                                padding: '1rem',
                                borderRadius: '0.75rem',
                                background: '#f8fafc',
                                border: '1px solid #e2e8f0',
                                borderLeft: `5px solid ${n.type === 'red' ? '#ef4444' : n.type === 'orange' ? '#f59e0b' : '#0284c7'}`
                            }}
                        >
                            <div style={{ flex: 1 }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                                    <div style={{ fontWeight: 700, fontSize: '0.95rem', color: '#0f172a' }}>{n.title}</div>
                                    <div style={{ fontSize: '0.75rem', color: '#64748b', fontWeight: 600 }}>{n.time}</div>
                                </div>
                                <div style={{ fontSize: '0.85rem', color: '#475569', lineHeight: 1.4 }}>{n.msg}</div>
                            </div>
                        </div>
                    ))}
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

                // Fetch current user profile from /api/auth/me
                const meRes = await fetch(`${BACKEND_URL}/api/auth/me`, {
                    headers: { 'Authorization': `Bearer ${token}` }
                });

                if (meRes.ok) {
                    const meData = await meRes.json();
                    if (isMounted) {
                        const userObj = meData.user || {};
                        const profObj = meData.profile || {};
                        setProfile({
                            id: userObj.id,
                            email: userObj.email,
                            full_name: profObj.full_name || userObj.email?.split('@')[0] || 'Citizen Contributor',
                            role: meData.role || 'citizen',
                            organization: profObj.organization || 'General Public',
                            account_status: profObj.account_status || 'active',
                            created_at: userObj.created_at
                        });
                    }
                }

                // Fetch citizen's submitted reports from /api/citizen/my-reports
                const repRes = await fetch(`${BACKEND_URL}/api/citizen/my-reports`, {
                    headers: { 'Authorization': `Bearer ${token}` }
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
        return () => { isMounted = false; };
    }, []);

    if (loading) {
        return (
            <div className="card" style={{ padding: '3rem', textAlign: 'center', color: '#64748b' }}>
                ⏳ Loading authenticated citizen profile...
            </div>
        );
    }

    if (!isAuthenticated) {
        return (
            <div className="card" style={{ padding: '3rem', textAlign: 'center', background: '#f8fafc', border: '1px solid #e2e8f0' }}>
                <div style={{ fontSize: '3rem', marginBottom: '0.75rem' }}>👤</div>
                <h3 style={{ margin: '0 0 0.5rem 0', fontWeight: 700, color: '#0f172a' }}>
                    Citizen Profile Session
                </h3>
                <p style={{ maxWidth: '460px', margin: '0 auto 1.5rem auto', color: '#64748b', fontSize: '0.9rem', lineHeight: 1.5 }}>
                    You are currently browsing River Sentinel as a guest. Log in to track your submitted pollution reports, receive resolution updates, and access your verified profile.
                </p>
                <div style={{ display: 'flex', justifyContent: 'center', gap: '1rem' }}>
                    <a href="/login" className="btn btn-primary" style={{ padding: '0.6rem 1.5rem' }}>
                        Sign In / Register
                    </a>
                </div>
            </div>
        );
    }

    const resolvedCount = reports.filter(r => r.status?.toLowerCase() === 'resolved').length;
    const pendingCount = reports.filter(r => ['pending', 'submitted', 'investigating'].includes(r.status?.toLowerCase())).length;

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '2rem' }}>
                {/* Profile Identity Card */}
                <div className="card" style={{ textAlign: 'center', padding: '2rem' }}>
                    <div style={{
                        width: '88px',
                        height: '88px',
                        borderRadius: '50%',
                        background: '#0284c7',
                        color: 'white',
                        fontSize: '2.5rem',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        margin: '0 auto 1rem',
                        fontWeight: 800
                    }}>
                        {(profile?.full_name || profile?.email || 'U').charAt(0).toUpperCase()}
                    </div>
                    <h2 style={{ margin: 0, fontWeight: 800, fontSize: '1.4rem', color: '#0f172a' }}>
                        {profile?.full_name || 'Citizen User'}
                    </h2>
                    <p style={{ color: '#64748b', fontSize: '0.85rem', margin: '0.25rem 0 0.75rem 0' }}>
                        {profile?.email}
                    </p>
                    <div style={{ display: 'flex', justifyContent: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                        <span className="badge badge-blue" style={{ fontSize: '0.75rem', textTransform: 'uppercase' }}>
                            ROLE: {profile?.role?.replace('_', ' ') || 'CITIZEN'}
                        </span>
                        <span className="badge badge-green" style={{ fontSize: '0.75rem', textTransform: 'uppercase' }}>
                            STATUS: {profile?.account_status || 'ACTIVE'}
                        </span>
                    </div>
                    {profile?.organization && (
                        <div style={{ marginTop: '0.75rem', fontSize: '0.8rem', color: '#475569' }}>
                            Organization: <strong>{profile.organization}</strong>
                        </div>
                    )}
                    {profile?.created_at && (
                        <div style={{ marginTop: '0.5rem', fontSize: '0.75rem', color: '#94a3b8' }}>
                            Member since {new Date(profile.created_at).toLocaleDateString()}
                        </div>
                    )}
                </div>

                {/* Account Activity Summary */}
                <div className="card" style={{ padding: '2rem' }}>
                    <h3 style={{ margin: '0 0 1.25rem 0', fontWeight: 700, fontSize: '1.1rem' }}>
                        Pollution Report Activity
                    </h3>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1.5rem' }}>
                        <div style={{ padding: '1rem', background: '#f8fafc', borderRadius: '0.5rem', border: '1px solid #e2e8f0' }}>
                            <div style={{ fontSize: '0.8rem', color: '#64748b', fontWeight: 600 }}>Total Reports Lodged</div>
                            <div style={{ fontSize: '2.2rem', fontWeight: 800, color: '#0284c7', margin: '0.25rem 0' }}>
                                {reports.length}
                            </div>
                            <div style={{ fontSize: '0.75rem', color: '#64748b' }}>Submitted via app</div>
                        </div>

                        <div style={{ padding: '1rem', background: '#f8fafc', borderRadius: '0.5rem', border: '1px solid #e2e8f0' }}>
                            <div style={{ fontSize: '0.8rem', color: '#64748b', fontWeight: 600 }}>Resolved by UPPCB</div>
                            <div style={{ fontSize: '2.2rem', fontWeight: 800, color: '#10b981', margin: '0.25rem 0' }}>
                                {resolvedCount}
                            </div>
                            <div style={{ fontSize: '0.75rem', color: '#166534' }}>Action completed</div>
                        </div>

                        <div style={{ padding: '1rem', background: '#f8fafc', borderRadius: '0.5rem', border: '1px solid #e2e8f0' }}>
                            <div style={{ fontSize: '0.8rem', color: '#64748b', fontWeight: 600 }}>Under Investigation</div>
                            <div style={{ fontSize: '2.2rem', fontWeight: 800, color: '#f59e0b', margin: '0.25rem 0' }}>
                                {pendingCount}
                            </div>
                            <div style={{ fontSize: '0.75rem', color: '#b45309' }}>In review / field check</div>
                        </div>

                        <div style={{ padding: '1rem', background: '#f8fafc', borderRadius: '0.5rem', border: '1px solid #e2e8f0' }}>
                            <div style={{ fontSize: '0.8rem', color: '#64748b', fontWeight: 600 }}>Active River Stations</div>
                            <div style={{ fontSize: '2.2rem', fontWeight: 800, color: '#0f172a', margin: '0.25rem 0' }}>
                                4
                            </div>
                            <div style={{ fontSize: '0.75rem', color: '#64748b' }}>Varanasi Ghats</div>
                        </div>
                    </div>
                </div>
            </div>

            {/* My Submitted Reports Table */}
            <div className="card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
                    <div>
                        <h3 style={{ margin: 0, fontWeight: 700, fontSize: '1.1rem' }}>My Pollution Reports</h3>
                        <p style={{ margin: '0.25rem 0 0 0', fontSize: '0.85rem', color: '#64748b' }}>
                            Real reports submitted to the Uttar Pradesh Pollution Control Board database.
                        </p>
                    </div>
                    <a href="/citizen-dashboard?tab=report" className="btn btn-secondary" style={{ fontSize: '0.8rem', padding: '0.4rem 0.8rem' }}>
                        + New Report
                    </a>
                </div>

                {reports.length === 0 ? (
                    <div style={{ padding: '2.5rem', textAlign: 'center', color: '#64748b', background: '#f8fafc', borderRadius: '0.5rem' }}>
                        <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>📝</div>
                        <div style={{ fontWeight: 600, color: '#334155' }}>No Reports Submitted Yet</div>
                        <p style={{ fontSize: '0.85rem', maxWidth: '380px', margin: '0.35rem auto 1rem auto' }}>
                            Help protect the Ganga by submitting pollution observations or pipe discharges through the Report Pollution tool.
                        </p>
                    </div>
                ) : (
                    <div style={{ overflowX: 'auto' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.85rem' }}>
                            <thead>
                                <tr style={{ borderBottom: '1px solid #e2e8f0', color: '#64748b' }}>
                                    <th style={{ padding: '0.75rem' }}>Date</th>
                                    <th style={{ padding: '0.75rem' }}>Location</th>
                                    <th style={{ padding: '0.75rem' }}>Severity</th>
                                    <th style={{ padding: '0.75rem' }}>Status</th>
                                    <th style={{ padding: '0.75rem' }}>Summary</th>
                                </tr>
                            </thead>
                            <tbody>
                                {reports.map((r) => {
                                    const st = (r.status || 'PENDING').toUpperCase();
                                    const badgeClass = st === 'RESOLVED' ? 'badge-green' : st === 'INVESTIGATING' ? 'badge-blue' : st === 'REJECTED' ? 'badge-red' : 'badge-orange';
                                    return (
                                        <tr key={r.id} style={{ borderBottom: '1px solid #f1f5f9' }}>
                                            <td style={{ padding: '0.75rem', color: '#64748b' }}>
                                                {new Date(r.created_at).toLocaleDateString()}
                                            </td>
                                            <td style={{ padding: '0.75rem', fontWeight: 600, color: '#0f172a' }}>
                                                {r.location_name || 'Varanasi Ghat'}
                                            </td>
                                            <td style={{ padding: '0.75rem' }}>
                                                <span className={`badge ${r.pollution_level === 'High' ? 'badge-red' : 'badge-orange'}`} style={{ fontSize: '0.75rem' }}>
                                                    {r.pollution_level}
                                                </span>
                                            </td>
                                            <td style={{ padding: '0.75rem' }}>
                                                <span className={`badge ${badgeClass}`} style={{ fontSize: '0.75rem' }}>
                                                    {st}
                                                </span>
                                            </td>
                                            <td style={{ padding: '0.75rem', color: '#475569', maxWidth: '280px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                                {r.assessment || r.description || 'Pollution observation'}
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
