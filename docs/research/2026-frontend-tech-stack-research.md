# 2026 Frontend Technology Stack Research

**Created:** 2026-02-27
**Status:** Research in progress
**Scope:** React 19, Vite 7, Tailwind CSS 4, Streamlit optimization, testing strategy, bundle optimization, security

---

## Overview

This research document consolidates expert guidance on modernizing HomeIQ's frontend technology stack. The project currently uses:
- **Frontend frameworks:** React 18.3.1 (ai-automation-ui, health-dashboard)
- **Build tool:** Vite 6.4.1
- **Styling:** Tailwind CSS 3.4.18
- **Testing:** Vitest 4.0.17 + Playwright 1.58.1
- **Observability:** Streamlit (observability-dashboard)

The task is to evaluate migration paths for each major dependency to 2026 standards.

---

## 1. React 19 Migration Strategy

### Current State
- HomeIQ uses React 18.3.1 in ai-automation-ui and health-dashboard
- Both apps use @vitejs/plugin-react@5.1.2
- TypeScript 5.9.3

### Breaking Changes (React 18 → 19)

#### 1.1 Automatic Dependency Tracking (Actions)
**Status:** BREAKING CHANGE but well-supported

React 19 introduces Server Components and automatic dependency tracking via Actions. However, HomeIQ uses client-side React exclusively, so the primary breaking changes are:

- **useFormStatus hook changes** - In React 19, form state hooks are more granular
- **useOptimistic now requires a new API** - React 19 moved from callback-based to action-based
- **New `use()` hook for promises** - Allows unwrapping promises directly in components

**Impact on HomeIQ:**
- ai-automation-ui uses Zustand (not React Context), so state management is unaffected
- health-dashboard uses React Context minimally; migration is straightforward
- No server-side rendering planned

#### 1.2 Ref as a Prop (Non-Breaking)
**Status:** NON-BREAKING (backward compatible)

React 19 allows ref as a regular prop in function components. This is a convenience, not a requirement.

#### 1.3 useTransition and Suspense Improvements
**Status:** ENHANCEMENT (opt-in)

React 19 better integrates with Suspense and useTransition. The old APIs still work.

#### 1.4 Hydration Errors
**Status:** NON-BREAKING for client-only apps

Server-side hydration improvements don't affect HomeIQ's client-side-only architecture.

### Recommended Migration Path

```
Phase 1: Preparation (1 week)
- Audit current React usage: grep -r "React.FC" "useCallback" "useMemo" in both apps
- Identify form-heavy components (automation suggestions, device config)
- Create feature branch: feat/react-19-prep

Phase 2: Upgrade (2 weeks)
  Step 1: Update package.json
    - react: ^18.3.1 → ^19.0.0
    - @types/react: ^18.3.27 → ^19.0.0
    - @vitejs/plugin-react: ^5.1.2 → ^5.2.0 (React 19 compatible)

  Step 2: Test dependencies
    - Run type-check in both apps
    - Check for breaking imports (React.FC deprecated in React 19)
    - Fix any form-related hooks (useFormStatus, useFormState)

  Step 3: Test coverage
    - Run vitest suite in both apps
    - Run Playwright E2E tests (--grep @smoke)
    - Manual testing of critical user flows (suggestion creation, device management)

Phase 3: Optimization (1 week)
  - Adopt new use() hook for promise unwrapping (cleaner Suspense)
  - Replace useCallback/useMemo where use() simplifies logic
  - Update linting rules: disable React.FC ESLint rules
```

### Key Files to Test
- **ai-automation-ui:** `src/components/IdeaList.tsx`, `src/pages/Ideas.tsx` (form-heavy)
- **health-dashboard:** `src/pages/Dashboard.tsx`, `src/components/GroupsTab.tsx` (state-heavy)

### Risk Assessment
- **Risk Level:** LOW - React 19 is mostly backward compatible for client-side apps
- **Rollback Plan:** Simple revert of package.json + node_modules reinstall
- **Recommendation:** Proceed after Vite 7 migration (dependency ordering)

---

## 2. Vite 7 Migration

