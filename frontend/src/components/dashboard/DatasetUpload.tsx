"use client";

import React, { useState } from "react";

const DatasetUpload = () => {
    const [file, setFile] = useState<File | null>(null);
    const [uploading, setUploading] = useState(false);

    const handleUpload = () => {
        if (!file) return;
        setUploading(true);
        setTimeout(() => {
            setUploading(false);
            alert("Dataset uploaded successfully! 2,450 rows processed.");
            setFile(null);
        }, 2000);
    };

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            <div className="card">
                <h3>Upload Regional Data</h3>
                <p style={{ color: '#64748b', marginBottom: '2rem' }}>Merge external water quality or industrial datasets into the RiverSentinel AI engine.</p>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                    <div>
                        <label style={{ display: 'block', fontSize: '0.9rem', fontWeight: 600, marginBottom: '0.5rem' }}>Dataset Type</label>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
                            {["Water Quality CSV", "Industrial Registry", "Flood History", "Rainfall Data"].map((type) => (
                                <label key={type} className="card" style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '1rem', cursor: 'pointer' }}>
                                    <input type="radio" name="dataset" defaultChecked={type.includes("Water")} />
                                    <span style={{ fontSize: '0.9rem', fontWeight: 600 }}>{type}</span>
                                </label>
                            ))}
                        </div>
                    </div>

                    <div
                        style={{
                            height: '200px',
                            border: '2px dashed var(--border)',
                            borderRadius: '1rem',
                            display: 'flex',
                            flexDirection: 'column',
                            alignItems: 'center',
                            justifyContent: 'center',
                            background: '#f8fafc',
                            cursor: 'pointer'
                        }}
                        onClick={() => document.getElementById('dataset-file')?.click()}
                    >
                        <span style={{ fontSize: '3rem' }}>📁</span>
                        <p style={{ color: '#64748b', marginTop: '0.5rem' }}>{file ? file.name : "Drag & drop CSV or click to browse"}</p>
                        <input type="file" id="dataset-file" hidden onChange={(e) => setFile(e.target.files?.[0] || null)} />
                    </div>

                    <button
                        className="btn btn-primary"
                        style={{ padding: '1rem', opacity: file ? 1 : 0.5 }}
                        disabled={!file || uploading}
                        onClick={handleUpload}
                    >
                        {uploading ? "Uploading & Validating..." : "Start Upload"}
                    </button>
                </div>
            </div>

            <div className="card">
                <h3>Recent Uploads</h3>
                <div style={{ overflowX: 'auto', marginTop: '1rem' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                        <thead>
                            <tr style={{ borderBottom: '1px solid var(--border)', color: '#64748b', fontSize: '0.85rem' }}>
                                <th style={{ padding: '0.75rem' }}>Date</th>
                                <th style={{ padding: '0.75rem' }}>Filename</th>
                                <th style={{ padding: '0.75rem' }}>Type</th>
                                <th style={{ padding: '0.75rem' }}>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            {[
                                { d: "2026-02-05", f: "up_water_q4.csv", t: "Water Quality", s: "PROCESSED" },
                                { d: "2026-02-01", f: "varanasi_factories.xlsx", t: "Industrial", s: "PROCESSED" },
                            ].map((u, i) => (
                                <tr key={i} style={{ borderBottom: '1px solid #f1f5f9' }}>
                                    <td style={{ padding: '0.75rem' }}>{u.d}</td>
                                    <td style={{ padding: '0.75rem', fontWeight: 600 }}>{u.f}</td>
                                    <td style={{ padding: '0.75rem' }}>{u.t}</td>
                                    <td style={{ padding: '0.75rem' }}><span className="badge badge-green">{u.s}</span></td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};

export default DatasetUpload;
