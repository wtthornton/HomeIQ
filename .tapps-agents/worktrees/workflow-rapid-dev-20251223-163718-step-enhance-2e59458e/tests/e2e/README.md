# HA Ingestor E2E Test Suite

This directory contains comprehensive end-to-end tests for the HA Ingestor system using Playwright. The tests are designed to run against the local Docker deployment and cover all aspects of the system including UI functionality, service integration, performance, and visual regression.

## Test Structure

### Test Files

- **`system-health.spec.ts`** - Tests health and connectivity of all backend services
- **`dashboard-functionality.spec.ts`** - Tests main dashboard UI and user interactions
- **`monitoring-screen.spec.ts`** - Tests monitoring interface functionality
- **`settings-screen.spec.ts`** - Tests settings and configuration interface
- **`visual-regression.spec.ts`** - Tests UI consistency and visual appearance
- **`integration.spec.ts`** - Tests end-to-end data flow and service integration
- **`performance.spec.ts`** - Tests system performance, load times, and responsiveness

### Configuration Files

- **`docker-deployment.config.ts`** - Playwright configuration for Docker deployment testing
- **`docker-global-setup.ts`** - Global setup for Docker environment validation
- **`docker-global-teardown.ts`** - Global teardown and cleanup
- **`utils/docker-test-helpers.ts`** - Docker-specific test utilities and helpers

### Test Runner

- **`run-docker-tests.sh`** - Comprehensive test runner script for Docker deployment

## Prerequisites

### System Requirements

1. **Docker and Docker Compose** - The HA Ingestor system must be deployed locally
2. **Node.js and npm** - For running Playwright tests
3. **Playwright browsers** - Will be installed automatically

### Docker Deployment

Before running tests, ensure the HA Ingestor system is deployed and running:

```bash
# Start the Docker deployment
docker-compose up -d

# Verify all services are running
docker-compose ps

# Check service health
curl http://localhost:8086/health    # InfluxDB
curl http://localhost:8001/health    # WebSocket Ingestion
curl http://localhost:8002/health    # Enrichment Pipeline
curl http://localhost:8003/api/v1/health  # Admin API
curl http://localhost:3000           # Health Dashboard
```

## Running Tests

### Quick Start

Run all tests with the automated test runner:

```bash
./tests/e2e/run-docker-tests.sh
```

### Individual Test Suites

Run specific test suites:

```bash
# System health tests
npx playwright test tests/e2e/system-health.spec.ts --config=tests/e2e/docker-deployment.config.ts

# Dashboard functionality tests
npx playwright test tests/e2e/dashboard-functionality.spec.ts --config=tests/e2e/docker-deployment.config.ts

# Visual regression tests
npx playwright test tests/e2e/visual-regression.spec.ts --config=tests/e2e/docker-deployment.config.ts

# Integration tests
npx playwright test tests/e2e/integration.spec.ts --config=tests/e2e/docker-deployment.config.ts

# Performance tests
npx playwright test tests/e2e/performance.spec.ts --config=tests/e2e/docker-deployment.config.ts
```

### Cross-Browser Testing

Test across multiple browsers:

```bash
./tests/e2e/run-docker-tests.sh --cross-browser
```

### Mobile Testing

Test mobile responsiveness:

```bash
./tests/e2e/run-docker-tests.sh --mobile
```

### Debug Mode

Run tests in debug mode:

```bash
npx playwright test tests/e2e/dashboard-functionality.spec.ts --config=tests/e2e/docker-deployment.config.ts --debug
```

### UI Mode

Run tests with Playwright UI:

```bash
npx playwright test --config=tests/e2e/docker-deployment.config.ts --ui
```

## AI Automation Testing ✨ NEW

### Quick Start for AI Automation Tests

```bash
# Run all AI automation tests
./tests/e2e/run-docker-tests.sh --service ai-automation

# Run specific AI automation test file
npx playwright test tests/e2e/ai-automation-smoke.spec.ts

# Debug AI automation tests
npx playwright test tests/e2e/ai-automation-*.spec.ts --debug
```

### Test Suites

**1. Smoke Tests** (`ai-automation-smoke.spec.ts`)
- UI loads successfully
- Navigation works across all 4 pages
- Page Object Models functional

**2. Approval Workflow** (`ai-automation-approval-workflow.spec.ts`) - *Planned*
- Browse and filter suggestions
- Approve suggestions
- Deploy to Home Assistant
- Error handling

**3. Rejection Workflow** (`ai-automation-rejection-workflow.spec.ts`) - *Planned*
- Reject suggestions with feedback
- Verify hiding behavior
- Feedback persistence

**4. Pattern Visualization** (`ai-automation-patterns.spec.ts`) - *Planned*
- View time-of-day and co-occurrence patterns
- Filter patterns
- Chart interactions

**5. Manual Analysis** (`ai-automation-analysis.spec.ts`) - *Planned*
- Trigger analysis manually
- Monitor progress
- Real-time UI updates

**6. Device Intelligence** (`ai-automation-device-intelligence.spec.ts`) - *Planned*
- Device utilization metrics
- Feature suggestions
- Capability discovery

