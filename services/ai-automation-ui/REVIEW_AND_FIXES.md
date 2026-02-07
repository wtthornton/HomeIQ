# AI Automation UI - Deep Code Review

**Service**: ai-automation-ui (Tier 7, Port 3001)
**Reviewed**: 2026-02-06
**Reviewer**: Senior Code Review (Automated)
**Scope**: All source files in `services/ai-automation-ui/`

---

## Executive Summary

The ai-automation-ui is a React 18 SPA built with TypeScript, Vite 6, Tailwind CSS 3, Zustand, and React Query. It serves as the frontend for the HomeIQ AI automation platform, proxying requests to 7 backend services via nginx. The codebase contains **2 critical**, **9 high**, **14 medium**, and **8 low** severity findings across security, architecture, code quality, and operational concerns.

The most urgent issues are **hardcoded API key fallbacks in 4 files** (security) and **CORS wildcard on all proxy routes** (security). The highest-impact architectural issue is **massive code duplication across 10 API modules** with identical `withAuthHeaders`/`fetchJSON` patterns copied verbatim.

---

## Table of Contents

1. [Security](#1-security)
2. [Code Quality & TypeScript](#2-code-quality--typescript)
3. [Architecture & Component Design](#3-architecture--component-design)
4. [Performance](#4-performance)
5. [API Design & Data Fetching](#5-api-design--data-fetching)
6. [Error Handling](#6-error-handling)
7. [Configuration & Environment](#7-configuration--environment)
8. [Docker & Deployment](#8-docker--deployment)
9. [Dependencies](#9-dependencies)
10. [Testing](#10-testing)
11. [Logging & Observability](#11-logging--observability)
12. [Frontend-Specific](#12-frontend-specific)
13. [Documentation](#13-documentation)
14. [Prioritized Action Plan](#14-prioritized-action-plan)

---

## 1. Security

### SEC-01: Hardcoded API Key Fallback in 4 Files [CRITICAL]

**Files**:
- `src/pages/Discovery.tsx:29`
- `src/api/admin.ts:49`
- `src/api/settings.ts:56`
- `src/api/preferences.ts:31`

```typescript
// All 4 files contain:
const API_KEY = import.meta.env.VITE_API_KEY || 'hs_P3rU9kQ2xZp6vL1fYc7bN4sTqD8mA0wR';
```

**Risk**: The fallback API key is checked into source control and embedded in the production JS bundle. Anyone with access to the built JS assets can extract this key and make authenticated API calls.

**Fix**: Remove the fallback entirely. If the env var is missing, the app should show an error or operate without auth (depending on requirements):
```typescript
const API_KEY = import.meta.env.VITE_API_KEY || '';
```

### SEC-02: CORS Wildcard on All Proxy Routes [CRITICAL]

**File**: `nginx.conf:41,72,106,138,170,202,240`

```nginx
add_header 'Access-Control-Allow-Origin' '*' always;
```

Every proxy location block sets `Access-Control-Allow-Origin: *`, which allows any website to make authenticated requests to the backend APIs through this nginx proxy. Combined with `credentials: 'include'` used in several API modules (admin.ts, settings.ts, preferences.ts), this is particularly dangerous.

**Fix**: Restrict to the actual origin or remove CORS headers entirely (since the UI and API are served from the same nginx, CORS is unnecessary for same-origin requests):
```nginx
# Remove all CORS add_header directives from proxy locations
# Same-origin requests don't need CORS headers
```

### SEC-03: Missing Content Security Policy Header [HIGH]

**File**: `nginx.conf`

No `Content-Security-Policy` header is configured. This leaves the application vulnerable to XSS via injected scripts.

**Fix**: Add a CSP header in nginx.conf:
```nginx
add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self';" always;
```

### SEC-04: Deprecated X-XSS-Protection Header [LOW]

**File**: `nginx.conf:16`

```nginx
add_header X-XSS-Protection "1; mode=block" always;
```

`X-XSS-Protection` is deprecated and can introduce vulnerabilities in some browsers. Modern browsers use CSP instead.

**Fix**: Remove this header and rely on CSP (SEC-03).

### SEC-05: API Key Exposed in Docker Build Args [HIGH]

**File**: `Dockerfile:25-29`

```dockerfile
ARG VITE_API_KEY
ENV VITE_API_KEY=${VITE_API_KEY}
```

The API key is passed as a build argument and set as an environment variable. Build args are visible in the image layer history (`docker history`). Since it's a Vite env var, it gets inlined into the JS bundle at build time, so there's no avoiding bundle exposure, but the Docker layer history is an additional leak vector.

**Fix**: Use `--build-arg` at build time and add a cleanup stage that doesn't carry the ENV, or use a `.env` file mounted at build time rather than build args:
```dockerfile
# Remove the ENV line - ARG is sufficient for build-time only
ARG VITE_API_KEY
# Do NOT set ENV VITE_API_KEY - it persists in layers
```

### SEC-06: Path Traversal in Health Check URL [LOW]

**File**: `src/services/proactiveApi.ts:190`

```typescript
return fetchJSON<{ status: string }>('/api/proactive/../health');
```

The URL uses `..` path traversal. While nginx will normalize this, it's confusing and could behave unexpectedly with different reverse proxy configurations.

**Fix**: Use the correct direct path:
```typescript
return fetchJSON<{ status: string }>('/api/proactive/health');
```

### SEC-07: MessageContent Renders Unsanitized Markdown [MEDIUM]

**File**: `src/components/ha-agent/MessageContent.tsx:29-105`

The `MessageContent` component renders markdown from AI agent responses using `ReactMarkdown` with `rehype-highlight` but does not apply the `sanitizeMarkdown` utility from `src/utils/inputSanitizer.ts` before rendering.

**Fix**: Apply `sanitizeMarkdown` to content before passing to ReactMarkdown:
```typescript
import { sanitizeMarkdown } from '../../utils/inputSanitizer';
// ...
<ReactMarkdown>{sanitizeMarkdown(content)}</ReactMarkdown>
```

---

## 2. Code Quality & TypeScript

### CQ-01: Excessive `any` Types Throughout Codebase [HIGH]

**Files and examples**:
- `src/pages/Synergies.tsx:27` - `const [stats, setStats] = useState<any>(null)`
- `src/pages/Patterns.tsx:23` - `stats` typed as `any`
- `src/pages/Patterns.tsx:27` - `scheduleInfo` typed as `any`
- `src/pages/Patterns.tsx:434` - `(b as any).detected_at`
- `src/pages/HAAgentChat.tsx:59` - `blueprintContext` typed as `any`
- `src/pages/HAAgentChat.tsx:215` - `(location.state as any)`
- `src/pages/Synergies.tsx:79` - `catch (err: any)`
- `src/pages/ConversationalDashboard.tsx` - Multiple `catch (error: any)` blocks
- `src/types/index.ts:13,24,82,90,103` - `Record<string, any>` in type definitions
- `src/utils/deviceNameCache.ts:43` - `[string, any]` in forEach

**Impact**: Bypasses TypeScript's type safety, allowing runtime errors that could be caught at compile time. The ESLint config has `no-explicit-any` set to `'warn'` rather than `'error'`.

**Fix**: Define proper types for each use case. For pattern stats:
```typescript
interface PatternStats {
  total_patterns: number;
  by_type: Record<string, number>;
  unique_devices: number;
  avg_confidence: number;
}
```

Promote `no-explicit-any` to `'error'` in `eslint.config.js`.

### CQ-02: Massive Monolithic Components [HIGH]

**Files**:
- `src/pages/Synergies.tsx` - 500+ lines of state/handlers before JSX even begins
- `src/pages/Patterns.tsx` - 1427 lines
- `src/pages/HAAgentChat.tsx` - 1139 lines with 25+ useState calls
- `src/pages/ConversationalDashboard.tsx` - 883 lines
- `src/pages/Settings.tsx` - 797 lines (mostly duplicated model selector JSX)

**Impact**: Difficult to maintain, test, and review. State management becomes tangled. Re-renders affect the entire component tree.

**Fix**: Extract logical sections into sub-components. For HAAgentChat:
- `ChatMessageList` - Message rendering
- `ChatInput` - Input area with keyboard handling
- `ChatSidebar` - Conversation list
- `BlueprintContext` - Blueprint context display

For Settings:
- Extract the model selector dropdown into a `ModelSelector` component (the same `<select>` with 13 model options is repeated 4 times verbatim, lines 373-416, 418-460, 472-514, 516-558).

### CQ-03: Incomplete Feature Implementation (Delete Patterns) [MEDIUM]

**File**: `src/pages/Patterns.tsx:1074`

```typescript
// TODO: Implement API call to delete patterns
toast.success(`Pattern ${patternId} deleted`);
```

The delete button shows a success toast but does not actually delete anything. Users believe the pattern is deleted when it's not.

**Fix**: Either implement the API call or remove the delete button and add a disabled state with tooltip explaining the feature is not yet available.

### CQ-04: TODO Stubs Presented as Working Features [MEDIUM]

**Files**:
- `src/pages/Synergies.tsx:313-314` - `handleTestAutomation` shows "feature will be available soon"
- `src/pages/Synergies.tsx:341` - `handleScheduleAutomation` shows "feature will be available soon"

**Fix**: Remove these buttons from the UI until the features are implemented, or clearly mark them as "Coming Soon" with a disabled state.

### CQ-05: Dead Code Files [MEDIUM]

**Files**:
- `src/App-simple.tsx` - Simplified version of App.tsx, not imported anywhere
- `src/components/Navigation-fixed.tsx` - Older version of Navigation.tsx with different styling and fewer nav items. Exports a `Navigation` component that conflicts with the actual Navigation component.

**Fix**: Delete both files. They add confusion and maintenance burden.

### CQ-06: Deprecated `onKeyPress` Handler [LOW]

**File**: `src/pages/HAAgentChat.tsx:1015`

```typescript
onKeyPress={...}
```

`onKeyPress` is deprecated in React. It doesn't fire for some keys and has inconsistent behavior.

**Fix**: Replace with `onKeyDown`:
```typescript
onKeyDown={(e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    handleSend();
  }
}}
```

### CQ-07: Hardcoded Device Hash Map [MEDIUM]

**File**: `src/pages/ConversationalDashboard.tsx:69-74`

```typescript
const deviceNameMap: Record<string, string> = {
  '1ba44a8f25eab1397cb48dd7b743edcd': 'Sun',
  '71d5add6cf1f844d6f9bb34a3b58a09d': 'Living Room Light',
  // ...
};
```

This is a hardcoded mapping of device hashes to names specific to one user's Home Assistant instance. It cannot work for any other installation.

**Fix**: Remove the hardcoded map and use the `deviceNameCache` utility (`src/utils/deviceNameCache.ts`) or the device name resolution from the API (`api.getDeviceName()`).

### CQ-08: Duplicated `parseDeviceIds` Function [LOW]

**File**: `src/pages/Synergies.tsx:195-209` and `src/pages/Synergies.tsx:421-434`

Two nearly identical functions `parseDeviceIds` and `parseDeviceIdsForSearch` exist in the same file with the same logic.

**Fix**: Keep one function and use it for both purposes.

### CQ-09: Duplicated `downloadFile` Function [LOW]

**Files**: `src/utils/exportUtils.ts:70-80` and `src/utils/synergyExportUtils.ts:83-93`

Identical `downloadFile` function implemented in both files.

**Fix**: Export from one location and import in the other, or create a shared `fileUtils.ts`.

---

## 3. Architecture & Component Design

### ARCH-01: Massive API Code Duplication Across 10 Modules [HIGH]

The `withAuthHeaders` function is duplicated verbatim in **10 separate files**:
1. `src/services/api.ts`
2. `src/services/api-v2.ts`
3. `src/services/haAiAgentApi.ts`
4. `src/services/proactiveApi.ts`
5. `src/services/blueprintSuggestionsApi.ts`
6. `src/services/deviceApi.ts`
7. `src/services/deviceSuggestionsApi.ts`
8. `src/api/admin.ts`
9. `src/api/settings.ts`
10. `src/api/preferences.ts`

Additionally, `fetchJSON`/`handleResponse` functions are duplicated with slight variations across all files. The `APIError`/`ProactiveAPIError` class is duplicated with different names.

**Impact**: Bug fixes or auth changes must be applied to 10 files. Risk of inconsistency is high (and already exists -- some files include `credentials: 'include'`, others don't).

**Fix**: Create a shared `src/services/httpClient.ts`:
```typescript
// src/services/httpClient.ts
const API_KEY = import.meta.env.VITE_API_KEY || '';

export class APIError extends Error {
  constructor(public status: number, message: string, public details?: unknown) {
    super(message);
    this.name = 'APIError';
  }
}

export function withAuthHeaders(headers: HeadersInit = {}): HeadersInit { ... }
export async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> { ... }
```

Then refactor all 10 modules to import from the shared client.

### ARCH-02: Two Competing API Directory Structures [MEDIUM]

API modules are split between two directories with no clear distinction:
- `src/services/` - api.ts, api-v2.ts, haAiAgentApi.ts, proactiveApi.ts, etc.
- `src/api/` - admin.ts, settings.ts, preferences.ts

Both contain identical patterns (auth headers, response handling) but live in different directories.

**Fix**: Consolidate all API modules into `src/api/` (or `src/services/`) with the shared httpClient.

### ARCH-03: Inconsistent State Management Patterns [MEDIUM]

The codebase uses three different state management patterns simultaneously:
1. **Zustand** (`src/store.ts`) - For global state (darkMode, suggestions, loading)
2. **React Query** (`@tanstack/react-query`) - For server state in Settings, Admin, ProactiveSuggestions
3. **Raw useState + useEffect + fetch** - For server state in ConversationalDashboard, Synergies, Patterns, Deployed

Pages like ConversationalDashboard manually implement polling with `setInterval`, loading states, error states, and caching -- all of which React Query provides out of the box.

**Fix**: Migrate the remaining pages (ConversationalDashboard, Synergies, Patterns, Deployed) to use React Query for server state. This eliminates manual polling, loading/error state management, and provides automatic caching.

### ARCH-04: AFRAME Stub Triplicated [LOW]

The AFRAME global stub is defined in 3 places:
1. `index.html:8-14` - Inline script
2. `vite.config.ts:8-31` - Plugin that injects script
3. `src/main.tsx:5-16` - Runtime assignment

This exists to suppress errors from `react-force-graph` which depends on AFRAME/THREE.js.

**Fix**: Keep only one -- the `main.tsx` runtime assignment is sufficient since it runs before any component code. Remove from `index.html` and the Vite plugin.

### ARCH-05: Dual Design System Approach [MEDIUM]

The codebase uses two competing styling approaches:
1. **Tailwind CSS** - Used in most pages and components
2. **CSS Custom Properties design system** (`src/styles/design-system.css` + `src/utils/designSystem.ts`) - Used in Navigation, some components, and BlueprintSuggestions

Some components use `darkMode ? 'bg-gray-900' : 'bg-white'` ternaries, while others use `var(--bg-primary)`. The `designSystem.ts` file provides inline style helpers that compete with Tailwind classes.

**Fix**: Choose one approach. Since Tailwind is more widely used, consider configuring Tailwind's dark mode with `class` strategy and using it consistently. The CSS custom properties in `design-system.css` can still power the Tailwind theme.

---

## 4. Performance

### PERF-01: No Default React Query Options [HIGH]

**File**: `src/main.tsx:18`

```typescript
const queryClient = new QueryClient();
```

No default options are configured. This means:
- No `staleTime` (data is considered stale immediately, triggering refetches on every mount)
- Default `cacheTime` of 5 minutes (may be too short or too long depending on data)
- Default retry of 3 (may cause slow failures)

**Fix**:
```typescript
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30 * 1000, // 30 seconds
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});
```

### PERF-02: useEffect Dependency Causes Re-fetch Loop [MEDIUM]

**File**: `src/pages/ConversationalDashboard.tsx:255`

```typescript
useEffect(() => {
  // Sets up 30-second polling interval
  // ...
}, [selectedStatus]);
```

When `selectedStatus` changes (user clicks a tab), the entire polling interval is torn down and recreated. The `setInterval` callback also captures stale closure variables.

**Fix**: Use React Query's `refetchInterval` option instead of manual `setInterval`, or use `useRef` for the status value to avoid re-creating the interval.

### PERF-03: Synergies Page Has 19 useState Calls [MEDIUM]

**File**: `src/pages/Synergies.tsx:26-46`

The Synergies component has 19 separate `useState` declarations in a single component. Each state update triggers a re-render of the entire component tree.

**Fix**: Group related state into objects using `useReducer` or consolidate into fewer state variables:
```typescript
const [filters, setFilters] = useState({
  type: null,
  validated: null,
  minConfidence: 0,
  searchQuery: '',
  sortBy: 'recommended',
});
```

### PERF-04: DeviceNameCache Writes to localStorage on Every Single Set [LOW]

**File**: `src/utils/deviceNameCache.ts:90-98`

Every call to `set()` triggers `saveToStorage()` which serializes the entire cache to localStorage. During batch operations, this could be called hundreds of times.

**Fix**: Debounce the localStorage write:
```typescript
private scheduleSave(): void {
  clearTimeout(this.saveTimer);
  this.saveTimer = setTimeout(() => this.saveToStorage(), 1000);
}
```

---

## 5. API Design & Data Fetching

### API-01: Inconsistent Auth Patterns Across Modules [HIGH]

- `src/services/proactiveApi.ts` - Uses `getHeaders()` function with `Content-Type: application/json` always included
- `src/services/api.ts` - Uses `withAuthHeaders()` with separate Content-Type addition per call
- `src/api/admin.ts` - Uses `withAuthHeaders()` + `credentials: 'include'`
- `src/api/settings.ts` - Uses `withAuthHeaders()` + `credentials: 'include'`
- `src/services/haAiAgentApi.ts` - Uses `withAuthHeaders()` without `credentials: 'include'`

The `credentials: 'include'` flag is only used in `src/api/*.ts` files but not in `src/services/*.ts` files. This inconsistency means cookie-based auth works for some endpoints but not others.

**Fix**: Centralize in the shared httpClient (see ARCH-01) with a consistent approach to credentials.

### API-02: api.ts is a 887-Line Monolith [MEDIUM]

**File**: `src/services/api.ts`

Contains 30+ methods in a single object covering suggestions, patterns, synergies, device names, analysis, and more. Many methods return `Promise<any>`.

**Fix**: Split into domain-specific modules (already partially done with proactiveApi, deviceApi, etc.) and ensure all modules use the shared httpClient.

### API-03: Hardcoded Fallback URL in api-v2.ts [MEDIUM]

**File**: `src/services/api-v2.ts`

```typescript
validateYAML: async (yaml: string) => {
  // Uses hardcoded fallback URL: 'http://localhost:7242'
}
```

Hardcoded localhost URL will not work in production Docker environment.

**Fix**: Use the centralized API config from `src/config/api.ts` or environment variables.

### API-04: Mixed Data Fetching Approaches [MEDIUM]

Some pages use React Query (Settings, Admin, ProactiveSuggestions), while others use raw `useState` + `useEffect` + `fetch` (ConversationalDashboard, Synergies, Patterns). This creates inconsistent loading/error UX and duplicates caching logic.

**Fix**: Standardize on React Query for all server state management. See ARCH-03.

---

## 6. Error Handling

### ERR-01: Broad catch(error: any) Throughout [MEDIUM]

**Files**: ConversationalDashboard.tsx, Synergies.tsx, Deployed.tsx, HAAgentChat.tsx, and others

```typescript
} catch (error: any) {
  toast.error(error.message || 'Unknown error');
}
```

Catching `any` loses type information. Many catch blocks only show `error.message` which may not be user-friendly for API errors.

**Fix**: Use `unknown` type and narrow:
```typescript
} catch (error) {
  const message = error instanceof APIError
    ? error.message
    : 'An unexpected error occurred';
  toast.error(message);
}
```

### ERR-02: Error Boundary Doesn't Integrate with Store [LOW]

**File**: `src/components/PageErrorBoundary.tsx:144-146`

```typescript
const darkMode = typeof document !== 'undefined'
  ? document.documentElement.classList.contains('dark')
  : false;
```

The `PageErrorBoundaryWrapper` reads dark mode from the DOM instead of the Zustand store. This is because hooks can't be used in error boundaries, but the wrapper is a functional component that could use `useAppStore`.

**Fix**:
```typescript
export const PageErrorBoundaryWrapper: React.FC<...> = ({ children, pageName }) => {
  const { darkMode } = useAppStore();
  return (
    <PageErrorBoundary pageName={pageName} darkMode={darkMode}>
      {children}
    </PageErrorBoundary>
  );
};
```

### ERR-03: Missing Error Tracking Integration [LOW]

**File**: `src/components/PageErrorBoundary.tsx:39-42`

```typescript
// TODO: Send error to error tracking service (e.g., Sentry)
```

No error tracking service is integrated. Errors in production will only be visible in browser console.

**Fix**: Integrate Sentry or a similar error tracking service when moving toward production deployment.

---

## 7. Configuration & Environment

### CFG-01: API Base URL Inconsistency [MEDIUM]

Different modules use different API base paths:
- `src/api/admin.ts:48` - `/api/v1/admin`
- `src/api/settings.ts:55` - `/api` (with comment "Changed from /api/v1 to /api to match nginx proxy")
- `src/api/preferences.ts:30` - `/api/v1`
- `src/services/api.ts` - Uses `src/config/api.ts` config
- `src/services/proactiveApi.ts:23` - `/api/proactive/suggestions`

Some modules use `/api/v1`, others use `/api`, and they resolve differently through nginx.

**Fix**: Centralize all base URLs in `src/config/api.ts` and import them consistently.

### CFG-02: Centralized Config Not Used by All Modules [MEDIUM]

**File**: `src/config/api.ts` provides centralized configuration for 6 services, but only `src/services/api.ts` and `src/services/api-v2.ts` use it. All other API modules define their own base URLs.

**Fix**: Update all API modules to import from `src/config/api.ts`.

---

## 8. Docker & Deployment

### DOCK-01: Health Check Targets Root Instead of /health [LOW]

**File**: `Dockerfile:65-66`

```dockerfile
HEALTHCHECK ... CMD curl -f http://localhost/ || exit 1
```

The health check requests `/` which serves the full SPA HTML. The nginx config has a dedicated `/health` endpoint that's lighter weight.

**Fix**:
```dockerfile
HEALTHCHECK ... CMD curl -f http://localhost/health || exit 1
```

### DOCK-02: No Rate Limiting in nginx [MEDIUM]

**File**: `nginx.conf`

No rate limiting is configured for any proxy location. A single client could overwhelm backend services.

**Fix**: Add rate limiting:
```nginx
limit_req_zone $binary_remote_addr zone=api:10m rate=30r/s;

location ~* ^/api/(.*) {
    limit_req zone=api burst=50 nodelay;
    # ... existing config
}
```

### DOCK-03: Static Asset Cache Headers Override Security Headers [LOW]

**File**: `nginx.conf:256-259`

```nginx
location ~* \.(js|css|png|jpg|...)$ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

When `add_header` is used in a location block, it overrides headers from the parent context. This means the security headers (X-Frame-Options, X-Content-Type-Options) are NOT applied to static assets.

**Fix**: Repeat security headers in the static assets location block, or use `map` with `add_header` in the `http` context.

---

## 9. Dependencies

### DEP-01: @types Packages in Dependencies Instead of devDependencies [MEDIUM]

**File**: `package.json:24-25`

```json
"dependencies": {
  "@types/canvas-confetti": "^1.9.0",
  "@types/react-syntax-highlighter": "^15.5.13",
}
```

Type definition packages should be in `devDependencies` since they're only needed at compile time, not runtime.

**Fix**: Move to devDependencies:
```bash
npm install --save-dev @types/canvas-confetti @types/react-syntax-highlighter
```

### DEP-02: No Lock File Pinning Verification [LOW]

No evidence of `npm ci` being used in Docker builds. `package.json` uses caret ranges (e.g., `"react": "^18.3.1"`) which could lead to different dependency versions between builds.

The Dockerfile uses `npm install --prefer-offline --no-audit`, not `npm ci`.

**Fix**: Replace `npm install` with `npm ci` in the Dockerfile, and ensure `package-lock.json` is copied:
```dockerfile
COPY package.json package-lock.json ./
RUN npm ci --prefer-offline --no-audit
```

---

## 10. Testing

### TEST-01: Very Low Test Coverage [HIGH]

Only **7 test files** exist for a codebase with 60+ source files:
1. `src/store/__tests__/store.test.ts` - Store tests (good coverage)
2. `src/utils/__tests__/inputSanitizer.test.ts` - Sanitizer tests (thorough)
3. `src/utils/__tests__/proposalParser.test.ts` - Parser tests
4. `src/components/__tests__/Navigation.test.tsx` - Navigation test
5. `src/components/__tests__/LoadingSpinner.test.tsx` - LoadingSpinner test
6. `src/components/ha-agent/__tests__/AutomationPreview.test.tsx` - AutomationPreview test
7. `src/pages/__tests__/HAAgentChat.originalPrompt.test.tsx` - HAAgentChat test

**Missing test coverage**:
- All API/service modules (0 tests for 10 modules)
- All page components except HAAgentChat (ConversationalDashboard, Synergies, Patterns, Settings, Admin, etc.)
- Hooks (useConversationV2, useKeyboardShortcuts, useOptimisticUpdates)
- Context (SelectionContext)
- Utility modules (exportUtils, synergyExportUtils, deviceNameCache, performanceTracker)
- 40+ component files have no tests

**Fix**: Prioritize tests for:
1. API client modules (mock fetch, verify request construction and error handling)
2. Critical page components (ConversationalDashboard, HAAgentChat)
3. Custom hooks
4. Remaining utility modules

### TEST-02: Test Setup is Minimal [LOW]

**File**: `src/test/setup.ts`

```typescript
import '@testing-library/jest-dom';
```

The test setup only imports jest-dom matchers. No global mocks for `fetch`, `localStorage`, `IntersectionObserver`, `matchMedia`, or other browser APIs that components depend on.

**Fix**: Add common mocks to the test setup:
```typescript
import '@testing-library/jest-dom';

// Mock fetch globally
global.fetch = vi.fn();

// Mock IntersectionObserver
global.IntersectionObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}));
```

---

## 11. Logging & Observability

### LOG-01: Excessive console.log Debug Statements [HIGH]

Debug `console.log` statements are scattered throughout production code:

- `src/pages/ConversationalDashboard.tsx` - ~15 console.log statements
- `src/pages/Deployed.tsx` - ~20 console.log/error statements
- `src/pages/HAAgentChat.tsx` - Multiple console.log statements
- `src/pages/Synergies.tsx:276-281` - Logs automation details
- `src/pages/Synergies.tsx:315` - Logs test automation info
- `src/utils/performanceTracker.ts:92` - Always logs performance reports

These pollute the browser console in production and may expose sensitive data (API responses, device IDs, etc.).

**Fix**:
1. Remove all debug `console.log` statements
2. Replace with a structured logger that can be disabled in production:
```typescript
const logger = {
  debug: (...args: unknown[]) => {
    if (import.meta.env.DEV) console.log(...args);
  },
  error: console.error, // Always log errors
};
```

### LOG-02: No Structured Error Logging [MEDIUM]

Errors are caught and displayed as toasts but not logged to any structured logging system. Failed API calls, render errors, and network failures are only visible in the browser console.

**Fix**: Integrate a frontend error tracking service (Sentry, LogRocket, etc.) for production visibility.

---

## 12. Frontend-Specific

### FE-01: Inconsistent Dark Mode Implementation [MEDIUM]

Three different dark mode approaches are used:
1. **Tailwind ternary**: `darkMode ? 'bg-gray-900' : 'bg-white'` - Used in most pages
2. **CSS custom properties**: `bg-[var(--bg-primary)]` - Used in Navigation, design-system.css
3. **Tailwind dark: prefix**: `dark:bg-gray-900` - Used in a few places (e.g., status badges in Admin.tsx)

The Tailwind `dark:` prefix approach requires a `dark` class on the HTML root element, which isn't consistently applied.

**Fix**: Choose one approach. The ternary approach with Zustand darkMode state is the most prevalent. Standardize on it and remove the CSS custom property approach where it conflicts.

### FE-02: No Loading Skeleton for Initial App Load [LOW]

**File**: `index.html`

The app shows a blank white page while the JS bundle loads. No loading indicator or skeleton screen is provided.

**Fix**: Add a lightweight CSS loading indicator in `index.html` that gets replaced when React mounts.

### FE-03: No Accessibility Labels on Several Interactive Elements [MEDIUM]

While the Navigation component has good ARIA attributes (`aria-label`, `aria-current`), several other interactive elements lack accessibility:

- `src/pages/Settings.tsx` - Checkbox inputs have no associated `id`/`htmlFor` labels
- `src/pages/Admin.tsx` - Delete buttons use emoji only (no text alternative)
- `src/pages/Synergies.tsx` - Filter buttons have no aria-label
- `src/pages/ConversationalDashboard.tsx` - Status tabs lack `role="tablist"` and `role="tab"`

**Fix**: Add `aria-label` attributes to all interactive elements that lack visible text labels. Use semantic HTML roles for tab interfaces.

### FE-04: `window.confirm` and `window.prompt` Used for Confirmations [LOW]

**Files**:
- `src/pages/Settings.tsx:110` - `confirm('Reset all settings?')`
- `src/pages/Admin.tsx:397-400` - `window.confirm('Delete training runs...')`
- `src/pages/Synergies.tsx:247-253` - `window.confirm('Create automation...')`
- `src/pages/Synergies.tsx:326` - `window.prompt('Schedule time...')`

Native browser dialogs block the main thread, cannot be styled, and provide a poor UX.

**Fix**: Replace with modal components (the codebase already has modal patterns in `ha-agent/ClearChatModal.tsx` and `ha-agent/DeleteConversationModal.tsx`).

### FE-05: Duplicated Model Selector JSX in Settings [LOW]

**File**: `src/pages/Settings.tsx:373-558`

The exact same `<select>` element with 13 model options is repeated **4 times** (suggestion model 1, suggestion model 2, YAML model 1, YAML model 2). Each is 45 lines of JSX.

**Fix**: Extract into a `<ModelSelector value={} onChange={} />` component:
```typescript
const ModelSelector: React.FC<{ value: string; onChange: (model: string) => void }> = ...
```

---

## 13. Documentation

### DOC-01: No README for the Service [LOW]

The `ai-automation-ui` directory has no `README.md` explaining:
- How to set up the development environment
- Required environment variables
- How to run tests
- Architecture overview
- Deployment instructions

### DOC-02: No JSDoc on Public API Functions [LOW]

While some files have good header comments, many exported functions in API modules lack JSDoc documentation for parameters and return types.

---

## 14. Prioritized Action Plan

### Phase 1: Critical Security Fixes (Immediate)

| # | Finding | Severity | Effort | Files |
|---|---------|----------|--------|-------|
| 1 | SEC-01: Remove hardcoded API key fallbacks | CRITICAL | Low | 4 files |
| 2 | SEC-02: Remove CORS wildcard headers | CRITICAL | Low | nginx.conf |
| 3 | SEC-03: Add Content Security Policy header | HIGH | Low | nginx.conf |
| 4 | SEC-05: Remove ENV from Dockerfile | HIGH | Low | Dockerfile |

### Phase 2: High-Impact Architecture (1-2 weeks)

| # | Finding | Severity | Effort | Files |
|---|---------|----------|--------|-------|
| 5 | ARCH-01: Create shared httpClient, eliminate API duplication | HIGH | Medium | 10+ files |
| 6 | LOG-01: Remove all console.log debug statements | HIGH | Medium | 5+ files |
| 7 | PERF-01: Configure QueryClient defaults | HIGH | Low | main.tsx |
| 8 | CQ-02: Break up largest components (HAAgentChat, Patterns) | HIGH | High | 4 files |
| 9 | TEST-01: Add tests for API modules and critical pages | HIGH | High | New files |

### Phase 3: Medium-Priority Improvements (2-4 weeks)

| # | Finding | Severity | Effort | Files |
|---|---------|----------|--------|-------|
| 10 | CQ-01: Replace `any` types with proper types | HIGH | Medium | 10+ files |
| 11 | API-01: Standardize auth patterns across modules | HIGH | Medium | 10 files |
| 12 | ARCH-03: Migrate remaining pages to React Query | MEDIUM | Medium | 4 pages |
| 13 | CFG-01/02: Centralize all API base URLs | MEDIUM | Low | 8 files |
| 14 | CQ-03: Fix or remove Pattern delete | MEDIUM | Low | Patterns.tsx |
| 15 | CQ-04: Remove TODO feature stubs from UI | MEDIUM | Low | Synergies.tsx |
| 16 | CQ-05: Delete dead code files | MEDIUM | Low | 2 files |
| 17 | SEC-07: Apply markdown sanitization | MEDIUM | Low | MessageContent.tsx |
| 18 | DOCK-02: Add nginx rate limiting | MEDIUM | Low | nginx.conf |
| 19 | ARCH-05: Consolidate design system approach | MEDIUM | Medium | Multiple |
| 20 | FE-01: Standardize dark mode implementation | MEDIUM | Medium | Multiple |
| 21 | FE-03: Add accessibility labels | MEDIUM | Medium | Multiple |
| 22 | DEP-01: Move @types to devDependencies | MEDIUM | Low | package.json |

### Phase 4: Low-Priority Polish (4+ weeks)

| # | Finding | Severity | Effort | Files |
|---|---------|----------|--------|-------|
| 23 | ARCH-04: Remove duplicate AFRAME stubs | LOW | Low | 3 files |
| 24 | CQ-06: Replace deprecated onKeyPress | LOW | Low | HAAgentChat.tsx |
| 25 | SEC-04: Remove deprecated X-XSS-Protection | LOW | Low | nginx.conf |
| 26 | SEC-06: Fix path traversal in health URL | LOW | Low | proactiveApi.ts |
| 27 | DOCK-01: Fix health check target | LOW | Low | Dockerfile |
| 28 | DOCK-03: Fix static asset header override | LOW | Low | nginx.conf |
| 29 | ERR-02: Fix error boundary dark mode | LOW | Low | PageErrorBoundary.tsx |
| 30 | FE-04: Replace window.confirm/prompt | LOW | Medium | 4 files |
| 31 | FE-05: Extract ModelSelector component | LOW | Low | Settings.tsx |
| 32 | PERF-04: Debounce deviceNameCache writes | LOW | Low | deviceNameCache.ts |
| 33 | DEP-02: Use npm ci in Dockerfile | LOW | Low | Dockerfile |

---

## Summary Statistics

| Severity | Count |
|----------|-------|
| CRITICAL | 2 |
| HIGH | 9 |
| MEDIUM | 14 |
| LOW | 8 |
| **Total** | **33** |

| Dimension | Findings |
|-----------|----------|
| Security | 7 |
| Code Quality | 9 |
| Architecture | 5 |
| Performance | 4 |
| API Design | 4 |
| Error Handling | 3 |
| Configuration | 2 |
| Docker/Deployment | 3 |
| Dependencies | 2 |
| Testing | 2 |
| Logging | 2 |
| Frontend | 5 |
| Documentation | 2 |

### Strengths Noted

- **Good input sanitization utilities** (`src/utils/inputSanitizer.ts`) with thorough test coverage
- **Well-structured type definitions** (`src/types/index.ts`, `src/types/proactive.ts`)
- **Good use of React Query** where implemented (Settings, Admin pages)
- **Proper error boundaries** with development-only error details
- **Good accessibility** on Navigation component (aria-labels, aria-current)
- **Solid Zustand store** with localStorage persistence and error handling
- **Good skeleton loading components** (SkeletonCard, SkeletonStats, SkeletonFilter)
- **Comprehensive device name caching** with batch processing and TTL
- **Proper Docker multi-stage build** with build cache optimization
