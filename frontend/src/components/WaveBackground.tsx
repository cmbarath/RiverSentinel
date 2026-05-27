"use client";

import React from "react";

const WaveBackground = () => {
    return (
        <div className="wave-container" style={{ height: '30vh', minHeight: '300px' }}>
            <div className="wave-layer wave-layer-1"></div>
            <div className="wave-layer wave-layer-2"></div>
            <div className="wave-layer wave-layer-3"></div>
        </div>
    );
};

export default WaveBackground;