**7. Settings** (`ai-automation-settings.spec.ts`) - *Planned*
- Configuration management
- API key validation
- Persistence verification

### Test Architecture

**Page Object Models:**
```
tests/e2e/page-objects/
├── DashboardPage.ts    # Suggestion browsing, filtering, approval
├── PatternsPage.ts     # Pattern visualization and analysis
├── DeployedPage.ts     # Deployed automations management
└── SettingsPage.ts     # Configuration management
```

**Test Utilities:**
```
tests/e2e/utils/
├── mock-data-generators.ts  # Generate realistic test data
├── custom-assertions.ts      # AI-specific assertions
└── api-mocks.ts             # Mock backend endpoints
```

**Test Fixtures:**
```
tests/e2e/fixtures/
└── ai-automation.ts  # Default mock data sets
```

### Example Test

```typescript
import { test, expect } from '@playwright/test';
import { DashboardPage } from './page-objects/DashboardPage';
import { mockSuggestionsEndpoint } from './utils/api-mocks';
import { expectToastMessage } from './utils/custom-assertions';

test('approve and deploy suggestion', async ({ page }) => {
  const dashboardPage = new DashboardPage(page);
  
  // Mock API
  await mockSuggestionsEndpoint(page);
  
  // Navigate and approve
  await dashboardPage.goto();
  await dashboardPage.approveSuggestion(0);
  
  // Deploy
  await dashboardPage.deploySuggestion('sug-1');
  
  // Verify success
  await expectToastMessage(page, 'success', 'deployed');
});
```

### Mock Data Utilities

```typescript
import { MockDataGenerator } from './utils/mock-data-generators';

// Generate suggestions
const suggestions = MockDataGenerator.generateSuggestions({
  count: 5,
  category: 'energy',
  confidence: 'high'
});

// Generate patterns
const patterns = MockDataGenerator.generatePatterns({ count: 8 });

// Generate device capabilities
const devices = MockDataGenerator.generateDeviceCapabilities({ count: 10 });
```

### Custom Assertions

```typescript
import { 
  expectToastMessage,
  expectSuggestionVisible,
  expectDeploymentSuccess,
  expectChartRendered 
} from './utils/custom-assertions';

// Assert success toast appears
await expectToastMessage(page, 'success', 'Successfully deployed');

// Assert suggestion is visible
await expectSuggestionVisible(page, 'sug-123');

// Assert automation deployed
await expectDeploymentSuccess(page, 'sug-123');

// Assert chart rendered
await expectChartRendered(page);
```

### API Mocking

```typescript
import {
  mockSuggestionsEndpoint,
  mockDeployEndpoint,
  mockPatternsEndpoint,
  mockAllEndpoints
} from './utils/api-mocks';

// Mock individual endpoints
await mockSuggestionsEndpoint(page);
await mockDeployEndpoint(page, true);  // success
await mockDeployEndpoint(page, false); // failure

// Mock all endpoints at once
await mockAllEndpoints(page);
```

## Test Coverage

### Backend Services

- ✅ **InfluxDB** - Database health and connectivity
- ✅ **WebSocket Ingestion** - Home Assistant connection and event processing
- ✅ **Enrichment Pipeline** - Data processing and weather integration
- ✅ **Admin API** - REST API endpoints and functionality
- ✅ **Data Retention** - Data cleanup and management
- ✅ **Weather API** - Weather data integration (if enabled)
- ✨ **AI Automation Service** - AI-powered automation suggestions (Port 8018)

### Frontend Screens

- ✅ **Health Dashboard** - Main dashboard with health cards, statistics, and events (Port 3000)
- ✅ **Monitoring** - System monitoring interface with service status
- ✅ **Settings** - Configuration management interface
- ✨ **AI Automation UI** - AI-powered automation suggestions interface (Port 3001)

### UI Components

- ✅ **Navigation** - Screen navigation and routing
- ✅ **Health Cards** - Service status indicators
- ✅ **Statistics Charts** - Data visualization components
- ✅ **Events Feed** - Real-time event display
- ✅ **Forms** - Settings and configuration forms
- ✅ **Modals** - Dialog boxes and overlays
- ✅ **Notifications** - Alert and notification system

### User Interactions

- ✅ **Navigation** - Screen switching and routing
- ✅ **Data Refresh** - Manual and automatic data updates
- ✅ **Settings Management** - Configuration changes and persistence
- ✅ **Export Functionality** - Data export in various formats
- ✅ **Theme Toggle** - Light/dark theme switching
- ✅ **Layout Switching** - Dashboard layout customization

### Visual Testing

- ✅ **Full Page Screenshots** - Complete screen captures
- ✅ **Component Screenshots** - Individual component testing
- ✅ **Responsive Design** - Mobile and tablet layouts
- ✅ **Theme Consistency** - Light and dark theme testing
- ✅ **Loading States** - Loading and error state visuals
- ✅ **Hover States** - Interactive element testing

### Integration Testing

