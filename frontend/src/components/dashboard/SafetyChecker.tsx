"use client";

import React, { useState, useEffect } from "react";

interface Station {
    id: string;
    station_code: string;
    station_name: string;
    location_name: string;
    status: string;
    is_online: boolean;
}

interface SafetyEvaluationResponse {
    status: string;
    evaluation_timestamp: string;
    station: {
        id: string;
        station_code: string;
        station_name: string;
        lifecycle_status: string;
    };
    observation: {
        observed_at: string;
        provenance: string;
        quality_status: string;
        raw_telemetry: {
            ph: number | null;
            turbidity: number | null;
            temperature: number | null;
            humidity: number | null;
            ec: number | null;
            water_level: number | null;
            do: number | null;
        };
    } | null;
    bathing_water_screening: {
        cpcb_class: string;
        suitability: 'SUITABLE' | 'UNSUITABLE' | 'INSUFFICIENT_TELEMETRY';
        criteria: {
            ph: { value: number | null; requirement: string; passed: boolean };
            dissolved_oxygen: { value: number | null; requirement: string; passed: boolean };
        };
        notes: string;
    };
    drinking_water_screening: {
        standard: string;
        suitability_level: 'NOT_RECOMMENDED_UNTIL_CONVENTIONAL_TREATMENT' | 'INSUFFICIENT_TELEMETRY' | 'DEVIATION_DETECTED';
        bis_is10500_compliance: {
            ph: { value: number | null; acceptable_limit: string; permissible_limit: string; status: string };
            turbidity: { value: number | null; acceptable_limit: string; permissible_limit: string; status: string };
            tds_ec: { value: number | null; benchmark: string; status: string };
        };
        disclaimer: string;
    };
    ecological_screening: {
        status: 'HEALTHY' | 'STRESSED' | 'HYPOXIC' | 'UNKNOWN';
        do_reading_mg_l: number | null;
        description: string;
    };
    sensor_anomaly_screening: {
        anomalies_detected: string[];
        is_simulated: boolean;
        confidence_score: number;
    };
}

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:5000';