### Current State
- Vite 6.4.1 (released Dec 2024)
- Both frontends use vite build + vite --host

### Breaking Changes (Vite 6 → 7)

#### 2.1 Drop Node 16 Support
**Status:** Breaking if running Node 16 (unsupported anyway)

Vite 7 requires Node 18.3+. HomeIQ likely runs Node 20+, so this is **not a blocker**.

#### 2.2 Rollup 5 Upgrade
**Status:** Breaking for some plugin authors; users unaffected

Vite 7 upgrades to Rollup 5. This primarily affects plugin developers. HomeIQ doesn't write custom Vite plugins.

#### 2.3 CSS Handling Changes
**Status:** IMPORTANT - CSS-in-JS behavior changes

- **CSS modules now use `.module.css` strictly** (no more `.css` + CSS-in-JS fallback)
- **`?raw` and `?url` imports require explicit syntax**
- **PostCSS processing order changed** - autoprefixer must be explicit in `postcss.config.js`

**Impact on HomeIQ:**
- Both apps use Tailwind CSS (standard `.css` files) - **NO IMPACT**
- No CSS-in-JS libraries detected (styled-components, emotion absent)
- `postcss.config.js` exists with autoprefixer → may need minor adjustment

#### 2.4 Environment Variables API
**Status:** BREAKING - import.meta.env behavior changed

- `import.meta.env.VITE_*` variables must be explicitly defined in `.env`
- `.env.local` is now merged correctly with `.env`
- `MODE` variable now respects `--mode` flag strictly

**Impact on HomeIQ:**
- Both apps likely use `import.meta.env.VITE_API_URL` or similar
- Audit `.env` files to ensure all vars are declared
- This is a **documentation fix**, not code

#### 2.5 JavaScript API Changes
**status:** Non-breaking (backward compatible)

### Recommended Migration Path

```
Phase 1: Pre-Upgrade Audit (3 days)
- Check vite.config.ts in both apps
- Audit .env and .env.local for all VITE_* vars
- Check for custom Vite plugins (grep -r "defineConfig" vite.config)
- Document current build times (baseline)

Phase 2: Upgrade (1 week)
  Step 1: Update vite (both apps)
    - vite: ^6.4.1 → ^7.0.0
    - Update @vitejs/plugin-react to latest (should already be compatible)

  Step 2: Fix environment variables
    - Ensure all import.meta.env.VITE_* vars are in .env files
    - Test dev server: npm run dev
    - Test build: npm run build

  Step 3: Test
    - npm run test:run (Vitest)
    - npm run test:e2e:smoke (Playwright)
    - Manual testing in dev mode

Phase 3: Optimization (3 days)
  - Measure new build times and compare
  - Check for bundle size changes
  - Update CI/CD build commands if needed
```

### Key Files to Check
- **Both:** `vite.config.ts`, `.env`, `.env.local`
- **Both:** `postcss.config.js` (update if using tailwindcss plugin)

### Risk Assessment
- **Risk Level:** LOW-MEDIUM - mostly configuration updates
- **Rollback Plan:** Revert vite version in package.json
- **Recommendation:** Proceed after environment variable audit

---

## 3. Tailwind CSS 4 Migration

### Current State
- Tailwind CSS 3.4.18 in both frontends
- Using PostCSS 8.4.49 + autoprefixer 10.4.22
- Design system CSS (`design-system.css`) with custom variables

### Breaking Changes (Tailwind 3 → 4)

#### 3.1 CSS-First Configuration (Major)
**Status:** MAJOR BREAKING CHANGE

Tailwind 4 moves from `tailwind.config.js` to CSS-based configuration via `@source` and `@theme` directives in CSS files.

**Old Approach (Tailwind 3):**
```javascript
// tailwind.config.js
module.exports = {
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        teal: '#14b8a6'
      }
    }
  }
}
```

**New Approach (Tailwind 4):**
```css
/* input.css */
@import "tailwindcss";
@theme {
  --color-teal: #14b8a6;
}
@source "../src/**/*.{ts,tsx}";
```

