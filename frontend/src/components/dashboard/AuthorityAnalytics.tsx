"use client";

import React from "react";
import { PieChart, Pie, Cell, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from "recharts";

const statusData = [
    { name: 'Safe', value: 8, color: '#10b981' },
    { name: 'Caution', value: 3, color: '#f59e0b' },
    { name: 'Unsafe', value: 1, color: '#ef4444' },
];

const paramData = [
    { name: 'Dashashwamedh', ph: 7.4, turbidity: 4 },
    { name: 'Assi', ph: 7.8, turbidity: 12 },
    { name: 'Manikarnika', ph: 7.2, turbidity: 3 },
    { name: 'Scindia', ph: 8.1, turbidity: 45 },
    { name: 'Harishchandra', ph: 7.5, turbidity: 5 },
];

const AuthorityAnalytics = () => {
    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))', gap: '2rem' }}>
                {/* Status Distribution */}
                <div className="card">
                    <h3 style={{ marginBottom: '1.5rem' }}>Station Status Distribution</h3>
                    <div style={{ height: '300px' }}>
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                                <Pie data={statusData} innerRadius={60} outerRadius={80} paddingAngle={5} dataKey="value">
                                    {statusData.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={entry.color} />
                                    ))}
                                </Pie>
                                <Tooltip />
                                <Legend verticalAlign="bottom" height={36} />
                            </PieChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Parameter Comparison */}
                <div className="card">
                    <h3 style={{ marginBottom: '1.5rem' }}>pH vs Turbidity by Station</h3>
                    <div style={{ height: '300px' }}>
                        <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={paramData}>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                                <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 10 }} />
                                <YAxis axisLine={false} tickLine={false} />
                                <Tooltip />
                                <Legend />
                                <Bar dataKey="ph" fill="var(--primary)" radius={[4, 4, 0, 0]} />
                                <Bar dataKey="turbidity" fill="var(--secondary)" radius={[4, 4, 0, 0]} />
                            </BarChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </div>

            <div className="card">
                <h3>System Performance Summary</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '2rem', marginTop: '1.5rem' }}>
                    {[
                        { l: "Uptime", v: "99.98%", s: "Optimal" },
                        { l: "Data Latency", v: "1.2s", s: "Excellent" },
                        { l: "Report Processing", v: "4min", s: "Avg Time" },
                        { l: "AI Accuracy", v: "87.4%", s: "Pollution Detection" },
                    ].map((s, i) => (
                        <div key={i}>
                            <div style={{ fontSize: '0.85rem', color: '#64748b' }}>{s.l}</div>
                            <div style={{ fontSize: '1.5rem', fontWeight: 800 }}>{s.v}</div>
                            <div style={{ fontSize: '0.75rem', color: '#10b981', fontWeight: 600 }}>{s.s}</div>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
};

export default AuthorityAnalytics;
