"use client";

import React from "react";
import Link from "next/link";

export interface SidebarTab {
    id: string;
    label: string;
    icon: string;
    [key: string]: unknown;
}

const Sidebar = ({ tabs, activeTab, setActiveTab }: { tabs: SidebarTab[], activeTab: string, setActiveTab: (id: string) => void }) => {
    return (
        <div style={{ width: '280px', height: '100vh', background: 'white', borderRight: '1px solid var(--border)', display: 'flex', flexDirection: 'column', position: 'sticky', top: 0, zIndex: 40 }}>
            <div style={{ padding: '2rem', display: 'flex', alignItems: 'center', gap: '0.75rem', fontWeight: 800, fontSize: '1.25rem' }}>
                <span>🌊</span>
                <span className="text-gradient">RiverSentinel</span>
            </div>

            <nav style={{ flex: 1, padding: '1rem', overflowY: 'auto' }} aria-label="Dashboard Navigation">
                <ul role="tablist" style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '0.5rem', margin: 0, padding: 0 }}>
                    {tabs.map((tab) => (
                        <li key={tab.id} role="presentation">
                            <button
                                role="tab"
                                aria-selected={activeTab === tab.id}
                                aria-label={tab.label}
                                onClick={() => setActiveTab(tab.id)}
                                style={{
                                    width: '100%',
                                    textAlign: 'left',
                                    padding: '0.75rem 1rem',
                                    borderRadius: '0.75rem',
                                    background: activeTab === tab.id ? 'var(--primary)' : 'transparent',
                                    color: activeTab === tab.id ? 'white' : '#64748b',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.75rem',
                                    fontWeight: 600,
                                    border: 'none',
                                    cursor: 'pointer',
                                    transition: 'all 0.2s ease'
                                }}
                            >
                                <span style={{ fontSize: '1.2rem' }} aria-hidden="true">{tab.icon}</span>
                                {tab.label}
                            </button>
                        </li>
                    ))}
                </ul>
            </nav>

            <div style={{ padding: '1.5rem', borderTop: '1px solid var(--border)' }}>
                <Link href="/login" aria-label="Logout of RiverSentinel session" style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', color: '#ef4444', fontWeight: 600, textDecoration: 'none' }}>
                    <span aria-hidden="true">🚪</span> Logout
                </Link>
            </div>
        </div>
    );
};

export default Sidebar;