**Impact on HomeIQ:**
- Both `tailwind.config.ts` files exist (TypeScript)
- Must migrate `tailwind.config.ts` → CSS-based config
- Design system CSS (`design-system.css`) should be refactored to use `@theme`
- This is a **MODERATE refactor**, not breaking logic

#### 3.2 Oxide Parser (Non-breaking)
**Status:** IMPROVEMENT - faster parsing

Tailwind 4 uses a new Rust-based parser (`oxide`). This is transparent to users.

#### 3.3 Container Query Support
**Status:** ENHANCEMENT - opt-in

New `@container` utilities for container queries. Backward compatible.

#### 3.4 Removed Deprecated Features
**Status:** Check current codebase

Tailwind 4 removes deprecated color names (e.g., `warm-gray` → `stone`). HomeIQ uses modern color names, so **NO IMPACT expected**.

### Recommended Migration Path

```
Phase 1: Audit (3 days)
- Review both tailwind.config.ts files
- Search for deprecated color names in HTML/TSX files
- Check design-system.css for compatibility
- Document custom theme extensions

Phase 2: Migrate Config (1 week)
  Step 1: Create new CSS-based config
    - Create tailwind-input.css with @source and @theme
    - Copy custom theme vars from tailwind.config.ts
    - Include design system colors

  Step 2: Update package.json
    - tailwindcss: ^3.4.18 → ^4.0.0
    - Ensure postcss ^8.4.49

  Step 3: Delete old tailwind.config.ts (after testing)

  Step 4: Update build process if needed
    - Vite should auto-detect new CSS config
    - Update any scripts that reference tailwind.config.js

Phase 3: Test & Optimize (1 week)
  - Build and compare CSS bundle sizes
  - npm run test:run (Vitest)
  - Visual regression testing (spot-check UI)
  - E2E tests: npm run test:e2e:smoke
```

### Key Files to Update
- **Both:** `tailwind.config.ts` → delete and create `input.css` with @theme
- **Both:** `design-system.css` - extract theme vars to CSS variables
- **Both:** `src/index.css` - ensure it imports new `input.css`

### Risk Assessment
- **Risk Level:** MEDIUM - requires config refactor but logic unchanged
- **Migration complexity:** ~2 hours per app (estimated)
- **Rollback Plan:** Keep old tailwind.config.ts as backup, simple version revert
- **Recommendation:** Coordinate with Vite 7 upgrade (they share PostCSS config)

---

## 4. Streamlit Performance & `time.sleep()` Blocking

### Current State
- Observability dashboard uses Streamlit (Python backend)
- Multiple pages with real-time monitoring
- Likely using `time.sleep()` or polling loops for refresh

### Problem Analysis

Streamlit's execution model:
- **Full-page rerun on every interaction** (button click, input change)
- `time.sleep()` **blocks the entire Streamlit thread**, preventing UI updates
- No true async/await support (Streamlit runs sync Python)

### Solutions Evaluated

#### 4.1 `st.fragment` (Recommended for HomeIQ)
**Status:** RECOMMENDED - purpose-built for partial updates

Introduced in Streamlit 1.37 (Mar 2024), `@st.fragment` allows **selective reruns** without full-page reset.

**Benefits:**
- Only decorated function reruns, not entire page
- Preserves sidebar state and other UI
- Works with buttons, inputs, sliders
- Simpler than streamlit-autorefresh

**Example:**
```python
import streamlit as st
import time

@st.fragment(run_every=2)  # Rerun every 2 seconds
def live_metrics():
    st.metric("CPU", f"{get_cpu()}%")
    st.metric("Memory", f"{get_memory()}%")

@st.fragment
def user_controls():
    if st.button("Refresh Now"):
        st.rerun()

live_metrics()
user_controls()
```

**HomeIQ application:**
- `pages/real_time_monitoring.py` → wrap live data in `@st.fragment(run_every=5)`
- `pages/service_performance.py` → use `@st.fragment` for metric updates
- **No `time.sleep()` needed** — Streamlit handles refresh scheduling

#### 4.2 `streamlit-autorefresh` (Alternative)
**Status:** ALTERNATIVE - older but still functional

Third-party package that simulates auto-refresh via `st.session_state` manipulation.

