# Ask AI E2E Tests - Quick Start

**⏱️ 2 Minute Setup** | **26 Comprehensive Tests** | **✅ Production Ready**

---

## 🚀 Run Tests Now

### 1. Start Services (30 seconds)
```bash
docker-compose up -d ai-automation-service ai-automation-ui
```

### 2. Run Tests (3-5 minutes)

**Windows:**
```powershell
.\tests\e2e\run-ask-ai-tests.ps1
```

**Linux/Mac:**
```bash
./tests/e2e/run-ask-ai-tests.sh
```

### 3. View Results
```bash
npx playwright show-report
```

---

## 📊 What Gets Tested

### ✅ Critical Features
- **Query Submission** - No execution (bug fix verified)
- **Test Button** - Executes automation (enhancement verified)
- **Approve Button** - Creates permanent automation
- **OpenAI Integration** - GPT-4o-mini generates suggestions

### ✅ Regression Tests
- Fix for immediate execution bug ✅
- Test button enhancement ✅
- Pattern matching entity extraction ✅

### ✅ User Experience
- Loading indicators ✅
- Toast notifications ✅
- Error handling ✅
- Page responsiveness ✅

---

## 🎯 Expected Output

```
========================================
Ask AI E2E Test Suite
========================================

📋 Checking service health...
✓ AI Automation UI is healthy
✓ AI Automation Service is healthy
✓ Home Assistant is reachable

========================================
Running Ask AI E2E Tests
========================================

🧪 Running tests...

Running 26 tests using 1 worker

  ✓ Ask AI page loads successfully (2.3s)
  ✓ Submitting query does NOT execute HA commands (12.4s)
  ✓ Test button creates and executes automation in HA (15.3s)
  ✓ Approve button creates permanent automation (8.7s)
  ... (22 more tests)

  26 passed (3.2m)

========================================
Test Results
========================================

✅ All tests passed!

📊 View detailed results:
   npx playwright show-report
```

---

## 🐛 Troubleshooting

### Service Not Running
```bash
# Check status
docker-compose ps

# View logs
docker-compose logs ai-automation-service
```

### Install Playwright
```bash
cd tests/e2e
npm install
npx playwright install
```

### Skip HA Integration Tests
```bash
# Run only query submission tests (no HA needed)
npx playwright test -g "Query submission"
```

---

## 📚 Full Documentation

- **Test Suite:** [ask-ai-complete.spec.ts](ask-ai-complete.spec.ts)
- **Page Object:** [page-objects/AskAIPage.ts](page-objects/AskAIPage.ts)
- **Complete Guide:** [ASK_AI_E2E_TESTS_README.md](ASK_AI_E2E_TESTS_README.md)
- **Implementation:** [../../implementation/ASK_AI_E2E_TESTS_IMPLEMENTATION.md](../../implementation/ASK_AI_E2E_TESTS_IMPLEMENTATION.md)

---

**Ready?** Run the tests now! ⚡