export default function SafetyChecker() {
    const [stations, setStations] = useState<Station[]>([]);
    const [selectedStationId, setSelectedStationId] = useState<string>("");
    const [evaluation, setEvaluation] = useState<SafetyEvaluationResponse | null>(null);
    const [loadingStations, setLoadingStations] = useState<boolean>(true);
    const [loadingEval, setLoadingEval] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);

    // 1. Fetch Station Directory
    useEffect(() => {
        let isMounted = true;
        async function fetchStations() {
            setLoadingStations(true);
            try {
                const res = await fetch(`${BACKEND_URL}/api/v1/stations`);
                if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch stations`);
                const data = await res.json();
                if (isMounted && data.stations && data.stations.length > 0) {
                    setStations(data.stations);
                    const activeStn = data.stations.find((s: Station) => s.status === 'active') || data.stations[0];
                    setSelectedStationId(activeStn.id);
                }
            } catch (err: any) {
                console.error("Error loading stations:", err);
                if (isMounted) setError("Failed to load monitoring stations.");
            } finally {
                if (isMounted) setLoadingStations(false);
            }
        }
        fetchStations();
        return () => { isMounted = false; };
    }, []);

    // 2. Fetch Safety Evaluation for selected station
    useEffect(() => {
        if (!selectedStationId) return;

        let isMounted = true;
        async function fetchEvaluation() {
            setLoadingEval(true);
            setError(null);
            try {
                const res = await fetch(`${BACKEND_URL}/api/v1/stations/${selectedStationId}/evaluate-safety`);
                if (!res.ok) {
                    const errJson = await res.json().catch(() => ({}));
                    throw new Error(errJson.message || `HTTP ${res.status}: Failed to evaluate safety`);
                }
                const data: SafetyEvaluationResponse = await res.json();
                if (isMounted) {
                    setEvaluation(data);
                }
            } catch (err: any) {
                console.error("Error evaluating station safety:", err);
                if (isMounted) {
                    setError(err.message || "Failed to evaluate station water safety.");
                    setEvaluation(null);
                }
            } finally {
                if (isMounted) setLoadingEval(false);
            }
        }
        fetchEvaluation();
        return () => { isMounted = false; };
    }, [selectedStationId]);

    const currentStation = stations.find(s => s.id === selectedStationId);
    const obs = evaluation?.observation;
    const raw = obs?.raw_telemetry;

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            {/* Header & Station Selection */}
            <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '1rem' }}>
                <div>
                    <h2 style={{ margin: 0, fontWeight: 800, fontSize: '1.5rem', color: '#0f172a' }}>
                        Station-Specific Water Safety Screening
                    </h2>
                    <p style={{ margin: '0.25rem 0 0 0', color: '#64748b', fontSize: '0.9rem' }}>
                        Transparent screening against Central Pollution Control Board (CPCB) Class B and BIS IS 10500 standards.
                    </p>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <label style={{ fontSize: '0.85rem', fontWeight: 600, color: '#475569' }}>Monitoring Station:</label>
                    <select
                        value={selectedStationId}
                        onChange={(e) => setSelectedStationId(e.target.value)}
                        disabled={loadingStations || stations.length === 0}
                        style={{
                            padding: '0.5rem 1rem',
                            borderRadius: '0.5rem',
                            border: '1px solid #cbd5e1',
                            background: '#fff',
                            fontWeight: 600,
                            fontSize: '0.9rem'
                        }}
                    >
                        {stations.map(stn => (
                            <option key={stn.id} value={stn.id}>
                                {stn.station_name} ({stn.station_code}) - {stn.status.toUpperCase()}
                            </option>
                        ))}
                    </select>
                </div>
            </div>

            {/* Error Message */}
            {error && (
                <div style={{ padding: '1rem', borderRadius: '0.5rem', background: '#fef2f2', border: '1px solid #fecaca', color: '#b91c1c', fontSize: '0.9rem' }}>
                    ⚠️ {error}
                </div>
            )}

            {/* Station Status & Provenance Bar */}
            {currentStation && (
                <div style={{
                    display: 'flex',
                    flexWrap: 'wrap',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '0.75rem 1.25rem',
                    borderRadius: '0.5rem',
                    background: '#f8fafc',
                    border: '1px solid #e2e8f0',
                    fontSize: '0.85rem'
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <span style={{ fontWeight: 700, color: '#1e293b' }}>
                            📍 {currentStation.location_name}
                        </span>
                        <span style={{
                            padding: '0.2rem 0.5rem',
                            borderRadius: '9999px',
                            fontSize: '0.75rem',
                            fontWeight: 700,
                            background: currentStation.status === 'active' ? '#dcfce7' : '#fef9c3',
                            color: currentStation.status === 'active' ? '#15803d' : '#854d0e',
                            border: `1px solid ${currentStation.status === 'active' ? '#86efac' : '#fde047'}`
                        }}>
                            {currentStation.status.toUpperCase()}
                        </span>
                        <span style={{
                            padding: '0.2rem 0.5rem',
                            borderRadius: '9999px',
                            fontSize: '0.75rem',
                            fontWeight: 600,
                            background: currentStation.is_online ? '#eff6ff' : '#f1f5f9',
                            color: currentStation.is_online ? '#1d4ed8' : '#64748b'
                        }}>
                            {currentStation.is_online ? '🟢 ESP32 Node Connected' : '⚪ Node Offline / Not Yet Provisioned'}
                        </span>
                    </div>

                    <div style={{ color: '#64748b' }}>
                        {obs ? (
                            <span>
                                Latest Telemetry: <strong style={{ color: '#0f172a' }}>{new Date(obs.observed_at).toLocaleString()}</strong>
                                {' '}({obs.provenance === 'real_sensor' ? '🟢 Physical Hardware' : '🟡 Software Simulation'})
                            </span>
                        ) : (
                            <span style={{ color: '#b45309', fontWeight: 600 }}>
                                ⚠️ No telemetry records logged for this station
                            </span>
                        )}
                    </div>
                </div>
            )}

            {/* Loading Indicator */}
            {loadingEval && (
                <div className="card" style={{ padding: '2rem', textAlign: 'center', color: '#64748b' }}>
                    ⏳ Evaluating station parameters against CPCB and BIS standards...
                </div>
            )}

            {/* No Telemetry Available State */}
            {!loadingEval && !obs && (
                <div className="card" style={{ padding: '3rem', textAlign: 'center' }}>
                    <div style={{ fontSize: '2.5rem', marginBottom: '0.5rem' }}>📡</div>
                    <h3 style={{ margin: '0 0 0.5rem 0', color: '#1e293b' }}>
                        Awaiting Physical Node Deployment
                    </h3>
                    <p style={{ maxWidth: '480px', margin: '0 auto', fontSize: '0.9rem', color: '#64748b', lineHeight: 1.5 }}>
                        Station &ldquo;{currentStation?.station_name}&rdquo; is currently in {currentStation?.status.toUpperCase()} lifecycle status.
                        No physical sensor readings or simulation packets have been ingested yet. Safety assessments cannot be determined without valid observations.
                    </p>
                </div>
            )}

            {/* Assessment Grid */}
            {!loadingEval && obs && evaluation && (
                <>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.5rem' }}>
                        {/* 1. Religious & Recreational Bathing Safety (CPCB Class B) */}
                        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '1rem', borderTop: `4px solid ${evaluation.bathing_water_screening.suitability === 'SUITABLE' ? '#10b981' : '#ef4444'}` }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <div>
                                    <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 700 }}>
                                        Religious Bathing Safety 🏊
                                    </h3>
                                    <div style={{ fontSize: '0.75rem', color: '#64748b' }}>CPCB Class B Primary Water Criteria</div>
                                </div>
                                <span className={`badge ${evaluation.bathing_water_screening.suitability === 'SUITABLE' ? 'badge-green' : 'badge-red'}`} style={{ fontSize: '0.85rem', padding: '0.35rem 0.75rem' }}>
                                    {evaluation.bathing_water_screening.suitability}
                                </span>
                            </div>

                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.75rem', background: '#f8fafc', padding: '0.75rem', borderRadius: '0.5rem' }}>
                                <div style={{ textAlign: 'center' }}>
                                    <div style={{ fontSize: '0.75rem', color: '#64748b' }}>pH (6.5–8.5)</div>
                                    <div style={{ fontWeight: 800, fontSize: '1.1rem', color: evaluation.bathing_water_screening.criteria.ph.passed ? '#15803d' : '#b91c1c' }}>
                                        {raw?.ph !== null ? raw?.ph.toFixed(2) : '—'}
                                    </div>
                                    <div style={{ fontSize: '0.7rem', color: evaluation.bathing_water_screening.criteria.ph.passed ? '#166534' : '#991b1b' }}>
                                        {evaluation.bathing_water_screening.criteria.ph.passed ? '✓ In Range' : '✕ Out of Range'}
                                    </div>
                                </div>

                                <div style={{ textAlign: 'center' }}>
                                    <div style={{ fontSize: '0.75rem', color: '#64748b' }}>DO (≥ 5 mg/L)</div>
                                    <div style={{ fontWeight: 800, fontSize: '1.1rem', color: evaluation.bathing_water_screening.criteria.dissolved_oxygen.passed ? '#15803d' : '#b91c1c' }}>
                                        {raw?.do !== null ? `${raw?.do.toFixed(1)}` : '—'}
                                    </div>
                                    <div style={{ fontSize: '0.7rem', color: evaluation.bathing_water_screening.criteria.dissolved_oxygen.passed ? '#166534' : '#991b1b' }}>
                                        {evaluation.bathing_water_screening.criteria.dissolved_oxygen.passed ? '✓ Healthy' : '✕ Depleted'}
                                    </div>
                                </div>

                                <div style={{ textAlign: 'center' }}>
                                    <div style={{ fontSize: '0.75rem', color: '#64748b' }}>Turbidity</div>
                                    <div style={{ fontWeight: 800, fontSize: '1.1rem', color: '#0f172a' }}>
                                        {raw?.turbidity !== null ? `${raw?.turbidity.toFixed(0)} NTU` : '—'}
                                    </div>
                                    <div style={{ fontSize: '0.7rem', color: '#64748b' }}>
                                        {raw?.turbidity && raw.turbidity < 10 ? 'Clear Water' : 'Moderate Silt'}
                                    </div>
                                </div>
                            </div>

                            <p style={{ margin: 0, fontSize: '0.85rem', color: '#334155', lineHeight: 1.4 }}>
                                {evaluation.bathing_water_screening.notes}
                            </p>
                        </div>

                        {/* 2. Drinking Water Suitability Screening (BIS IS 10500:2012) */}
                        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '1rem', borderTop: '4px solid #f59e0b' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <div>
                                    <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 700 }}>
                                        Drinking Water Screening 🚰
                                    </h3>
                                    <div style={{ fontSize: '0.75rem', color: '#64748b' }}>BIS IS 10500:2012 Benchmark</div>
                                </div>
                                <span className="badge badge-orange" style={{ fontSize: '0.8rem', padding: '0.35rem 0.65rem' }}>
                                    TREATMENT MANDATORY
                                </span>
                            </div>

                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', background: '#fffbeb', padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid #fef3c7' }}>
                                <div>
                                    <div style={{ fontSize: '0.75rem', color: '#92400e', fontWeight: 600 }}>Screening Parameters</div>
                                    <div style={{ fontSize: '0.8rem', color: '#78350f', marginTop: '0.2rem' }}>
                                        pH: <strong>{raw?.ph ?? '—'}</strong> (Limit: 6.5–8.5)<br />
                                        Turbidity: <strong>{raw?.turbidity ?? '—'} NTU</strong> (Limit: 1–5)<br />
                                        EC: <strong>{raw?.ec ?? '—'} µS/cm</strong>
                                    </div>
                                </div>
                                <div>
                                    <div style={{ fontSize: '0.75rem', color: '#92400e', fontWeight: 600 }}>Suitability Determination</div>
                                    <div style={{ fontSize: '0.8rem', color: '#b45309', fontWeight: 700, marginTop: '0.2rem' }}>
                                        Raw river water requires conventional treatment & disinfection before drinking.
                                    </div>
                                </div>
                            </div>

                            <div style={{ padding: '0.65rem', borderRadius: '0.375rem', background: '#f8fafc', fontSize: '0.75rem', color: '#64748b', lineHeight: 1.4 }}>
                                <strong>⚠️ Scientific Disclaimer:</strong> {evaluation.drinking_water_screening.disclaimer}
                            </div>
                        </div>

                        {/* 3. Aquatic Ecology & Dissolved Oxygen Health */}
                        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '1rem', borderTop: '4px solid #0284c7' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <div>
                                    <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 700 }}>
                                        Aquatic Ecology Health 🐟
                                    </h3>
                                    <div style={{ fontSize: '0.75rem', color: '#64748b' }}>Dissolved Oxygen & River Biota</div>
                                </div>
                                <span className={`badge ${evaluation.ecological_screening.status === 'HEALTHY' ? 'badge-green' : 'badge-orange'}`} style={{ fontSize: '0.85rem' }}>
                                    {evaluation.ecological_screening.status}
                                </span>
                            </div>

                            <div style={{ background: '#f0f9ff', padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid #e0f2fe' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    <span style={{ fontSize: '0.85rem', color: '#0369a1', fontWeight: 600 }}>Dissolved Oxygen:</span>
                                    <strong style={{ fontSize: '1.25rem', color: '#0284c7' }}>
                                        {evaluation.ecological_screening.do_reading_mg_l !== null ? `${evaluation.ecological_screening.do_reading_mg_l.toFixed(1)} mg/L` : 'Sensor Uncalibrated'}
                                    </strong>
                                </div>
                                <p style={{ margin: '0.4rem 0 0 0', fontSize: '0.8rem', color: '#0284c7', lineHeight: 1.4 }}>
                                    {evaluation.ecological_screening.description}
                                </p>
                            </div>

                            <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
                                Benchmarks: ≥ 5.0 mg/L support Gangetic dolphin and major carp species. Depletion below 4.0 mg/L indicates acute biological stress.
                            </div>
                        </div>

                        {/* 4. Probe Anomaly Screening & Calibration */}
                        <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '1rem', borderTop: '4px solid #8b5cf6' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <div>
                                    <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 700 }}>
                                        Probe Calibration & Confidence 🔬
                                    </h3>
                                    <div style={{ fontSize: '0.75rem', color: '#64748b' }}>Hardware Health & Plausibility Checks</div>
                                </div>
                                <span className="badge" style={{ background: '#f3e8ff', color: '#7e22ce', border: '1px solid #d8b4fe' }}>
                                    Score: {(evaluation.sensor_anomaly_screening.confidence_score * 100).toFixed(0)}%
                                </span>
                            </div>

                            <div style={{ fontSize: '0.85rem', color: '#475569' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
                                    <span>Stream Provenance:</span>
                                    <strong>{evaluation.sensor_anomaly_screening.is_simulated ? '🟡 Synthetic Telemetry' : '🟢 Verified Physical Probe'}</strong>
                                </div>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
                                    <span>Quality Status:</span>
                                    <strong>{obs.quality_status.toUpperCase()}</strong>
                                </div>
                                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                    <span>Detected Anomalies:</span>
                                    <strong style={{ color: evaluation.sensor_anomaly_screening.anomalies_detected.length === 0 ? '#15803d' : '#b91c1c' }}>
                                        {evaluation.sensor_anomaly_screening.anomalies_detected.length === 0 ? 'None (Nominal)' : evaluation.sensor_anomaly_screening.anomalies_detected.join(', ')}
                                    </strong>
                                </div>
                            </div>

                            <div style={{ fontSize: '0.75rem', color: '#64748b', background: '#f8fafc', padding: '0.5rem', borderRadius: '0.375rem' }}>
                                Automated boundary check verifies that telemetry falls within physical electro-chemical limits for freshwater riverine systems.
                            </div>
                        </div>
                    </div>

                    {/* Sensor Snapshot Cards */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '1rem' }}>
                        {[
                            { label: "pH Level", value: raw?.ph !== null && raw?.ph !== undefined ? raw.ph.toFixed(2) : "—", unit: "", ok: raw?.ph !== null && raw?.ph !== undefined && raw.ph >= 6.5 && raw.ph <= 8.5 },
                            { label: "Turbidity", value: raw?.turbidity !== null && raw?.turbidity !== undefined ? raw.turbidity.toFixed(1) : "—", unit: "NTU", ok: raw?.turbidity !== null && raw?.turbidity !== undefined && raw.turbidity <= 10 },
                            { label: "Water Temp", value: raw?.temperature !== null && raw?.temperature !== undefined ? raw.temperature.toFixed(1) : "—", unit: "°C", ok: true },
                            { label: "Conductivity", value: raw?.ec !== null && raw?.ec !== undefined ? raw.ec.toFixed(0) : "—", unit: "µS/cm", ok: true },
                            { label: "Dissolved O₂", value: raw?.do !== null && raw?.do !== undefined ? raw.do.toFixed(1) : "—", unit: "mg/L", ok: raw?.do !== null && raw?.do !== undefined && raw.do >= 5.0 },
                            { label: "River Stage", value: raw?.water_level !== null && raw?.water_level !== undefined ? raw.water_level.toFixed(2) : "—", unit: "m", ok: raw?.water_level !== null && raw?.water_level !== undefined && raw.water_level < 70.26 },
                        ].map((sensor, i) => (
                            <div key={i} className="card" style={{ padding: '0.85rem', display: 'flex', flexDirection: 'column', borderLeft: `4px solid ${sensor.ok ? '#10b981' : '#f59e0b'}` }}>
                                <div style={{ fontSize: '0.75rem', color: '#64748b', fontWeight: 600 }}>{sensor.label}</div>
                                <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#0f172a', margin: '0.2rem 0' }}>
                                    {sensor.value}<small style={{ fontSize: '0.75rem', fontWeight: 500, marginLeft: '2px', color: '#64748b' }}>{sensor.unit}</small>
                                </div>
                                <div style={{ fontSize: '0.7rem', color: sensor.ok ? '#15803d' : '#b45309', fontWeight: 600 }}>
                                    {sensor.ok ? '✓ Within Limits' : '⚠️ Elevated / Check'}
                                </div>
                            </div>
                        ))}
                    </div>
                </>
            )}
        </div>
    );
}
