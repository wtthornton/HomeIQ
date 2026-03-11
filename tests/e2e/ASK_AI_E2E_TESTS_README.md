# Ask AI E2E Tests

Comprehensive end-to-end tests for the Ask AI feature, covering query submission, test execution, approval workflow, and regression tests for bug fixes.

## Test modes and CI (Epic 49)

Ask AI has two E2E modes:

1. **Mocked E2E (CI, fast)** — `tests/e2e/ai-automation-ui/workflows/ask-ai-mocked.spec.ts` runs in Docker E2E. It mocks `/api/v1/ask-ai/*` so no OpenAI API key or Home Assistant is required. Run time &lt; 30s.
2. **Full E2E (local/optional)** — `tests/e2e/ask-ai-complete.spec.ts` and `tests/e2e/ask-ai-debug.spec.ts` use live OpenAI and (for test/approve) Home Assistant. They are **not** in the default Docker E2E run; run them locally with the appropriate env (e.g. `OPENAI_API_KEY`). Use long timeout (e.g. 90s per test).

**HA Agent Chat E2E:** `tests/e2e/ai-automation-ui/pages/ha-agent-chat.spec.ts` covers the Chat page. It can use mocks or a live backend depending on config; see that spec for details.

## 📋 Test Coverage

### Core Functionality
- ✅ **Query Submission** - Natural language queries generate suggestions WITHOUT executing commands
- ✅ **Test Button** - Creates temporary automation, executes it, and disables it
- ✅ **Approve Button** - Creates permanent automation in Home Assistant
- ✅ **Reject Button** - Removes suggestion from view with feedback
- ✅ **OpenAI Integration** - Verifies GPT-4o-mini generates creative suggestions

### Bug Fixes & Regressions
- ✅ **Immediate Execution Fix** - Query submission no longer executes HA commands
- ✅ **Test Execution Enhancement** - Test button now executes automation
- ✅ **Entity Extraction** - Uses pattern matching (not HA Conversation API)

### User Experience
- ✅ **Loading Indicators** - Progress feedback during processing
- ✅ **Toast Notifications** - Success, error, and info messages
- ✅ **Sidebar Examples** - Pre-populated query examples
- ✅ **Clear Chat** - Reset conversation state

### Edge Cases
- ✅ **Complex Queries** - Multi-device, multi-condition automations
- ✅ **Invalid Entities** - Graceful error handling
- ✅ **Performance** - Response times under 30 seconds
- ✅ **Reliability** - Page remains responsive during operations

## 🚀 Quick Start

### Prerequisites
```bash
# Start required services
docker-compose up -d ai-automation-service ai-automation-ui

# Verify services are running
curl http://localhost:3001           # AI Automation UI
curl http://localhost:8018/health    # AI Automation Service
```

### Run All Tests

**Windows (PowerShell):**
```powershell
.\tests\e2e\run-ask-ai-tests.ps1
```

**Linux/Mac:**
```bash
./tests/e2e/run-ask-ai-tests.sh
```

### Run Specific Tests

```bash
# Run specific test file
npx playwright test tests/e2e/ask-ai-complete.spec.ts

# Run specific test by name
npx playwright test -g "Query submission does NOT execute"

# Run in debug mode
npx playwright test tests/e2e/ask-ai-complete.spec.ts --debug

# Run in UI mode
npx playwright test tests/e2e/ask-ai-complete.spec.ts --ui
```

## 📁 Test Structure

### Test Files
```
tests/e2e/
├── ask-ai-complete.spec.ts         # Complete test suite
├── page-objects/
│   └── AskAIPage.ts                # Page Object Model for Ask AI
├── run-ask-ai-tests.sh             # Test runner (Linux/Mac)
└── run-ask-ai-tests.ps1            # Test runner (Windows)
```

### Page Object Model

The `AskAIPage` class provides a clean interface for interacting with Ask AI:

```typescript
import { AskAIPage } from './page-objects/AskAIPage';

test('example', async ({ page }) => {
  const askAI = new AskAIPage(page);
  
  // Navigate
  await askAI.goto();
  
  // Submit query
  await askAI.submitQuery('Turn on the office lights');
  await askAI.waitForResponse();
  
  // Test suggestion
  await askAI.testSuggestion(0);
  await askAI.waitForToast(/test automation executed/i);
  
  // Approve suggestion
  await askAI.approveSuggestion(0);
});
```

## 🧪 Test Scenarios

### 1. Query Submission (No Execution)

**Critical Test:** Verifies fix for immediate execution bug

```typescript
test('Submitting query does NOT execute HA commands', async () => {
  await askAI.submitQuery('Turn on the office lights');
  await askAI.waitForResponse();
  
  // Verify suggestions generated
  await askAI.waitForToast(/found.*suggestion/i);
  
  // Verify NO execution occurred
  await askAI.verifyNoDeviceExecution();
  
  const suggestionCount = await askAI.getSuggestionCount();
  expect(suggestionCount).toBeGreaterThan(0);
});
```

**What This Tests:**
- Query uses pattern matching (not HA Conversation API)
- No devices change state
- OpenAI generates suggestions
- Toast notifications show success

### 2. Test Button Execution

**Critical Test:** Verifies test button enhancement

```typescript
test('Test button creates and executes automation in HA', async () => {
  await askAI.submitQuery('Turn on the office lights');
  await askAI.waitForResponse();
  
  // Click Test
  await askAI.testSuggestion(0);
  
  // Verify loading toast
  await askAI.waitForToast(/creating.*test automation/i);
  
  // Verify execution success
  await askAI.waitForToast(/test automation executed/i);
  
  // Verify cleanup info
  await askAI.waitForToast(/test automation.*disabled/i);
});
```

