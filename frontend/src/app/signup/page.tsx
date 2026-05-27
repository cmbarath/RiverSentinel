"use client";

import SignUpWizard from "@/components/auth/SignUpWizard";
import Navbar from "@/components/Navbar";
import WaveBackground from "@/components/WaveBackground";

export default function SignUpPage() {
    return (
        <main style={{ minHeight: '100vh', background: 'linear-gradient(to bottom, #f0f9ff, #e0f2fe)', position: 'relative', display: 'flex', flexDirection: 'column' }}>
            <Navbar />
            <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', paddingTop: '80px', paddingBottom: '100px', zIndex: 20 }}>
                <SignUpWizard />
            </div>
            <WaveBackground />
        </main>
    );
}
