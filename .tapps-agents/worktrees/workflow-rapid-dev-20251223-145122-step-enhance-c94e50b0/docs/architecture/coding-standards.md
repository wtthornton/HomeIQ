# Coding Standards

### Critical Fullstack Rules

- **Type Sharing:** Always define types in `shared/types/` and import from there
- **API Calls:** Never make direct HTTP calls - use the service layer in `services/`
- **Environment Variables:** Access only through config objects, never `process.env` directly
- **Error Handling:** All API routes must use the standard error handler
- **State Updates:** Never mutate state directly - use proper state management patterns

### Code Complexity Standards

#### Complexity Thresholds

**Python (Radon):**
- **A (1-5)**: Simple, low risk - **preferred for all new code**
- **B (6-10)**: Moderate complexity - **acceptable**
- **C (11-20)**: Complex - **document thoroughly, refactor when touched**
- **D (21-50)**: Very complex - **refactor as high priority**
- **F (51+)**: Extremely complex - **immediate refactoring required**

**Project Standards:**
- Warn: Complexity > 15
- Error: Complexity > 20
- Target: Average complexity ≤ 5

**TypeScript/JavaScript (ESLint):**
- Max cyclomatic complexity: 15 (warn)
- Max lines per function: 100 (warn)
- Max nesting depth: 4 (warn)
- Max parameters: 5 (warn)
- Max lines per file: 500 (warn)

#### Maintainability Index (Python)
- **A (85-100)**: Highly maintainable - **excellent**
- **B (65-84)**: Moderately maintainable - **acceptable**
- **C (50-64)**: Difficult to maintain - **needs improvement**
- **D/F (0-49)**: Very difficult to maintain - **refactor immediately**

**Project Standard:** Minimum B grade (≥65)

#### Code Duplication
- **Target:** < 3%
- **Warning:** 3-5%
- **Error:** > 5%

**Current Project Metrics (Oct 2025):**
- Python: 0.64% duplication ✅ Excellent
- TypeScript: To be measured

#### When to Refactor vs. Document

**Refactor Immediately If:**
- Complexity > 20 (D/F rating)
- Maintainability < 50 (C/D/F rating)
- Duplication > 5%
- Critical path code with complexity > 15
- Code is actively being modified

**Document Thoroughly If:**
- Complexity 11-20 (C rating) and code is stable
- Complex algorithm that cannot be simplified
- Performance-critical code where simplification would hurt performance
- Legacy code with extensive test coverage (refactoring risk high)
- Domain-specific business logic

**Best Practices:**
- Always document complex code (C rating or higher)
- Plan refactoring when making changes to complex code
- Prefer simplicity over cleverness
- Extract functions when complexity > 10
- Use custom hooks to reduce React component complexity

### Naming Conventions

| Element | Frontend | Backend | Example |
|---------|----------|---------|---------|
| Components | PascalCase | - | `HealthDashboard.tsx` |
| Hooks | camelCase with 'use' | - | `useHealthStatus.ts` |
| API Routes | - | kebab-case | `/api/health-status` |
| Database Tables | - | snake_case | `home_assistant_events` |
| Functions | camelCase | snake_case | `getHealthStatus()` / `get_health_status()` |
| Variables | camelCase | snake_case | `userName` / `user_name` |
| Constants | UPPER_SNAKE_CASE | UPPER_SNAKE_CASE | `MAX_RETRIES` |
| Classes | PascalCase | PascalCase | `EventProcessor` |
| Files | camelCase (TS) / kebab-case (components) | snake_case | `useHealth.ts` / `health-dashboard.tsx` / `event_processor.py` |

### Python Standards

#### Type Hints (MANDATORY)
- **All functions** must have type hints for parameters and return types
- Use `typing` module for complex types (Optional, List, Dict, etc.)
- Use `from __future__ import annotations` for forward references
- Example:
```python
from typing import Optional, List
from __future__ import annotations

async def process_events(events: List[dict], timeout: Optional[int] = None) -> List[dict]:
    """Process a list of events."""
    pass
```

#### Async/Await Patterns
- **Always use async/await** for I/O operations (database, HTTP, WebSocket)
- Never use blocking operations in async functions
- Use `aiohttp` for HTTP, `aiosqlite` for database, `websockets` for WebSocket
- Example:
```python
# ✅ CORRECT
async def fetch_data(url: str) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()

# ❌ WRONG - Blocking in async
async def fetch_data(url: str) -> dict:
    response = requests.get(url)  # Blocking!
    return response.json()
```

#### Error Handling
- **Always preserve exception chains** when re-raising (B904 compliance)
- Use specific exception types, avoid bare `except:`
- Example:
```python
# ✅ CORRECT
try:
    result = await process_event(event)
except ValueError as e:
    logger.error(f"Invalid event: {e}")
    raise HTTPException(status_code=400, detail=str(e)) from e

# ❌ WRONG - Loses exception chain
try:
    result = await process_event(event)
except Exception as e:
    raise HTTPException(status_code=500, detail=str(e))  # Missing 'from e'
```

#### Path Handling
- **Always use `pathlib.Path`** instead of `os.path` (PTH compliance)
- Example:
```python
# ✅ CORRECT
from pathlib import Path

config_path = Path(__file__).parent / "config.yaml"
data_dir = Path("/app/data")

# ❌ WRONG
import os
config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
```

