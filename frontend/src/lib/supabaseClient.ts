import { createClient } from '@supabase/supabase-js';

const isVercel = typeof process !== 'undefined' && (
  process.env.NEXT_PUBLIC_VERCEL_ENV !== undefined ||
  process.env.VERCEL === '1'
);
const isExplicitProd = process.env.NEXT_PUBLIC_APP_ENV === 'production';
const isDeployedProd = isVercel || isExplicitProd;

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL?.trim() || 'https://xqzobddgkawysprpmkpk.supabase.co';
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY?.trim() || '';

if (isDeployedProd) {
  if (!process.env.NEXT_PUBLIC_SUPABASE_URL) {
    throw new Error(
      '[Config Error] Critical: NEXT_PUBLIC_SUPABASE_URL is not configured for production environment.'
    );
  }
  if (!supabaseUrl.startsWith('https://')) {
    throw new Error(
      `[Security Error] Deployed production Supabase URL must use HTTPS. Received: "${supabaseUrl}"`
    );
  }
  if (!supabaseAnonKey) {
    throw new Error(
      '[Config Error] Critical: NEXT_PUBLIC_SUPABASE_ANON_KEY is missing in production.'
    );
  }
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    persistSession: true,
    autoRefreshToken: true,
    detectSessionInUrl: true,
  },
});
