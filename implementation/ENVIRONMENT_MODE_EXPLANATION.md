# Environment Mode Explanation

**Date:** January 16, 2026  
**Topic:** Understanding `import.meta.env.MODE` and Why It's Needed

---

## What is Environment Mode?

**Environment Mode** is a Vite concept that determines how your application is running. It's accessed via `import.meta.env.MODE` and can have these values:

- **`'development'`** - When running `vite dev` or `npm run dev`
- **`'production'`** - When running `vite build` followed by serving the built files
- **Custom modes** - Can be defined (e.g., `'staging'`, `'test'`)

---

## How It's Used in This Project

### Current Implementation

**File:** `services/ai-automation-ui/src/config/api.ts`

```typescript
// Determine if we're running in production (Docker) or development
const isProduction = import.meta.env.MODE === 'production';

// API Base URLs
export const API_CONFIG = {
  // Data API
  DATA: isProduction ? '/api/data' : 'http://localhost:8006/api',
  
  // Other services follow same pattern...
};
```

### The Two Scenarios

#### 1. Development Mode (`MODE === 'development'`)

**When:** Running `npm run dev` locally

**API URLs:**
- `DATA: 'http://localhost:8006/api'`
- Direct connection to services running on localhost

**Why:**
- Services run as separate processes on different ports
- No reverse proxy needed
- Direct HTTP calls work fine
- CORS may need to be configured

**Example Request:**
```
GET http://localhost:8006/api/devices?limit=100
```

#### 2. Production Mode (`MODE === 'production'`)

**When:** Running in Docker container (built app)

**API URLs:**
- `DATA: '/api/data'`
- Relative paths that go through reverse proxy

**Why:**
- All services run in Docker containers
- Frontend is served by nginx (port 80)
- Backend services are behind reverse proxy
- Reverse proxy routes `/api/data/*` → `data-api:8006/api/*`
- No CORS issues (same origin)

**Example Request:**
```
GET /api/data/devices?limit=100
→ Proxied to → http://data-api:8006/api/devices?limit=100
```

---

## Why Environment Mode is Needed

### Problem Without Mode Detection

Without environment mode detection, you'd have to:

1. **Hardcode URLs** - Would break in different environments
2. **Use environment variables** - More complex, requires setup
3. **Manual configuration** - Error-prone, easy to forget

### Solution: Automatic Detection

Environment mode automatically detects:
- **Development:** Direct localhost URLs
- **Production:** Relative paths for proxy

**Benefits:**
- ✅ No configuration needed
- ✅ Works automatically in both environments
- ✅ No code changes when deploying
- ✅ Vite handles it automatically

---

## Current Issue

### The Problem

**Error Observed:**
```
Failed to load resource: 404 (Not Found)
@ http://localhost:3001/api/data/devices?limit=100
```

