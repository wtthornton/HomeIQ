# Story 26.5: Device Intelligence Features E2E Tests

## Status
Draft

## Story

**As a** QA engineer,
**I want** comprehensive E2E tests for device intelligence features,
**so that** we can ensure users can view device utilization metrics, discover underutilized features, and get feature-based automation suggestions.

## Acceptance Criteria

1. **Test Coverage:** 3 E2E tests for device intelligence, <1 minute execution
2. **Utilization Metrics:** Display device list with utilization percentages, highlight underutilized devices (<50%), show feature usage breakdown
3. **Feature Suggestions:** Display unused feature suggestions, show capability information, link to documentation, priority scoring visible
4. **Capability Discovery:** Show capability discovery status, display device model information, Zigbee2MQTT integration status, refresh capability data

## Tasks / Subtasks

- [ ] **Task 1:** Create test file `ai-automation-device-intelligence.spec.ts`
- [ ] **Task 2:** Implement utilization metrics tests (device list, percentages, underutilized, breakdown)
- [ ] **Task 3:** Implement feature suggestion tests (unused features, capabilities, docs, priority)
- [ ] **Task 4:** Implement capability discovery tests (status, model info, Zigbee2MQTT, refresh)

## Dev Notes

**Device Intelligence Data:**
```typescript
interface DeviceUtilization {
  device_id: string;
  device_name: string;
  total_capabilities: number;
  used_capabilities: number;
  utilization_percentage: number;
  unused_features: string[];
}
```

**Key Test Example:**
```typescript
test('view device utilization metrics', async ({ page }) => {
  await page.goto('http://localhost:3001/devices');
  
  // Mock utilization data
  await page.route('**/api/device-intelligence/utilization', (route) => {
    route.fulfill({
      status: 200,
      body: JSON.stringify([
        {
          device_id: 'device-1',
          device_name: 'Living Room Switch',
          total_capabilities: 10,
          used_capabilities: 3,
          utilization_percentage: 30,
          unused_features: ['LED indicator', 'Power monitoring']
        }
      ])
    });
  });
  
  await page.reload();
  
  // Verify device displayed
  await expect(page.getByText('Living Room Switch')).toBeVisible();
  await expect(page.getByText('30%')).toBeVisible();
  
  // Verify highlighted as underutilized
  const deviceCard = page.getByTestId('device-card-device-1');
  await expect(deviceCard).toHaveClass(/underutilized/);
});

test('view unused feature suggestions', async ({ page }) => {
  await page.goto('http://localhost:3001/devices');
  
  const suggestions = page.getByTestId('feature-suggestion');
  await expect(suggestions).toHaveCount({ min: 1 });
  
  // Click first suggestion
  await suggestions.first().click();
  
  // Verify capability details
  await expect(page.getByTestId('capability-details')).toBeVisible();
  await expect(page.getByText('LED indicator')).toBeVisible();
});
```

**Required data-testid Attributes:**
- `device-utilization-list`
- `device-card-{id}`
- `utilization-percentage`
- `feature-suggestion`
- `capability-details`
- `refresh-capabilities-button`

## Change Log
| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2025-10-18 | 1.0 | Initial story creation | BMad Master |

## Dev Agent Record
(To be filled by dev agent)

## File List
**New Files:**
- `tests/e2e/ai-automation-device-intelligence.spec.ts`

## QA Results
(To be filled by QA agent)

