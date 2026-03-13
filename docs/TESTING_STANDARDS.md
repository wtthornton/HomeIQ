# HomeIQ Frontend Testing Standards

**Created:** 2026-03-13 | **Epic:** 58 (Frontend Test Quality)
**Applies to:** health-dashboard, ai-automation-ui, observability-dashboard

---

## Test File Conventions

### Naming & Location

- **Unit/component tests:** `src/<category>/__tests__/<ComponentName>.test.tsx`
- **Hook tests:** `src/hooks/__tests__/<hookName>.test.ts`
- **Utility tests:** `src/utils/__tests__/<utilName>.test.ts`
- **Service/API tests:** `src/services/__tests__/<serviceName>.test.ts`
- **Python tests (obs-dashboard):** `tests/test_<module>.py`

### File Structure

```tsx
/**
 * <ComponentName> Tests
 * Brief description of what is being tested
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
// or for health-dashboard: import { render, screen } from '../../../tests/test-utils';

describe('<ComponentName>', () => {
  // === Rendering ===
  it('renders without crashing', () => { ... });
  it('displays expected content', () => { ... });

  // === Interactions ===
  it('handles user click', () => { ... });

  // === States ===
  it('shows loading state', () => { ... });
  it('shows error state', () => { ... });
  it('shows empty state', () => { ... });

  // === Accessibility ===
  it('has proper ARIA roles', () => { ... });
  it('supports keyboard navigation', () => { ... });

  // === Dark Mode ===
  it('applies dark mode classes', () => { ... });
});
```

---

## Required Test Categories

Every test file MUST include tests from these categories (where applicable):

### Components

| Category | Required | Example |
|----------|----------|---------|
| **Rendering** | Always | `screen.getByRole('heading', { name: /title/i })` |
| **Loading state** | If async | `screen.getByRole('status')` or skeleton check |
| **Error state** | If async | `screen.getByRole('alert')` or error message check |
| **Empty state** | If data-driven | No-data fallback renders |
| **Interactions** | If interactive | Button clicks, form inputs, toggles |
| **Accessibility** | Always | `getByRole`, `getByLabelText`, ARIA attributes |
| **Dark mode** | If prop/class exists | `className` contains dark variant |

### Hooks

| Category | Required | Example |
|----------|----------|---------|
| **Success path** | Always | Returns expected data |
| **Error path** | Always | Returns error state |
| **Loading path** | If async | Returns loading: true initially |
| **Parameter variations** | If parameterized | Different args produce different results |

### Services / API Clients

| Category | Required | Example |
|----------|----------|---------|
| **Success response** | Always | 200 response parsed correctly |
| **Error responses** | Always | 400, 401, 404, 500 handled |
| **Auth headers** | If authenticated | Bearer token included |
| **Network failure** | Always | Timeout / connection refused |

---

## Accessibility Testing Patterns

Use `@testing-library/react` queries that enforce accessibility:

```tsx
// PREFER: role-based queries (enforce semantic HTML)
screen.getByRole('button', { name: /submit/i });
screen.getByRole('heading', { level: 2, name: /dashboard/i });
screen.getByRole('alert');
screen.getByRole('status');
screen.getByRole('navigation');
screen.getByRole('main');

// GOOD: label-based queries
screen.getByLabelText(/email address/i);
screen.getByPlaceholderText(/search/i);

// ACCEPTABLE: test-id (only when no semantic query works)
screen.getByTestId('custom-widget');

// AVOID: class-based queries for content
container.querySelector('.my-class'); // Only for visual assertions
```

### Minimum a11y assertions per component:

1. **Interactive elements** have accessible names (`getByRole('button', { name })`)
2. **Forms** have associated labels (`getByLabelText`)
3. **Modals** have `role="dialog"` and `aria-modal="true"`
4. **Loading states** have `role="status"` or `aria-busy="true"`
5. **Error messages** have `role="alert"`
6. **Navigation** uses `<nav>` with `aria-label`

