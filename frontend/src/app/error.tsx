"use client";

import React, { useEffect } from "react";
import Link from "next/link";

export default function GlobalError({
    error,
    reset,
}: {
    error: Error & { digest?: string };
    reset: () => void;
}) {
    useEffect(() => {
        // Log client exception for diagnostics
        console.error("[River Sentinel ErrorBoundary]", error);
    }, [error]);

    return (
        <div style={{
            minHeight: "100vh",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            padding: "2rem",
            background: "#f8fafc",
            fontFamily: "system-ui, -apple-system, sans-serif",
            textAlign: "center"
        }}>
            <div style={{
                background: "#ffffff",
                padding: "2.5rem",
                borderRadius: "1rem",
                boxShadow: "0 10px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.01)",
                maxWidth: "500px",
                width: "100%",
                border: "1px solid #e2e8f0"
            }}>
                <div style={{ fontSize: "3rem", marginBottom: "1rem" }}>🌊</div>
                <h2 style={{ fontSize: "1.5rem", fontWeight: 700, color: "#1e293b", marginBottom: "0.5rem" }}>
                    Service Temporarily Degraded
                </h2>
                <p style={{ color: "#64748b", fontSize: "0.95rem", lineHeight: 1.5, marginBottom: "1.5rem" }}>
                    We encountered an unexpected error while communicating with the river monitoring systems. No data was lost.
                </p>

                {error?.digest && (
                    <div style={{
                        background: "#f1f5f9",
                        padding: "0.5rem 1rem",
                        borderRadius: "0.5rem",
                        fontSize: "0.8rem",
                        color: "#475569",
                        marginBottom: "1.5rem",
                        fontFamily: "monospace"
                    }}>
                        Reference Digest: {error.digest}
                    </div>
                )}

                <div style={{ display: "flex", gap: "1rem", justifyContent: "center" }}>
                    <button
                        onClick={() => reset()}
                        style={{
                            background: "#0284c7",
                            color: "#ffffff",
                            padding: "0.75rem 1.5rem",
                            borderRadius: "0.5rem",
                            fontWeight: 600,
                            border: "none",
                            cursor: "pointer",
                            transition: "background 0.2s ease"
                        }}
                    >
                        Try Again
                    </button>
                    <Link
                        href="/"
                        style={{
                            background: "#f1f5f9",
                            color: "#334155",
                            padding: "0.75rem 1.5rem",
                            borderRadius: "0.5rem",
                            fontWeight: 600,
                            textDecoration: "none",
                            display: "inline-block",
                            border: "1px solid #cbd5e1"
                        }}
                    >
                        Return Home
                    </Link>
                </div>
            </div>
        </div>
    );
}