#### Database Patterns
- Use **SQLAlchemy 2.0 async patterns** with `AsyncSession`
- Always use transactions for multi-step operations
- Example:
```python
from sqlalchemy.ext.asyncio import AsyncSession

async def create_device(session: AsyncSession, device_data: dict) -> Device:
    async with session.begin():
        device = Device(**device_data)
        session.add(device)
        return device
```

#### Code Quality Tools
- **Ruff**: Fast Python linter and formatter (replaces flake8, black, isort)
- **mypy**: Static type checking (strict mode enabled)
- **Radon**: Complexity analysis (target: A/B ratings)
- Run before committing: `ruff check . && mypy . && ruff format .`

### TypeScript/React Standards

#### Type Safety
- **Strict mode enabled** in `tsconfig.json`
- Use `interface` for object shapes, `type` for unions/primitives
- Avoid `any` - use `unknown` if type is truly unknown
- Example:
```typescript
// ✅ CORRECT
interface HealthStatus {
  status: 'healthy' | 'unhealthy';
  timestamp: number;
}

type EventType = 'state_changed' | 'service_called';

// ❌ WRONG
const data: any = fetchData();  // Use unknown or proper type
```

#### React Patterns
- **Functional components only** - no class components
- Use hooks for state and side effects
- Extract complex logic to custom hooks
- Example:
```typescript
// ✅ CORRECT
function HealthDashboard() {
  const { status, loading } = useHealth();
  
  if (loading) return <LoadingSpinner />;
  return <StatusDisplay status={status} />;
}

// Custom hook
function useHealth() {
  const [status, setStatus] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    fetchHealthStatus().then(setStatus).finally(() => setLoading(false));
  }, []);
  
  return { status, loading };
}
```

#### State Management
- **React Context + Hooks** for simple state (health-dashboard)
- **Zustand** for complex state (ai-automation-ui)
- Never mutate state directly
- Example:
```typescript
// ✅ CORRECT - Zustand
import { create } from 'zustand';

interface AppState {
  user: User | null;
  setUser: (user: User) => void;
}

const useAppStore = create<AppState>((set) => ({
  user: null,
  setUser: (user) => set({ user }),
}));

// ❌ WRONG - Direct mutation
const state = { user: null };
state.user = newUser;  // Mutation!
```

#### Error Handling
- Use **error boundaries** for React component errors
- Handle async errors with try/catch or `.catch()`
- Example:
```typescript
// ✅ CORRECT
async function fetchData() {
  try {
    const response = await fetch('/api/data');
    if (!response.ok) throw new Error('Failed to fetch');
    return await response.json();
  } catch (error) {
    console.error('Fetch error:', error);
    throw error;  // Re-throw for error boundary
  }
}
```

#### Code Quality Tools
- **ESLint**: Linting with complexity plugin
- **TypeScript**: Compile-time type checking
- **Vitest**: Unit testing framework
- **Playwright**: E2E testing
- Run before committing: `npm run lint && npm run type-check && npm run test`

### Import Organization

#### Python
```python
# Standard library imports
import asyncio
from pathlib import Path
from typing import Optional, List

# Third-party imports
from fastapi import FastAPI, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

# Local imports
from .models import Device
from shared.logging_config import setup_logging
```

#### TypeScript
```typescript
// React imports
import { useState, useEffect } from 'react';

// Third-party imports
import { useQuery } from '@tanstack/react-query';
import { z } from 'zod';

// Local imports
import { useHealth } from './hooks/useHealth';
import type { HealthStatus } from '../types';
```

### Testing Standards

#### Python (pytest)
- Use `pytest` with `pytest-asyncio` for async tests
- Test files: `test_*.py` or `*_test.py`
- Use fixtures for common setup
- Example:
```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
```

#### TypeScript (Vitest)
- Use `Vitest` for unit tests
- Test files: `*.test.ts` or `*.test.tsx`
- Use React Testing Library for component tests
- Example:
```typescript
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { HealthDashboard } from './HealthDashboard';

describe('HealthDashboard', () => {
  it('displays health status', () => {
    render(<HealthDashboard />);
    expect(screen.getByText(/healthy/i)).toBeInTheDocument();
  });
});
```

### Documentation Standards

#### Python Docstrings
- Use Google or NumPy style
- Include type information in docstrings
- Example:
```python
async def process_event(event: dict) -> dict:
    """Process a single Home Assistant event.
    
    Args:
        event: Event dictionary with 'event_type' and 'data' keys.
        
    Returns:
        Processed event dictionary with normalized fields.
        
    Raises:
        ValueError: If event is missing required fields.
    """
    pass
```

#### TypeScript JSDoc
- Use JSDoc for complex functions
- Include parameter and return types
- Example:
```typescript
/**
 * Fetches health status from the API.
 * 
 * @param endpoint - API endpoint URL
 * @returns Promise resolving to health status object
 * @throws {Error} If API request fails
 */
async function fetchHealthStatus(endpoint: string): Promise<HealthStatus> {
  // Implementation
}
```

### Current Project Metrics (November 2025)

- **Python Duplication**: 0.64% ✅ Excellent
- **Python Complexity**: Target A/B ratings (1-10), warn at 15, error at 20
- **TypeScript**: ESLint complexity warnings at 15
- **Code Quality Tools**: Ruff, mypy, ESLint, Vitest, Playwright
- **Type Coverage**: Python (mypy strict), TypeScript (strict mode)

