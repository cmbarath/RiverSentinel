"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import Navbar from "@/components/Navbar";
import WaveBackground from "@/components/WaveBackground";
import { supabase } from "@/lib/supabaseClient";

const LoginPage = () => {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [showPassword, setShowPassword] = useState(false);
    const [loading, setLoading] = useState(false);
    const [errorMessage, setErrorMessage] = useState<string | null>(null);
    const router = useRouter();

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setErrorMessage(null);

        try {
            // Real Supabase Authentication
            const { data, error } = await supabase.auth.signInWithPassword({
                email,
                password,
            });

            if (error) {
                // If invalid credentials or unconfirmed email
                setErrorMessage(error.message || "Invalid email or password.");
                setLoading(false);
                return;
            }

            if (data.user) {
                // Fetch user role from public.profiles
                const { data: profile } = await supabase
                    .from('profiles')
                    .select('role')
                    .eq('id', data.user.id)
                    .single();

                const role = profile?.role || 'citizen';
                if (role === 'authority_admin' || role === 'field_officer') {
                    router.push('/authority-dashboard');
                } else {
                    router.push('/citizen-dashboard');
                }
            }
        } catch (err: unknown) {
            console.error("Login exception:", err);
            const msg = err instanceof Error ? err.message : "An unexpected error occurred during login.";
            setErrorMessage(msg);
        } finally {
            setLoading(false);
        }
    };

    const handleDemoBypass = (role: "citizen" | "authority") => {
        if (role === "authority") {
            router.push("/authority-dashboard");
        } else {
            router.push("/citizen-dashboard");
        }
    };

    const fillDemo = (role: "citizen" | "authority") => {
        if (role === "citizen") {
            setEmail("citizen@demo.com");
            setPassword("CitizenPass@2026");
        } else {
            setEmail("authority@demo.com");
            setPassword("AuthorityPass@2026");
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
                        <p style={{ color: '#64748b', fontSize: '0.9rem', marginTop: '0.25rem' }}>River Sentinel 2.0 Secure Access</p>
                    </div>

                    {errorMessage && (
                        <div style={{ background: '#fef2f2', border: '1px solid #fecaca', color: '#b91c1c', padding: '0.75rem 1rem', borderRadius: '0.5rem', marginBottom: '1.25rem', fontSize: '0.85rem' }}>
                            {errorMessage}
                        </div>
                    )}

                    <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                        <div>
                            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600 }}>Email Address</label>
                            <input
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                placeholder="name@domain.com"
                                required
                                style={{ width: '100%', padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid var(--border)' }}
                            />
                        </div>
                        <div style={{ position: 'relative' }}>
                            <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600 }}>Password</label>
                            <input
                                type={showPassword ? "text" : "password"}
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder="••••••••"
                                required
                                style={{ width: '100%', padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid var(--border)' }}
                            />
                            <button
                                type="button"
                                onClick={() => setShowPassword(!showPassword)}
                                style={{ position: 'absolute', right: '1rem', top: '2.5rem', color: '#64748b', background: 'none', border: 'none', cursor: 'pointer' }}
                            >
                                {showPassword ? "👁️" : "👁️‍🗨️"}
                            </button>
                        </div>

                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.9rem' }}>
                            <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                                <input type="checkbox" /> Remember me
                            </label>
                            <Link href="#" style={{ color: 'var(--primary)', fontWeight: 600 }}>Forgot Password?</Link>
                        </div>

                        <button
                            type="submit"
                            disabled={loading}
                            className="btn btn-primary"
                            style={{ padding: '1rem', cursor: loading ? 'not-allowed' : 'pointer', opacity: loading ? 0.7 : 1 }}
                        >
                            {loading ? "Authenticating..." : "Login"}
                        </button>
                    </form>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', margin: '2rem 0' }}>
                        <div style={{ flex: 1, height: '1px', background: 'var(--border)' }}></div>
                        <span style={{ color: '#64748b', fontSize: '0.85rem' }}>Demo / Offline Preview</span>
                        <div style={{ flex: 1, height: '1px', background: 'var(--border)' }}></div>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                        <div style={{ display: 'flex', gap: '0.75rem' }}>
                            <button onClick={() => fillDemo("citizen")} type="button" className="btn btn-secondary" style={{ flex: 1, fontSize: '0.8rem', padding: '0.5rem' }}>
                                Prefill Citizen
                            </button>
                            <button onClick={() => fillDemo("authority")} type="button" className="btn btn-secondary" style={{ flex: 1, fontSize: '0.8rem', padding: '0.5rem' }}>
                                Prefill Authority
                            </button>
                        </div>
                        <div style={{ display: 'flex', gap: '0.75rem' }}>
                            <button onClick={() => handleDemoBypass("citizen")} type="button" style={{ flex: 1, fontSize: '0.75rem', padding: '0.4rem', background: '#f8fafc', border: '1px dashed #cbd5e1', borderRadius: '0.375rem', color: '#475569', cursor: 'pointer' }}>
                                Quick Preview Citizen
                            </button>
                            <button onClick={() => handleDemoBypass("authority")} type="button" style={{ flex: 1, fontSize: '0.75rem', padding: '0.4rem', background: '#f8fafc', border: '1px dashed #cbd5e1', borderRadius: '0.375rem', color: '#475569', cursor: 'pointer' }}>
                                Quick Preview Authority
                            </button>
                        </div>
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