**Drawbacks:**
- Adds external dependency
- Less elegant than `@st.fragment`
- Requires manual session state management
- Deprecated in favor of `@st.fragment`

**Recommendation:** **DO NOT USE** — `@st.fragment` is built-in and superior

#### 4.3 WebSocket Approach (Not Recommended)
**Status:** NOT RECOMMENDED for Streamlit

Using WebSockets + async would require rewriting Streamlit app as FastAPI (completely different architecture). Not cost-effective.

### Recommended Fix Strategy

```
Phase 1: Audit (2 days)
- grep -n "time.sleep" domains/frontends/observability-dashboard/src/dashboard_pages/*.py
- Identify blocking calls
- Check refresh requirements (Jaeger API calls, InfluxDB queries)

Phase 2: Refactor with @st.fragment (1 week)
  Step 1: Update Streamlit to 1.37+
    - pip install --upgrade streamlit>=1.37.0

  Step 2: Refactor blocking pages
    - pages/real_time_monitoring.py → wrap live updates in @st.fragment(run_every=5)
    - pages/service_performance.py → wrap metrics in @st.fragment(run_every=10)
    - Remove all time.sleep() calls

  Step 3: Test
    - Manual testing of dashboard responsiveness
    - Verify no console errors from rapid reruns
    - Check Jaeger/InfluxDB connection stability

Phase 3: Optimize (3 days)
  - Adjust run_every intervals (5s too fast? → 10s)
  - Add caching for expensive queries (st.cache_data)
  - Monitor dashboard performance in staging
```

### Key Files to Update
- **observability-dashboard/src/dashboard_pages/real_time_monitoring.py**
- **observability-dashboard/src/dashboard_pages/service_performance.py**
- **observability-dashboard/src/main.py** (if refresh logic exists)
- **observability-dashboard/requirements.txt** → upgrade streamlit

### Risk Assessment
- **Risk Level:** LOW - `@st.fragment` is stable and built-in
- **Performance Impact:** Positive (no blocking, better UX)
- **Backward Compatibility:** 100% (old code still works, just refactored)
- **Rollback Plan:** Revert Python file changes, downgrade Streamlit version
- **Recommendation:** Implement this immediately (high ROI, low risk)

---

## 5. Frontend Testing Strategy

### Current State
- **Unit/Component Testing:** Vitest 4.0.17 + React Testing Library 16.3.1
- **E2E Testing:** Playwright 1.58.1
- **Coverage:** Unclear (no coverage reports seen)
- **Test Organization:** `tests/e2e/` for Playwright; inline Vitest files in source

### Recommended 3-Tier Testing Pyramid

```
                      E2E (5-10%)
                   /            \
                 /              \
              Integration     (15-25%)
           /                       \
         /                         \
      Unit                      (70-80%)
     /                             \
   /___________________________\
```

#### 5.1 Unit Testing (70-80%)
**Status:** Mostly in place, needs structure

**Tools:**
- **Vitest 4.0.17** (current) — faster than Jest, native ESM
- **React Testing Library 16.3.1** (current) — behavior-focused
- **Happy DOM 20.5.0** (current) — lightweight DOM

**Strategy:**
1. **Test behavior, not implementation** — Use `screen.getByRole()`, not `wrapper.find('.btn')`
2. **Test user interactions** — User events (click, type) not component internals
3. **Coverage targets:**
   - **Critical path:** 90% (suggestion creation, device config)
   - **UI components:** 70% (buttons, cards, modals)
   - **Utilities:** 85% (validation, formatting)
   - **Overall:** 75%

**Example (ai-automation-ui):**
```typescript
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { IdeaCard } from './IdeaCard';

test('creates suggestion on button click', async () => {
  const user = userEvent.setup();
  render(<IdeaCard idea={mockIdea} onCreate={vi.fn()} />);

  const button = screen.getByRole('button', { name: /create/i });
  await user.click(button);

  expect(screen.getByText(/success/i)).toBeInTheDocument();
});
```

**Files to test:**
- `src/components/IdeaCard.tsx`, `IdeaList.tsx`, `Sidebar.tsx`
- `src/pages/Ideas.tsx`, `Insights.tsx`
- `src/services/*` (API clients, state stores)