**What This Tests:**
- YAML generation from suggestion
- Validation before creation
- Automation creation in HA with test_ prefix
- Immediate trigger execution
- Auto-disable after execution
- User feedback via toasts

### 3. Approve Button

```typescript
test('Approve button creates permanent automation', async () => {
  await askAI.submitQuery('Turn on lights at sunset');
  await askAI.waitForResponse();
  
  await askAI.approveSuggestion(0);
  
  // Verify success
  await askAI.waitForToast(/automation approved/i);
});
```

**What This Tests:**
- Permanent automation creation
- YAML generation and storage
- Suggestion removal from view
- Success feedback

### 4. Regression Tests

```typescript
test('BUG FIX: Query submission no longer executes HA commands', async () => {
  const queries = [
    'Turn on the office lights',
    'Turn off all lights',
    'Dim bedroom lights to 25%'
  ];
  
  for (const query of queries) {
    await askAI.submitQuery(query);
    await askAI.waitForResponse();
    
    // CRITICAL: Verify no execution occurred
    await askAI.verifyNoDeviceExecution();
  }
});
```

**What This Tests:**
- Fix for ASK_AI_IMMEDIATE_EXECUTION_FIX.md
- Pattern matching vs HA Conversation API
- No unintended device control

## 📊 Test Results

### Viewing Results

```bash
# Open HTML report
npx playwright show-report

# Or navigate to:
test-results/html-report/index.html
```

### Result Artifacts

| Artifact | Location | Description |
|----------|----------|-------------|
| **HTML Report** | `test-results/html-report/` | Interactive test results |
| **Screenshots** | `test-results/ask-ai/` | Screenshots on failure |
| **Videos** | `test-results/ask-ai/` | Video recordings on failure |
| **Traces** | `test-results/ask-ai/` | Detailed execution traces |

## 🐛 Troubleshooting

### Services Not Running

```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs ai-automation-service
docker-compose logs ai-automation-ui

# Restart services
docker-compose restart ai-automation-service ai-automation-ui
```

### Tests Timing Out

```bash
# Increase timeout in test
test.setTimeout(60000); // 60 seconds

# Or run with longer timeout
npx playwright test --timeout=60000
```

### OpenAI API Errors

Tests that require OpenAI will fail if:
- No API key configured
- API rate limits exceeded
- Network connectivity issues

**Solution:** Check environment variables and API status

### Home Assistant Not Reachable

Test execution tests will fail if HA is not available:
- Verify HA is running: `curl http://192.168.1.86:8123/api/`
- Check network connectivity
- Verify access token is valid

Tests will still pass for query submission (doesn't need HA).

## 📈 Performance Benchmarks

Expected test durations:

| Test | Expected Duration | Max Timeout |
|------|-------------------|-------------|
| **Query Submission** | 5-15 seconds | 30 seconds |
| **Test Execution** | 10-20 seconds | 25 seconds |
| **Approve** | 5-10 seconds | 15 seconds |
| **Full Suite** | 3-5 minutes | 10 minutes |

## 🔧 Configuration

### Test Configuration

Tests use Playwright's default configuration with:
- **Browsers:** Chromium (default), Firefox, WebKit (optional)
- **Viewport:** 1280x720
- **Timeout:** 30 seconds per test
- **Retries:** 2 on failure
- **Screenshots:** On failure only
- **Videos:** On failure only

### Environment Variables

```bash
# Optional: Override service URLs
export ASK_AI_UI_URL=http://localhost:3001
export ASK_AI_API_URL=http://localhost:8018
export HA_URL=http://192.168.1.86:8123
```

## 🎯 CI/CD Integration

### GitHub Actions Example

```yaml
name: Ask AI E2E Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Start services
        run: docker-compose up -d ai-automation-service ai-automation-ui
      
      - name: Wait for services
        run: |
          sleep 10
          curl --retry 5 --retry-delay 2 http://localhost:3001
          curl --retry 5 --retry-delay 2 http://localhost:8018/health
      
      - name: Run tests
        run: ./tests/e2e/run-ask-ai-tests.sh
      
      - name: Upload results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: test-results
          path: test-results/
```

## 📚 Related Documentation

- **Bug Fix:** [ASK_AI_IMMEDIATE_EXECUTION_FIX.md](../../implementation/ASK_AI_IMMEDIATE_EXECUTION_FIX.md)
- **Enhancement:** [ASK_AI_TEST_EXECUTION_ENHANCEMENT.md](../../implementation/ASK_AI_TEST_EXECUTION_ENHANCEMENT.md)
- **Summary:** [ASK_AI_FIXES_SUMMARY.md](../../implementation/ASK_AI_FIXES_SUMMARY.md)
- **Design Spec:** [ASK_AI_TAB_DESIGN_SPECIFICATION.md](../../implementation/ASK_AI_TAB_DESIGN_SPECIFICATION.md)

## ✅ Test Coverage Summary

| Category | Tests | Status |
|----------|-------|--------|
| **Page Load** | 3 | ✅ |
| **Query Submission** | 3 | ✅ |
| **Test Execution** | 4 | ✅ |
| **Approve/Reject** | 3 | ✅ |
| **User Experience** | 3 | ✅ |
| **Complex Queries** | 3 | ✅ |
| **OpenAI Integration** | 2 | ✅ |
| **Regression Tests** | 2 | ✅ |
| **Performance** | 3 | ✅ |
| **Total** | **26 tests** | ✅ |

---

**Created:** October 19, 2025  
**Status:** ✅ Ready for Testing  
**Maintainer:** BMad Master

