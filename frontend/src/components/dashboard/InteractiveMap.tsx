"use client";

import React, { useEffect, useState, useSyncExternalStore } from "react";
import dynamic from "next/dynamic";
import "leaflet/dist/leaflet.css";

// Dynamic import for Leaflet (SSR-friendly)
const MapContainer = dynamic(() => import("react-leaflet").then(m => m.MapContainer), { ssr: false });
const TileLayer = dynamic(() => import("react-leaflet").then(m => m.TileLayer), { ssr: false });
const Marker = dynamic(() => import("react-leaflet").then(m => m.Marker), { ssr: false });
const Popup = dynamic(() => import("react-leaflet").then(m => m.Popup), { ssr: false });

interface MonitoringStation {
    id: string;
    station_code: string;
    station_name: string;
    latitude: number;
    longitude: number;
    status: string;
    location_name?: string;
    warning_water_level_m?: number;
    danger_water_level_m?: number;
}

const DEFAULT_STATIONS: MonitoringStation[] = [
    { id: "1", station_code: "STN-VAR-ASSI-01", station_name: "Assi Ghat Monitoring Station", latitude: 25.2891, longitude: 83.0067, status: "planned", location_name: "Assi Ghat, Varanasi", warning_water_level_m: 70.26, danger_water_level_m: 71.26 },
    { id: "2", station_code: "STN-VAR-DASH-02", station_name: "Dashashwamedh Ghat Station", latitude: 25.3061, longitude: 83.0104, status: "planned", location_name: "Dashashwamedh Ghat, Varanasi", warning_water_level_m: 70.26, danger_water_level_m: 71.26 },
    { id: "3", station_code: "STN-VAR-MANI-03", station_name: "Manikarnika Ghat Station", latitude: 25.3110, longitude: 83.0125, status: "planned", location_name: "Manikarnika Ghat, Varanasi", warning_water_level_m: 70.26, danger_water_level_m: 71.26 },
    { id: "4", station_code: "STN-VAR-RAJG-04", station_name: "Rajghat Monitoring Station", latitude: 25.3267, longitude: 83.0335, status: "planned", location_name: "Rajghat, Varanasi", warning_water_level_m: 70.26, danger_water_level_m: 71.26 },
];

const emptySubscribe = () => () => {};

const InteractiveMap = () => {
    const isClient = useSyncExternalStore(
        emptySubscribe,
        () => true,
        () => false
    );
    const [stations, setStations] = useState<MonitoringStation[]>(DEFAULT_STATIONS);
    const [loadingStations, setLoadingStations] = useState(true);

    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:5000';

    useEffect(() => {
        // Fetch real monitoring stations from River Sentinel backend API
        fetch(`${backendUrl}/api/v1/stations`)
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success' && Array.isArray(data.stations) && data.stations.length > 0) {
                    setStations(data.stations);
                }
            })
            .catch(err => {
                console.warn("[Map] Failed to load stations from backend, using Varanasi baseline:", err);
            })
            .finally(() => {
                setLoadingStations(false);
            });
    }, [backendUrl]);

    if (!isClient) {
        return (
            <div style={{ height: '600px', background: '#f1f5f9', borderRadius: '1rem', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#64748b' }}>
                Loading Ganga River Map...
            </div>
        );
    }

    return (
        <div className="card" style={{ height: '70vh', padding: 0, overflow: 'hidden', position: 'relative' }}>
            {loadingStations && (
                <div style={{ position: 'absolute', top: '10px', right: '10px', zIndex: 1000, background: 'rgba(255,255,255,0.9)', padding: '0.25rem 0.75rem', borderRadius: '0.375rem', fontSize: '0.75rem', color: '#475569' }}>
                    Syncing stations...
                </div>
            )}
            <MapContainer center={[25.3061, 83.0104]} zoom={13} style={{ height: '100%', width: '100%' }}>
                <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
                {stations.map((s) => (
                    <Marker key={s.id || s.station_code} position={[Number(s.latitude), Number(s.longitude)]}>
                        <Popup>
                            <div style={{ fontWeight: 700, fontSize: '0.95rem' }}>{s.station_name}</div>
                            <div style={{ fontSize: '0.8rem', color: '#64748b', marginTop: '0.25rem' }}>Code: {s.station_code}</div>
                            <div style={{ fontSize: '0.8rem', marginTop: '0.25rem' }}>
                                Status: <span style={{ color: s.status === 'active' ? '#10b981' : s.status === 'planned' ? '#d97706' : '#ef4444', fontWeight: 600 }}>
                                    {s.status === 'planned' ? 'PLANNED (DEPLOYMENT PENDING)' : s.status.toUpperCase()}
                                </span>
                            </div>
                            {s.warning_water_level_m && (
                                <div style={{ fontSize: '0.75rem', color: '#475569', marginTop: '0.25rem' }}>
                                    Warning: {s.warning_water_level_m}m | Danger: {s.danger_water_level_m}m <span style={{ fontSize: '0.7rem', color: '#64748b' }}>(CWC Baseline)</span>
                                </div>
                            )}
                        </Popup>
                    </Marker>
                ))}
            </MapContainer>
        </div>
    );
};

export default InteractiveMap;