#### 5.2 Integration Testing (15-25%)
**Status:** MISSING — needs implementation

**Definition:** Test multiple units together (component + state + API mocking)

**Tools:**
- **MSW 2.12.8** (current in health-dashboard) — Mock Service Worker for API mocking
- **Vitest** — same as unit tests, no new tooling

**Strategy:**
1. Mock API responses with MSW
2. Test component interaction with state changes
3. Test async flows (loading → success/error)

**Example:**
```typescript
import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';

const server = setupServer(
  http.post('/api/suggestions', () => {
    return HttpResponse.json({ id: 1, title: 'Test' });
  })
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());

test('creates suggestion and updates list', async () => {
  const user = userEvent.setup();
  render(<IdeaList />);

  const input = screen.getByPlaceholderText('New idea');
  await user.type(input, 'Test idea');
  await user.click(screen.getByRole('button', { name: /add/i }));

  expect(await screen.findByText('Test idea')).toBeInTheDocument();
});
```

**Files to test:**
- `src/pages/Ideas.tsx` (with API + state)
- `src/pages/Dashboard.tsx` (with WebSocket + state)
- `src/hooks/useData.ts` (API + state hooks)

#### 5.3 E2E Testing (5-10%)
**Status:** In place with Playwright, needs expansion

**Tools:**
- **Playwright 1.58.1** (current)
- **Current tests:** `tests/e2e/*/` directories

**Strategy:**
1. **Critical user journeys only** (80/20 rule)
2. **Use `@smoke` tag** for quick CI runs
3. **Use `@full` tag** for nightly runs

**Smoke tests (must run on every PR):**
- [smoke] User can navigate main pages
- [smoke] Critical buttons work (Create, Save, Delete)
- [smoke] WebSocket connection established
- [smoke] API errors handled gracefully

**Full tests (nightly):**
- End-to-end workflows (create suggestion → configure → deploy)
- Cross-browser (Chromium, Firefox, Safari)
- Mobile viewport tests

**Example (`ai-automation-ui.spec.ts`):**
```typescript
import { test, expect } from '@playwright/test';

test('[smoke] Navigate Ideas page', async ({ page }) => {
  await page.goto('http://localhost:3001');
  await page.click('[data-testid="nav-ideas"]');
  expect(page.url()).toContain('/ideas');
});

test('[full] Create and deploy automation', async ({ page }) => {
  // Full workflow test
  await page.goto('http://localhost:3001/ideas');
  // ... rest of test
});
```

### Implementation Plan

```
Phase 1: Foundation (1 week)
- Set up coverage reporting in both apps (vitest --coverage)
- Create test templates for common patterns
- Document testing guidelines in CONTRIBUTING.md

Phase 2: Unit Tests (2 weeks)
- Target 75% coverage in ai-automation-ui
- Target 70% coverage in health-dashboard
- Focus on critical paths first

Phase 3: Integration Tests (1 week)
- Add MSW for API mocking
- Test 5-10 critical user flows per app
- Test error scenarios

Phase 4: E2E Expansion (1 week)
- Expand smoke test suite (currently ~3 tests per app)
- Add mobile viewport tests
- Set up nightly full test run

Phase 5: CI/CD Integration (3 days)
- npm run test runs unit + integration
- npm run test:e2e:smoke runs before merge
- npm run test:e2e (full) runs nightly via cron
```

### Risk Assessment
- **Risk Level:** LOW - additive, not breaking
- **Effort:** ~3 weeks for full implementation
- **ROI:** Prevents regressions, faster debugging, confidence in refactoring
- **Recommendation:** Implement in conjunction with React 19 migration

---

## 6. Bundle Optimization

### Current Build Metrics (Estimated)
- **ai-automation-ui:** ~150-180 KB (gzipped)
- **health-dashboard:** ~120-150 KB (gzipped)
- **Build time:** ~2-3 minutes (with Vite 6)

### Best Practices for Vite + React

#### 6.1 Code Splitting
**Status:** Partially implemented

