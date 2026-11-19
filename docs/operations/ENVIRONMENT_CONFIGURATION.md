# ENVIRONMENT CONFIGURATION & SECRET MANAGEMENT GUIDE
**Project:** River Sentinel 2.0  
**Phase:** Phase 1A  
**Security Level:** Internal Engineering Reference (Zero Real Secrets Stored Here)  

---

## 1. Overview & Principle of Least Privilege

River Sentinel 2.0 strictly enforces a two-tier configuration model:
1. **Client-Side (Public)**: Managed in `frontend/.env.local`. Exclusively exposes variables prefixed with `NEXT_PUBLIC_*`. Only the Supabase publishable anon key is permitted in browser code.
2. **Server-Side (Private)**: Managed in `backend/.env`. Holds privileged service keys (`SUPABASE_SERVICE_ROLE_KEY`), AI tokens (`GROQ_API_KEY`), and simulator ingestion tokens (`SIMULATOR_API_TOKEN`).

Neither `.env` nor `.env.local` is ever committed to Git. Both are strictly ignored by `.gitignore`.

---

## 2. Backend Environment Variables (`backend/.env`)

| Variable Name | Required | Description | Example / Format |
| :--- | :--- | :--- | :--- |
| `PORT` | Optional | Local Flask server listening port (Default: 5000) | `5000` |
| `FLASK_ENV` | Optional | Execution environment (`development` / `production`) | `development` |
| `SUPABASE_URL` | **Required** | Base HTTPS URL of the Supabase project | `https://xqzobddgkawysprpmkpk.supabase.co` |
| `SUPABASE_KEY` | Optional | Publishable anon key (safe for client queries) | `sb_publishable_...` |
| `SUPABASE_SERVICE_ROLE_KEY` | **Required** | Secret service role key with `BYPASSRLS` privileges | `sb_secret_...` |
| `GROQ_API_KEY` | **Required** | API Key for Groq Cloud (Qwen 3.8 27B model access) | `gsk_...` |
| `SIMULATOR_API_TOKEN` | **Required** | Pre-shared token used to authenticate simulator and IoT telemetry | `rs_sim_dev_sec_...` |

---

## 3. Frontend Environment Variables (`frontend/.env.local`)

| Variable Name | Required | Description | Example / Format |
| :--- | :--- | :--- | :--- |
| `NEXT_PUBLIC_BACKEND_URL` | **Required** | Base URL pointing to the running Flask backend | `http://localhost:5000` |
| `NEXT_PUBLIC_SUPABASE_URL` | **Required** | Base HTTPS URL of the Supabase project | `https://xqzobddgkawysprpmkpk.supabase.co` |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | **Required** | Public publishable key for browser-side read operations | `sb_publishable_...` |
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` | Optional | Alias for `NEXT_PUBLIC_SUPABASE_ANON_KEY` | `sb_publishable_...` |

---

## 4. Secret Scan & Credential Audit Findings

1. **Active Repository Files**:
   - Comprehensive regex scanning across all tracked files in `backend/` and `frontend/` confirmed **0 exposed production keys**.
   - Two legacy unimported files containing static Firebase project keys (`frontend/src/firebaseConfig.ts` and `frontend/src/services/firebaseConfig.ts`) were deleted from the working tree.
2. **Git Commit History**:
   - The initial commit `223c7dc` contains historical traces of the deprecated Firebase web config. Because the Firebase database is deactivated by Google, the historical token carries no read/write access.
   - Zero Groq API keys, OpenAI keys, or Supabase service role secret keys exist in Git history.
