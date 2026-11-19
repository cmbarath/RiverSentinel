"use client";

import React, { useState, useEffect } from "react";
import Sidebar from "@/components/Sidebar";
import CommandCenter from "@/components/dashboard/CommandCenter";
import AuthorityAlerts from "@/components/dashboard/AuthorityAlerts";
import LiveSensorData from "@/components/dashboard/LiveSensorData";
import FloodMapViewer from "@/components/dashboard/FloodMapViewer";
import DatasetUpload from "@/components/dashboard/DatasetUpload";
import ManageReports from "@/components/dashboard/ManageReports";
import AuthorityAnalytics from "@/components/dashboard/AuthorityAnalytics";
import SendSMSAlerts from "@/components/dashboard/SendSMSAlerts";
import GenerateReports from "@/components/dashboard/GenerateReports";
import { supabase } from "@/lib/supabaseClient";

const tabs = [
    { id: "command", label: "Command Center", icon: "🏢" },
    { id: "alerts", label: "Alert Center", icon: "🚨" },
    { id: "live", label: "Live Sensor Data", icon: "📊" },
    { id: "map", label: "Flood Susceptibility Map", icon: "📍" },
    { id: "manage", label: "Manage Reports", icon: "🛡️" },
    { id: "analytics", label: "Analytics", icon: "📈" },
    { id: "generate", label: "Generate Reports", icon: "📄" },
    { id: "sms", label: "SMS Broadcast Gateway", icon: "📱" },
    { id: "upload", label: "ML Model Staging", icon: "📤" },
];

export default function AuthorityDashboard() {
    const [activeTab, setActiveTab] = useState("command");
    const [officerName, setOfficerName] = useState<string>("Authority Officer");
    const [officerRole, setOfficerRole] = useState<string>("UPPCB VERIFIED");
    const [userInitial, setUserInitial] = useState<string>("A");

    useEffect(() => {
        async function fetchOfficer() {
            try {
                const { data } = await supabase.auth.getUser();
                if (data?.user) {
                    const email = data.user.email || "";
                    const metaName = data.user.user_metadata?.full_name || email.split('@')[0] || "Officer";
                    const role = data.user.user_metadata?.role || "AUTHORITY ADMIN";
                    setOfficerName(metaName);
                    setOfficerRole(role.toUpperCase().replace('_', ' '));
                    setUserInitial(metaName.charAt(0).toUpperCase());
                }
            } catch (err) {
                console.error("Error reading authority session:", err);
            }
        }
        fetchOfficer();
    }, []);

    const renderContent = () => {
        switch (activeTab) {
            case "command": return <CommandCenter />;
            case "alerts": return <AuthorityAlerts />;
            case "live": return <LiveSensorData />;
            case "map": return <FloodMapViewer />;
            case "manage": return <ManageReports />;
            case "analytics": return <AuthorityAnalytics />;
            case "generate": return <GenerateReports />;
            case "sms": return <SendSMSAlerts />;
            case "upload": return <DatasetUpload />;
            default: return (
                <div style={{ textAlign: 'center', padding: '5rem' }}>
                    <h2 style={{ opacity: 0.3 }}>{tabs.find(t => t.id === activeTab)?.label} Content Placeholder</h2>
                </div>
            );
        }
    };

    return (
        <div style={{ display: 'flex', minHeight: '100vh', background: '#f8fafc' }}>
            <Sidebar tabs={tabs} activeTab={activeTab} setActiveTab={setActiveTab} />
            <main style={{ flex: 1, padding: '2rem', overflowY: 'auto' }}>
                <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem', padding: '0 0.5rem' }}>
                    <div style={{ fontWeight: 700, fontSize: '1.25rem', color: '#1e293b' }}>
                        UPPCB & CWC Authority Operations
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
                        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                            <span className="badge badge-green" style={{ fontSize: '0.75rem' }}>
                                {officerRole}
                            </span>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', background: 'white', padding: '0.4rem 0.9rem', borderRadius: '999px', border: '1px solid #e2e8f0' }}>
                                <div style={{ width: '30px', height: '30px', borderRadius: '50%', background: '#dc2626', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: '0.85rem' }}>
                                    {userInitial}
                                </div>
                                <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#334155' }}>
                                    {officerName}
                                </div>
                            </div>
                        </div>
                    </div>
                </header>

                <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
                    {renderContent()}
                </div>
            </main>
        </div>
    );
}