---

## Dark Mode Testing Pattern

```tsx
// health-dashboard: uses darkMode prop
it('applies dark mode styling', () => {
  render(<Component darkMode={true} />);
  const el = screen.getByRole('main');
  expect(el.className).toContain('bg-gray-900');
});

// ai-automation-ui: uses document class or store
it('applies dark mode styling', () => {
  document.documentElement.classList.add('dark');
  render(<Component />);
  // Assert dark-specific classes or visual elements
  document.documentElement.classList.remove('dark');
});
```

---

## Error Boundary Testing Pattern

```tsx
// Create a component that throws
const ThrowingComponent = () => {
  throw new Error('Test error');
};

it('catches errors and shows fallback', () => {
  const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
  render(
    <ErrorBoundary>
      <ThrowingComponent />
    </ErrorBoundary>
  );
  expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
  consoleSpy.mockRestore();
});

it('renders children when no error', () => {
  render(
    <ErrorBoundary>
      <div>Normal content</div>
    </ErrorBoundary>
  );
  expect(screen.getByText('Normal content')).toBeInTheDocument();
});
```

---

## Mock Setup Patterns

### MSW (health-dashboard)

```tsx
// Use existing handlers from src/tests/mocks/handlers.ts
// Add new handlers for missing endpoints
import { http, HttpResponse } from 'msw';

// Success handler
http.get('/api/v1/endpoint', () => {
  return HttpResponse.json({ data: 'value' });
});

// Error handler
http.get('/api/v1/endpoint', () => {
  return HttpResponse.json({ error: 'Not found' }, { status: 404 });
});
```

### vi.mock (ai-automation-ui)

```tsx
// Mock framer-motion (common in skeleton/animated components)
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}));

// Mock hooks
vi.mock('../../hooks/useMyHook');
const mockHook = vi.mocked(useMyHook);
mockHook.mockReturnValue({ data: [], loading: false });
```

---

## Coverage Targets

| File Type | Target | Rationale |
|-----------|--------|-----------|
| **Utilities** | 85% | Pure functions, easy to test exhaustively |
| **Hooks** | 70% | All paths: success, error, loading |
| **Components** | 60% | Rendering + interactions + states |
| **Pages** | 50% | Core flows; deep testing via E2E |
| **Services/API** | 75% | All endpoints + error handling |

### Per-App Targets

| App | Current | Target (Epic 58) | Stretch |
|-----|---------|-------------------|---------|
| health-dashboard | ~16% files | 20%+ | 55% |
| ai-automation-ui | ~19% files | 25%+ | 45% |
| observability-dashboard | ~57% logic | 60%+ | 70% |

---

## Reference Test Files

Use these as templates when creating new tests:

| Pattern | Reference File |
|---------|---------------|
| Tab component | `health-dashboard/src/components/sports/__tests__/SportsTab.test.tsx` |
| Hook | `health-dashboard/src/hooks/__tests__/useHealth.test.ts` |
| Store | `ai-automation-ui/src/store/__tests__/store.test.ts` |
| Complex component | `ai-automation-ui/src/components/ha-agent/__tests__/AutomationPreview.test.tsx` |
| Security utility | `health-dashboard/src/utils/__tests__/inputSanitizer.test.ts` |
| Loading component | `ai-automation-ui/src/components/__tests__/LoadingSpinner.test.tsx` |
| API client | `ai-automation-ui/src/services/__tests__/api-v2.test.ts` |

---

## When to Use Unit vs Integration vs E2E

| Test Type | Use When | Framework |
|-----------|----------|-----------|
| **Unit** | Testing a single function, hook, or component in isolation | Vitest + RTL |
| **Integration** | Testing cross-component data flows (e.g., tab navigation + state) | Vitest + RTL + MSW |
| **E2E** | Testing real user journeys across pages | Playwright |

**Rule of thumb:** If you need to mock more than 3 dependencies, consider writing an integration test with MSW instead of mocking everything.
