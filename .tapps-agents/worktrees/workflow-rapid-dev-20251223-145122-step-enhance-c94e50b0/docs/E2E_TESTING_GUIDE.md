# E2E Testing Guide - Services Tab

**Created:** October 11, 2025  
**Purpose:** Comprehensive end-to-end testing for all three phases of the Services Tab

---

## 🎯 Overview

This guide covers E2E testing for:
- **Phase 1:** Service Cards & Monitoring
- **Phase 2:** Service Details Modal
- **Phase 3:** Dependencies Visualization

---

## 📁 Test Files

```
services/health-dashboard/tests/e2e/
├── global-setup.ts                    # Test environment setup
├── global-teardown.ts                 # Test cleanup
├── services-tab-phase1.spec.ts        # Phase 1: 15 tests
├── services-tab-phase2.spec.ts        # Phase 2: 17 tests
└── services-tab-phase3.spec.ts        # Phase 3: 18 tests

Total: 50 comprehensive E2E tests
```

---

## 🚀 Quick Start

### Prerequisites

```bash
# 1. Navigate to dashboard directory
cd services/health-dashboard

# 2. Install dependencies (if not already installed)
npm install

# 3. Install Playwright
npm install -D @playwright/test
npx playwright install
```

### Run Tests

**Option 1: PowerShell Script (Recommended)**
```powershell
# Full deployment and testing
.\scripts\deploy-and-test.ps1

# With browser UI (not headless)
.\scripts\deploy-and-test.ps1 -Headless:$false

# Skip build step
.\scripts\deploy-and-test.ps1 -SkipBuild

# Specific browser
.\scripts\deploy-and-test.ps1 -Browser firefox
```

**Option 2: NPM Commands**
```bash
# Run all E2E tests
npm run test:e2e

# Run with UI mode (interactive)
npm run test:e2e:ui

# Run with browser visible
npm run test:e2e:headed

# Debug mode
npm run test:e2e:debug

# View report
npm run test:e2e:report

# Specific browser
npm run test:e2e:chromium
npm run test:e2e:firefox
npm run test:e2e:webkit
```

**Option 3: Direct Playwright Commands**
```bash
# All tests
npx playwright test

# Specific file
npx playwright test services-tab-phase1

# Specific test
npx playwright test -g "should display Services tab"

# Watch mode
npx playwright test --watch

# Update snapshots
npx playwright test --update-snapshots
```

---

## 📊 Test Coverage

### Phase 1: Service Cards (15 tests)
- ✅ Tab navigation
- ✅ Service card grid display
- ✅ Core and External service sections
- ✅ Service icons and status indicators
- ✅ Auto-refresh functionality
- ✅ Manual refresh button
- ✅ Last updated timestamp
- ✅ View Details buttons
- ✅ Responsive layout
- ✅ Dark mode compatibility

### Phase 2: Service Details Modal (17 tests)
- ✅ Modal opens on click
- ✅ All 4 tabs present (Overview, Logs, Metrics, Health)
- ✅ Service information display
- ✅ Resource usage bars (CPU, Memory)
- ✅ Tab switching
- ✅ Logs with timestamps and levels
- ✅ Copy Logs button
- ✅ Metrics placeholder
- ✅ Health statistics and timeline
- ✅ Close via X button
- ✅ Close via Escape key
- ✅ Close via backdrop click
- ✅ Dark mode compatibility
- ✅ Mobile responsiveness

### Phase 3: Dependencies Visualization (18 tests)
- ✅ Dependencies tab in navigation
- ✅ Header and instructions
- ✅ Legend with all status colors
- ✅ All 12 service nodes visible
- ✅ Service icons displayed
- ✅ External Data Sources section
- ✅ Connection arrows
- ✅ Node click highlights dependencies
- ✅ Clear Selection button
- ✅ Clear selection functionality
- ✅ Hover tooltips
- ✅ Toggle selection
- ✅ Dark mode compatibility
- ✅ Horizontal scroll on mobile

---

## 🔍 Test Details

### Phase 1 Tests

**Navigation & Display**
```typescript
test('should display Services tab in navigation')
test('should navigate to Services tab when clicked')
test('should display service cards grid')
test('should display Core Services section')
test('should display External Data Services section')
```

**Functionality**
```typescript
test('should show service icons')
test('should display Auto-Refresh toggle')
test('should toggle Auto-Refresh when clicked')
test('should display Refresh Now button')
test('should show last updated timestamp')
```

**Interactivity**
```typescript
test('should display View Details buttons on service cards')
test('should display service status indicators')
test('should be responsive on mobile viewport')
test('should work in dark mode')
```

### Phase 2 Tests

**Modal Interaction**
```typescript
test('should open modal when View Details is clicked')
test('should display modal tabs')
test('should close modal with X button')
test('should close modal with Escape key')
test('should close modal when clicking backdrop')
```

**Tab Content**
```typescript
test('should display service information in Overview tab')
test('should display CPU and Memory usage bars')
test('should switch to Logs tab when clicked')
test('should display logs with timestamps and levels')
test('should switch to Metrics tab')
test('should display Chart.js installation notice')
test('should switch to Health tab')
test('should display health statistics')
test('should display health timeline')
```

### Phase 3 Tests

**Visualization**
```typescript
test('should display Dependencies tab in navigation')
test('should display legend')
test('should display all 12 services')
test('should display connection arrows')
```

