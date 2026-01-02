# Step 7: Testing Plan - Debug Tab Integration

## Test Coverage Plan

### Unit Tests Required

#### 1. Tab Navigation Tests
- [ ] Test that Preview tab is selected by default
- [ ] Test that clicking Debug tab switches to debug view
- [ ] Test that clicking Preview tab switches back to preview view
- [ ] Test that active tab is visually highlighted
- [ ] Test that tab state persists during modal lifecycle

#### 2. DebugTab Integration Tests
- [ ] Test that DebugTab component is rendered when Debug tab is active
- [ ] Test that conversationId prop is passed to DebugTab
- [ ] Test that darkMode prop is passed to DebugTab
- [ ] Test that DebugTab receives null when conversationId is undefined
- [ ] Test that DebugTab handles missing conversationId gracefully

#### 3. Preview Tab Tests
- [ ] Test that YAML content is displayed when Preview tab is active
- [ ] Test that existing YAML functionality still works
- [ ] Test that validation feedback still displays
- [ ] Test that Create Automation button still functions

#### 4. Component Props Tests
- [ ] Test that conversationId prop is now used (was previously unused)
- [ ] Test that all existing props still work correctly
- [ ] Test that onEdit callback still functions
- [ ] Test that onClose callback still functions

#### 5. Edge Cases
- [ ] Test behavior when conversationId is null
- [ ] Test behavior when conversationId is empty string
- [ ] Test tab switching with rapid clicks
- [ ] Test component unmounting during tab switch

## Test Implementation Notes

### Testing Framework
- **Framework**: Vitest (as per project setup)
- **Testing Library**: @testing-library/react
- **Mocking**: Mock DebugTab component for isolation

### Test File Location
`services/ai-automation-ui/src/components/ha-agent/__tests__/AutomationPreview.test.tsx`

### Example Test Structure

```typescript
import { render, screen, fireEvent } from '@testing-library/react';
import { AutomationPreview } from '../AutomationPreview';
import { DebugTab } from '../DebugTab';

// Mock DebugTab component
jest.mock('../DebugTab', () => ({
  DebugTab: jest.fn(() => <div>Debug Tab Content</div>)
}));

describe('AutomationPreview - Tab Navigation', () => {
  const defaultProps = {
    automationYaml: 'alias: Test Automation',
    darkMode: false,
    onClose: jest.fn(),
    conversationId: 'test-conversation-id',
  };

  it('should render Preview tab by default', () => {
    render(<AutomationPreview {...defaultProps} />);
    expect(screen.getByText('Preview')).toBeInTheDocument();
    expect(screen.getByText(/Test Automation/)).toBeInTheDocument();
  });

  it('should switch to Debug tab when clicked', () => {
    render(<AutomationPreview {...defaultProps} />);
    const debugTab = screen.getByText('🐛 Debug');
    fireEvent.click(debugTab);
    expect(DebugTab).toHaveBeenCalledWith(
      expect.objectContaining({
        conversationId: 'test-conversation-id',
        darkMode: false,
      }),
      expect.anything()
    );
  });
});
```

## Integration Tests

### Manual Testing Checklist
- [x] Open Automation Preview modal
- [x] Verify Preview tab is active by default
- [x] Click Debug tab
- [x] Verify DebugTab component loads
- [x] Verify prompt breakdown information displays
- [x] Click Preview tab
- [x] Verify YAML content displays
- [x] Test with dark mode enabled
- [x] Test with dark mode disabled
- [x] Test with null conversationId
- [x] Verify existing functionality (validation, create, edit) still works

## Test Coverage Goals

- **Target Coverage**: 80%
- **Current Coverage**: ~50% (estimated)
- **Priority Areas**:
  1. Tab navigation logic
  2. DebugTab integration
  3. Props passing
  4. Edge cases

## Notes

- DebugTab component has its own tests (separate file)
- Focus on testing AutomationPreview's integration with DebugTab
- Mock DebugTab to isolate AutomationPreview tests
- Test user interactions (tab clicks) thoroughly
