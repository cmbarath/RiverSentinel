"use client";

import React, { useState, useEffect } from "react";
import { BACKEND_URL } from "@/lib/apiConfig";

interface WeatherData {
    temperature: number;
    feels_like: number;
    humidity: number;
    pressure: number;
    description: string;
    icon: string;
    wind_speed: number;
    clouds: number;
    visibility: number;
    rain: number;
    city: string;
    timestamp: number;
    fallback?: boolean;
}

interface FloodPrediction {
    prediction: string;  // "FLOOD" or "NO_FLOOD"
    flood_probability: number;
    risk_level: string;  // "LOW", "MODERATE", "HIGH"
    message: string;
    reasons: string[];
    sensor_data: {
        water_level: number;
        discharge: number;
        rain_varanasi: number;
        rain_upstream: number;
        temperature: number;
        humidity: number;
        bod?: number;
        cod?: number;
        do?: number;
    };
    prediction_time: string;
}

const WeatherAndFlood = () => {
    const [weather, setWeather] = useState<WeatherData | null>(null);
    const [floodPrediction, setFloodPrediction] = useState<FloodPrediction | null>(null);
    const [loading, setLoading] = useState(true);
    const [currentTime, setCurrentTime] = useState(new Date());

    // Fetch weather data
    useEffect(() => {
        const fetchWeather = async () => {
            try {
                const response = await fetch(`${BACKEND_URL}/api/weather`);
                const data = await response.json();
                setWeather(data);
                setLoading(false);
            } catch (error) {
                console.error('Error fetching weather:', error);
                setLoading(false);
            }
        };

        fetchWeather();
        // Refresh weather every 10 minutes
        const weatherInterval = setInterval(fetchWeather, 600000);

        return () => clearInterval(weatherInterval);
    }, []);

    // Fetch flood prediction
    useEffect(() => {
        const fetchFloodPrediction = async () => {
            try {
                const response = await fetch(`${BACKEND_URL}/api/flood/predict`);
                const data = await response.json();
                setFloodPrediction(data);
                console.log('Flood prediction:', data);
            } catch (error) {
                console.error('Error fetching flood prediction:', error);
            }
        };

        fetchFloodPrediction();
        // Refresh flood prediction every 5 minutes
        const floodInterval = setInterval(fetchFloodPrediction, 300000);

        return () => clearInterval(floodInterval);
    }, []);

    // Update time every minute
    useEffect(() => {
        const timer = setInterval(() => setCurrentTime(new Date()), 60000);
        return () => clearInterval(timer);
    }, []);

    // Get risk color based on risk level
    const getRiskColor = (riskLevel: string) => {
        switch (riskLevel) {
            case 'HIGH': return '#ef4444';      // Red
            case 'MODERATE': return '#f59e0b';  // Orange
            case 'LOW': return '#10b981';       // Green
            default: return '#6b7280';          // Gray
        }
    };

    const riskColor = floodPrediction ? getRiskColor(floodPrediction.risk_level) : '#10b981';


    // Get weather icon emoji
    const getWeatherIcon = (iconCode: string) => {
        const iconMap: { [key: string]: string } = {
            '01d': '☀️', '01n': '🌙',
            '02d': '⛅', '02n': '☁️',
            '03d': '☁️', '03n': '☁️',
            '04d': '☁️', '04n': '☁️',
            '09d': '🌧️', '09n': '🌧️',
            '10d': '🌦️', '10n': '🌧️',
            '11d': '⛈️', '11n': '⛈️',
            '13d': '❄️', '13n': '❄️',
            '50d': '🌫️', '50n': '🌫️'
        };
        return iconMap[iconCode] || '⛅';
    };

    // Calculate rain probability based on humidity and clouds
    const rainProbability = weather ? Math.min(95, Math.round((weather.humidity * 0.4) + (weather.clouds * 0.4))) : 15;

    if (loading || !weather) {
        return (
            <div style={{ padding: '2rem', textAlign: 'center' }}>
                <div style={{ fontSize: '2rem', marginBottom: '1rem' }}>🌦️</div>
                <div>Loading weather data...</div>
            </div>
        );
    }

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            {weather.fallback && (
                <div style={{ padding: '1rem', background: '#fef3c7', borderRadius: '0.5rem', color: '#92400e' }}>
                    ⚠️ Using fallback weather data. Live data temporarily unavailable.
                </div>
            )}

            <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: '2rem' }}>
                {/* Main Weather Card */}
                <div className="card" style={{ background: 'linear-gradient(135deg, #3b82f6, #06b6d4)', color: 'white', display: 'flex', justifyContent: 'space-between', padding: '2.5rem' }}>
                    <div>
                        <h1 style={{ fontSize: '4rem', margin: 0 }}>{Math.round(weather.temperature)}°C</h1>
                        <h2 style={{ fontSize: '1.5rem', opacity: 0.9, marginBottom: '1rem', textTransform: 'capitalize' }}>{weather.description}</h2>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', fontSize: '0.9rem' }}>
                            <div>Humidity: {weather.humidity}%</div>
                            <div>Wind: {weather.wind_speed} km/h</div>
                            <div>Rainfall: {weather.rain > 0 ? `${weather.rain.toFixed(1)} mm/h` : 'No rain'}</div>
                            <div>Visibility: {weather.visibility} km</div>
                            <div>Pressure: {weather.pressure} hPa</div>
                            <div>Rain Prob: {rainProbability}%</div>
                        </div>
                        <div style={{ marginTop: '1rem', fontSize: '0.8rem', opacity: 0.8 }}>
                            Updated: {currentTime.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}
                        </div>
                    </div>
                    <div style={{ fontSize: '6rem', display: 'flex', alignItems: 'center' }}>{getWeatherIcon(weather.icon)}</div>
                </div>

                {/* Flood Risk Card - ML Predicted */}
                <div className="card" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', borderLeft: `8px solid ${riskColor}` }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                        <div style={{ fontSize: '0.9rem', color: '#64748b', fontWeight: 600 }}>FLOOD RISK STATUS</div>
                        <div style={{ fontSize: '0.7rem', background: '#3b82f6', color: 'white', padding: '0.25rem 0.5rem', borderRadius: '0.25rem', fontWeight: 600 }}>
                            🤖 AI-PREDICTED
                        </div>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.5rem' }}>
                        <span style={{ fontSize: '2.5rem', fontWeight: 800, color: riskColor }}>
                            {floodPrediction?.risk_level || 'LOADING'}
                        </span>
                        <span style={{ fontSize: '1.1rem', color: '#64748b' }}>
                            {floodPrediction?.flood_probability || 0}%
                        </span>
                    </div>

                    {/* Prediction Message */}
                    {floodPrediction?.message && (
                        <div style={{ marginTop: '0.5rem', fontSize: '0.85rem', color: '#64748b', fontStyle: 'italic' }}>
                            {floodPrediction.message}
                        </div>
                    )}

                    {/* Prediction Reasons */}
                    {floodPrediction && floodPrediction.reasons && floodPrediction.reasons.length > 0 && (
                        <div style={{ marginTop: '1rem', fontSize: '0.85rem', color: '#64748b' }}>
                            <div style={{ fontWeight: 600, marginBottom: '0.5rem' }}>Key Factors:</div>
                            <ul style={{ margin: 0, paddingLeft: '1.2rem', lineHeight: '1.6' }}>
                                {floodPrediction.reasons.slice(0, 3).map((reason, idx) => (
                                    <li key={idx}>{reason}</li>
                                ))}
                            </ul>
                        </div>
                    )}

                    {/* Real-Time Sensor Data Comparison */}
                    {floodPrediction?.sensor_data && (
                        <div style={{ marginTop: '1rem', fontSize: '0.75rem', color: '#94a3b8', borderTop: '1px solid #e2e8f0', paddingTop: '0.75rem' }}>
                            <div style={{ fontWeight: 600, marginBottom: '0.5rem', color: '#64748b' }}>📊 Real-Time Sensor Data:</div>
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem' }}>
                                <div>💧 Water: {floodPrediction.sensor_data.water_level.toFixed(2)}m</div>
                                <div>🌊 Discharge: {floodPrediction.sensor_data.discharge.toFixed(0)} cumec</div>
                                <div>🌧️ Rain (Local): {floodPrediction.sensor_data.rain_varanasi.toFixed(1)}mm/h</div>
                                <div>☔ Rain (Upstream): {floodPrediction.sensor_data.rain_upstream.toFixed(1)}mm/h</div>
                                <div>🌡️ Temp: {floodPrediction.sensor_data.temperature.toFixed(1)}°C</div>
                                <div>💨 Humidity: {floodPrediction.sensor_data.humidity.toFixed(0)}%</div>
                                {floodPrediction.sensor_data.bod !== undefined && <div>🧪 BOD: {floodPrediction.sensor_data.bod.toFixed(1)} mg/L</div>}
                                {floodPrediction.sensor_data.cod !== undefined && <div>🧪 COD: {floodPrediction.sensor_data.cod.toFixed(1)} mg/L</div>}
                                {floodPrediction.sensor_data.do !== undefined && <div>🫧 DO: {floodPrediction.sensor_data.do.toFixed(1)} mg/L</div>}
                            </div>
                        </div>
                    )}

                    {/* Prediction Time */}
                    {floodPrediction?.prediction_time && (
                        <div style={{ marginTop: '0.75rem', fontSize: '0.7rem', color: '#94a3b8', textAlign: 'right' }}>
                            Updated: {new Date(floodPrediction.prediction_time).toLocaleTimeString('en-IN')}
                        </div>
                    )}

                    <div style={{ fontSize: '0.7rem', color: '#94a3b8', borderTop: '1px solid #f1f5f9', paddingTop: '0.5rem', marginTop: '0.5rem' }}>
                        * Note: Flood probability is an automated early-warning estimate from the 6-feature Random Forest model; consult official CWC bulletins for statutory warnings.
                    </div>
                </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.5rem' }}>
                {/* Rain Forecast */}
                <div className="card">
                    <h3 style={{ fontSize: '1.2rem' }}>24h Rain Forecast</h3>
                    <div style={{ margin: '1.5rem 0' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem', fontSize: '0.9rem' }}>
                            <span>Probability</span>
                            <span style={{ fontWeight: 700 }}>{rainProbability}%</span>
                        </div>
                        <div style={{ height: '8px', background: '#e2e8f0', borderRadius: '4px', overflow: 'hidden' }}>
                            <div style={{ width: `${rainProbability}%`, height: '100%', background: 'var(--primary)' }}></div>
                        </div>
                    </div>
                    <div style={{ fontSize: '0.9rem', color: '#64748b' }}>
                        Current: {weather.rain > 0 ? `${weather.rain}mm/h` : 'No rain'}
                    </div>
                </div>

                {/* Monsoon Status */}
                <div className="card">
                    <h3 style={{ fontSize: '1.2rem' }}>Monsoon Status</h3>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem', marginTop: '1rem' }}>
                        <span style={{ fontSize: '3rem' }}>
                            {new Date().getMonth() >= 6 && new Date().getMonth() <= 9 ? '🌧️' : '☀️'}
                        </span>
                        <div>
                            <div style={{ fontWeight: 700, color: 'var(--primary)' }}>
                                {new Date().getMonth() >= 6 && new Date().getMonth() <= 9 ? 'Active Monsoon' : 'Post-Monsoon'}
                            </div>
                            <div style={{ fontSize: '0.85rem', color: '#64748b' }}>
                                {weather.rain > 5 ? 'Heavy rainfall detected' : weather.rain > 0 ? 'Light rainfall' : 'Clear skies'}
                            </div>
                        </div>
                    </div>
                </div>

                {/* Nearby Shelters */}
                <div className="card">
                    <h3 style={{ fontSize: '1.2rem' }}>Nearest Shelter</h3>
                    <div style={{ marginTop: '1rem' }}>
                        <div style={{ fontWeight: 700 }}>Godowlia City Centre</div>
                        <div style={{ fontSize: '0.85rem', color: '#64748b' }}>1.2 km away • Capacity: 500</div>
                        <button className="btn btn-secondary" style={{ marginTop: '1rem', width: '100%', fontSize: '0.85rem', padding: '0.5rem' }}>📍 Directions</button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default WeatherAndFlood;
