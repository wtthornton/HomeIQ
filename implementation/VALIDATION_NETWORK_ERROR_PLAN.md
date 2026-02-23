# Plan: Validation Unavailable (Network Error) in Automation Preview

**Date:** 2026-02-09  
**Issue:** Automation Preview shows "Validation Unavailable (Network Error)" when validating YAML. UI tries to reach `http://localhost:7242/api/v1/validation/validate` but cannot connect.

**Summary:** The UI was using the wrong default port for the HA AI Agent Service (**7242** instead of **8030**). The default in `domains/frontends/ai-automation-ui/src/services/api-v2.ts` has been changed to `http://localhost:8030`. Rebuild/refresh the UI and ensure `ha-ai-agent-service` is running on 8030; validation should then work.

---

## What is api-v2?

**api-v2** (`domains/frontends/ai-automation-ui/src/services/api-v2.ts`) is the **TypeScript client for the “v2” conversation and automation APIs** used by the HA Agent chat flow. It does two different things:

| Responsibility | Base URL | Used for |
|-----------------|----------|----------|
| **V2 conversation API** | `VITE_API_URL` or `/api` (proxied to ai-automation-service) | Start conversation, send message, stream turn, get conversation, get suggestions. Same backend as the main app `/api`. |
| **YAML validation** | `VITE_HA_AGENT_SERVICE_URL` or `http://localhost:8030` | Single method: `validateYAML()` → `POST …/api/v1/validation/validate` on the **HA AI Agent Service** (port 8030). |

So **api-v2** is mostly the v2 conversation API client, plus one direct call to the HA AI Agent Service for validation. The rest of the HA Agent (chat, tool execution, conversation list, etc.) is in **haAiAgentApi.ts**, which correctly uses `API_CONFIG.HA_AI_AGENT` (8030). Only `validateYAML` in api-v2 was using a separate, wrong default (7242); that default is now 8030.

---

## Root cause

| Item | Finding |
|------|--------|
| **UI call** | `api-v2.ts` builds the validation URL from `haAgentUrl` with default **`http://localhost:7242`**. |
| **Actual service** | HA AI Agent Service runs on **port 8030** (docker-compose, health at `http://localhost:8030/health`). |
| **Result** | Wrong default port (7242) causes connection failure when `VITE_HA_AGENT_SERVICE_URL` is not set. |

Evidence:

- `domains/frontends/ai-automation-ui/src/services/api-v2.ts` line 482:  
  `const haAgentUrl = import.meta.env.VITE_HA_AGENT_SERVICE_URL || 'http://localhost:7242';`
- `domains/frontends/ai-automation-ui/src/config/api.ts` line 24:  
  `HA_AI_AGENT: isProduction ? '/api/ha-ai-agent' : 'http://localhost:8030/api'` (correct port).
- `docker-compose.yml`: `ha-ai-agent-service` exposes `8030:8030`.
- `ha-ai-agent-service` implements `POST /api/v1/validation/validate` in `src/main.py`.

Port **7242** appears to be an old or telemetry port (e.g. debug ingest in `AutomationPreview.tsx`); it is not the HA AI Agent API.

---

## Plan

### 1. Fix default HA Agent URL in api-v2.ts (done)

- **Action:** Use port **8030** as the default when `VITE_HA_AGENT_SERVICE_URL` is unset, and align with `api.ts` so the same base is used everywhere.
- **Change:** In `api-v2.ts`, set default to `http://localhost:8030` (or derive from `API_CONFIG.HA_AI_AGENT` by stripping `/api` so a single source of truth is used).
- **Outcome:** Browser requests from the UI (e.g. on port 3001) will hit `http://localhost:8030/api/v1/validation/validate` and reach the running service.

### 2. Optional: Single source of truth for HA Agent base URL

- **Action:** Have `api-v2.ts` use `API_CONFIG.HA_AI_AGENT` from `config/api.ts` (stripping trailing `/api` for the base) so dev/prod and port are configured in one place.
- **Benefit:** Avoids future port/env drift between api.ts and api-v2.ts.

### 3. Verify service and CORS

- **Check service:** Ensure `ha-ai-agent-service` is up and healthy:  
  `Invoke-RestMethod -Uri "http://localhost:8030/health"` (PowerShell).
- **Check CORS:** If the UI is on a different origin (e.g. `localhost:3001`), ensure the HA AI Agent Service allows that origin. If 8030 is correct and CORS is configured, the “check browser console for CORS errors” note in the UI message should not apply once the URL is fixed.

### 4. Re-test in UI

- **Action:** After deploying the fix, open Automation Preview and trigger validation again.
- **Expected:** Validation runs and the modal shows success or validation errors/warnings instead of “Validation Unavailable (Network Error)”.

### 5. Documentation / env template

- **Action:** If the project has a `.env.example` or frontend env docs, add `VITE_HA_AGENT_SERVICE_URL=http://localhost:8030` (or the appropriate production proxy URL) so future setups don’t rely on the default.
- **Optional:** In REVIEW_AND_FIXES.md (or similar), remove or update any mention of “hardcoded fallback URL: 'http://localhost:7242'” now that the default is 8030.

---

## Status

- [x] Root cause identified (wrong default port 7242 vs 8030).
- [x] Code fix: default in `api-v2.ts` updated to 8030 (see below).
- [x] Refactor: `validateYAML` moved to haAiAgentApi; api-v2 delegates to it (single source: `API_CONFIG.HA_AI_AGENT`).
- [x] Document: API clients table added to `domains/frontends/ai-automation-ui/README.md`.
- [x] Re-test: AutomationPreview tests run without 7242; validation URL is 8030. (Full build still blocked by pre-existing TS errors in ConversationalDashboard.tsx / Deployed.tsx.)

---

## Recommendations

1. **Use a single source of truth for the HA Agent base URL**  
   In `api-v2.ts`, derive the validation base URL from `API_CONFIG.HA_AI_AGENT` (strip `/api` for the base) instead of a separate `VITE_HA_AGENT_SERVICE_URL` default. That way dev/prod and port stay in sync with `config/api.ts` and `haAiAgentApi.ts`.

2. **Consider moving `validateYAML` to haAiAgentApi**  
   Validation is the only HA AI Agent call in api-v2. Moving it to `haAiAgentApi.ts` would put all HA AI Agent calls in one client and remove the need for a second HA Agent URL in api-v2.

3. **Document frontend API clients**  
   Add a short note (e.g. in `domains/frontends/ai-automation-ui/README.md` or a dedicated API.md) that explains:
   - **api.ts** – main AI Automation backend (patterns, synergies, etc.).
   - **api-v2.ts** – v2 conversation API + (currently) validateYAML to HA AI Agent.
   - **haAiAgentApi.ts** – HA AI Agent Service (chat, conversations, tools).
   So “what is api-v2?” is answered in the repo.

4. **Env template**  
   If you use `.env.example` or similar, add:
   - `VITE_HA_AGENT_SERVICE_URL=http://localhost:8030` (optional; 8030 is now the default in code).
   - Keep documenting `VITE_API_URL` and `VITE_API_KEY` for the main and v2 APIs.

5. **Re-test after change**  
   After any refactor, run the HA Agent flow and Automation Preview validation to confirm both conversation and validation still work.

6. **Debug ingest (executed)**  
   AutomationPreview had hardcoded `http://127.0.0.1:7242` for debug telemetry ingest. That caused ECONNREFUSED noise in tests. Telemetry is now guarded: it only runs when `VITE_DEBUG_INGEST_URL` is set (e.g. `http://127.0.0.1:7242`). Default is no ingest, so tests and normal runs don’t connect to 7242.
