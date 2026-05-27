"use client";

import React from "react";

const steps = [
    { step: "Step 1", title: "SENSE", desc: "12 IoT nodes, pH, turbidity, temp, EC, ORP, acoustic sensors collect real-time data." },
    { step: "Step 2", title: "UNDERSTAND", desc: "STAF ML models and location-aware detection identify 9 different pollution types." },
    { step: "Step 3", title: "PREDICT", desc: "LSTM + ArcGIS integration provides 48hr forecasts with 95% flood accuracy." },
    { step: "Step 4", title: "ACT", desc: "Automated notices, SMS alerts, and enforcement actions triggered within 30 minutes." },
];

const HowItWorksSection = () => {
    return (
        <section id="how-it-works" style={{ padding: '6rem 2rem', background: 'white' }}>
            <div style={{ maxWidth: '1000px', margin: '0 auto' }}>
                <h2 style={{ textAlign: 'center', fontSize: '2.5rem', marginBottom: '5rem' }}>How It <span className="text-gradient">Works</span></h2>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem', position: 'relative' }}>
                    {/* Vertical line for desktop */}
                    <div className="hidden md:block" style={{ position: 'absolute', left: '50%', top: 0, bottom: 0, width: '2px', background: 'var(--border)', transform: 'translateX(-50%)' }}></div>

                    {steps.map((step, index) => (
                        <div key={index} style={{ display: 'flex', justifyContent: index % 2 === 0 ? 'flex-start' : 'flex-end', width: '100%' }}>
                            <div className="card" style={{ width: '45%', position: 'relative', zIndex: 1, padding: '2rem' }}>
                                <div className="badge badge-blue" style={{ marginBottom: '0.5rem' }}>{step.step}</div>
                                <h3 style={{ fontSize: '1.5rem', color: 'var(--primary)', marginBottom: '1rem' }}>{step.title}</h3>
                                <p style={{ color: '#64748b' }}>{step.desc}</p>
                                {/* Connector dot */}
                                <div style={{ position: 'absolute', top: '50%', [index % 2 === 0 ? 'right' : 'left']: '-3.5rem', width: '1rem', height: '1rem', borderRadius: '50%', background: 'var(--primary)', border: '4px solid white', transform: 'translateY(-50%)' }} className="hidden md:block"></div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </section>
    );
};

export default HowItWorksSection;
