"use client";

import React, { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import "leaflet/dist/leaflet.css";

// Dynamic import for Leaflet (SSR-friendly)
const MapContainer = dynamic(() => import("react-leaflet").then(m => m.MapContainer), { ssr: false });
const TileLayer = dynamic(() => import("react-leaflet").then(m => m.TileLayer), { ssr: false });
const Marker = dynamic(() => import("react-leaflet").then(m => m.Marker), { ssr: false });
const Popup = dynamic(() => import("react-leaflet").then(m => m.Popup), { ssr: false });

const stations = [
    { name: "Dashashwamedh Ghat", pos: [25.3061, 83.0104], status: "SAFE" },
    { name: "Assi Ghat", pos: [25.2891, 83.0067], status: "CAUTION" },
    { name: "Manikarnika Ghat", pos: [25.3110, 83.0125], status: "SAFE" },
    { name: "Harishchandra Ghat", pos: [25.2974, 83.0076], status: "SAFE" },
    { name: "Scindia Ghat", pos: [25.3125, 83.0135], status: "UNSAFE" },
];

const InteractiveMap = () => {
    const [isClient, setIsClient] = useState(false);
    useEffect(() => { setIsClient(true); }, []);

    if (!isClient) return <div style={{ height: '600px', background: '#f1f5f9', borderRadius: '1rem', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>Loading Map...</div>;

    return (
        <div className="card" style={{ height: '70vh', padding: 0, overflow: 'hidden' }}>
            <MapContainer center={[25.3, 83.01]} zoom={14} style={{ height: '100%', width: '100%' }}>
                <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
                {stations.map((s, i) => (
                    <Marker key={i} position={s.pos as [number, number]}>
                        <Popup>
                            <div style={{ fontWeight: 700 }}>{s.name}</div>
                            <div style={{ fontSize: '0.85rem' }}>Status: <span style={{ color: s.status === 'SAFE' ? '#10b981' : s.status === 'CAUTION' ? '#f59e0b' : '#ef4444' }}>{s.status}</span></div>
                            <button className="btn btn-primary" style={{ marginTop: '0.5rem', padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}>View Details</button>
                        </Popup>
                    </Marker>
                ))}
            </MapContainer>
        </div>
    );
};

export default InteractiveMap;
