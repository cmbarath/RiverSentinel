"use client";

import React, { useState, useEffect } from "react";
import Sidebar from "@/components/Sidebar";
import SafetyChecker from "@/components/dashboard/SafetyChecker";
import WeatherAndFlood from "@/components/dashboard/WeatherAndFlood";
import WaterQuality from "@/components/dashboard/WaterQuality";
import ReportPollution from "@/components/dashboard/ReportPollution";
import HistoricalTrends from "@/components/dashboard/HistoricalTrends";
import AIChatbot from "@/components/dashboard/AIChatbot";
import { Notifications, Profile } from "@/components/dashboard/ProfileAndNotif";
import DownloadReport from "@/components/dashboard/DownloadReport";
import { supabase } from "@/lib/supabaseClient";

const tabs = [
    { id: "safety", label: "Safety Checker", icon: "🛡️" },
    { id: "weather", label: "Weather & Flood", icon: "🌦️" },
    { id: "water", label: "Water Quality", icon: "💧" },
    { id: "trends", label: "Historical Trends", icon: "📊" },
    { id: "report", label: "Report Pollution", icon: "📸" },
    { id: "chatbot", label: "AI Chatbot", icon: "🤖" },
    { id: "download", label: "Download Report", icon: "📥" },
    { id: "notifications", label: "Notifications", icon: "🔔" },
    { id: "profile", label: "My Profile", icon: "👤" },
];

export default function CitizenDashboard() {
    const [activeTab, setActiveTab] = useState("safety");
    const [userName, setUserName] = useState<string>("Guest Citizen");
    const [userInitial, setUserInitial] = useState<string>("G");

    useEffect(() => {
        async function fetchUser() {
            try {
                const { data } = await supabase.auth.getUser();
                if (data?.user) {
                    const email = data.user.email || "";
                    const metaName = data.user.user_metadata?.full_name || email.split('@')[0] || "Citizen";
                    setUserName(metaName);
                    setUserInitial(metaName.charAt(0).toUpperCase());
                }
            } catch (err) {
                console.error("Error reading session:", err);
            }
        }
        fetchUser();
    }, []);

    const renderContent = () => {
        switch (activeTab) {
            case "safety": return <SafetyChecker />;
            case "weather": return <WeatherAndFlood />;
            case "water": return <WaterQuality />;
            case "report": return <ReportPollution />;
            case "trends": return <HistoricalTrends />;
            case "chatbot": return <AIChatbot />;
            case "download": return <DownloadReport />;
            case "notifications": return <Notifications />;
            case "profile": return <Profile />;
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
                        {tabs.find(t => t.id === activeTab)?.label}
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
                        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                            <button
                                type="button"
                                aria-label="Open notifications tab"
                                onClick={() => setActiveTab('notifications')}
                                style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '1.25rem', padding: '0.25rem' }}
                                title="Notifications"
                            >
                                🔔
                            </button>
                            <button
                                type="button"
                                aria-label={`Logged in as ${userName}. Open profile settings`}
                                onClick={() => setActiveTab('profile')}
                                style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', background: 'white', padding: '0.4rem 0.9rem', borderRadius: '999px', border: '1px solid #e2e8f0', cursor: 'pointer', font: 'inherit' }}
                            >
                                <div style={{ width: '30px', height: '30px', borderRadius: '50%', background: 'var(--primary)', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: '0.85rem' }}>
                                    {userInitial}
                                </div>
                                <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#334155' }}>
                                    {userName}
                                </div>
                            </button>
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