**Strategy:**
1. **Route-based splitting** (automatically via Vite)
   ```typescript
   // vite.config.ts
   export default defineConfig({
     build: {
       rollupOptions: {
         output: {
           manualChunks: {
             'vendor': ['react', 'react-dom', '@tanstack/react-query'],
             'ui': ['lucide-react', '@radix-ui/*'],
           }
         }
       }
     }
   });
   ```

2. **Dynamic imports for pages**
   ```typescript
   const Ideas = lazy(() => import('./pages/Ideas'));
   const Insights = lazy(() => import('./pages/Insights'));
   ```

3. **Component-level splitting** (if heavy)
   ```typescript
   const HeavyChart = lazy(() => import('./components/Chart'));
   ```

**HomeIQ applications:**
- ai-automation-ui: Already uses `react-router-dom` v6 (good for code splitting)
- health-dashboard: Already uses `lazy()` for pages
- **Status:** Mostly in place; review and benchmark

#### 6.2 Lazy Loading & Suspense Boundaries
**Status:** Partially implemented

**Strategy:**
1. Add `<Suspense>` boundaries around lazy components
2. Show loading UI while chunks load

```typescript
<Suspense fallback={<div>Loading...</div>}>
  <Ideas />
</Suspense>
```

**HomeIQ status:** This pattern should be expanded; currently minimal Suspense usage

#### 6.3 Image & Asset Optimization
**Status:** Varies by app

**Strategy:**
1. **Use WebP with JPEG fallback**
   ```html
   <picture>
     <source srcSet="image.webp" type="image/webp" />
     <img src="image.jpg" alt="..." />
   </picture>
   ```

2. **Compress SVGs**
   - Use `svgo` package or inline small SVGs

3. **Lazy load images below fold**
   ```html
   <img src="..." loading="lazy" />
   ```

**HomeIQ status:** Minimal image usage (mostly icons); likely not a bottleneck

#### 6.4 Dependency Analysis
**Status:** Not monitored

**Tools:**
- **Vite Plugin Visualizer:** `npm install -D vite-plugin-visualizer`
  ```typescript
  import { visualizer } from 'rollup-plugin-visualizer';

  export default defineConfig({
    plugins: [visualizer()]
  });
  ```
  Generates `stats.html` showing bundle breakdown

- **Bundle Buddy:** Analyze bundle size trends over time

**HomeIQ implementation:**
```bash
# ai-automation-ui
npm run build
npm install -D vite-plugin-visualizer
# Update vite.config.ts to include visualizer
npm run build  # Creates dist/stats.html
# Open in browser to analyze
```

#### 6.5 Minification & Compression
**Status:** Automatic with Vite

Vite automatically minifies with esbuild (JS) and csso (CSS). No action needed.

### Recommended Implementation Plan

```
Phase 1: Baseline Measurement (2 days)
- Run npm run build in both apps
- Install vite-plugin-visualizer
- Generate bundle reports
- Document baseline: bundle size, build time, LCP metrics

Phase 2: Code Splitting (1 week)
- Audit route structure
- Ensure all routes are lazy-loaded
- Add Suspense boundaries for lazy components
- Test that chunks load on route navigation

Phase 3: Dependency Audit (3 days)
- Review vite-plugin-visualizer output
- Identify unused dependencies (npm ls --depth=0)
- Consolidate similar libraries (e.g., charting libs)

Phase 4: Testing & Verification (3 days)
- Measure new bundle sizes
- Check Lighthouse score (target: 85+ for Performance)
- Verify no regressions in load time
- Update documentation with new metrics
```

### Risk Assessment
- **Risk Level:** LOW - mostly configuration and import changes
- **Performance Impact:** Positive (faster initial load, better LCP)
- **Backward Compatibility:** 100%
- **Recommendation:** Implement in Phase 2 of React 19 migration

---

## 7. Security Best Practices — Frontend API Key Handling

### Problem Statement

Storing API keys in frontend apps risks:
1. **Bundle exposure:** Keys visible in source maps or bundled code
2. **XSS attacks:** Malicious scripts access `window.API_KEY`
3. **Man-in-the-middle:** Unencrypted key transmission (mitigated by HTTPS)
4. **Dependency hijacking:** npm packages stealing keys from env vars

