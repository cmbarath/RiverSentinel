"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";

const Navbar = () => {
    const [isScrolled, setIsScrolled] = useState(false);
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

    useEffect(() => {
        const handleScroll = () => {
            setIsScrolled(window.scrollY > 20);
        };
        window.addEventListener("scroll", handleScroll);
        return () => window.removeEventListener("scroll", handleScroll);
    }, []);

    return (
        <nav className={`fixed top-0 left-0 w-full z-50 transition-all duration-300 ${isScrolled ? "glass py-3" : "py-5"}`} style={{ paddingLeft: '2rem', paddingRight: '2rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', maxWidth: '1200px', margin: '0 auto' }}>
                <Link href="/" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontWeight: 800, fontSize: '1.5rem', fontFamily: 'var(--font-heading)' }}>
                    <span style={{ fontSize: '2rem' }}>🌊</span>
                    <span className="text-gradient">RiverSentinel 2.0</span>
                </Link>

                {/* Desktop Links */}
                <div style={{ display: 'flex', gap: '2rem', alignItems: 'center' }} className="hidden md:flex">
                    <Link href="#features">Features</Link>
                    <Link href="#how-it-works">How It Works</Link>
                    <Link href="#impact">Impact</Link>
                    <Link href="#contact">Contact</Link>
                    <div style={{ display: 'flex', gap: '1rem', marginLeft: '1rem' }}>
                        <Link href="/login" className="btn btn-secondary" style={{ padding: '0.5rem 1.5rem' }}>Login</Link>
                        <Link href="/signup" className="btn btn-primary" style={{ padding: '0.5rem 1.5rem' }}>Get Started</Link>
                    </div>
                </div>

                {/* Mobile Menu Button can be added here */}
            </div>
        </nav>
    );
};

export default Navbar;
