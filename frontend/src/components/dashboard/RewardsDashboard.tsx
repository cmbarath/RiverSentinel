"use client";

import React from "react";

const RewardsDashboard = () => {
    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.5rem' }}>
                {/* Total Points */}
                <div className="card" style={{ textAlign: 'center', background: 'linear-gradient(135deg, #14b8a6, #06b6d4)', color: 'white' }}>
                    <div style={{ fontSize: '0.9rem', opacity: 0.9, fontWeight: 600 }}>TOTAL IMPACT POINTS</div>
                    <div style={{ fontSize: '4rem', fontWeight: 800, margin: '0.5rem 0' }}>1,250</div>
                    <div className="badge" style={{ background: 'rgba(255,255,255,0.2)', color: 'white' }}>Ranked #24 in Varanasi</div>
                </div>

                {/* Current Tier */}
                <div className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                        <span style={{ fontSize: '3rem' }}>🏆</span>
                        <div>
                            <h3 style={{ margin: 0 }}>River Guardian</h3>
                            <p style={{ color: '#64748b', fontSize: '0.9rem' }}>Top 1% of contributors</p>
                        </div>
                    </div>
                    <div style={{ marginTop: '1.5rem' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem', fontSize: '0.8rem', fontWeight: 600 }}>
                            <span>NEXT TIER: ECO LEGEND</span>
                            <span>250 pts left</span>
                        </div>
                        <div style={{ height: '8px', background: '#e2e8f0', borderRadius: '4px', overflow: 'hidden' }}>
                            <div style={{ width: '75%', height: '100%', background: 'var(--accent)' }}></div>
                        </div>
                    </div>
                </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(300px, 1fr) 1.5fr', gap: '2rem' }}>
                {/* Available Rewards */}
                <div className="card">
                    <h3 style={{ marginBottom: '1.5rem' }}>Claim Rewards</h3>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                        {[
                            { title: "Certificate of Honor", pts: 200, icon: "📜" },
                            { title: "₹250 Amazon Voucher", pts: 500, icon: "🎫" },
                            { title: "₹500 Clean Ganga Kit", pts: 1000, icon: "🧰" },
                        ].map((r, i) => (
                            <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '1rem', border: '1px solid var(--border)', borderRadius: '0.75rem' }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                                    <span style={{ fontSize: '1.5rem' }}>{r.icon}</span>
                                    <div>
                                        <div style={{ fontWeight: 600 }}>{r.title}</div>
                                        <div style={{ fontSize: '0.8rem', color: '#64748b' }}>{r.pts} Points Required</div>
                                    </div>
                                </div>
                                <button className="btn btn-secondary" style={{ padding: '0.4rem 1rem', fontSize: '0.8rem' }}>Claim</button>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Leaderboard */}
                <div className="card">
                    <h3 style={{ marginBottom: '1.5rem' }}>Local Leaderboard</h3>
                    <div style={{ overflowX: 'auto' }}>
                        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                            <thead>
                                <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border)', fontSize: '0.85rem', color: '#64748b' }}>
                                    <th style={{ padding: '0.75rem' }}>Rank</th>
                                    <th style={{ padding: '0.75rem' }}>Contributor</th>
                                    <th style={{ padding: '0.75rem' }}>Impact</th>
                                    <th style={{ padding: '0.75rem' }}>Score</th>
                                </tr>
                            </thead>
                            <tbody>
                                {[
                                    { rank: 1, name: "Rahul S.", impact: "45 Reports", score: 2450, me: false },
                                    { rank: 2, name: "Priya V.", impact: "42 Reports", score: 2310, me: false },
                                    { rank: 3, name: "Amit K.", impact: "38 Reports", score: 2180, me: false },
                                    { rank: 24, name: "Aviral (You)", impact: "25 Reports", score: 1250, me: true },
                                ].map((u, i) => (
                                    <tr key={i} style={{ background: u.me ? '#f0f9ff' : 'transparent', borderBottom: '1px solid #f1f5f9' }}>
                                        <td style={{ padding: '0.75rem', fontWeight: 700 }}>{u.rank}</td>
                                        <td style={{ padding: '0.75rem', fontWeight: 600 }}>{u.name}</td>
                                        <td style={{ padding: '0.75rem', fontSize: '0.85rem', color: '#64748b' }}>{u.impact}</td>
                                        <td style={{ padding: '0.75rem', fontWeight: 800, color: 'var(--primary)' }}>{u.score}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default RewardsDashboard;