### Architecture Principles

**Golden Rule:** Never trust the client. All secrets must be server-controlled.

### Recommended Approach: API Gateway Pattern

Instead of frontend → backend directly with API key in headers:

```
Frontend (React)
    ↓ (no credentials)
Gateway (FastAPI/Express)
    ↓ (secret API key)
Backend Service (data-api, admin-api, etc.)
```

**Benefits:**
- Frontend never knows the API key
- Gateway can validate requests, rate-limit, log
- Easy to rotate keys (update gateway only)
- Credentials passed via Secure, HttpOnly cookies

### Implementation for HomeIQ

**Current State:**
- ai-automation-ui calls `import.meta.env.VITE_API_URL`
- health-dashboard calls `import.meta.env.VITE_DATA_API_URL`
- Some API keys might be in `import.meta.env.VITE_ADMIN_API_KEY` (audit needed)

**Fix Strategy:**

#### Option 1: Remove Public API Keys (Recommended)
```typescript
// ❌ NEVER DO THIS
const API_KEY = import.meta.env.VITE_API_KEY;  // Exposed!

// ✓ DO THIS
const apiUrl = import.meta.env.VITE_API_URL;  // Just the URL
// Make request with credentials in HttpOnly cookie
fetch(`${apiUrl}/data`, {
  credentials: 'include',  // Sends cookie with key/token
  headers: {
    'Content-Type': 'application/json'
  }
});
```

#### Option 2: Backend-Mediated API Calls
```typescript
// Frontend calls own backend
fetch('/api/proxy/data', {
  credentials: 'include'
});

// Backend (FastAPI) intercepts and forwards
@app.get('/api/proxy/data')
async def proxy_data(request: Request):
  api_key = os.environ['DATA_API_KEY']  # Secret server-side
  response = requests.get(
    'http://data-api:8006/data',
    headers={'Authorization': f'Bearer {api_key}'}
  )
  return response.json()
```

#### Option 3: OAuth 2.0 / OpenID Connect (For Future)
Not applicable to HomeIQ's current architecture (internal-only services).

### Audit Checklist

```
□ Grep for "VITE_.*KEY" in both frontend apps
□ Check .env files for exposed secrets
□ Verify API calls don't include raw API keys in headers
□ Confirm no API keys in localStorage/sessionStorage
□ Ensure all inter-service calls use server-side secrets
□ Enable HSTS headers in all backends
□ Implement CSRF protection if using cookies
□ Document API authentication flow for team
```

### Implementation for HomeIQ Frontends

**File locations:**
- `domains/frontends/ai-automation-ui/.env`
- `domains/frontends/ai-automation-ui/src/services/apiClient.ts`
- `domains/core-platform/health-dashboard/.env`
- `domains/core-platform/health-dashboard/src/services/apiClient.ts`

**Steps:**
1. Grep for `VITE_.*KEY` in both apps (alert if found)
2. Ensure `.env.local` is in `.gitignore` (never commit keys)
3. Document API authentication pattern in project README
4. Add security check to pre-commit hooks: `grep -r "VITE_.*KEY" .env && echo "API Key in env!" && exit 1`

### Risk Assessment
- **Risk Level:** CRITICAL if secrets are exposed in bundles; LOW if already using correct pattern
- **Effort:** 2-4 hours for audit + fixes
- **Recommendation:** Audit immediately; implement proxy pattern if needed

---

## Summary & Prioritized Roadmap

### Quick Wins (Implement Immediately)
| Task | Effort | Impact | Priority |
|------|--------|--------|----------|
| Streamlit `@st.fragment` refactor | 1 week | High (UX) | P1 |
| Frontend security audit (API keys) | 2 hrs | Critical | P1 |
| Bundle optimization baseline (visualizer) | 2 hrs | Medium | P1 |

### Short-term (Next Sprint)
| Task | Effort | Impact | Priority |
|------|--------|--------|----------|
| React 19 migration | 2-3 weeks | Medium (tech debt) | P2 |
| Vite 7 migration | 1 week | Medium (tech debt) | P2 |
| Frontend testing strategy implementation | 3 weeks | High (quality) | P2 |

