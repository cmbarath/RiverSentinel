"use client";

import React, { useState } from "react";
import Sidebar from "@/components/Sidebar";
import CommandCenter from "@/components/dashboard/CommandCenter";
import LiveSensorData from "@/components/dashboard/LiveSensorData";
import InteractiveMap from "@/components/dashboard/InteractiveMap";
import FloodMapViewer from "@/components/dashboard/FloodMapViewer";
import DatasetUpload from "@/components/dashboard/DatasetUpload";
import ManageReports from "@/components/dashboard/ManageReports";
import AuthorityAnalytics from "@/components/dashboard/AuthorityAnalytics";
import SendSMSAlerts from "@/components/dashboard/SendSMSAlerts";
import GenerateReports from "@/components/dashboard/GenerateReports";

const tabs = [
    { id: "command", label: "Command Center", icon: "🏢" },
    { id: "live", label: "Live Sensor Data", icon: "📊" },
    { id: "map", label: "Flood Susceptibility Map", icon: "📍" },
    { id: "upload", label: "Upload Dataset", icon: "📤" },
    { id: "manage", label: "Manage Reports", icon: "🛡️" },
    { id: "analytics", label: "Analytics", icon: "📈" },
    { id: "generate", label: "Generate Reports", icon: "📄" },
    { id: "sms", label: "Send SMS Alerts", icon: "📱" },
];

export default function AuthorityDashboard() {
    const [activeTab, setActiveTab] = useState("command");

    const renderContent = () => {
        switch (activeTab) {
            case "command": return <CommandCenter />;
            case "live": return <LiveSensorData />;
            case "map": return <FloodMapViewer />; // Replaced InteractiveMap with FloodMapViewer as requested
            case "upload": return <DatasetUpload />;
            case "manage": return <ManageReports />;
            case "analytics": return <AuthorityAnalytics />;
            case "generate": return <GenerateReports />;
            case "sms": return <SendSMSAlerts />;
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
                        Authority Dashboard
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
                        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                            <span className="badge badge-green">VERIFIED AUTHORITY</span>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', background: 'white', padding: '0.5rem 1rem', borderRadius: '999px', border: '1px solid var(--border)' }}>
                                <div style={{ width: '32px', height: '32px', borderRadius: '50%', background: '#ef4444', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700 }}>A</div>
                                <div style={{ fontSize: '0.9rem', fontWeight: 600 }}>Admin (UPPCB)</div>
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