- ✅ **Data Flow** - End-to-end data pipeline testing
- ✅ **Service Dependencies** - Service interaction validation
- ✅ **Error Propagation** - Error handling across services
- ✅ **Real-time Updates** - WebSocket and live data testing
- ✅ **Configuration Management** - Settings persistence and validation

### Performance Testing

- ✅ **Load Times** - Page and component loading performance
- ✅ **API Response Times** - Backend service performance
- ✅ **Concurrent Users** - Multi-user simulation
- ✅ **Large Datasets** - Performance with high data volumes
- ✅ **Memory Usage** - Memory stability during extended use
- ✅ **Mobile Performance** - Mobile device performance

## Test Data and Environment

### Test Data

The tests work with real data from the Docker deployment. No special test data setup is required as the tests validate the actual system functionality.

### Environment Variables

Tests use the following endpoints (configurable in `docker-deployment.config.ts`):

- **Health Dashboard**: http://localhost:3000
- **InfluxDB**: http://localhost:8086
- **WebSocket Ingestion**: http://localhost:8001
- **Enrichment Pipeline**: http://localhost:8002
- **Admin API**: http://localhost:8003
- **Data Retention**: http://localhost:8080

### Docker Integration

The tests include Docker-specific utilities for:

- Container health checking
- Service restart simulation
- Log collection
- Resource monitoring
- Network connectivity testing

## Test Results and Reporting

### Output Formats

Tests generate results in multiple formats:

- **HTML Report** - Interactive test results with screenshots and videos
- **JSON Results** - Machine-readable test results
- **JUnit XML** - CI/CD integration format
- **Console Output** - Real-time test execution feedback

### Result Locations

- **Test Results**: `test-results/`
- **HTML Report**: `test-results/html-report/index.html`
- **Screenshots**: `test-results/` (on test failures)
- **Videos**: `test-results/` (on test failures)
- **Traces**: `test-results/` (on test failures)

### Viewing Results

```bash
# Open HTML report in browser
npx playwright show-report

# Or open directly
open test-results/html-report/index.html
```

## Troubleshooting

### Common Issues

1. **Services Not Ready**
   - Ensure Docker deployment is fully started
   - Wait for all services to be healthy before running tests
   - Check service logs: `docker-compose logs <service-name>`

2. **Test Timeouts**
   - Increase timeout values in test configuration
   - Check system performance and resource usage
   - Verify network connectivity between containers

3. **Visual Regression Failures**
   - Update baseline screenshots if UI changes are intentional
   - Check for consistent test environment setup
   - Verify browser and viewport settings

4. **Performance Test Failures**
   - Check system resources (CPU, memory, disk)
   - Verify Docker container resource limits
   - Consider running tests on more powerful hardware

### Debug Commands

```bash
# Check Docker container status
docker-compose ps

# View service logs
docker-compose logs websocket-ingestion
docker-compose logs admin-api

# Check service health
curl http://localhost:8003/api/v1/health

# Run single test with debug output
npx playwright test tests/e2e/dashboard-functionality.spec.ts --config=tests/e2e/docker-deployment.config.ts --debug --headed
```

### Getting Help

1. Check the HTML test report for detailed failure information
2. Review service logs for backend issues
3. Use debug mode to step through failing tests
4. Check the Docker deployment health independently

## Continuous Integration

### CI/CD Integration

The tests are designed to run in CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run E2E Tests
  run: |
    docker-compose up -d
    ./tests/e2e/run-docker-tests.sh
```

### Docker Compose Integration

Tests can be integrated with Docker Compose for automated testing:

```bash
# Run tests as part of Docker Compose
docker-compose -f docker-compose.yml -f docker-compose.test.yml up --abort-on-container-exit
```

## Best Practices

### Test Development

1. **Use data-testid attributes** for reliable element selection
2. **Wait for elements** rather than fixed timeouts
3. **Test real user workflows** rather than isolated functions
4. **Include error scenarios** in test coverage
5. **Keep tests independent** and avoid test interdependencies

### Maintenance

1. **Update screenshots** when UI changes are intentional
2. **Monitor test execution times** and optimize slow tests
3. **Review test failures** promptly and fix flaky tests
4. **Keep test data clean** and avoid test pollution
5. **Document test scenarios** and expected behaviors

### Performance

1. **Run tests in parallel** when possible
2. **Use efficient selectors** and avoid complex CSS selectors
3. **Minimize browser launches** by reusing contexts
4. **Clean up resources** after tests complete
5. **Monitor system resources** during test execution

## Contributing

### Adding New Tests

1. Create test files following the existing naming convention
2. Use the `data-testid` attributes for element selection
3. Include proper error handling and cleanup
4. Add tests to the appropriate test suite
5. Update this documentation

### Test Standards

- Use descriptive test names and descriptions
- Include both positive and negative test cases
- Test edge cases and error conditions
- Ensure tests are deterministic and repeatable
- Add appropriate assertions and validations

### Code Quality

- Follow TypeScript best practices
- Use meaningful variable and function names
- Add comments for complex test logic
- Keep test functions focused and single-purpose
- Use helper functions for common operations
