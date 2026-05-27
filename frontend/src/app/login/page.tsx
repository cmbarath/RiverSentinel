"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Navbar from "@/components/Navbar";
import WaveBackground from "@/components/WaveBackground";

const LoginPage = () => {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [showPassword, setShowPassword] = useState(false);
    const router = useRouter();

    const handleLogin = (e: React.FormEvent) => {
        e.preventDefault();
        if (email.includes("authority")) {
            router.push("/authority-dashboard");
        } else {
            router.push("/citizen-dashboard");
        }
    };

    const fillDemo = (role: "citizen" | "authority") => {
        if (role === "citizen") {
            setEmail("citizen@demo.com");
            setPassword("demo123");
        } else {
            setEmail("authority@demo.com");
            setPassword("demo123");
        }
    };

    return (
        <main style={{ minHeight: '100vh', background: 'linear-gradient(to bottom, #f0f9ff, #e0f2fe)', position: 'relative', display: 'flex', flexDirection: 'column' }}>
            <Navbar />
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', paddingTop: '80px', paddingBottom: '100px', zIndex: 20 }}>
                <div className="glass" style={{ width: '100%', maxWidth: '450px', padding: '2.5rem', borderRadius: '1.5rem' }}>
                    <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
                        <span style={{ fontSize: '3rem' }}>🌊</span>
                        <h2 style={{ marginTop: '1rem' }}>Welcome Back</h2>
                    </div>

                    <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                        <div>
                            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600 }}>Email Address</label>
                            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="name@company.com" required style={{ width: '100%', padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid var(--border)' }} />
                        </div>
                        <div style={{ position: 'relative' }}>
                            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600 }}>Password</label>
                            <input type={showPassword ? "text" : "password"} value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" required style={{ width: '100%', padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid var(--border)' }} />
                            <button type="button" onClick={() => setShowPassword(!showPassword)} style={{ position: 'absolute', right: '1rem', top: '2.5rem', color: '#64748b' }}>
                                {showPassword ? "👁️" : "👁️‍🗨️"}
                            </button>
                        </div>

                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.9rem' }}>
                            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                                <input type="checkbox" /> Remember me
                            </label>
                            <Link href="#" style={{ color: 'var(--primary)', fontWeight: 600 }}>Forgot Password?</Link>
                        </div>

                        <button type="submit" className="btn btn-primary" style={{ padding: '1rem' }}>Login</button>
                    </form>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', margin: '2rem 0' }}>
                        <div style={{ flex: 1, height: '1px', background: 'var(--border)' }}></div>
                        <span style={{ color: '#64748b', fontSize: '0.9rem' }}>Demo Accounts</span>
                        <div style={{ flex: 1, height: '1px', background: 'var(--border)' }}></div>
                    </div>

                    <div style={{ display: 'flex', gap: '1rem' }}>
                        <button onClick={() => fillDemo("citizen")} className="btn btn-secondary" style={{ flex: 1, fontSize: '0.85rem' }}>Citizen Demo</button>
                        <button onClick={() => fillDemo("authority")} className="btn btn-secondary" style={{ flex: 1, fontSize: '0.85rem' }}>Authority Demo</button>
                    </div>

                    <div style={{ textAlign: 'center', marginTop: '2rem', fontSize: '0.9rem', color: '#64748b' }}>
                        Don&apos;t have an account? <Link href="/signup" style={{ color: 'var(--primary)', fontWeight: 600 }}>Sign Up</Link>
                    </div>
                </div>
            </div>
            <WaveBackground />
        </main>
    );
};

export default LoginPage;
