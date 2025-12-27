# Vitest Documentation Cache
# Version: 3.2.4
# Last Updated: 2025-10-12
# Source: Context7 (/vitest-dev/vitest/v3_2_4)

## Overview
Vitest is a fast, Vite-native testing framework with Jest compatibility. This cache contains focused documentation on testing, mocking, coverage, and configuration for version 3.2.4.

## Test Framework Setup

### Configuration with defineConfig
```ts
import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    coverage: {
      provider: 'istanbul', // or 'v8'
      reporter: ['text', 'json', 'html'],
    },
  },
})
```

### Basic Test Structure
- **Test files**: Organizing test suites (.test.ts, .spec.ts)
- **Test functions**: Individual test cases with `test()` or `it()`
- **Test suites**: Grouping related tests with `describe()`
- **Setup and teardown**: `beforeAll`, `afterAll`, `beforeEach`, `afterEach`
- **Test isolation**: Independent test execution
- **Watch mode**: Automatic test re-running

### Runtime Configuration
Update configuration dynamically within test files:

```ts
vi.setConfig({
  allowOnly: true,
  testTimeout: 10_000,
  hookTimeout: 10_000,
  clearMocks: true,
  restoreMocks: true,
  fakeTimers: {
    now: new Date(2021, 11, 19),
  },
  maxConcurrency: 10,
  sequence: {
    hooks: 'stack'
  }
})
```

## Mocking Capabilities

### Mock Functions
```ts
// Creating mock functions
const mockFn = vi.fn()
const spy = vi.spyOn(object, 'method')

// Mock implementations
spy.mockImplementation(() => 'mocked value')

// Mock return values
mockFn.mockReturnValue('value')
mockFn.mockReturnThis() // Returns this context for chaining

// Clear mock history
spy.mockClear()
```

### Module Mocking
```ts
// ESM mocking
vi.mock('./module', () => ({
  default: vi.fn(),
  namedExport: vi.fn()
}))

// Partial mocking
vi.mock('./module', async (importOriginal) => {
  const actual = await importOriginal()
  return {
    ...actual,
    mockedFunction: vi.fn()
  }
})
```

### Environment Variable Mocking (v3.2+)
```ts
import { expect, it, vi } from 'vitest'

// Automatic reset with unstubEnvs configuration
it('changes value', () => {
  vi.stubEnv('VITE_ENV', 'staging')
  expect(import.meta.env.VITE_ENV).toBe('staging')
})

// Automatically restored before next test
it('the value is restored', () => {
  expect(import.meta.env.VITE_ENV).toBe('test')
})
```

**Configuration for automatic env reset:**
```ts
export default defineConfig({
  test: {
    unstubEnvs: true,
  },
})
```

### Global Variable Mocking
```ts
vi.stubGlobal('__VERSION__', '1.0.0')
expect(__VERSION__).toBe('1.0.0')
```

### Mock Service Worker (MSW) Integration
```js
import { afterAll, afterEach, beforeAll } from 'vitest'
import { setupServer } from 'msw/node'
import { http, HttpResponse } from 'msw'

const restHandlers = [
  http.get('https://api.example.com/posts', () => {
    return HttpResponse.json(posts)
  })
]

const server = setupServer(...restHandlers)

beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
afterAll(() => server.close())
afterEach(() => server.resetHandlers())
```

## Coverage Configuration

### Coverage Providers
```typescript
import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    coverage: {
      provider: 'v8', // or 'istanbul' or 'custom'
      customProviderModule: 'my-custom-coverage-provider' // for custom
    },
  },
})
```

### Coverage Reporters
```ts
{
  coverage: {
    reporter: [
      ['lcov', { 'projectRoot': './src' }],
      ['json', { 'file': 'coverage.json' }],
      ['text']
    ]
  }
}
```

### Custom Coverage Reporters
```ts
import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    coverage: {
      reporter: [
        // NPM package
        ['@vitest/custom-coverage-reporter', { someOption: true }],
        // Local path
        '/absolute/path/to/custom-reporter.cjs'
      ]
    }
  }
})
```

### Coverage Thresholds (v3.2+ Enhanced API)
```ts
{
  coverage: {
    thresholds: {
      // Global thresholds
      functions: 95,
      branches: 70,
      lines: 90,
      statements: 90,
      
      // Glob pattern specific thresholds
      'src/utils/**.ts': {
        statements: 95,
        functions: 90,
        branches: 85,
        lines: 80,
      },
      
      // 100% coverage requirement
      '**/math.ts': { 100: true },
      
      // Maximum uncovered lines
      lines: -10, // No more than 10 lines uncovered
    }
  }
}
```

### Coverage Watermarks
```typescript
{
  statements: [50, 80],
  functions: [50, 80],
  branches: [50, 80],
  lines: [50, 80]
}
```

### Ignore Empty Lines (v8 provider)
```typescript
import { defineConfig } from 'vitest/config'

export default defineConfig({
  esbuild: {
    // Required for ignoreEmptyLines to work
    include: ['**/*.js', '**/*.jsx', '**/*.mjs', '**/*.ts', '**/*.tsx'],
  },
  test: {
    coverage: {
      provider: 'v8',
      ignoreEmptyLines: true,
    },
  },
})
```

### Coverage CLI Commands
```json
{
  "scripts": {
    "test": "vitest",
    "coverage": "vitest run --coverage"
  }
}
```

```sh
# CLI options
npx vitest --coverage.enabled --coverage.provider=istanbul --coverage.all
```

### Change Coverage Output Directory
```javascript
import { defineConfig } from 'vite'

export default defineConfig({
  test: {
    coverage: {
      reportsDirectory: './tests/unit/coverage'
    }
  }
})
```

## Migration Notes (v3.2+)

### Coverage Thresholds API Update
The coverage configuration has been restructured:

```diff
export default defineConfig({
  test: {
    coverage: {
-      perFile: true,
-      thresholdAutoUpdate: true,
-      100: true,
-      lines: 100,
-      functions: 100,
-      branches: 100,
-      statements: 100,
+      thresholds: {
+        perFile: true,
+        autoUpdate: true,
+        100: true,
+        lines: 100,
+        functions: 100,
+        branches: 100,
+        statements: 100,
+      }
    }
  }
})
```

### Mocking External Libraries
Unlike Jest, Vitest requires explicit configuration:

```yaml
server.deps.inline: ["lib-name"]
```

## Best Practices

### Test Organization
- Use descriptive test names
- Group related tests with `describe()`
- Use `beforeEach` for test setup
- Clean up with `afterEach`

### Mocking Strategy
- Mock external dependencies
- Use `vi.mock()` for modules
- Clear mocks between tests with `clearMocks: true`
- Restore mocks with `restoreMocks: true`

### Coverage Goals
- Aim for 80%+ overall coverage
- Set stricter thresholds for critical code
- Use glob patterns for file-specific requirements
- Enable automatic threshold updates for maintenance

## TypeScript Support

Vitest has native TypeScript support:
- No additional configuration needed
- Type-safe mocking
- IntelliSense for all APIs
- Seamless integration with Vite's TypeScript handling

## Performance Tips

1. Use `vi.fn()` instead of complex mocks when possible
2. Enable parallel execution (default)
3. Use coverage thresholds to catch regressions
4. Configure `maxConcurrency` for large test suites
5. Use watch mode during development
