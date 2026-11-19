"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabaseClient";

const SignUpWizard = () => {
    const [step, setStep] = useState(1);
    const [role, setRole] = useState<"citizen" | "authority" | null>(null);
    const [loading, setLoading] = useState(false);
    const [errorMessage, setErrorMessage] = useState<string | null>(null);
    const [successMessage, setSuccessMessage] = useState<string | null>(null);

    const [formData, setFormData] = useState({
        fullName: "",
        email: "",
        phone: "",
        password: "",
        confirmPassword: "",
        address: "",
        city: "Varanasi",
        state: "UP",
        pincode: "",
        language: "English",
        organization: "",
        department: "Pollution Board",
        designation: "",
        employeeId: "",
        officialEmail: "",
    });
    const router = useRouter();

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    };

    const nextStep = () => {
        setErrorMessage(null);
        setStep(step + 1);
    };

    const prevStep = () => {
        setErrorMessage(null);
        setStep(step - 1);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setErrorMessage(null);
        setSuccessMessage(null);

        if (!formData.email || !formData.password) {
            setErrorMessage("Email and password are required.");
            setLoading(false);
            return;
        }

        if (formData.password.length < 6) {
            setErrorMessage("Password must be at least 6 characters.");
            setLoading(false);
            return;
        }

        try {
            // Real Supabase Auth Registration
            // Role elevation defense: Database trigger handle_new_user() hardcodes role = 'citizen'
            // Requested role is passed only in user_metadata for administrative review.
            const { data, error } = await supabase.auth.signUp({
                email: formData.email,
                password: formData.password,
                options: {
                    data: {
                        full_name: formData.fullName,
                        phone: formData.phone,
                        city: formData.city,
                        language: formData.language,
                        address: formData.address,
                        requested_role: role,
                        organization: formData.organization,
                        department: formData.department,
                        employee_id: formData.employeeId,
                    }
                }
            });

            if (error) {
                setErrorMessage(error.message);
                setLoading(false);
                return;
            }

            if (data.user) {
                setSuccessMessage(
                    role === "authority"
                        ? "Account created! Authority access requests require administrative verification. Check your email for confirmation."
                        : "Registration successful! You may now sign in to access citizen river reports."
                );

                setTimeout(() => {
                    router.push("/login");
                }, 2500);
            }
        } catch (err: unknown) {
            console.error("Signup exception:", err);
            const msg = err instanceof Error ? err.message : "An unexpected error occurred during signup.";
            setErrorMessage(msg);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="glass" style={{ width: '100%', maxWidth: '600px', padding: '2.5rem', borderRadius: '1.5rem', margin: '2rem auto' }}>
            <div style={{ display: 'flex', justifyContent: 'center', gap: '1rem', marginBottom: '2rem' }}>
                {[1, 2, 3].map((s) => (
                    <div key={s} style={{ width: '12px', height: '12px', borderRadius: '50%', background: step === s ? 'var(--primary)' : '#cbd5e1' }}></div>
                ))}
            </div>

            {errorMessage && (
                <div style={{ background: '#fef2f2', border: '1px solid #fecaca', color: '#b91c1c', padding: '0.75rem 1rem', borderRadius: '0.5rem', marginBottom: '1.25rem', fontSize: '0.85rem' }}>
                    {errorMessage}
                </div>
            )}

            {successMessage && (
                <div style={{ background: '#f0fdf4', border: '1px solid #bbf7d0', color: '#15803d', padding: '0.75rem 1rem', borderRadius: '0.5rem', marginBottom: '1.25rem', fontSize: '0.85rem' }}>
                    {successMessage}
                </div>
            )}

            <form onSubmit={handleSubmit}>
                {step === 1 && (
                    <div>
                        <h2 style={{ textAlign: 'center', marginBottom: '0.5rem' }}>Choose Your Role</h2>
                        <p style={{ textAlign: 'center', color: '#64748b', fontSize: '0.85rem', marginBottom: '1.5rem' }}>Select account type to configure dashboard features</p>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
                            <div
                                className="card"
                                style={{ cursor: 'pointer', border: role === "citizen" ? '2px solid var(--primary)' : '1px solid var(--border)', textAlign: 'center', padding: '1.5rem' }}
                                onClick={() => { setRole("citizen"); nextStep(); }}
                            >
                                <div style={{ fontSize: '3rem', marginBottom: '0.5rem' }}>👤</div>
                                <h3 style={{ fontSize: '1.2rem', marginBottom: '0.5rem' }}>Citizen</h3>
                                <ul style={{ fontSize: '0.85rem', color: '#64748b', listStyle: 'none', padding: 0 }}>
                                    <li>• Report Pollution</li>
                                    <li>• Real-time Alerts</li>
                                    <li>• Ghat Water Quality</li>
                                </ul>
                            </div>
                            <div
                                className="card"
                                style={{ cursor: 'pointer', border: role === "authority" ? '2px solid var(--primary)' : '1px solid var(--border)', textAlign: 'center', padding: '1.5rem' }}
                                onClick={() => { setRole("authority"); nextStep(); }}
                            >
                                <div style={{ fontSize: '3rem', marginBottom: '0.5rem' }}>🛡️</div>
                                <h3 style={{ fontSize: '1.2rem', marginBottom: '0.5rem' }}>Authority / Officer</h3>
                                <ul style={{ fontSize: '0.85rem', color: '#64748b', listStyle: 'none', padding: 0 }}>
                                    <li>• Station Monitoring</li>
                                    <li>• Incident Management</li>
                                    <li>• Requires Admin Approval</li>
                                </ul>
                            </div>
                        </div>
                    </div>
                )}

                {step === 2 && (
                    <div>
                        <h2 style={{ textAlign: 'center', marginBottom: '1.5rem' }}>Basic Information</h2>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                            <input
                                type="text"
                                name="fullName"
                                placeholder="Full Name"
                                value={formData.fullName}
                                onChange={handleInputChange}
                                required
                                style={{ padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid var(--border)' }}
                            />
                            <input
                                type="email"
                                name="email"
                                placeholder="Email Address"
                                value={formData.email}
                                onChange={handleInputChange}
                                required
                                style={{ padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid var(--border)' }}
                            />
                            <input
                                type="tel"
                                name="phone"
                                placeholder="Phone Number (+91)"
                                value={formData.phone}
                                onChange={handleInputChange}
                                required
                                style={{ padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid var(--border)' }}
                            />
                            <input
                                type="password"
                                name="password"
                                placeholder="Password (minimum 6 characters)"
                                value={formData.password}
                                onChange={handleInputChange}
                                required
                                style={{ padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid var(--border)' }}
                            />
                            <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
                                <button type="button" onClick={prevStep} className="btn btn-secondary" style={{ flex: 1 }}>Back</button>
                                <button
                                    type="button"
                                    onClick={() => {
                                        if (!formData.fullName || !formData.email || !formData.password) {
                                            setErrorMessage("Please fill in all basic fields.");
                                            return;
                                        }
                                        nextStep();
                                    }}
                                    className="btn btn-primary"
                                    style={{ flex: 1 }}
                                >
                                    Continue
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                {step === 3 && role === "citizen" && (
                    <div>
                        <h2 style={{ textAlign: 'center', marginBottom: '1.5rem' }}>Citizen Profile Details</h2>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                            <textarea
                                name="address"
                                placeholder="Address / Ghat Vicinity"
                                value={formData.address}
                                onChange={handleInputChange}
                                rows={3}
                                style={{ padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid var(--border)', fontFamily: 'inherit' }}
                            />
                            <select
                                name="city"
                                value={formData.city}
                                onChange={handleInputChange}
                                style={{ padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid var(--border)' }}
                            >
                                <option value="Varanasi">Varanasi</option>
                                <option value="Prayagraj">Prayagraj</option>
                                <option value="Kanpur">Kanpur</option>
                            </select>
                            <select
                                name="language"
                                value={formData.language}
                                onChange={handleInputChange}
                                style={{ padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid var(--border)' }}
                            >
                                <option value="English">English</option>
                                <option value="Hindi">हिन्दी</option>
                                <option value="Bengali">বাংলা</option>
                            </select>
                            <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
                                <button type="button" onClick={prevStep} className="btn btn-secondary" style={{ flex: 1 }}>Back</button>
                                <button
                                    type="submit"
                                    disabled={loading}
                                    className="btn btn-primary"
                                    style={{ flex: 1, opacity: loading ? 0.7 : 1 }}
                                >
                                    {loading ? "Registering..." : "Finish Registration"}
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                {step === 3 && role === "authority" && (
                    <div>
                        <h2 style={{ textAlign: 'center', marginBottom: '1rem' }}>Authority Verification Request</h2>
                        <div style={{ fontSize: '0.8rem', color: '#92400e', background: '#fffbeb', padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid #fde68a', marginBottom: '1rem' }}>
                            ℹ️ <strong>Security Notice:</strong> In accordance with role-based security rules, new authority accounts are provisioned as citizen profiles until official identity and organization credentials are administratively verified.
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                            <input
                                type="text"
                                name="organization"
                                placeholder="Organization Name (e.g. UPPCB)"
                                value={formData.organization}
                                onChange={handleInputChange}
                                required
                                style={{ padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid var(--border)' }}
                            />
                            <select
                                name="department"
                                value={formData.department}
                                onChange={handleInputChange}
                                style={{ padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid var(--border)' }}
                            >
                                <option value="Pollution Board">UP Pollution Control Board</option>
                                <option value="Municipal">Varanasi Nagar Nigam</option>
                                <option value="Disaster Mgmt">District Disaster Management Authority</option>
                                <option value="Irrigation">UP Irrigation & Water Resources</option>
                            </select>
                            <input
                                type="text"
                                name="employeeId"
                                placeholder="Official Employee ID / Badge No."
                                value={formData.employeeId}
                                onChange={handleInputChange}
                                required
                                style={{ padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid var(--border)' }}
                            />
                            <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
                                <button type="button" onClick={prevStep} className="btn btn-secondary" style={{ flex: 1 }}>Back</button>
                                <button
                                    type="submit"
                                    disabled={loading}
                                    className="btn btn-primary"
                                    style={{ flex: 1, opacity: loading ? 0.7 : 1 }}
                                >
                                    {loading ? "Submitting Request..." : "Submit for Verification"}
                                </button>
                            </div>
                        </div>
                    </div>
                )}
            </form>

            <div style={{ textAlign: 'center', marginTop: '1.5rem', fontSize: '0.9rem', color: '#64748b' }}>
                Already have an account? <Link href="/login" style={{ color: 'var(--primary)', fontWeight: 600 }}>Login</Link>
            </div>
        </div>
    );
};

export default SignUpWizard;
