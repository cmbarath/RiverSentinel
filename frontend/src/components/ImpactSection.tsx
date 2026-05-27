"use client";

import React, { useEffect, useState, useRef } from "react";

const stats = [
    { label: "People Protected", value: 2300000, suffix: "M", divisor: 1000000 },
    { label: "Ghats Monitored", value: 85, suffix: "" },
    { label: "Flood Accuracy", value: 95, suffix: "%" },
    { label: "Response Time", value: 30, suffix: " Min" },
];

const Counter = ({ value, suffix, divisor = 1 }: { value: number, suffix: string, divisor?: number }) => {
    const [count, setCount] = useState(0);
    const elementRef = useRef<HTMLDivElement>(null);
    const [isVisible, setIsVisible] = useState(false);

    useEffect(() => {
        const observer = new IntersectionObserver(([entry]) => {
            if (entry.isIntersecting) setIsVisible(true);
        }, { threshold: 0.5 });

        if (elementRef.current) observer.observe(elementRef.current);
        return () => observer.disconnect();
    }, []);

    useEffect(() => {
        if (!isVisible) return;
        let start = 0;
        const end = value / divisor;
        const duration = 2000;
        const increment = end / (duration / 16);

        const timer = setInterval(() => {
            start += increment;
            if (start >= end) {
                setCount(end);
                clearInterval(timer);
            } else {
                setCount(Math.floor(start));
            }
        }, 16);
        return () => clearInterval(timer);
    }, [isVisible, value, divisor]);

    return <div ref={elementRef} style={{ fontSize: '3.5rem', fontWeight: 800, color: 'var(--primary)', marginBottom: '0.5rem' }}>{count}{suffix}</div>;
};

const ImpactSection = () => {
    return (
        <section id="impact" style={{ padding: '6rem 2rem', background: '#f8fafc' }}>
            <div style={{ maxWidth: '1200px', margin: '0 auto', textAlign: 'center' }}>
                <h2 style={{ fontSize: '2.5rem', marginBottom: '4rem' }}>Our <span className="text-gradient">Impact</span></h2>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '3rem' }}>
                    {stats.map((stat, index) => (
                        <div key={index}>
                            <Counter value={stat.value} suffix={stat.suffix} divisor={stat.divisor} />
                            <div style={{ fontSize: '1.2rem', color: '#64748b', fontWeight: 600 }}>{stat.label}</div>
                        </div>
                    ))}
                </div>
            </div>
        </section>
    );
};

export default ImpactSection;
