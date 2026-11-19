import React from "react";
import Link from "next/link";

export default function NotFound() {
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
                boxShadow: "0 10px 25px -5px rgba(0, 0, 0, 0.05)",
                maxWidth: "480px",
                width: "100%",
                border: "1px solid #e2e8f0"
            }}>
                <div style={{ fontSize: "3rem", marginBottom: "1rem" }}>🔍</div>
                <h2 style={{ fontSize: "1.5rem", fontWeight: 700, color: "#1e293b", marginBottom: "0.5rem" }}>
                    Page Not Found
                </h2>
                <p style={{ color: "#64748b", fontSize: "0.95rem", lineHeight: 1.5, marginBottom: "1.5rem" }}>
                    The monitoring dashboard or page you requested could not be found.
                </p>
                <Link
                    href="/"
                    style={{
                        background: "#0284c7",
                        color: "#ffffff",
                        padding: "0.75rem 1.5rem",
                        borderRadius: "0.5rem",
                        fontWeight: 600,
                        textDecoration: "none",
                        display: "inline-block"
                    }}
                >
                    Back to River Sentinel Home
                </Link>
            </div>
        </div>
    );
}
