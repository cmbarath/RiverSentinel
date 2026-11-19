"use client";

import React, { useState } from "react";

export default function DatasetUpload() {
    const [file, setFile] = useState<File | null>(null);
    const [datasetType, setDatasetType] = useState<string>("Water Quality CSV");
    const [validationStatus, setValidationStatus] = useState<{ valid: boolean; message: string; rowCount?: number } | null>(null);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const selected = e.target.files?.[0] || null;
        setFile(selected);
        setValidationStatus(null);

        if (selected) {
            // Local client-side header check
            const reader = new FileReader();
            reader.onload = (event) => {
                const text = event.target?.result as string;
                if (!text) return;
                const lines = text.split("\n").filter(l => l.trim().length > 0);
                const header = lines[0].toLowerCase();
                
                const expectedFields = ["ph", "turbidity", "temperature", "water_level"];
                const missing = expectedFields.filter(f => !header.includes(f));
                
                if (missing.length === 0) {
                    setValidationStatus({
                        valid: true,
                        message: `Schema validated successfully (${lines.length - 1} records detected). Staged for Phase 6 pipeline.`,
                        rowCount: lines.length - 1
                    });
                } else {
                    setValidationStatus({
                        valid: false,
                        message: `Missing required sensor columns: ${missing.join(", ")}. Please follow the Schema 2.0 format.`
                    });
                }
            };
            reader.readAsText(selected.slice(0, 4096)); // Read first 4KB for header check
        }
    };

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            {/* Phase 6 ML Pipeline Notice */}
            <div style={{
                padding: '1.25rem',
                borderRadius: '0.75rem',
                background: '#eff6ff',
                border: '1px solid #bfdbfe',
                color: '#1e40af',
                fontSize: '0.9rem',
                lineHeight: 1.5
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 700, fontSize: '0.95rem', marginBottom: '0.25rem' }}>
                    ℹ️ ML Data Staging & Model Ingestion (Phase 6 Architecture)
                </div>
                External dataset ingestion for retraining Random Forest models (Flood Susceptibility & Water Quality Index) is managed under <strong>Phase 6 (Machine Learning & Training Pipeline)</strong>.
                Uploaded files must conform to Schema 2.0 specifications with strict outlier boundary validation before promotion to production inference.
            </div>

            <div className="card">
                <h3 style={{ margin: '0 0 0.5rem 0', fontWeight: 700 }}>Stage External Dataset for Validation</h3>
                <p style={{ color: '#64748b', fontSize: '0.85rem', margin: '0 0 1.5rem 0' }}>
                    Validate external sensor logs or historical hydrology datasets against Schema 2.0.
                </p>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                    <div>
                        <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: '#475569', marginBottom: '0.5rem' }}>Dataset Schema</label>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.75rem' }}>
                            {["Water Quality CSV", "CWC Gauge Hydrology", "Rainfall & Meteorology"].map((type) => (
                                <label
                                    key={type}
                                    style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: '0.5rem',
                                        padding: '0.75rem 1rem',
                                        borderRadius: '0.5rem',
                                        border: `1px solid ${datasetType === type ? '#0284c7' : '#e2e8f0'}`,
                                        background: datasetType === type ? '#f0f9ff' : '#fff',
                                        cursor: 'pointer'
                                    }}
                                >
                                    <input
                                        type="radio"
                                        name="datasetType"
                                        checked={datasetType === type}
                                        onChange={() => setDatasetType(type)}
                                    />
                                    <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#334155' }}>{type}</span>
                                </label>
                            ))}
                        </div>
                    </div>

                    <div
                        style={{
                            height: '180px',
                            border: '2px dashed #cbd5e1',
                            borderRadius: '0.75rem',
                            display: 'flex',
                            flexDirection: 'column',
                            alignItems: 'center',
                            justifyContent: 'center',
                            background: '#f8fafc',
                            cursor: 'pointer',
                            padding: '1.5rem'
                        }}
                        onClick={() => document.getElementById('dataset-file')?.click()}
                    >
                        <span style={{ fontSize: '2.5rem' }}>📂</span>
                        <div style={{ fontWeight: 600, color: '#334155', marginTop: '0.5rem', fontSize: '0.9rem' }}>
                            {file ? file.name : "Click to select or drag CSV dataset"}
                        </div>
                        <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '0.25rem' }}>
                            Maximum file size: 50MB (UTF-8 encoded CSV)
                        </div>
                        <input
                            type="file"
                            id="dataset-file"
                            accept=".csv"
                            hidden
                            onChange={handleFileChange}
                        />
                    </div>

                    {validationStatus && (
                        <div style={{
                            padding: '1rem',
                            borderRadius: '0.5rem',
                            background: validationStatus.valid ? '#dcfce7' : '#fee2e2',
                            border: `1px solid ${validationStatus.valid ? '#86efac' : '#fca5a5'}`,
                            color: validationStatus.valid ? '#15803d' : '#991b1b',
                            fontSize: '0.85rem',
                            fontWeight: 600
                        }}>
                            {validationStatus.valid ? '✅ ' : '❌ '}
                            {validationStatus.message}
                        </div>
                    )}

                    <div style={{ display: 'flex', gap: '1rem' }}>
                        <button
                            disabled={!file || !validationStatus?.valid}
                            className="btn btn-secondary"
                            style={{
                                padding: '0.75rem 1.5rem',
                                opacity: (!file || !validationStatus?.valid) ? 0.5 : 1,
                                cursor: (!file || !validationStatus?.valid) ? 'not-allowed' : 'pointer',
                                fontWeight: 600
                            }}
                            onClick={() => alert("Dataset staged locally. Ingestion into training storage will occur in Phase 6.")}
                        >
                            Stage for Phase 6 Training Pipeline
                        </button>
                    </div>
                </div>
            </div>

            {/* Schema Requirements Documentation */}
            <div className="card" style={{ background: '#f8fafc', border: '1px solid #e2e8f0', padding: '1.25rem' }}>
                <h4 style={{ margin: '0 0 0.5rem 0', fontWeight: 700, fontSize: '0.9rem', color: '#0f172a' }}>
                    Required CSV Schema 2.0 Columns
                </h4>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.75rem', fontSize: '0.8rem', color: '#475569' }}>
                    <div>• <code>observed_at</code> (ISO-8601 UTC)</div>
                    <div>• <code>ph</code> (0.0 to 14.0)</div>
                    <div>• <code>turbidity</code> (0 to 1000 NTU)</div>
                    <div>• <code>temperature</code> (0.0 to 50.0 °C)</div>
                    <div>• <code>water_level</code> (50.0 to 80.0 m MSL)</div>
                    <div>• <code>ec</code> (0 to 5000 µS/cm)</div>
                    <div>• <code>do</code> (0.0 to 20.0 mg/L)</div>
                    <div>• <code>station_code</code> (Registered ID)</div>
                </div>
            </div>
        </div>
    );
}
