"use client";

import React, { useState } from "react";
import Sidebar from "@/components/Sidebar";
import SafetyChecker from "@/components/dashboard/SafetyChecker";
import WeatherAndFlood from "@/components/dashboard/WeatherAndFlood";
import WaterQuality from "@/components/dashboard/WaterQuality";
import ReportPollution from "@/components/dashboard/ReportPollution";
import HistoricalTrends from "@/components/dashboard/HistoricalTrends";
import RewardsDashboard from "@/components/dashboard/RewardsDashboard";
import AIChatbot from "@/components/dashboard/AIChatbot";
import { Notifications, Profile } from "@/components/dashboard/ProfileAndNotif";
import DownloadReport from "@/components/dashboard/DownloadReport";

const tabs = [
    { id: "safety", label: "Safety Checker", icon: "🛡️" },
    { id: "weather", label: "Weather & Flood", icon: "🌦️" },
    { id: "water", label: "Water Quality", icon: "💧" },
    { id: "trends", label: "Historical Trends", icon: "📊" },
    { id: "report", label: "Report Pollution", icon: "📸" },
    { id: "rewards", label: "Rewards & Points", icon: "⭐" },
    { id: "chatbot", label: "AI Chatbot", icon: "🤖" },
    { id: "download", label: "Download Report", icon: "📥" },
    { id: "notifications", label: "Notifications", icon: "🔔" },
    { id: "profile", label: "My Profile", icon: "👤" },
];

export default function CitizenDashboard() {
    const [activeTab, setActiveTab] = useState("safety");

    const renderContent = () => {
        switch (activeTab) {
            case "safety": return <SafetyChecker />;
            case "weather": return <WeatherAndFlood />;
            case "water": return <WaterQuality />;
            case "report": return <ReportPollution />;
            case "trends": return <HistoricalTrends />;
            case "rewards": return <RewardsDashboard />;
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
                            <span style={{ cursor: 'pointer', fontSize: '1.5rem' }}>🔔</span>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', background: 'white', padding: '0.5rem 1rem', borderRadius: '999px', border: '1px solid var(--border)' }}>
                                <div style={{ width: '32px', height: '32px', borderRadius: '50%', background: 'var(--primary)', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700 }}>A</div>
                                <div style={{ fontSize: '0.9rem', fontWeight: 600 }}>Aviral</div>
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
