/**
 * Centralized API & Environment Configuration for River Sentinel 2.0 Frontend.
 *
 * Security & Architectural Guarantees:
 * 1. Centralized Management: All components import the backend URL from this module.
 * 2. Development Support: Falls back to 'http://localhost:5000' only in local development.
 * 3. Production Hardening:
 *    - Deployed production environments (Vercel / cloud) STRICTLY REQUIRE NEXT_PUBLIC_BACKEND_URL.
 *    - Silent fallback to localhost in production is strictly forbidden and throws a clear Error.
 *    - Production backend URL must use secure HTTPS ('https://...').
 * 4. Zero Secrets: Ensures client-side bundles never ingest or expose sensitive tokens.
 */

export function validateEnvironment(): void {
    const isVercel = typeof process !== 'undefined' && (
        process.env.NEXT_PUBLIC_VERCEL_ENV !== undefined ||
        process.env.VERCEL === '1'
    );
    const isExplicitProd = process.env.NEXT_PUBLIC_APP_ENV === 'production';
    const isDeployedProd = isVercel || isExplicitProd;

    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL?.trim();

    if (isDeployedProd) {
        if (!backendUrl) {
            throw new Error(
                '[Config Error] Critical: NEXT_PUBLIC_BACKEND_URL is not defined in production environment! ' +
                'Silent fallback to localhost in production is strictly prohibited. ' +
                'Configure NEXT_PUBLIC_BACKEND_URL in your hosting provider environment variables.'
            );
        }
        if (!backendUrl.startsWith('https://')) {
            throw new Error(
                `[Security Error] Critical: Deployed production backend URL must use HTTPS. Received: "${backendUrl}"`
            );
        }
    }

    // Safety audit: Check that no client-exposed variables contain sensitive keywords
    if (typeof process !== 'undefined' && process.env) {
        for (const [key, value] of Object.entries(process.env)) {
            if (key.startsWith('NEXT_PUBLIC_') && value) {
                const lowerKey = key.toLowerCase();
                if (
                    lowerKey.includes('service_role') ||
                    lowerKey.includes('secret') ||
                    lowerKey.includes('password') ||
                    lowerKey.includes('private_key')
                ) {
                    throw new Error(
                        `[Security Error] Potential credential exposure detected in client variable "${key}". ` +
                        'Secrets must NEVER be prefixed with NEXT_PUBLIC_.'
                    );
                }
            }
        }
    }
}

export function getBackendUrl(): string {
    const configuredUrl = process.env.NEXT_PUBLIC_BACKEND_URL?.trim();

    const isVercel = typeof process !== 'undefined' && (
        process.env.NEXT_PUBLIC_VERCEL_ENV !== undefined ||
        process.env.VERCEL === '1'
    );
    const isExplicitProd = process.env.NEXT_PUBLIC_APP_ENV === 'production';
    const isDeployedProd = isVercel || isExplicitProd;
    const isProdBuild = process.env.NODE_ENV === 'production';

    if (isDeployedProd) {
        if (!configuredUrl) {
            throw new Error(
                '[Config Error] Critical: NEXT_PUBLIC_BACKEND_URL is not defined in production environment! ' +
                'Configure NEXT_PUBLIC_BACKEND_URL in hosting provider environment settings.'
            );
        }
        if (!configuredUrl.startsWith('https://')) {
            throw new Error(
                `[Security Error] Deployed production backend URL must use HTTPS. Received: "${configuredUrl}"`
            );
        }
        return configuredUrl.replace(/\/+$/, '');
    }

    if (configuredUrl) {
        // If a remote domain is configured in production mode, enforce HTTPS
        if (isProdBuild && !configuredUrl.includes('localhost') && !configuredUrl.includes('127.0.0.1')) {
            if (!configuredUrl.startsWith('https://')) {
                throw new Error(
                    `[Security Error] Remote backend URL in production must use HTTPS. Received: "${configuredUrl}"`
                );
            }
        }
        return configuredUrl.replace(/\/+$/, '');
    }

    // Local development fallback
    if (!isProdBuild) {
        return 'http://localhost:5000';
    }

    // Production build without configured URL
    throw new Error(
        '[Config Error] Critical: NEXT_PUBLIC_BACKEND_URL is missing in production environment. ' +
        'Please define NEXT_PUBLIC_BACKEND_URL.'
    );
}

// Run environment validation once on load
try {
    validateEnvironment();
} catch (err) {
    // Re-throw so build or runtime halts immediately
    console.error(err);
    throw err;
}

/**
 * Standard centralized backend API URL for River Sentinel 2.0.
 */
export const BACKEND_URL: string = getBackendUrl();
