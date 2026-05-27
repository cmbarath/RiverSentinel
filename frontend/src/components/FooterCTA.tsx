"use client";

import React from "react";
import Link from "next/link";

const FooterCTA = () => {
    return (
        <>
            <section style={{ padding: '6rem 2rem', background: 'linear-gradient(135deg, var(--primary), var(--secondary))', color: 'white', textAlign: 'center' }}>
                <div style={{ maxWidth: '800px', margin: '0 auto' }}>
                    <h2 style={{ fontSize: '2.5rem', marginBottom: '1.5rem' }}>Protect Your Community Today</h2>
                    <p style={{ fontSize: '1.2rem', opacity: 0.9, marginBottom: '2.5rem' }}>Join India&apos;s most advanced river protection initiative. Report pollution, stay safe, and earn rewards.</p>
                    <Link href="/signup" className="btn" style={{ background: 'white', color: 'var(--primary)', fontSize: '1.1rem', padding: '1rem 2.5rem' }}>Sign Up Free</Link>
                </div>
            </section>

            <footer style={{ padding: '4rem 2rem', background: '#0f172a', color: 'white' }}>
                <div style={{ maxWidth: '1200px', margin: '0 auto', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '3rem' }}>
                    <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 800, fontSize: '1.5rem', marginBottom: '1.5rem' }}>
                            <span>🌊</span>
                            <span>RiverSentinel 2.0</span>
                        </div>
                        <p style={{ opacity: 0.7 }}>India&apos;s first geospatially-intelligent river protection system, monitoring the Ganges with AI and IoT.</p>
                    </div>
                    <div>
                        <h4 style={{ marginBottom: '1.5rem' }}>Quick Links</h4>
                        <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '0.75rem', opacity: 0.7 }}>
                            <li><Link href="#features">Features</Link></li>
                            <li><Link href="#how-it-works">How It Works</Link></li>
                            <li><Link href="#impact">Impact</Link></li>
                            <li><Link href="/login">Login</Link></li>
                        </ul>
                    </div>
                    <div>
                        <h4 style={{ marginBottom: '1.5rem' }}>Contact</h4>
                        <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '0.75rem', opacity: 0.7 }}>
                            <li>Varanasi, Uttar Pradesh, India</li>
                            <li>info@riversentinel.org</li>
                            <li>+91 (542) 234-5678</li>
                        </ul>
                    </div>
                </div>
                <div style={{ maxWidth: '1200px', margin: '2rem auto 0', paddingTop: '2rem', borderTop: '1px solid rgba(255,255,255,0.1)', opacity: 0.5, fontSize: '0.9rem', textAlign: 'center' }}>
                    &copy; {new Date().getFullYear()} RiverSentinel 2.0. All rights reserved.
                </div>
            </footer>
        </>
    );
};

export default FooterCTA;