**What's Happening:**
1. App is running in **development mode** (`npm run dev`)
2. But it's trying to use **production paths** (`/api/data`)
3. No Vite proxy is configured to handle `/api/data`
4. Request goes to `http://localhost:3001/api/data/devices` (doesn't exist)
5. Should go to `http://localhost:8006/api/devices` instead

### Root Cause

**Possible Causes:**

1. **Mode Detection Issue:**
   - `import.meta.env.MODE` might be incorrectly set to `'production'`
   - Check: `console.log(import.meta.env.MODE)` in browser console

2. **Missing Proxy Configuration:**
   - `vite.config.ts` has no proxy setup
   - Even if mode is correct, production paths won't work in dev without proxy

3. **Build vs Dev Confusion:**
   - App might be running built files instead of dev server
   - Check: Are you running `npm run dev` or `npm run preview`?

---

## How to Check Current Mode

### Method 1: Browser Console

1. Open browser DevTools (F12)
2. Go to Console tab
3. Type: `import.meta.env.MODE`
4. Should show: `"development"` or `"production"`

### Method 2: Add Debug Log

**File:** `services/ai-automation-ui/src/config/api.ts`

```typescript
// Add this temporarily
console.log('Environment Mode:', import.meta.env.MODE);
console.log('Is Production:', import.meta.env.MODE === 'production');
console.log('API_CONFIG.DATA:', API_CONFIG.DATA);

const isProduction = import.meta.env.MODE === 'production';
```

### Method 3: Check How App is Running

**Development:**
```powershell
cd services/ai-automation-ui
npm run dev
# Should show: "VITE v6.x.x  ready in xxx ms"
# Mode: 'development'
```

**Production (Built):**
```powershell
cd services/ai-automation-ui
npm run build
npm run preview
# Mode: 'production'
```

**Docker:**
```powershell
docker-compose up ai-automation-ui
# Mode: 'production' (built app served by nginx)
```

---

## Solutions

### Solution 1: Add Vite Proxy (Recommended)

**Why:** Allows using same paths in both dev and production

**File:** `services/ai-automation-ui/vite.config.ts`

```typescript
export default defineConfig({
  // ... existing config ...
  server: {
    host: '0.0.0.0',
    port: 3001,
    strictPort: true,
    proxy: {
      '/api/data': {
        target: 'http://localhost:8006',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api\/data/, '/api'),
        secure: false,
      },
    },
  },
})
```

**Then update API config to always use proxy path:**

```typescript
// Always use proxy path (works in both dev and prod)
export const API_CONFIG = {
  DATA: '/api/data',  // Always use proxy path
  // ... other services
};
```

**Benefits:**
- ✅ Same code works in dev and production
- ✅ No mode detection needed
- ✅ Consistent API paths
- ✅ Easier to maintain

### Solution 2: Fix Mode Detection

**If mode is incorrectly set:**

1. **Check Vite command:**
   - Use `vite dev` not `vite build && vite preview`
   - Use `npm run dev` not `npm run preview`

2. **Check environment variables:**
   ```powershell
   # Should not set NODE_ENV=production in dev
   $env:NODE_ENV = "development"  # PowerShell
   ```

3. **Check package.json scripts:**
   ```json
   {
     "scripts": {
       "dev": "vite --host 0.0.0.0 --port 3001",  // ✅ Correct
       "preview": "vite preview"  // ⚠️ This uses production mode
     }
   }
   ```

### Solution 3: Use Environment Variables (Alternative)

**If you want explicit control:**

```typescript
// Use explicit environment variable
const API_BASE_URL = import.meta.env.VITE_DATA_API_URL || 
  (import.meta.env.MODE === 'production' ? '/api/data' : 'http://localhost:8006/api');

export const API_CONFIG = {
  DATA: API_BASE_URL,
};
```

**Set in `.env`:**
```
VITE_DATA_API_URL=http://localhost:8006/api
```

---

## Recommended Approach

### For This Project: Use Vite Proxy

**Why:**
1. **Consistency** - Same paths in dev and production
2. **Simplicity** - No mode detection needed
3. **Docker-Ready** - Matches production setup
4. **CORS-Free** - Proxy handles CORS automatically

**Implementation:**

1. **Add proxy to `vite.config.ts`** (see Solution 1 above)
2. **Update `api.ts` to always use proxy paths:**
   ```typescript
   export const API_CONFIG = {
     DATA: '/api/data',  // Always use proxy
     // ... other services use proxy paths too
   };
   ```
3. **Remove mode detection** (no longer needed):
   ```typescript
   // Remove this:
   const isProduction = import.meta.env.MODE === 'production';
   
   // Use this instead:
   export const API_CONFIG = {
     DATA: '/api/data',
   };
   ```

---

## Summary

### What is Environment Mode?
- Vite's way of detecting dev vs production
- Accessed via `import.meta.env.MODE`
- Automatically set based on how app runs

### Why is it Needed?
- Different API URLs for dev (localhost) vs production (proxy)
- Automatic detection avoids manual configuration
- Ensures correct endpoints in each environment

### Current Issue
- App might be using production paths in development
- No proxy configured to handle those paths
- Results in 404 errors

### Best Solution
- Add Vite proxy configuration
- Use same paths in both environments
- Simpler and more maintainable

---

## Quick Reference

| Environment | Mode | API URL | How to Run |
|------------|------|---------|------------|
| **Development** | `'development'` | `http://localhost:8006/api` | `npm run dev` |
| **Production (Built)** | `'production'` | `/api/data` | `npm run build && npm run preview` |
| **Docker** | `'production'` | `/api/data` | `docker-compose up` |

**Current Problem:** Development mode trying to use production paths without proxy.

**Fix:** Add Vite proxy or ensure mode detection works correctly.
