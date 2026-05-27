"use client";

import React from "react";

const features = [
    {
        title: "Real-Time Detection",
        desc: "12 IoT nodes, 6 sensors, 15min updates",
        badge: "24/7",
        icon: "📡",
    },
    {
        title: "AI Analysis",
        desc: "9 pollution types, 87% accuracy",
        badge: "87%",
        icon: "🧠",
    },
    {
        title: "Geospatial Intelligence",
        desc: "15yr LiDAR, 48hr forecast",
        badge: "48hr",
        icon: "🗺️",
    },
    {
        title: "Instant Action",
        desc: "SMS alerts, 30min response",
        badge: "30min",
        icon: "⚡",
    },
];

const FeaturesSection = () => {
    return (
        <section id="features" style={{ padding: '6rem 2rem', background: 'white' }}>
            <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
                <h2 style={{ textAlign: 'center', fontSize: '2.5rem', marginBottom: '4rem' }}>
                    Cutting-Edge <span className="text-gradient">Capabilities</span>
                </h2>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '2rem' }}>
                    {features.map((feature, index) => (
                        <div key={index} className="card" style={{ position: 'relative', overflow: 'hidden' }}>
                            <div className="badge badge-blue" style={{ position: 'absolute', top: '1rem', right: '1rem' }}>
                                {feature.badge}
                            </div>
                            <div style={{ fontSize: '3rem', marginBottom: '1.5rem' }}>{feature.icon}</div>
                            <h3 style={{ fontSize: '1.5rem', marginBottom: '1rem' }}>{feature.title}</h3>
                            <p style={{ color: '#64748b' }}>{feature.desc}</p>
                        </div>
                    ))}
                </div>
            </div>
        </section>
    );
};

export default FeaturesSection;
