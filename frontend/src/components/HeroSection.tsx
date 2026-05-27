"use client";

import React from "react";
import WaveBackground from "./WaveBackground";
import Link from "next/link";

const HeroSection = () => {
    return (
        <section style={{ position: 'relative', width: '100%', minHeight: '90vh', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', textAlign: 'center', padding: '0 2rem', background: 'linear-gradient(to bottom, #f0f9ff, #e0f2fe)' }}>
            <div style={{ maxWidth: '800px', zIndex: 20 }}>
                <div className="badge badge-blue" style={{ marginBottom: '1.5rem', fontSize: '0.9rem', padding: '0.5rem 1rem' }}>
                    Protecting 2.3M Lives
                </div>
                <h1 style={{ fontSize: '4rem', marginBottom: '1rem' }}>
                    RiverSentinel <span className="text-gradient">2.0</span>
                </h1>
                <h2 style={{ fontSize: '1.5rem', fontWeight: 600, color: '#475569', marginBottom: '1.5rem' }}>
                    India&apos;s First Geospatially-Intelligent River Protection System
                </h2>
                <p style={{ fontSize: '1.2rem', color: '#64748b', marginBottom: '2.5rem', maxWidth: '700px', margin: '0 auto 2.5rem' }}>
                    12 IoT sensors, AI pollution detection, 95% flood accuracy, 30min response.
                </p>
                <div style={{ display: 'flex', gap: '1.5rem', justifyContent: 'center' }}>
                    <Link href="/signup" className="btn btn-primary" style={{ fontSize: '1.1rem', padding: '1rem 2rem' }}>Sign Up Now</Link>
                    <button className="btn btn-secondary" style={{ fontSize: '1.1rem', padding: '1rem 2rem' }}>Watch Demo</button>
                </div>
            </div>
            <WaveBackground />
        </section>
    );
};

export default HeroSection;
