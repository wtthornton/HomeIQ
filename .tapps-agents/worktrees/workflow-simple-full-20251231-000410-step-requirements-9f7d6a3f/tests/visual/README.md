# Visual Testing Suite

Comprehensive Puppeteer-based visual testing for the AI Automation UI.

## Overview

This suite validates UI pages against design specifications, checks for visual regressions, and ensures consistent UX across light and dark modes.

## Files

- **`test-all-pages.js`** - Comprehensive test suite for all pages
- **`test-quick-check.js`** - Fast single-page validation
- **`README.md`** - This file

## Prerequisites

```bash
# Install Puppeteer (already in package.json)
npm install puppeteer

# Ensure the UI is running
docker-compose up ai-automation-ui
# or
cd services/ai-automation-ui && npm run dev
```

## Usage

### Full Test Suite

Tests all pages with comprehensive checks:

```bash
node tests/visual/test-all-pages.js
```

**What it does:**
- ✅ Tests all 4 pages (Dashboard, Patterns, Deployed, Settings)
- ✅ Captures light and dark mode screenshots
- ✅ Validates design token usage
- ✅ Checks touch target sizes (44x44px minimum)
- ✅ Verifies navigation, cards, charts, buttons
- ✅ Generates JSON report with results

**Output:**
- Screenshots: `test-results/visual/{page}-{mode}.png`
- Report: `test-results/visual/test-report.json`
- Console: Detailed pass/fail/warning summary

### Quick Check

Fast validation for a single page:

```bash
# Check dashboard (default)
node tests/visual/test-quick-check.js

# Check specific page
node tests/visual/test-quick-check.js patterns
node tests/visual/test-quick-check.js deployed
node tests/visual/test-quick-check.js settings
```

**What it does:**
- ✅ Quick screenshot capture
- ✅ Basic element presence checks
- ✅ Fast feedback (< 10 seconds)

## Test Coverage

### Pages Tested
1. **Dashboard** (`/`)
   - Health metrics
   - Service status
   - Event statistics
   - Charts and visualizations

2. **Patterns** (`/patterns`)
   - Pattern list with readable names
   - Pattern type distribution
   - Confidence charts
   - Top devices chart

3. **Deployed** (`/deployed`)
   - Deployed automation list
   - Action buttons
   - Status indicators

4. **Settings** (`/settings`)
   - Configuration forms
   - Input fields
   - Save/cancel buttons

### Design Validation

Based on `docs/design-tokens.md`:

#### Colors ✅
- Light mode: bg-white, bg-gray-50, text-gray-900
- Dark mode: bg-gray-800, bg-gray-900, text-white
- Status colors: green, yellow, red, blue

#### Spacing ✅
- 4px/8px grid system
- Consistent padding and margins
- Gap spacing validation

#### Border Radius ✅
- rounded (4px)
- rounded-lg (8px)
- rounded-xl (12px)
- rounded-full (9999px)

#### Touch Targets ✅
- Minimum 44x44px for all interactive elements
- Button size validation
- Link target size validation

#### Accessibility ✅
- Dark mode toggle present
- Navigation accessibility
- Focus states (visual inspection)

## Example Output

```
==========================================================
📄 Testing: Patterns
==========================================================

🔗 Navigating to http://localhost:3001/patterns...
⏳ Waiting for content...
📸 Taking light mode screenshot...
📸 Taking dark mode screenshot...
✅ hasNavigation: Navigation found
✅ hasPatternList: Found 12 pattern items
✅ hasCharts: Found 3 charts
✅ hasReadableNames: Found readable names: Co-occurrence Pattern (5 occurrences, 85% confidence)...
✅ checkColors: Using 24 color classes (sample: bg-white, text-gray-900, bg-green-100, text-green-800, bg-yellow-100)
✅ checkSpacing: Using 18 spacing classes (sample: p-4, p-6, gap-4, m-2, gap-6)
✅ checkBorderRadius: Using 8 border radius classes (sample: rounded-lg, rounded-full, rounded-xl)
✅ checkTouchTargets: All touch targets meet minimum size requirements

==========================================================
📊 VISUAL TESTING REPORT
==========================================================

✅ Passed: 4 pages
   - Dashboard: All checks completed
   - Patterns: All checks completed
   - Deployed: All checks completed
   - Settings: All checks completed

📁 Screenshots saved to: test-results/visual
📄 JSON report saved to: test-results/visual/test-report.json

==========================================================
🎉 ALL TESTS PASSED! UI looks great!
==========================================================
```

## Integration with CI/CD

Add to GitHub Actions workflow:

```yaml
- name: Run Visual Tests
  run: |
    docker-compose up -d ai-automation-ui
    npm install
    node tests/visual/test-all-pages.js
    
- name: Upload Screenshots
  uses: actions/upload-artifact@v3
  with:
    name: visual-test-screenshots
    path: test-results/visual/
```

## Troubleshooting

### Browser not installed
```bash
# Install Chromium for Puppeteer
npx puppeteer browsers install chrome
```

### Port already in use
```bash
# Check if UI is running on port 3001
netstat -an | findstr :3001

# If not, start it
docker-compose up ai-automation-ui
```

### Screenshots are blank
- Increase wait time in script
- Check if content is loading
- Verify network requests complete

### Tests timing out
- Increase timeout values
- Check backend services are running
- Verify API endpoints are responsive

## Best Practices

1. **Run before commits** - Catch visual regressions early
2. **Test both modes** - Always verify light and dark mode
3. **Review screenshots** - Visual inspection is crucial
4. **Update baselines** - When design changes are intentional
5. **CI integration** - Automate in pull request checks

## Future Enhancements

- [ ] Visual diff comparison with baseline screenshots
- [ ] Performance metrics (page load times)
- [ ] Responsive design testing (multiple viewports)
- [ ] Accessibility audits (axe-core integration)
- [ ] Animation testing
- [ ] Cross-browser testing (Firefox, Safari)

## Related Documentation

- [Design Tokens](../../docs/design-tokens.md) - Design system specification
- [Testing Strategy](../../docs/architecture/testing-strategy.md) - Overall testing approach
- [Tech Stack](../../docs/architecture/tech-stack.md) - Technology choices

## Maintainer

**BMad Master** - Epic 23: Data Enhancement & UX Polish

