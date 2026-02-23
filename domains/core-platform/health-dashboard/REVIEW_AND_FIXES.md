# Health Dashboard Deep Code Review

**Service**: health-dashboard (Tier 1, Rank #5 - Mission-Critical)
**Review Date**: 2026-02-06
**Reviewer**: Claude Opus 4.6 (Automated Deep Review)
**Files Reviewed**: ~100+ production source files across src/ (tsx, ts)
**Framework**: React 18.3 + TypeScript 5.9 + Vite 6.4 + Tailwind CSS 3.4
**Test Framework**: Vitest 4.0 + Testing Library + Playwright

---

## Executive Summary

The health-dashboard is a large React/TypeScript SPA with 16 tabs, 80+ components, 12 custom hooks, and 5 API client classes. It serves as the primary user interface for the entire HomeIQ platform. The codebase demonstrates solid foundational practices (TypeScript strict mode, CSRF implementation, input sanitization library, good accessibility fundamentals) but has significant gaps in security enforcement, performance optimization, state management, and test coverage that are concerning for a Tier 1 mission-critical service.

**Overall Health Score: 6/10** - Functional and well-structured, but needs targeted investment to meet Tier 1 reliability standards.

---

## Quality Scores

| Category              | Score | Rating     | Notes                                             |
|-----------------------|-------|------------|---------------------------------------------------|
| **Security**          | 6/10  | Adequate   | CSRF exists, sanitizers exist, but gaps in enforcement |
| **Error Handling**    | 7/10  | Good       | Error boundaries present, stale data resilience good |
| **Performance**       | 5/10  | Needs Work | No lazy loading, aggressive polling, large initial bundle |
| **State Management**  | 5/10  | Needs Work | No centralized state, prop drilling, duplicate fetches |
| **Code Quality**      | 6/10  | Adequate   | Dead code present, 64 `any` usages, good linting |
| **Accessibility**     | 7/10  | Good       | ARIA roles present, keyboard nav, some gaps |
| **API Integration**   | 7/10  | Good       | Well-structured clients, but inconsistent auth patterns |
| **Build/Deploy**      | 8/10  | Very Good  | Solid Vite config, Docker multi-stage, nginx |
| **Testing**           | 3/10  | Poor       | 14 test files for 100+ source files (~14% coverage) |
| **Overall**           | 6/10  | Adequate   | Functional but needs investment for Tier 1 status |

---

## CRITICAL Issues

### CRIT-01: API Key Exposed in Client-Side Bundle (SECURITY)
**File**: `src/services/api.ts`, lines 109-117; `src/components/IntegrationDetailsModal.tsx`, lines 125-133
**Severity**: CRITICAL
**Impact**: API key is compiled into the JavaScript bundle and sent to every browser

The `VITE_API_KEY` environment variable is read at build time via `import.meta.env.VITE_API_KEY` and becomes a string literal in the production JavaScript bundle. Anyone can open DevTools and extract it. While there is a console warning in `api.ts` (line 112-114), the code still uses the key.

Worse, `IntegrationDetailsModal.tsx` (line 125) reads `VITE_API_KEY` directly and sends it as both `Authorization: Bearer` and `X-HomeIQ-API-Key` headers, bypassing the centralized auth headers entirely:

```typescript
// src/components/IntegrationDetailsModal.tsx, line 125-133
const API_KEY = import.meta.env.VITE_API_KEY || '';
const analyticsResponse = await fetch(`/api/integrations/${platform}/analytics`, {
  headers: {
    'Authorization': `Bearer ${API_KEY}`,
    'X-HomeIQ-API-Key': API_KEY,
  },
});
```

The `Dockerfile` (line 22, 37) also accepts `VITE_API_KEY` as a build argument and sets it as an environment variable, which bakes it into the production build.

**Fix**: Remove `VITE_API_KEY` from the Dockerfile build args. Remove all direct `import.meta.env.VITE_API_KEY` references. Route all API calls through the centralized `adminApi`/`dataApi` clients. In production, let nginx inject auth headers on proxy.

---

### CRIT-02: Unsanitized User Input in RegExp Constructor (ReDoS)
**File**: `src/services/haClient.ts`, lines 66-77
**Severity**: CRITICAL
**Impact**: Regex Denial of Service if user-supplied patterns are passed

```typescript
// src/services/haClient.ts, line 70
async getSensorsByPattern(pattern: string): Promise<HASensor[]> {
  const states = await this.getAllStates();
  try {
    const regex = new RegExp(pattern); // User input directly in RegExp
    return states.filter(sensor => regex.test(sensor.entity_id));
  } catch (e) {
    console.warn(`Invalid regex pattern "${pattern}", falling back to string match`);
    return states.filter(sensor => sensor.entity_id.includes(pattern));
  }
}
```

While the try/catch handles syntax errors, it does NOT prevent catastrophic backtracking. A pattern like `(a+)+$` passed to this function would freeze the browser tab. Currently called only with hardcoded patterns (`'^sensor\\.nhl_'`), but the public API surface accepts arbitrary strings.

**Fix**: Escape user input with a regex escape utility, use string-based matching (`startsWith`, `includes`), or implement a timeout-based execution guard. At minimum, add JSDoc warning that this method should NEVER receive user-provided input.

---

### CRIT-03: Direct `fetch()` Bypassing Auth in Multiple Hooks (SECURITY)
**Files**: `src/hooks/useAlerts.ts` lines 56-61; `src/hooks/useAnalyticsData.ts` lines 56-61; `src/hooks/useEnvironmentHealth.ts` line 30; `src/components/ConfigForm.tsx` lines 41, 60, 91; `src/components/IntegrationDetailsModal.tsx` line 129
**Severity**: CRITICAL
**Impact**: Several hooks and components make API calls without consistent authentication headers

Multiple components bypass the centralized `BaseApiClient` authentication layer. Some manually add `sessionStorage.getItem('api_key')` headers (inconsistent pattern), while others use no auth at all:

```typescript
// src/hooks/useAlerts.ts, lines 56-62 - Manual partial auth
const alertsResponse = await fetch(`/api/v1/alerts?${params.toString()}`, {
  signal: controller.signal,
  headers: {
    'Content-Type': 'application/json',
    ...(sessionStorage.getItem('api_key') ? { 'X-API-Key': sessionStorage.getItem('api_key')! } : {}),
  },
});

// src/components/ConfigForm.tsx, line 41 - NO auth headers at all
const response = await fetch(`/api/v1/integrations/${service}/config`);
```

The `useAlerts` hook also duplicates auth header construction logic instead of using `withAuthHeaders()` from the API module. This means if auth logic changes, these call sites will be missed.

**Fix**: Route ALL API calls through the centralized `adminApi` or `dataApi` clients, or create new service clients that extend `BaseApiClient`. Never call `fetch()` directly in components or hooks.

---

### CRIT-04: CSRF Token is Client-Generated Without Server Validation (SECURITY)
**File**: `src/utils/security.ts`, lines 25-43
**Severity**: HIGH (downgraded from CRITICAL due to SameSite=Strict mitigation)
**Impact**: CSRF protection relies on client-generated tokens

The CSRF implementation generates a token client-side, writes it as a cookie (without `HttpOnly`), and sends it as a header. The cookie is accessible via JavaScript since it must be read by the frontend. The primary defense is `SameSite=Strict` (line 34), which is effective against most CSRF vectors in modern browsers.

However, the crypto fallback (line 48) uses `Math.random()` which is not cryptographically secure:

```typescript
// src/utils/security.ts, line 48
return Math.random().toString(36).substring(2, 18); // Weak PRNG fallback
```

**Fix**: The `SameSite=Strict` setting provides adequate CSRF protection for the deployment context (internal dashboard). For defense-in-depth, implement server-side CSRF validation. Remove the `Math.random()` fallback or make it throw an error instead, since all modern browsers support `crypto.getRandomValues`.

---

## HIGH Issues

### HIGH-01: Aggressive Polling Without Coordination (PERFORMANCE)
**Files**: Multiple hooks and components
**Severity**: HIGH
**Impact**: 10+ concurrent polling intervals creating constant network traffic

The dashboard creates numerous independent polling intervals:

| Source | Interval | Endpoint |
|--------|----------|----------|
| `EventStreamViewer.tsx` | **3 sec** | `/api/v1/events` |
| `useRealTimeMetrics.ts` | **5 sec** | `/api/v1/real-time-metrics` |
| `ServiceControl.tsx` | **5 sec** | `/api/v1/health/services` |
| `AlertBanner.tsx` | 30 sec | `/api/v1/alerts/active` |
| `useHealth.ts` | 30 sec | `/api/health` |
| `useDataSources.ts` | 30 sec | `/api/v1/health/services` |
| `useEnvironmentHealth.ts` | 30 sec | `/setup-service/api/health/environment` |
| `OverviewTab.tsx` | 30 sec | `/api/v1/health` (enhanced) |
| `useStatistics.ts` | 60 sec | `/api/v1/stats` |
| `useAlerts.ts` | 120 sec | `/api/v1/alerts` |

Some hooks implement `visibilitychange` handlers (`useHealth`, `useDataSources`, `useRealTimeMetrics`) to pause polling when the tab is hidden, but others do NOT (`useStatistics`, `useEnvironmentHealth`, `ServiceControl`, `EventStreamViewer`). The `OverviewTab` alone triggers 6-7 simultaneous polling intervals.

**Fix**:
1. Add `visibilitychange` handling consistently to all polling hooks.
2. Implement exponential backoff on errors.
3. Consider TanStack Query for automatic deduplication and cache sharing.
4. Use WebSocket for real-time data (the `react-use-websocket` dependency is already installed but appears unused for data polling).

---

### HIGH-02: No Lazy Loading for Tab Components (PERFORMANCE)
**File**: `src/components/Dashboard.tsx`, lines 1-26
**Severity**: HIGH
**Impact**: All 16 tab components loaded eagerly on initial page load

```typescript
// src/components/Dashboard.tsx
import * as Tabs from './tabs'; // Imports ALL 16 tabs eagerly

const TAB_COMPONENTS: Record<string, React.FC<Tabs.TabProps>> = {
  overview: Tabs.OverviewTab,
  setup: Tabs.SetupTab,
  // ... 14 more tabs
};
```

Despite `React.lazy` being imported (line 1) and `Suspense` being used (line 337), no actual lazy loading occurs. All tab components and their dependencies (chart libraries, sports logic, validation UI) are bundled into the initial load. The `manualChunks` config only splits `react` and `react-dom` (vite.config.ts line 103-104).

Estimated unnecessary initial load: recharts (~400KB), chart.js (~200KB), lucide-react (~100KB), 18 Radix UI packages, plus all tab-specific code.

**Fix**: Replace eager imports with `React.lazy()` for each tab. Add chunking for major libraries:
```typescript
// Example lazy loading
const SportsTab = lazy(() => import('./tabs/SportsTab').then(m => ({ default: m.SportsTab })));
```

---

### HIGH-03: Service Name Not Validated in Container Operations (SECURITY)
**File**: `src/services/api.ts`, lines 329-383
**Severity**: HIGH
**Impact**: Path traversal potential in container management API calls

The `AdminApiClient` has a `validateServiceName` method (line 318) but only applies it to `startContainer`, `stopContainer`, and `restartContainer`. The `getContainerLogs` and `getContainerStats` methods interpolate `serviceName` directly into URLs without validation:

```typescript
// src/services/api.ts, lines 373-383 - NO validation
async getContainerLogs(serviceName: string, tail: number = 100): Promise<{ logs: string }> {
  return this.fetchWithErrorHandling<{ logs: string }>(
    this.buildUrl(`/api/v1/docker/containers/${serviceName}/logs?tail=${tail}`)
  );
}

async getContainerStats(serviceName: string): Promise<ContainerStats> {
  return this.fetchWithErrorHandling<ContainerStats>(
    this.buildUrl(`/api/v1/docker/containers/${serviceName}/stats`)
  );
}
```

A value like `../../admin` could cause path traversal. The `tail` parameter is also not validated and could be abused with extremely large values.

**Fix**: Apply `validateServiceName()` to ALL container operation methods. Validate the `tail` parameter range (e.g., 1-10000).

---

### HIGH-04: `automationUiUrl` Environment Variable Rendered as Href Without Sanitization (SECURITY)
**File**: `src/components/Dashboard.tsx`, lines 48, 253-264
**Severity**: HIGH
**Impact**: Environment variable rendered as clickable link without URL sanitization

```typescript
// src/components/Dashboard.tsx, line 48
const automationUiUrl = import.meta.env.VITE_AI_AUTOMATION_UI_URL;

// Line 254 - rendered directly as href
<a href={automationUiUrl} target="_blank" rel="noopener noreferrer" ...>
```

If `VITE_AI_AUTOMATION_UI_URL` is set to a `javascript:` URL during CI/build, this becomes an XSS vector. The `sanitizeUrl()` function exists in `src/utils/inputSanitizer.ts` but is not used here or in any other component.

**Fix**: Apply `sanitizeUrl()` to all environment-derived URLs before rendering in `href` attributes. Audit all uses of `import.meta.env.VITE_*` in JSX.

---

### HIGH-05: Duplicate Type Definitions Causing Confusion
**Files**: `src/types.ts` (root) vs `src/types/health.ts`, `src/types/alerts.ts` vs `src/constants/alerts.ts`
**Severity**: HIGH
**Impact**: Two different `HealthStatus` types, two different `Alert` types, leading to potential type mismatches

There are conflicting type definitions:
1. `src/types.ts` (line 1) defines `HealthStatus` as an **interface** with fields like `service`, `status`, `dependencies`
2. `src/types/health.ts` (line 7) defines `HealthStatus` as an **enum** with values `HEALTHY`, `WARNING`, `CRITICAL`, `UNKNOWN`
3. `src/types/index.ts` re-exports everything from `types/health.ts`, which means `import { HealthStatus } from '../types'` could resolve to the enum

Similarly:
1. `src/types/alerts.ts` defines `Alert` interface with `severity: AlertSeverity`
2. `src/constants/alerts.ts` (imported by AlertBanner.tsx) likely defines a different `Alert` type
3. `src/components/AlertCenter.tsx` (line 3) defines its own local `Alert` interface

This causes confusion about which type is canonical and risks runtime errors from type mismatches.

**Fix**: Consolidate to a single canonical type definition per entity. Remove the root-level `src/types.ts` or make it re-export from `src/types/index.ts`. Audit all local interface redefinitions.

---

## MEDIUM Issues

### MED-01: Dead Code - 5 `.OLD.` and `.REFACTORED.` Files (CODE QUALITY)
**Files**:
- `src/components/AlertBanner.OLD.tsx`
- `src/components/AlertBanner.REFACTORED.tsx`
- `src/components/AlertsPanel.OLD.tsx`
- `src/components/AlertsPanel.REFACTORED.tsx`
- `src/components/AnalyticsPanel.OLD.tsx`
**Severity**: MEDIUM
**Impact**: Developer confusion, maintenance burden

These files are not imported by any other file (confirmed by grep). While Vite tree-shaking should exclude them from the production bundle, they add noise and confusion.

**Fix**: Delete all `.OLD.` and `.REFACTORED.` files. Use git history to reference old implementations.

---

### MED-02: `darkMode` Prop Drilling Through Entire Component Tree (STATE MANAGEMENT)
**File**: `src/components/Dashboard.tsx` -> all tabs -> all sub-components
**Severity**: MEDIUM
**Impact**: Every component receives `darkMode` as a prop; theme change requires touching dozens of files

```typescript
// src/components/tabs/types.ts
export interface TabProps {
  darkMode: boolean; // Passed to every single tab
}
```

The `darkMode` boolean is passed through `Dashboard -> TabComponent -> SubComponents`. This is a textbook case for React Context. Every tab and most sub-components accept and forward `darkMode`, creating a fragile prop chain.

**Fix**: Create a `ThemeContext` provider wrapping the app. Components consume it via `useContext(ThemeContext)` instead of props.

---

### MED-03: 64 Instances of `any` Type Usage (TYPE SAFETY)
**Files**: 27 files with `any` type usage
**Severity**: MEDIUM
**Impact**: Undermines TypeScript's type safety guarantees

Despite `strict: true` in tsconfig.json, there are 64 instances of `: any` across 27 files. Key offenders:

| File | Count | Examples |
|------|-------|---------|
| `services/api.ts` | 3 | `testServiceHealth` return type, `getRealTimeMetrics` return type |
| `components/EventStreamViewer.tsx` | 4 | `mapApiEvent(apiEvent: any)`, `catch (err: any)` |
| `hooks/useDevices.ts` | 4 | All catch blocks use `catch (err: any)` |
| `components/ConfigForm.tsx` | 3 | All catch blocks use `catch (err: any)` |
| `components/ServiceControl.tsx` | 3 | All catch blocks use `catch (err: any)` |

There are 16 instances of `catch (err: any)` across the codebase, which should use `catch (err: unknown)` with proper type narrowing.

**Fix**: Replace `any` with proper types. Use `unknown` for catch blocks with type narrowing. Create proper return types for API methods that currently return `Promise<any>`.

---

### MED-04: `confirm()` and `alert()` Used for Critical Actions (UX)
**Files**: `src/components/ConfigForm.tsx` (lines 83, 98); `src/components/ServiceControl.tsx` (lines 53, 61, 68, 80, 83); `src/components/ServicesTab.tsx` (lines 224, 227, 425, 460); `src/components/tabs/ValidationTab.tsx` (lines 139, 166, 171); `src/components/tabs/SynergiesTab.tsx` (line 668)
**Severity**: MEDIUM
**Impact**: 22 instances of native browser dialogs in a themed SPA

Native `window.confirm()` and `window.alert()` calls:
1. Break the dark mode theme
2. Are not accessible (no ARIA support)
3. Can be suppressed by popup blockers
4. Block the main thread

**Fix**: Replace with Radix UI Dialog/AlertDialog (already a dependency: `@radix-ui/react-dialog`, `@radix-ui/react-alert-dialog`).

---

### MED-05: Console Logging in Production - 130 Instances Across 54 Files (CODE QUALITY)
**Files**: Throughout the codebase
**Severity**: MEDIUM
**Impact**: Sensitive information (API URLs, error stacks, event data) logged to browser console

Found 130 `console.log/warn/error` calls across 54 files. The `EventStreamViewer.tsx` is particularly verbose with 13 console calls including debug logging of event IDs, state transitions, and error stacks (lines 153-258):

```typescript
// src/components/EventStreamViewer.tsx, line 153
console.log(`[EventStreamViewer] ensureEventDetails called for eventId: ${eventId}`);
console.log(`[EventStreamViewer] Current detail state for ${eventId}:`, current);
```

**Fix**: Implement a structured logger that respects `import.meta.env.VITE_LOG_LEVEL`. Strip `console.log` calls in production via Vite's esbuild drop config:
```typescript
// vite.config.ts
build: {
  esbuild: { drop: isProduction ? ['console', 'debugger'] : [] },
}
```

---

### MED-06: Missing `aria-label` on Icon-Only Buttons (ACCESSIBILITY)
**Files**: `src/components/EventStreamViewer.tsx` (lines 437-449), `src/components/AlertCenter.tsx` (lines 199-214)
**Severity**: MEDIUM
**Impact**: Screen readers cannot announce purpose of emoji-only buttons

```typescript
// src/components/EventStreamViewer.tsx, lines 437-443
<button onClick={() => handleToggleDetails(event.id)}
  className="..." title="Toggle details">
  {expandedEvent === event.id ? '...' : '...'} // Emoji content only
  // No aria-label
</button>

// src/components/AlertCenter.tsx, lines 199-206
<button onClick={() => onResolveAlert(alert.id)} title="Mark as resolved">
  ... // Checkmark character only, no aria-label
</button>
```

While many buttons have proper `aria-label` attributes (particularly in `Dashboard.tsx`), icon-only buttons in sub-components often rely on `title` attributes which are not consistently read by screen readers.

**Fix**: Add `aria-label` to all interactive elements that lack visible text labels.

---

### MED-07: `useEffect` Dependency Array Issues (STATE MANAGEMENT)
**Files**: `src/hooks/useHealth.ts`, `src/hooks/useDataSources.ts`, `src/hooks/useStatistics.ts`
**Severity**: MEDIUM
**Impact**: Stale closures, functions not in dependency arrays

Several hooks define fetch functions inline within useEffect but outside useCallback, and reference them from both the effect body and the `refresh` function:

```typescript
// src/hooks/useHealth.ts - fetchHealth defined inside useEffect
useEffect(() => {
  let mounted = true;
  const fetchHealth = async () => { /* ... */ };
  const startPolling = () => { fetchHealth(); interval = setInterval(fetchHealth, refreshInterval); };
  startPolling();
  return () => { mounted = false; /* ... */ };
}, [refreshInterval]);

// But refresh() is defined OUTSIDE the effect, creating a different function
const refresh = async () => {
  const healthData = await apiService.getHealth();
  setHealth(healthData);  // Different function, no mounted guard
};
```

The `refresh` function (line 65-76) is a completely separate implementation without the `mounted` guard or error handling consistency of the version inside the effect.

**Fix**: Use `useCallback` for fetch functions and reference them from both the effect and the exposed refresh method. See `useRealTimeMetrics.ts` for the correct pattern.

---

### MED-08: `isStale` Calculation Never Becomes True Reactively (PERFORMANCE)
**File**: `src/hooks/useDataFreshness.ts`, lines 106-110
**Severity**: MEDIUM
**Impact**: Stale indicator relies on `useMemo` with `Date.now()` which is not reactive

```typescript
const isStale = useMemo(() => {
  if (!lastUpdate) return true;
  const age = Date.now() - lastUpdate.getTime();
  return age > staleThresholdMs;
}, [lastUpdate, staleThresholdMs]); // Date.now() is NOT a dependency
```

Since `Date.now()` is not a React state value, `isStale` only recomputes when `lastUpdate` changes. It will NOT automatically transition from `false` to `true` when the threshold time elapses.

**Fix**: Add a periodic timer that triggers re-evaluation, or use `useEffect` + `setInterval` to periodically re-check freshness.

---

### MED-09: Redundant Vendor Chunk Configuration (BUILD)
**File**: `vite.config.ts`, lines 103-104
**Severity**: MEDIUM
**Impact**: Only react/react-dom chunked; large dependencies in main bundle

```typescript
manualChunks: {
  vendor: ['react', 'react-dom'],
},
```

Large dependencies bundled into the main chunk: `recharts` (~400KB), `chart.js` (~200KB), `lucide-react` (~100KB), 18+ Radix UI packages.

**Fix**: Create separate chunks:
```typescript
manualChunks: {
  vendor: ['react', 'react-dom'],
  charts: ['recharts', 'chart.js', 'react-chartjs-2'],
  ui: ['lucide-react', '@radix-ui/react-dialog', '@radix-ui/react-tabs', /* etc */],
},
```

---

### MED-10: `react-use-websocket` Dependency Installed But Potentially Unused for Data (BUILD)
**File**: `package.json`, line 56
**Severity**: MEDIUM
**Impact**: Unused dependency adds to bundle size; missed opportunity for real-time updates

The `react-use-websocket` package (v4.13.0) is listed as a dependency but data polling is done via HTTP `fetch()` + `setInterval()`. If WebSocket integration exists, it is not used for the primary data flow (health, stats, events, alerts). This represents both wasted bundle space and a missed architectural opportunity.

**Fix**: Either leverage WebSocket for real-time data (replacing polling) or remove the dependency.

---

### MED-11: Nginx Runs as Root User in Production Container (SECURITY/DEPLOY)
**File**: `Dockerfile`, lines 57-61, 74
**Severity**: MEDIUM
**Impact**: Web server runs with root privileges

While the Dockerfile creates a non-root user (`appuser`) and assigns file ownership, the `CMD ["nginx", "-g", "daemon off;"]` still runs nginx as root. The `appuser` is created for file ownership only.

**Fix**: Configure nginx to run as a non-root user by adding `user appuser;` to the nginx config or using the official `nginx-unprivileged` base image.

---

## LOW Issues

### LOW-01: ChartTest.tsx in Production Source Tree
**File**: `src/components/ChartTest.tsx`
**Severity**: LOW
**Impact**: Test/debug component in production source directory

A `ChartTest.tsx` file exists in the components directory, which appears to be a development testing artifact.

**Fix**: Move to a `__tests__` or `__stories__` directory, or delete.

---

### LOW-02: Emoji Characters Used as Status Icons
**Files**: Throughout the codebase (SystemStatusHero, AlertCenter, ServiceControl, etc.)
**Severity**: LOW
**Impact**: Inconsistent rendering across platforms; not ideal for accessibility

Status indicators use emoji characters (e.g., `'...'`, `'...'`, `'...'`) instead of SVG icons. The `lucide-react` icon library is already a dependency but these components use emoji strings.

**Fix**: Replace emoji status icons with `lucide-react` SVG icons for consistent cross-platform rendering.

---

### LOW-03: `index.html` References Non-Existent Assets
**File**: `index.html`, lines 5, 23, 30, 33
**Severity**: LOW
**Impact**: Missing favicon, OG image, and PWA manifest

References to `/vite.svg`, `/og-image.png`, and `/manifest.json` may not exist in the public directory (not verified). Missing assets cause 404 errors in production.

**Fix**: Verify all referenced assets exist in the `public/` directory or remove the references.

---

### LOW-04: `robots` Meta Tag Set to `index, follow` for Internal Dashboard
**File**: `index.html`, line 14
**Severity**: LOW
**Impact**: Search engines could index an internal dashboard if exposed

```html
<meta name="robots" content="index, follow" />
```

An internal monitoring dashboard should not be indexed by search engines.

**Fix**: Change to `<meta name="robots" content="noindex, nofollow" />`.

---

## Architecture Analysis

### ARCH-01: No Centralized State Management
**Severity**: HIGH
**Impact**: Duplicate data fetching, inconsistent views, wasted network resources

The Overview tab alone initializes 7+ hooks that independently fetch data. The Services tab, Alerts tab, and Data Sources tab each independently fetch overlapping data. There is no shared cache or state layer.

**Recommendation**: Implement TanStack Query (React Query) for:
- Automatic request deduplication
- Cache sharing between tabs
- Background refetching with stale-while-revalidate
- Built-in retry and error handling

---

### ARCH-02: Tab Navigation via DOM Queries (ANTI-PATTERN)
**File**: `src/components/tabs/OverviewTab.tsx` (multiple locations)
**Severity**: MEDIUM
**Impact**: Fragile tab navigation coupled to DOM structure

```typescript
const devicesTab = document.querySelector('[data-tab="devices"]') as HTMLElement;
if (devicesTab) devicesTab.click();
```

Some components navigate tabs by querying the DOM and programmatically clicking. A custom event system exists (`navigateToTab` at Dashboard.tsx line 122-130) but is not used consistently.

**Fix**: Use the existing `navigateToTab` custom event consistently, or better yet, lift `setSelectedTab` to a context.

---

### ARCH-03: Inconsistent Fetch Patterns Across Hooks
**Severity**: MEDIUM
**Impact**: Some hooks have race condition guards, others do not

Pattern compliance across hooks:

| Hook | `mounted` guard | `AbortController` | `visibilitychange` | `useCallback` fetch |
|------|:-:|:-:|:-:|:-:|
| `useHealth` | Yes | Yes (unused) | Yes | No |
| `useStatistics` | Yes | Yes (unused) | No | No |
| `useDataSources` | Yes | Yes (unused) | Yes | No |
| `useRealTimeMetrics` | No | No | Yes | Yes |
| `useAlerts` | Yes | Yes (used) | No | Yes |
| `useAnalyticsData` | No | No | No | Yes |
| `useEnvironmentHealth` | No | No | No | Yes |
| `useDevices` | No | No | No | Yes |

Note: The `AbortController` in `useHealth`, `useStatistics`, and `useDataSources` is created but never passed to `fetch()` calls (the API client does not support abort signals). This means the abort never actually cancels requests.

**Fix**: Create a reusable `usePolling` hook that standardizes all these patterns.

---

## Testing Gap Analysis

### Current Coverage: 14 test files for 100+ source files (~14% file coverage)

| Area | Test Files | Production Files | Coverage |
|------|-----------|-----------------|----------|
| API Client | 2 | 4 | 50% |
| Hooks | 2 | 12 | 17% |
| Components | 5 | ~80+ | ~6% |
| Utils | 1 | 6 | 17% |
| Types | 0 | 7 | 0% |
| Sports | 3 | 14 | 21% |
| Tabs | 0 | 16 | 0% |

### Critical Missing Tests

**Security Tests (P0)**:
- No tests for CSRF token generation/validation in `security.ts`
- No tests for API key handling in `api.ts` `getAuthHeaders()`
- No tests for `sanitizeUrl()` being applied before rendering
- `inputSanitizer.test.ts` exists and is comprehensive (good) but no integration tests verify sanitizers are actually used in components

**Error Handling Tests (P1)**:
- No tests for `ErrorBoundary.tsx` or `PageErrorBoundary.tsx` fallback behavior
- No tests for error recovery flows (reset, reload)
- No tests for network error handling in any hook

**Hook Tests (P1)**:
- No tests for `useAlerts` (complex fetch + optimistic updates)
- No tests for `useDevices` (parallel fetching)
- No tests for `useEnvironmentHealth` (extensive error normalization)
- No tests for `useRealTimeMetrics`, `usePerformanceHistory`, `useDataFreshness`, `useAnalyticsData`

**Component Tests (P2)**:
- No tests for `ConfigForm` (save, restart, sensitive field masking)
- No tests for `EventStreamViewer` (polling, detail loading, copy)
- No tests for `AlertBanner` (acknowledge/resolve flows)
- No tests for `ServiceControl` (restart operations)
- No tests for any tab component

**Dashboard Integration Tests (P1)**:
- Existing `Dashboard.test.tsx` has 3 tests but assertions reference stale text (`HA Ingestor Dashboard` vs actual `HomeIQ Dashboard`)
- `Dashboard.interactions.test.tsx` exists but content not verified

---

## Fix Priority Matrix

| Priority | Issue ID | Category | Effort | Impact |
|----------|----------|----------|--------|--------|
| **P0 - Immediate** | CRIT-01 | Security | Medium | API key leaked in bundle |
| **P0 - Immediate** | CRIT-03 | Security | Medium | Auth bypass in hooks |
| **P0 - Immediate** | HIGH-03 | Security | Low | Path traversal in container ops |
| **P1 - This Sprint** | CRIT-02 | Security | Low | ReDoS vulnerability |
| **P1 - This Sprint** | CRIT-04 | Security | Low | CSRF Math.random fallback |
| **P1 - This Sprint** | HIGH-01 | Performance | Medium | Aggressive polling |
| **P1 - This Sprint** | HIGH-04 | Security | Low | URL sanitization |
| **P1 - This Sprint** | HIGH-05 | Code Quality | Medium | Duplicate type definitions |
| **P2 - Next Sprint** | HIGH-02 | Performance | Medium | Lazy load tabs |
| **P2 - Next Sprint** | MED-01 | Code Quality | Low | Delete dead code files |
| **P2 - Next Sprint** | MED-03 | Type Safety | Medium | Replace `any` with proper types |
| **P2 - Next Sprint** | MED-05 | Code Quality | Medium | Production logging |
| **P2 - Next Sprint** | MED-09 | Build | Low | Chunk optimization |
| **P2 - Next Sprint** | Testing | Testing | High | Critical test coverage |
| **P3 - Backlog** | MED-02 | State | Medium | Theme context |
| **P3 - Backlog** | MED-04 | UX | Low | Replace confirm/alert |
| **P3 - Backlog** | MED-06 | A11y | Low | ARIA labels |
| **P3 - Backlog** | MED-07 | State | Low | Hook dependency fixes |
| **P3 - Backlog** | MED-08 | Performance | Low | Staleness timer |
| **P3 - Backlog** | MED-10 | Build | Low | Remove unused WebSocket dep |
| **P3 - Backlog** | MED-11 | Security | Low | Nginx non-root |
| **P3 - Backlog** | ARCH-01 | Architecture | High | Centralized state (TanStack Query) |
| **P3 - Backlog** | ARCH-02 | Architecture | Medium | Tab navigation refactor |

---

## Positive Observations

1. **Good Error Boundary Coverage**: Both `ErrorBoundary.tsx` and `PageErrorBoundary.tsx` exist with proper fallback UIs, reset capabilities, and development-only error details. The root `main.tsx` wraps the entire app in an ErrorBoundary.

2. **CSRF Implementation Exists**: The double-submit cookie pattern with `SameSite=Strict` provides reasonable CSRF protection. The `withCsrfHeader()` utility is correctly applied to all mutating requests in the `BaseApiClient`.

3. **Comprehensive Input Sanitization Library**: `inputSanitizer.ts` provides 11 sanitization/validation functions covering URL, HTML attributes, entity IDs, device IDs, service names, markdown, JSON, search queries, filter values, time ranges, and numeric inputs. Each function has proper type checking and length limits.

4. **Accessibility Fundamentals**: Dashboard.tsx correctly implements ARIA `role="tablist"`, `role="tab"`, `role="tabpanel"`, `aria-selected`, `aria-controls`, keyboard navigation (Arrow keys, Home, End), and focus management. Multiple components use `role="status"`, `aria-live="polite"`, and `aria-label`.

5. **TypeScript Strict Mode**: `tsconfig.json` enables `strict: true`, `noUnusedLocals`, `noUnusedParameters`, and `noFallthroughCasesInSwitch`.

6. **Docker Multi-Stage Build**: Efficient Dockerfile with cache mounts, non-root file ownership, health checks, timezone configuration, and proper layer ordering.

7. **Stale Data Resilience**: Multiple hooks correctly preserve existing data on fetch errors rather than clearing to empty state, preventing data flicker during transient failures. This is particularly well-implemented in `useDevices.ts` and `useEnvironmentHealth.ts`.

8. **Service Worker Support**: PWA service worker registration in `main.tsx` with update detection and controlled refresh.

9. **Well-Structured API Clients**: The `api.ts` module provides 5 distinct API clients (`AdminApiClient`, `DataApiClient`, `AIAutomationApiClient`, `RAGServiceClient`, `SetupServiceClient`) with proper separation of concerns and consistent error handling patterns.

10. **Responsive Design**: Dashboard uses Tailwind responsive breakpoints (`sm:`, `md:`, `lg:`) throughout, with mobile-optimized layouts, minimum touch target sizes (`min-h-[44px]`), and hidden elements for smaller screens.

11. **Visibility-Aware Polling**: Three hooks (`useHealth`, `useDataSources`, `useRealTimeMetrics`) correctly implement `document.visibilitychange` listeners to pause polling when the tab is hidden, saving resources.

12. **Service Name Validation**: The `AdminApiClient.validateServiceName()` method (line 318) validates service names with a regex pattern, preventing injection - though it needs to be applied consistently.