**Interactivity**
```typescript
test('should highlight dependencies when node is clicked')
test('should display Clear Selection button')
test('should clear selection when button is clicked')
test('should show tooltip on hover')
test('should toggle selection when clicking same node twice')
```

---

## 🌐 Browser Support

Tests run on:
- ✅ Chromium (Chrome/Edge)
- ✅ Firefox
- ✅ WebKit (Safari)
- ✅ Mobile Chrome (Pixel 5)
- ✅ Mobile Safari (iPhone 12)

---

## 📸 Test Artifacts

Playwright automatically captures:
- **Screenshots** - On test failure
- **Videos** - On test failure
- **Traces** - On retry
- **HTML Report** - After all tests

Artifacts location: `test-results/`

---

## 🐛 Debugging Tests

### View Test UI
```bash
npm run test:e2e:ui
```

Interactive mode with:
- Test picker
- Timeline
- DOM snapshots
- Network logs
- Console output

### Debug Specific Test
```bash
npx playwright test --debug -g "should open modal"
```

Opens Playwright Inspector with:
- Step-by-step execution
- DOM explorer
- Console logs
- Network activity

### View Last Test Report
```bash
npm run test:e2e:report
```

Opens HTML report with:
- Test results
- Screenshots
- Videos
- Traces

---

## 🔧 Configuration

### Playwright Config (`playwright.config.ts`)

**Key Settings:**
```typescript
baseURL: 'http://localhost:3000'
timeout: 30000
retries: 2 (on CI)
workers: 1 (on CI)
webServer: {
  command: 'npm run dev',
  url: 'http://localhost:3000',
  timeout: 120000
}
```

**Modify for your needs:**
- Change timeout values
- Add/remove browsers
- Adjust retry behavior
- Configure reporters

---

## 📊 CI/CD Integration

### GitHub Actions Example

```yaml
name: E2E Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: 18
      
      - name: Install dependencies
        run: cd services/health-dashboard && npm ci
      
      - name: Install Playwright
        run: cd services/health-dashboard && npx playwright install --with-deps
      
      - name: Run E2E tests
        run: cd services/health-dashboard && npm run test:e2e
      
      - uses: actions/upload-artifact@v3
        if: always()
        with:
          name: playwright-report
          path: services/health-dashboard/playwright-report/
```

---

## 🎯 Test Scenarios

### Happy Path
1. ✅ Navigate to Services tab
2. ✅ View all service cards
3. ✅ Click View Details
4. ✅ Explore all modal tabs
5. ✅ Close modal
6. ✅ Navigate to Dependencies
7. ✅ Click service nodes
8. ✅ View dependencies highlight

### Error Scenarios
1. ✅ Services API failure
2. ✅ Network timeout
3. ✅ Invalid service data
4. ✅ Modal close edge cases

### Responsive Tests
1. ✅ Mobile viewport (375x667)
2. ✅ Tablet viewport (768x1024)
3. ✅ Desktop viewport (1920x1080)
4. ✅ Ultra-wide viewport (2560x1440)

---

## 📝 Adding New Tests

### Create New Test File

```typescript
import { test, expect } from '@playwright/test';

test.describe('My New Feature', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  test('should do something', async ({ page }) => {
    // Your test code
    await expect(page.locator('text=Something')).toBeVisible();
  });
});
```

### Best Practices

1. **Use Data-Testid** for stable selectors
   ```typescript
   await page.locator('[data-testid="service-card"]').click();
   ```

2. **Wait for Network** before assertions
   ```typescript
   await page.waitForLoadState('networkidle');
   ```

3. **Use Explicit Waits**
   ```typescript
   await expect(element).toBeVisible({ timeout: 5000 });
   ```

4. **Clean State** in beforeEach
   ```typescript
   test.beforeEach(async ({ page }) => {
     await page.goto('/');
     // Reset state
   });
   ```

---

## 🚨 Troubleshooting

### Tests Fail to Start
```bash
# Reinstall Playwright browsers
npx playwright install --with-deps
```

### Port 3000 Already in Use
```bash
# Kill process on port 3000
netstat -ano | findstr :3000
taskkill /PID <PID> /F
```

### Tests Timeout
- Increase timeout in `playwright.config.ts`
- Check if dev server is slow to start
- Verify network connectivity

### Modal Tests Fail
- Check z-index values
- Verify backdrop click targets
- Ensure proper wait conditions

### Flaky Tests
- Add explicit waits
- Use `page.waitForLoadState('networkidle')`
- Increase timeouts for slow operations

---

## 📈 Performance Metrics

**Expected Test Durations:**
- Phase 1: ~45 seconds
- Phase 2: ~60 seconds
- Phase 3: ~50 seconds

**Total: ~2.5 minutes for all 50 tests**

---

## ✅ Success Criteria

All tests pass when:
- ✅ All 50 E2E tests passing
- ✅ No console errors
- ✅ All UI elements visible
- ✅ Interactions work correctly
- ✅ Dark mode works
- ✅ Mobile responsive
- ✅ Cross-browser compatible

---

## 📚 Resources

- [Playwright Documentation](https://playwright.dev/)
- [Best Practices](https://playwright.dev/docs/best-practices)
- [Debugging Guide](https://playwright.dev/docs/debug)
- [CI/CD Integration](https://playwright.dev/docs/ci)

---

**Ready to test!** Run `.\scripts\deploy-and-test.ps1` to verify all three phases! 🚀

