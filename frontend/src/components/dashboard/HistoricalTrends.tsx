"use client";

import React from "react";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line, Legend } from "recharts";

const data = [
    { time: "06:00", ph: 7.2, turbidity: 4.5, temp: 22 },
    { time: "09:00", ph: 7.5, turbidity: 5.2, temp: 24 },
    { time: "12:00", ph: 7.8, turbidity: 6.1, temp: 26 },
    { time: "15:00", ph: 7.4, turbidity: 4.8, temp: 25 },
    { time: "18:00", ph: 7.1, turbidity: 4.2, temp: 23 },
    { time: "21:00", ph: 7.0, turbidity: 3.9, temp: 22 },
    { time: "00:00", ph: 7.1, turbidity: 3.8, temp: 21 },
];

const HistoricalTrends = () => {
    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h3>Ganga Water Quality Trends (Last 24h)</h3>
                <div style={{ display: 'flex', gap: '1rem' }}>
                    <select style={{ padding: '0.5rem', borderRadius: '0.5rem', border: '1px solid var(--border)' }}>
                        <option>Last 24 Hours</option>
                        <option>Last 7 Days</option>
                        <option>Last 30 Days</option>
                    </select>
                </div>
            </div>

            <div className="card" style={{ height: '400px', width: '100%', padding: '2rem 1rem 1rem 0' }}>
                <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={data}>
                        <defs>
                            <linearGradient id="colorPh" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="5%" stopColor="var(--primary)" stopOpacity={0.3} />
                                <stop offset="95%" stopColor="var(--primary)" stopOpacity={0} />
                            </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                        <XAxis dataKey="time" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748b' }} />
                        <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#64748b' }} />
                        <Tooltip
                            contentStyle={{ borderRadius: '1rem', border: 'none', boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)' }}
                        />
                        <Area type="monotone" dataKey="ph" stroke="var(--primary)" strokeWidth={3} fillOpacity={1} fill="url(#colorPh)" />
                        <Area type="monotone" dataKey="turbidity" stroke="var(--secondary)" strokeWidth={3} fillOpacity={0.1} fill="var(--secondary)" />
                    </AreaChart>
                </ResponsiveContainer>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1.5rem' }}>
                {[
                    { label: "Avg pH", value: "7.3", trend: "+0.2" },
                    { label: "Avg Turbidity", value: "4.6", trend: "-1.2", suffix: " NTU" },
                    { label: "Avg Temp", value: "23", trend: "-2", suffix: "°C" },
                    { label: "Peak Pollution", value: "12:15", trend: "PM" },
                ].map((stat, i) => (
                    <div key={i} className="card" style={{ textAlign: 'center' }}>
                        <div style={{ fontSize: '0.85rem', color: '#64748b', fontWeight: 600 }}>{stat.label}</div>
                        <div style={{ fontSize: '1.75rem', fontWeight: 800, margin: '0.25rem 0' }}>{stat.value}{stat.suffix}</div>
                        <div style={{ fontSize: '0.8rem', color: stat.trend.includes('-') ? '#10b981' : '#f59e0b', fontWeight: 700 }}>{stat.trend} {stat.trend.length > 2 ? 'vs yesterday' : ''}</div>
                    </div>
                ))}
            </div>

            <div className="card" style={{ background: '#f0f9ff', border: '1px solid #bae6fd' }}>
                <h4 style={{ color: '#0369a1', marginBottom: '0.5rem' }}>💡 Historical Insights</h4>
                <p style={{ color: '#0369a1', fontSize: '0.9rem' }}>
                    Water quality remains consistently 15% better during early morning hours (05:00 - 07:00).
                    Turbidity peaks typically follow ritual bathing hours between 12:00 PM and 02:00 PM.
                </p>
            </div>
        </div>
    );
};

export default HistoricalTrends;
