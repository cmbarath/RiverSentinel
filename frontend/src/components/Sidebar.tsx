"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

const Sidebar = ({ tabs, activeTab, setActiveTab }: { tabs: any[], activeTab: string, setActiveTab: (id: string) => void }) => {
    return (
        <div style={{ width: '280px', height: '100vh', background: 'white', borderRight: '1px solid var(--border)', display: 'flex', flexDirection: 'column', position: 'sticky', top: 0, zIndex: 40 }}>
            <div style={{ padding: '2rem', display: 'flex', alignItems: 'center', gap: '0.75rem', fontWeight: 800, fontSize: '1.25rem' }}>
                <span>🌊</span>
                <span className="text-gradient">RiverSentinel</span>
            </div>

            <nav style={{ flex: 1, padding: '1rem', overflowY: 'auto' }}>
                <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    {tabs.map((tab) => (
                        <li key={tab.id}>
                            <button
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
                                    transition: 'all 0.2s ease'
                                }}
                            >
                                <span style={{ fontSize: '1.2rem' }}>{tab.icon}</span>
                                {tab.label}
                            </button>
                        </li>
                    ))}
                </ul>
            </nav>

            <div style={{ padding: '1.5rem', borderTop: '1px solid var(--border)' }}>
                <Link href="/login" style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', color: '#ef4444', fontWeight: 600 }}>
                    <span>🚪</span> Logout
                </Link>
            </div>
        </div>
    );
};

export default Sidebar;