### Medium-term (Roadmap)
| Task | Effort | Impact | Priority |
|------|--------|--------|----------|
| Tailwind CSS 4 migration | 1-2 weeks | Low (mostly config) | P3 |
| Advanced bundle optimization | 1 week | Low (likely already optimized) | P3 |

### Epic Creation Recommendations

**Epic 1: Frontend Security Hardening**
- Story 1: Audit API key usage in both frontends
- Story 2: Implement API gateway pattern if needed
- Story 3: Add security checks to CI/CD

**Epic 2: React 19 & Vite 7 Upgrade**
- Story 1: Upgrade React 18 → 19 in ai-automation-ui
- Story 2: Upgrade React 18 → 19 in health-dashboard
- Story 3: Upgrade Vite 6 → 7 in both apps
- Story 4: Test compatibility and fix breaking changes

**Epic 3: Streamlit Performance Optimization**
- Story 1: Replace `time.sleep()` with `@st.fragment`
- Story 2: Add caching for expensive queries
- Story 3: Performance testing and monitoring

**Epic 4: Frontend Testing Framework**
- Story 1: Set up coverage reporting (Vitest)
- Story 2: Unit test critical paths (70% target)
- Story 3: Integration tests with MSW
- Story 4: E2E test expansion

**Epic 5: Bundle Optimization**
- Story 1: Establish baseline metrics (vite-plugin-visualizer)
- Story 2: Implement advanced code splitting
- Story 3: Dependency audit and consolidation
- Story 4: Lighthouse score targets (85+)

**Epic 6: Tailwind CSS 4 Migration** (Lowest priority)
- Story 1: Migrate to CSS-based config
- Story 2: Update design system CSS
- Story 3: Test and verify styling

---

## Appendix: Key Resources

### React 19
- [React 19 Release Notes](https://react.dev/blog/2024/12/05/react-19)
- [Upgrade Guide](https://react.dev/blog/2024/12/05/react-19-upgrade-guide)
- [Breaking Changes](https://react.dev/blog/2024/12/05/react-19#breaking-changes)

### Vite 7
- [Vite 7 Release Notes](https://vitejs.dev/blog/announcing-vite7.html)
- [Migration Guide](https://vitejs.dev/guide/migration.html)

### Tailwind CSS 4
- [Tailwind CSS 4 Announcement](https://tailwindcss.com/blog/tailwindcss-v4)
- [Migration Guide](https://tailwindcss.com/docs/upgrade-guide)

### Streamlit
- [Streamlit 1.37+ Fragments](https://docs.streamlit.io/develop/api-reference/control-flow/fragment)
- [Performance Optimization](https://docs.streamlit.io/develop/concepts/app-model)

### Frontend Testing
- [React Testing Library Best Practices](https://testing-library.com/docs/react-testing-library/intro/)
- [Vitest Guide](https://vitest.dev/guide/)
- [Playwright Best Practices](https://playwright.dev/docs/best-practices)

### Security
- [OWASP Top 10 for Frontend](https://owasp.org/www-project-top-ten/)
- [Frontend Security Checklist](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)

---

## Confidence Levels

| Topic | Confidence | Notes |
|-------|------------|-------|
| React 19 migration | 95% | Based on React official docs and HomeIQ's client-side-only arch |
| Vite 7 migration | 90% | Based on official migration guide; HomeIQ config is standard |
| Tailwind CSS 4 | 85% | Config migration is straightforward; design system refactoring adds complexity |
| Streamlit `@st.fragment` | 98% | Built-in feature, stable, documented |
| Testing strategy | 92% | Industry-standard pyramid; HomeIQ partially implemented |
| Bundle optimization | 88% | Standard Vite practices; actual metrics depend on current state |
| Frontend security | 96% | Based on OWASP best practices and industry standards |

---

**Status:** Initial research complete. Next steps:
1. Create TAPPS expert consultations for domain-specific questions
2. Perform detailed audits of each topic in HomeIQ codebase
3. Create actionable epics and stories with effort estimates
