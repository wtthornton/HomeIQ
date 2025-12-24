# Testing Strategy

### Testing Pyramid

```
Visual Tests (Puppeteer)
/        \
E2E Tests (Integration)
/        \
Integration Tests (API)
/            \
Frontend Unit  Backend Unit
```

### Test Organization

#### Frontend Tests
```
frontend/tests/
├── components/
│   ├── HealthDashboard.test.tsx
│   ├── EventList.test.tsx
│   └── ConfigForm.test.tsx
├── services/
│   └── api.test.ts
└── __mocks__/
    └── api.ts
```

#### Backend Tests
```
services/*/tests/
├── test_websocket_client.py
├── test_event_processor.py
├── test_weather_service.py
├── test_influxdb_client.py
└── test_api_endpoints.py
```

#### E2E Tests
```
tests/
├── test_integration.py
├── test_data_flow.py
└── fixtures/
    └── sample_events.json
```

#### Visual Tests (Puppeteer)
```
tests/visual/
├── test-patterns-visual.js
├── test-dashboard-visual.js
├── test-ui-regression.js
└── screenshots/
    ├── patterns-baseline.png
    ├── dashboard-baseline.png
    └── regression-comparisons/
```

### Test Examples

#### Frontend Component Test
```typescript
import { render, screen } from '@testing-library/react';
import { HealthDashboard } from '../HealthDashboard';

test('displays system health status', () => {
  const mockHealth = {
    service_status: { websocket_client: 'healthy' },
    event_stats: { events_per_hour: 100 }
  };
  
  render(<HealthDashboard health={mockHealth} />);
  expect(screen.getByText('healthy')).toBeInTheDocument();
});
```

#### Backend API Test
```python
import pytest
from fastapi.testclient import TestClient
from admin_api.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert "service_status" in response.json()
```

#### E2E Test
```python
import pytest
import asyncio
from services.websocket_ingestion.src.websocket_client import WebSocketClient

@pytest.mark.asyncio
async def test_end_to_end_data_flow():
    # Test complete data flow from HA to InfluxDB
    client = WebSocketClient("ws://test-ha:8123/websocket")
    await client.connect()
    
    # Simulate event and verify storage
    event = await client.receive_event()
    assert event is not None
    
    # Verify event stored in InfluxDB
    stored_event = await query_influxdb(event.entity_id)
    assert stored_event is not None
```

#### Visual Test (Puppeteer)
```javascript
const puppeteer = require('puppeteer');

async function testPatternsVisual() {
  const browser = await puppeteer.launch({ headless: false });
  const page = await browser.newPage();
  
  try {
    // Navigate to patterns page
    await page.goto('http://localhost:3001/patterns', { waitUntil: 'networkidle2' });
    
    // Wait for patterns to load
    await new Promise(resolve => setTimeout(resolve, 5000));
    
    // Take screenshot for visual verification
    await page.screenshot({ path: 'patterns-test.png', fullPage: true });
    
    // Verify readable pattern names
    const patternTexts = await page.evaluate(() => {
      const elements = document.querySelectorAll('*');
      const texts = [];
      elements.forEach(el => {
        const text = el.textContent?.trim();
        if (text && text.length > 20 && text.length < 100 && 
            (text.includes('Co-occurrence') || text.includes('Pattern'))) {
          texts.push(text);
        }
      });
      return [...new Set(texts)].slice(0, 10);
    });
    
    // Assert readable names are present
    const hasReadableNames = patternTexts.some(text => 
      text.includes('Co-occurrence') || text.includes('Pattern')
    );
    
    if (hasReadableNames) {
      console.log('✅ SUCCESS: Found readable pattern names!');
    } else {
      throw new Error('❌ FAILED: Still showing hash IDs instead of readable names');
    }
    
  } finally {
    await browser.close();
  }
}

testPatternsVisual();
```

### Visual Testing with Puppeteer

#### When to Use Puppeteer
- **UI Regression Testing**: Verify visual changes don't break existing functionality
- **Screenshot Verification**: Capture and compare UI states
- **User Experience Testing**: Test actual browser behavior and interactions
- **Cross-browser Testing**: Verify functionality across different browsers
- **Performance Testing**: Measure page load times and rendering performance

#### Puppeteer vs Other Testing Tools

| Tool | Use Case | Strengths |
|------|----------|-----------|
| **Puppeteer** | Visual testing, screenshots, browser automation | Real browser, screenshot capture, reliable automation |
| **Playwright** | E2E testing, cross-browser | Multi-browser support, built-in assertions |
| **Vitest** | Unit testing, component testing | Fast, Vite integration, TypeScript support |
| **pytest** | Backend testing, API testing | Python ecosystem, comprehensive assertions |

#### Best Practices for Visual Testing
1. **Screenshot Baselines**: Store reference screenshots for comparison
2. **Selective Testing**: Focus on critical UI components and user flows
3. **Environment Consistency**: Use consistent browser settings and viewport sizes
4. **Automated Comparison**: Use tools like `pixelmatch` for automated visual diff detection
5. **CI Integration**: Run visual tests in CI/CD pipeline for regression detection

### Visual Testing Suite

We have implemented a comprehensive Puppeteer-based visual testing suite that validates all pages against design specifications.

#### Location
- **Test Suite**: `tests/visual/test-all-pages.js`
- **Quick Check**: `tests/visual/test-quick-check.js`
- **Documentation**: `tests/visual/README.md`

#### Running Tests

```bash
# Full suite (all pages)
node tests/visual/test-all-pages.js

# Quick check (single page)
node tests/visual/test-quick-check.js patterns
```

#### What Gets Tested
- ✅ All 4 pages (Dashboard, Patterns, Deployed, Settings)
- ✅ Light and dark mode screenshots
- ✅ Design token compliance (colors, spacing, border radius)
- ✅ Touch target sizes (44x44px minimum)
- ✅ Navigation, cards, charts, buttons presence
- ✅ Readable names vs hash IDs
- ✅ Accessibility features (dark mode toggle)

#### Test Output
- Screenshots: `test-results/visual/{page}-{mode}.png`
- JSON Report: `test-results/visual/test-report.json`
- Console: Detailed pass/fail/warning summary

#### Design Validation
The suite validates against specifications in `docs/design-tokens.md`:
- **Colors**: Status colors (green/yellow/red/blue), background, text, borders
- **Spacing**: 4px/8px grid system (p-2, p-4, p-6, p-8, gap-*)
- **Border Radius**: rounded, rounded-lg, rounded-xl, rounded-full
- **Touch Targets**: Minimum 44x44px for all interactive elements
- **Accessibility**: Dark mode support, navigation, focus states

#### When to Run
- Before committing UI changes
- After design token updates
- During PR reviews
- As part of CI/CD pipeline
- When fixing visual bugs

See [tests/visual/README.md](mdc:tests/visual/README.md) for complete documentation.

