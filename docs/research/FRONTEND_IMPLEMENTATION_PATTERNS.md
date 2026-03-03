# Frontend Implementation Patterns & Code Examples

**Created:** 2026-02-27
**Based on:** Research in `2026-frontend-tech-stack-research.md`
**Audience:** Implementation teams for each epic

---

## Table of Contents

1. [React 19 Migration](#react-19-migration)
2. [Vite 7 Migration](#vite-7-migration)
3. [Tailwind CSS 4 Migration](#tailwind-css-4-migration)
4. [Streamlit Performance](#streamlit-performance)
5. [Testing Patterns](#testing-patterns)
6. [Bundle Optimization](#bundle-optimization)
7. [Security Patterns](#security-patterns)

---

## React 19 Migration

### Before (React 18)

```typescript
// src/components/SuggestionForm.tsx
import React, { useState } from 'react';

export const SuggestionForm: React.FC<{ onSubmit: (text: string) => void }> = ({ onSubmit }) => {
  const [text, setText] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      onSubmit(text);
      setText('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <input value={text} onChange={(e) => setText(e.target.value)} />
      {error && <div role="alert">{error}</div>}
      <button type="submit">Add Suggestion</button>
    </form>
  );
};
```

### After (React 19)

```typescript
// src/components/SuggestionForm.tsx
import { useState } from 'react';

interface Props {
  onSubmit: (text: string) => void;
}

export function SuggestionForm({ onSubmit }: Props) {
  const [text, setText] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      onSubmit(text);
      setText('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <input
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Enter suggestion"
      />
      {error && <div role="alert">{error}</div>}
      <button type="submit">Add Suggestion</button>
    </form>
  );
}
```

**Changes:**
- Removed `React.FC<>` (deprecated in React 19)
- Changed to regular function component with explicit Props interface
- No functional changes, just modernized syntax

### React 19 Form Hook Pattern

```typescript
// src/hooks/useFormSubmit.ts (NEW — React 19)
import { useActionState } from 'react';

interface FormState {
  message: string;
  errors?: Record<string, string>;
}

export function useFormSubmit(action: (formData: FormData) => Promise<FormState>) {
  const [state, formAction, isPending] = useActionState(action, { message: '' });
  return { state, formAction, isPending };
}

// Usage in component:
export function SuggestionForm() {
  const { state, formAction, isPending } = useFormSubmit(async (formData) => {
    const text = formData.get('suggestion') as string;
    const response = await fetch('/api/suggestions', {
      method: 'POST',
      body: JSON.stringify({ text }),
    });
    const data = await response.json();
    return data as FormState;
  });

  return (
    <form action={formAction}>
      <input name="suggestion" placeholder="Enter suggestion" />
      {state.message && <p>{state.message}</p>}
      {state.errors?.['suggestion'] && <p role="alert">{state.errors['suggestion']}</p>}
      <button disabled={isPending}>
        {isPending ? 'Submitting...' : 'Add'}
      </button>
    </form>
  );
}
```

### Migration Checklist

```
□ Update React version in package.json
□ Run npm install
□ Run tsc --noEmit to find type errors
□ Replace React.FC with function components
□ Update ESLint config (disable react/fc-deprecated)
□ Test form components for hook changes
□ Run npm run test:run
□ Run npm run test:e2e:smoke
□ Manual testing of critical user flows
□ Update documentation with new patterns
```

---

## Vite 7 Migration

### Before (Vite 6)

**vite.config.ts:**
```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3001,
    host: '0.0.0.0',
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
  },
});
```

**.env:**
```
VITE_API_URL=http://localhost:8006
VITE_ADMIN_API_URL=http://localhost:8004
```

### After (Vite 7)

**vite.config.ts:** (mostly unchanged)
```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3001,
    host: '0.0.0.0',
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
  },
  // No changes needed unless using custom plugins
});
```

**.env:** (IMPORTANT: All VITE_* vars must be explicitly declared)
```
# Core API endpoints
VITE_API_URL=http://localhost:8006
VITE_ADMIN_API_URL=http://localhost:8004

# Note: Never add VITE_API_KEY or secrets here!
```

### Environment Variable Usage Pattern

```typescript
// src/config.ts
export const config = {
  apiUrl: import.meta.env.VITE_API_URL || 'http://localhost:8006',
  adminApiUrl: import.meta.env.VITE_ADMIN_API_URL || 'http://localhost:8004',
  isDev: import.meta.env.DEV,
  isProd: import.meta.env.PROD,
  mode: import.meta.env.MODE,
};

// Usage in API client:
export const apiClient = axios.create({
  baseURL: config.apiUrl,
  withCredentials: true,  // Include cookies (secure auth)
});
```

### Migration Checklist

```
□ Audit .env files for all VITE_* variables
□ Ensure no secrets in .env (use .env.local, in .gitignore)
□ Update vite version: npm install vite@^7.0.0
□ Verify postcss.config.js has autoprefixer
□ Test dev server: npm run dev
□ Test build: npm run build
□ Verify env vars load correctly in both dev and prod
□ Run tests to confirm no regressions
```

---

## Tailwind CSS 4 Migration

### Before (Tailwind 3)

**tailwind.config.ts:**
```typescript
import type { Config } from 'tailwindcss';

export default {
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        teal: '#14b8a6',
        gold: '#d4a847',
      },
      spacing: {
        sm: '0.5rem',
        md: '1rem',
        lg: '1.5rem',
      },
    },
  },
  plugins: [],
} satisfies Config;
```

**src/index.css:**
```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

### After (Tailwind 4)

**src/input.css:** (NEW)
```css
@import "tailwindcss";

@theme {
  --color-teal: #14b8a6;
  --color-gold: #d4a847;
  --spacing-sm: 0.5rem;
  --spacing-md: 1rem;
  --spacing-lg: 1.5rem;
}

@source "../src/**/*.{ts,tsx}";

/* Custom components */
@layer components {
  .btn {
    @apply px-4 py-2 rounded-lg font-semibold transition-colors;
  }
  .btn-primary {
    @apply btn bg-teal text-white hover:bg-teal/90;
  }
}
```

**tailwind.config.ts:** (DELETE)
```
// File deleted — config now in CSS via @theme
```

**src/index.css:** (SIMPLIFY)
```css
@import "./input.css";
```

### Migration Checklist

```
□ Review current tailwind.config.ts
□ Search for deprecated color names (warm-gray → stone)
□ Create src/input.css with @theme directives
□ Move all theme extensions to CSS
□ Copy @layer components to input.css
□ Update package.json: tailwindcss@^4.0.0
□ Delete tailwind.config.ts
□ Test build: npm run build
□ Visual regression testing
□ Compare bundle sizes
□ Run full test suite
```

---

## Streamlit Performance

### Before (Blocking with `time.sleep()`)

**src/pages/real_time_monitoring.py:**
```python
import streamlit as st
import time
from src.services.jaeger_client import JaegerClient

st.set_page_config(page_title="Live Monitoring", layout="wide")

def show():
    st.title("📡 Live Monitoring")

    # PROBLEM: This blocks the entire UI!
    while True:
        jaeger = JaegerClient(st.session_state.config['jaeger_api_url'])
        services = jaeger.get_services()

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Active Services", len(services))
        with col2:
            st.metric("Total Traces", jaeger.get_trace_count())

        # BLOCKS UI FOR 5 SECONDS!
        time.sleep(5)
        st.rerun()
```

### After (Non-blocking with `@st.fragment`)

**src/pages/real_time_monitoring.py:**
```python
import streamlit as st
from src.services.jaeger_client import JaegerClient

st.set_page_config(page_title="Live Monitoring", layout="wide")

@st.fragment(run_every=5)  # Rerun every 5 seconds — no blocking!
def live_metrics():
    """Fragment only reruns this section, not entire page."""
    jaeger = JaegerClient(st.session_state.config['jaeger_api_url'])
    services = jaeger.get_services()

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Active Services", len(services))
    with col2:
        st.metric("Total Traces", jaeger.get_trace_count())

@st.fragment
def user_controls():
    """Non-refreshing controls section."""
    if st.button("Refresh Now"):
        st.rerun()

def show():
    st.title("📡 Live Monitoring")

    # Static content section (doesn't rerun)
    st.info("This dashboard updates automatically every 5 seconds.")

    # Live metrics section (reruns automatically)
    live_metrics()

    # User controls (doesn't rerun unless clicked)
    user_controls()
```

### Caching Pattern for Expensive Queries

```python
import streamlit as st
from src.services.influxdb_client import InfluxDBClient

@st.cache_data(ttl=60)  # Cache for 60 seconds
def fetch_service_metrics(service_name: str) -> dict:
    """Fetch metrics — cached to avoid expensive queries."""
    influx = InfluxDBClient(st.session_state.config['influxdb_url'])
    return influx.query(f'SELECT * FROM {service_name} WHERE time > now() - 1h')

@st.fragment(run_every=10)  # Rerun every 10 seconds
def service_performance():
    """Performance metrics with caching."""
    service_name = st.selectbox("Service", ["data-api", "admin-api", "health-dashboard"])
    metrics = fetch_service_metrics(service_name)
    st.json(metrics)
```

### Migration Checklist

```
□ Upgrade Streamlit: pip install --upgrade streamlit>=1.37.0
□ Find all time.sleep() calls: grep -n "time.sleep" src/pages/*.py
□ Identify refresh rates needed (5s, 10s, 30s, etc.)
□ Wrap live data sections in @st.fragment(run_every=N)
□ Remove time.sleep() calls
□ Add @st.cache_data() for expensive queries
□ Test dashboard responsiveness
□ Manual testing: verify smooth updates, no frozen UI
```

---

## Testing Patterns

### Unit Test Pattern (React Testing Library)

```typescript
// src/components/__tests__/IdeaCard.test.tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { IdeaCard } from '../IdeaCard';

describe('IdeaCard', () => {
  const mockIdea = {
    id: '1',
    title: 'Auto-adjust thermostat',
    description: 'Lower temperature at night',
  };

  test('renders idea content', () => {
    render(<IdeaCard idea={mockIdea} />);
    expect(screen.getByText('Auto-adjust thermostat')).toBeInTheDocument();
    expect(screen.getByText('Lower temperature at night')).toBeInTheDocument();
  });

  test('calls onCreate when button clicked', async () => {
    const user = userEvent.setup();
    const onCreate = vi.fn();

    render(<IdeaCard idea={mockIdea} onCreate={onCreate} />);

    const button = screen.getByRole('button', { name: /create/i });
    await user.click(button);

    expect(onCreate).toHaveBeenCalledWith(mockIdea.id);
  });

  test('shows loading state while creating', async () => {
    const user = userEvent.setup();
    const onCreate = vi.fn(() => new Promise(resolve => setTimeout(resolve, 100)));

    render(<IdeaCard idea={mockIdea} onCreate={onCreate} />);

    const button = screen.getByRole('button', { name: /create/i });
    await user.click(button);

    expect(button).toHaveAttribute('disabled');
    expect(screen.getByText(/creating/i)).toBeInTheDocument();
  });
});
```

### Integration Test Pattern (with MSW)

```typescript
// src/__tests__/integration/suggestions.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { setupServer } from 'msw/node';
import { http, HttpResponse } from 'msw';
import { SuggestionForm } from '../../components/SuggestionForm';

const mockServer = setupServer(
  http.post('/api/suggestions', async ({ request }) => {
    const body = await request.json() as { text: string };

    if (!body.text) {
      return HttpResponse.json(
        { error: 'Text is required' },
        { status: 400 }
      );
    }

    return HttpResponse.json(
      { id: '1', text: body.text, createdAt: new Date() },
      { status: 201 }
    );
  })
);

beforeAll(() => mockServer.listen());
afterEach(() => mockServer.resetHandlers());
afterAll(() => mockServer.close());

test('creates suggestion and shows success', async () => {
  const user = userEvent.setup();
  render(<SuggestionForm />);

  const input = screen.getByPlaceholderText('Enter suggestion');
  const button = screen.getByRole('button', { name: /add/i });

  await user.type(input, 'Auto-adjust thermostat');
  await user.click(button);

  // Wait for success message
  const successMessage = await screen.findByText(/success|created/i);
  expect(successMessage).toBeInTheDocument();

  // Input should be cleared
  expect(input).toHaveValue('');
});

test('shows error when submission fails', async () => {
  const user = userEvent.setup();

  // Override handler for this test
  mockServer.use(
    http.post('/api/suggestions', () => {
      return HttpResponse.json(
        { error: 'Server error' },
        { status: 500 }
      );
    })
  );

  render(<SuggestionForm />);

  const input = screen.getByPlaceholderText('Enter suggestion');
  const button = screen.getByRole('button', { name: /add/i });

  await user.type(input, 'Test');
  await user.click(button);

  const errorMessage = await screen.findByText(/error|failed/i);
  expect(errorMessage).toBeInTheDocument();
});
```

### E2E Test Pattern (Playwright)

```typescript
// tests/e2e/ai-automation-ui/suggestions.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Suggestions Flow @smoke', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('http://localhost:3001');
  });

  test('[smoke] Navigate to Ideas page', async ({ page }) => {
    await page.click('[data-testid="nav-ideas"]');
    await expect(page).toHaveURL(/\/ideas/);
    await expect(page.locator('h1')).toContainText('Ideas');
  });

  test('[smoke] Create new suggestion', async ({ page }) => {
    await page.click('[data-testid="nav-ideas"]');

    const input = page.locator('[placeholder="Enter suggestion"]');
    await input.fill('Auto-adjust thermostat at night');

    const button = page.locator('button:has-text("Add Suggestion")');
    await button.click();

    // Wait for success feedback
    await expect(page.locator('text=Suggestion created')).toBeVisible();

    // Verify item appears in list
    await expect(
      page.locator('text=Auto-adjust thermostat at night')
    ).toBeVisible();
  });
});

test.describe('Suggestions Flow @full', () => {
  test('[full] Create and configure automation', async ({ page }) => {
    // Multi-step workflow
    await page.goto('http://localhost:3001');

    // Create suggestion
    await page.click('[data-testid="nav-ideas"]');
    const input = page.locator('[placeholder="Enter suggestion"]');
    await input.fill('Temperature automation');
    await page.locator('button:has-text("Add")').click();

    // Verify creation
    await expect(page.locator('text=Temperature automation')).toBeVisible();

    // Configure (if needed)
    await page.locator('[data-testid="configure"]').click();
    await page.locator('[placeholder="conditions"]').fill('after 6pm');
    await page.locator('button:has-text("Save")').click();

    // Deploy
    await page.locator('[data-testid="deploy"]').click();
    await expect(page.locator('text=Deployed')).toBeVisible();
  });
});
```

**Chat page (HAAgentChat):** Use `data-testid="message-input"`, `data-testid="send-button"`, `data-testid="chat-message"` for message bubbles, and `data-testid="chat-loading"` for loading/thinking state. See `tests/e2e/ai-automation-ui/` for chat and conversation-flow specs.

### vitest Configuration

**vitest.config.ts:**
```typescript
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'happy-dom',
    setupFiles: [],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      lines: 75,
      statements: 75,
      branches: 75,
      functions: 75,
    },
  },
});
```

---

## Bundle Optimization

### Code Splitting Configuration

**vite.config.ts:**
```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { visualizer } from 'rollup-plugin-visualizer';

export default defineConfig({
  plugins: [
    react(),
    visualizer({
      open: true,  // Open stats.html after build
    }),
  ],
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          // Split vendor libraries
          'vendor-react': ['react', 'react-dom'],
          'vendor-ui': ['lucide-react', '@radix-ui/react-accordion'],
          'vendor-query': ['@tanstack/react-query'],
          'vendor-other': ['zustand', 'framer-motion'],
        },
      },
    },
  },
});
```

### Lazy Loading + Suspense Pattern

```typescript
// src/App.tsx
import { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';

const Ideas = lazy(() => import('./pages/Ideas'));
const Insights = lazy(() => import('./pages/Insights'));
const Dashboard = lazy(() => import('./pages/Dashboard'));

function LoadingSpinner() {
  return <div className="flex items-center justify-center p-8">Loading...</div>;
}

export function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<LoadingSpinner />}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/ideas" element={<Ideas />} />
          <Route path="/insights" element={<Insights />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}
```

### Dependency Analysis Script

```bash
#!/bin/bash
# analyze-bundle.sh

echo "Building and analyzing bundle..."
npm run build

echo ""
echo "Bundle size analysis:"
du -sh dist/
du -sh dist/assets/*

echo ""
echo "Checking for unused dependencies..."
npm ls --depth=0

echo ""
echo "For detailed analysis, open dist/stats.html in browser"
```

---

## Security Patterns

### Secure API Client Pattern

```typescript
// src/services/apiClient.ts
import axios from 'axios';
import { config } from '../config';

// CORRECT: No secrets in client
const apiClient = axios.create({
  baseURL: config.apiUrl,
  withCredentials: true,  // Browser includes HttpOnly cookies
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor (add token from secure cookie if available)
apiClient.interceptors.request.use(
  (request) => {
    // Don't add Authorization header here — let the cookie handle it
    // Server-side secret key is used by backend
    return request;
  },
  (error) => Promise.reject(error)
);

export default apiClient;
```

### Secure Environment Variables

**.env (public — no secrets):**
```
VITE_API_URL=https://api.homeiq.local
VITE_ADMIN_API_URL=https://admin.homeiq.local
```

**.env.local (private — in .gitignore):**
```
# Only for local development
# Never commit this file!
# CI/CD sets these as secrets
```

**.gitignore:**
```
.env.local
.env.*.local
.env.test
```

### Pre-commit Hook (Security Check)

**.husky/pre-commit:**
```bash
#!/bin/sh

# Prevent committing files with exposed secrets
echo "🔒 Checking for exposed API keys..."

# Check for VITE_.*KEY pattern
if grep -r "VITE_.*KEY" .env 2>/dev/null; then
    echo "❌ ERROR: API key found in .env file!"
    echo "Never commit secrets to version control."
    echo "Use .env.local (in .gitignore) for local development."
    exit 1
fi

# Check for common secret patterns in staged files
if git diff --cached | grep -E "(api[_-]?key|secret|password|token)" -i; then
    echo "⚠️  WARNING: Possible secrets in staged files"
    echo "Review carefully before committing."
fi

echo "✓ Security checks passed"
```

### API Gateway Pattern (Backend)

```python
# domains/core-platform/admin-api/src/api/proxy.py
from fastapi import APIRouter, Request, Depends
from typing import Any
import httpx
import os

router = APIRouter(prefix="/api/proxy", tags=["proxy"])

async def require_auth(request: Request) -> None:
    """Verify user is authenticated (via session/cookie)."""
    # Implement your auth verification
    pass

@router.get("/{path:path}")
async def proxy_get(path: str, _: None = Depends(require_auth)) -> Any:
    """
    Proxy requests to backend services without exposing secrets.

    Frontend makes request to /api/proxy/data
    Backend uses internal secret key to call data-api:8006/data
    """
    # Read secret server-side
    data_api_key = os.environ.get("DATA_API_KEY")
    data_api_url = os.environ.get("DATA_API_URL", "http://data-api:8006")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{data_api_url}/{path}",
            headers={"Authorization": f"Bearer {data_api_key}"},
        )

    return response.json()
```

---

## Quick Reference

### File Changes Summary

```
React 19 Migration:
  ├─ package.json: react ^18 → ^19, @types/react ^18 → ^19
  ├─ **/*.tsx: Remove React.FC<>, use function components
  ├─ Hooks: Update useFormStatus, useFormState patterns
  └─ ESLint: Disable react/fc-deprecated rule

Vite 7 Migration:
  ├─ package.json: vite ^6 → ^7
  ├─ .env: Ensure all VITE_* vars declared
  ├─ vite.config.ts: Usually no changes needed
  └─ postcss.config.js: Verify autoprefixer present

Tailwind 4 Migration:
  ├─ src/input.css: NEW — @theme directives
  ├─ src/index.css: SIMPLIFY — import input.css only
  ├─ tailwind.config.ts: DELETE
  └─ package.json: tailwindcss ^3 → ^4

Streamlit Performance:
  ├─ requirements.txt: streamlit >=1.37.0
  ├─ src/pages/*.py: Add @st.fragment(run_every=N)
  ├─ src/pages/*.py: Remove time.sleep() calls
  └─ src/pages/*.py: Add @st.cache_data(ttl=60)

Testing:
  ├─ vitest.config.ts: NEW — coverage config
  ├─ src/**/__tests__/*.test.tsx: NEW unit tests
  ├─ src/__tests__/integration/*.test.tsx: NEW integration
  ├─ vite.config.ts: Add @vitejs/plugin-html
  └─ src/setupTests.ts: NEW — test configuration

Bundle Optimization:
  ├─ package.json: npm install -D vite-plugin-visualizer
  ├─ vite.config.ts: Add visualizer plugin, manualChunks
  ├─ src/App.tsx: Add Suspense + lazy() imports
  └─ src/index.css: Verify no unused imports

Security:
  ├─ .env: NO secrets (only URLs)
  ├─ .gitignore: Add .env.local
  ├─ .husky/pre-commit: NEW — security checks
  └─ src/services/apiClient.ts: REVIEW — no hard-coded keys
```

---

## Testing Checklist

Before considering each migration complete:

```
React 19:
  □ tsc --noEmit passes
  □ npm run test:run passes (all unit tests)
  □ npm run test:e2e:smoke passes
  □ Manual testing of forms and interactions
  □ No console errors or warnings
  □ npm run lint passes

Vite 7:
  □ npm run dev starts without errors
  □ npm run build succeeds
  □ All env vars load correctly
  □ npm run test:run passes
  □ No build warnings

Tailwind 4:
  □ npm run build succeeds
  □ Styles render correctly in browser
  □ npm run test:run passes
  □ Visual regression check (screenshot comparison)
  □ Bundle size not regressed

Streamlit:
  □ streamlit run src/main.py starts
  □ Pages load without errors
  □ Live data updates smoothly (no freezing)
  □ Metrics update at expected intervals
  □ No memory leaks from repeated reruns

Testing:
  □ Coverage reports generated
  □ 75% coverage target met
  □ MSW mocking working for all API calls
  □ E2E tests pass on multiple runs
  □ CI/CD integration complete

Bundle:
  □ stats.html shows chunk breakdown
  □ Lazy loading verified (chunks appear on route change)
  □ Bundle size not regressed from baseline
  □ Lighthouse Performance 85+
  □ No console errors about missing chunks

Security:
  □ Grep for VITE_.*KEY returns zero matches
  □ Pre-commit hook prevents future leaks
  □ API client never includes raw secrets
  □ .env.local in .gitignore
  □ Security audit documented
```

---

**See full implementation guidance in:**
- `C:\cursor\HomeIQ\docs\research\2026-frontend-tech-stack-research.md`
- `C:\cursor\HomeIQ\docs\planning\frontend-epics-roadmap.md`
