"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

const SignUpWizard = () => {
    const [step, setStep] = useState(1);
    const [role, setRole] = useState<"citizen" | "authority" | null>(null);
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

    const nextStep = () => setStep(step + 1);
    const prevStep = () => setStep(step - 1);

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        // Simulate submission
        setTimeout(() => {
            alert("Registration Successful!");
            router.push(role === "authority" ? "/authority-dashboard" : "/citizen-dashboard");
        }, 1000);
    };

    return (
        <div className="glass" style={{ width: '100%', maxWidth: '600px', padding: '2.5rem', borderRadius: '1.5rem', margin: '2rem auto' }}>
            <div style={{ display: 'flex', justifyContent: 'center', gap: '1rem', marginBottom: '2rem' }}>
                {[1, 2, 3].map((s) => (
                    <div key={s} style={{ width: '12px', height: '12px', borderRadius: '50%', background: step === s ? 'var(--primary)' : '#cbd5e1' }}></div>
                ))}
            </div>

            <form onSubmit={handleSubmit}>
                {step === 1 && (
                    <div>
                        <h2 style={{ textAlign: 'center', marginBottom: '1.5rem' }}>Choose Your Role</h2>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
                            <div
                                className="card"
                                style={{ cursor: 'pointer', border: role === "citizen" ? '2px solid var(--primary)' : '1px solid var(--border)', textAlign: 'center' }}
                                onClick={() => { setRole("citizen"); nextStep(); }}
                            >
                                <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>👤</div>
                                <h3 style={{ fontSize: '1.2rem', marginBottom: '0.5rem' }}>Citizen</h3>
                                <ul style={{ fontSize: '0.85rem', color: '#64748b', listStyle: 'none', padding: 0 }}>
                                    <li>• Report Pollution</li>
                                    <li>• Get Alerts</li>
                                    <li>• Earn Rewards</li>
                                </ul>
                            </div>
                            <div
                                className="card"
                                style={{ cursor: 'pointer', border: role === "authority" ? '2px solid var(--primary)' : '1px solid var(--border)', textAlign: 'center' }}
                                onClick={() => { setRole("authority"); nextStep(); }}
                            >
                                <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🛡️</div>
                                <h3 style={{ fontSize: '1.2rem', marginBottom: '0.5rem' }}>Authority</h3>
                                <ul style={{ fontSize: '0.85rem', color: '#64748b', listStyle: 'none', padding: 0 }}>
                                    <li>• Monitor Stations</li>
                                    <li>• Manage Reports</li>
                                    <li>• Send Alerts</li>
                                </ul>
                            </div>
                        </div>
                    </div>
                )}

                {step === 2 && (
                    <div>
                        <h2 style={{ textAlign: 'center', marginBottom: '1.5rem' }}>Basic Information</h2>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                            <input type="text" name="fullName" placeholder="Full Name" value={formData.fullName} onChange={handleInputChange} required style={{ padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid var(--border)' }} />
                            <input type="email" name="email" placeholder="Email Address" value={formData.email} onChange={handleInputChange} required style={{ padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid var(--border)' }} />
                            <input type="tel" name="phone" placeholder="Phone Number (+91)" value={formData.phone} onChange={handleInputChange} required style={{ padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid var(--border)' }} />
                            <input type="password" name="password" placeholder="Password" value={formData.password} onChange={handleInputChange} required style={{ padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid var(--border)' }} />
                            <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
                                <button type="button" onClick={prevStep} className="btn btn-secondary" style={{ flex: 1 }}>Back</button>
                                <button type="button" onClick={nextStep} className="btn btn-primary" style={{ flex: 1 }}>Continue</button>
                            </div>
                        </div>
                    </div>
                )}

                {step === 3 && role === "citizen" && (
                    <div>
                        <h2 style={{ textAlign: 'center', marginBottom: '1.5rem' }}>Additional Details</h2>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                            <textarea name="address" placeholder="Address" value={formData.address} onChange={handleInputChange} rows={3} style={{ padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid var(--border)', fontFamily: 'inherit' }} />
                            <select name="city" value={formData.city} onChange={handleInputChange} style={{ padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid var(--border)' }}>
                                <option value="Varanasi">Varanasi</option>
                                <option value="Prayagraj">Prayagraj</option>
                                <option value="Kanpur">Kanpur</option>
                            </select>
                            <select name="language" value={formData.language} onChange={handleInputChange} style={{ padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid var(--border)' }}>
                                <option value="English">English</option>
                                <option value="Hindi">हिन्दी</option>
                                <option value="Bengali">বাংলা</option>
                            </select>
                            <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
                                <button type="button" onClick={prevStep} className="btn btn-secondary" style={{ flex: 1 }}>Back</button>
                                <button type="submit" className="btn btn-primary" style={{ flex: 1 }}>Finish Registration</button>
                            </div>
                        </div>
                    </div>
                )}

                {step === 3 && role === "authority" && (
                    <div>
                        <h2 style={{ textAlign: 'center', marginBottom: '1.5rem' }}>Authority Credentials</h2>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                            <input type="text" name="organization" placeholder="Organization Name" value={formData.organization} onChange={handleInputChange} required style={{ padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid var(--border)' }} />
                            <select name="department" value={formData.department} onChange={handleInputChange} style={{ padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid var(--border)' }}>
                                <option value="Pollution Board">Pollution Board</option>
                                <option value="Municipal">Municipal Corporation</option>
                                <option value="Disaster Mgmt">Disaster Management</option>
                            </select>
                            <input type="text" name="employeeId" placeholder="Employee ID" value={formData.employeeId} onChange={handleInputChange} required style={{ padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid var(--border)' }} />
                            <div style={{ fontSize: '0.8rem', color: '#64748b', background: '#fff7ed', padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid #fed7aa' }}>
                                ⚠️ Verification may take 24-48 hours. Please ensure your credentials are correct.
                            </div>
                            <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
                                <button type="button" onClick={prevStep} className="btn btn-secondary" style={{ flex: 1 }}>Back</button>
                                <button type="submit" className="btn btn-primary" style={{ flex: 1 }}>Submit for Review</button>
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
