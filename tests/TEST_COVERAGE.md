# Test Coverage Documentation

Comprehensive coverage documentation for HomeIQ E2E test suite.

## Coverage Overview

### Health Dashboard (Port 3000)

| Category | Coverage | Status |
|----------|----------|--------|
| **Pages/Tabs** | 17 tabs (overview, services, groups, dependencies, configuration, devices, events, data-sources, energy, sports, alerts, hygiene, validation, evaluation, memory, logs, analytics) | ✅ Complete |
| **Components** | 40+ components | ✅ Complete |
| **Interactions** | All major interactions | ✅ Complete |
| **Accessibility** | WCAG 2.1 AA compliance | ✅ Complete |
| **Error States** | All error scenarios | ✅ Complete |
| **Loading States** | All loading scenarios | ✅ Complete |

### AI Automation UI (Port 3001)

Route–spec matrix: [docs/planning/ai-automation-ui-routes-e2e-matrix.md](../docs/planning/ai-automation-ui-routes-e2e-matrix.md)

| Category | Coverage | Status |
|----------|----------|--------|
| **Pages/Routes** | /, /chat, /explore, /insights, /automations, /scheduled, /settings, /name-enhancement + legacy redirects | ✅ Complete |
| **Components** | 50+ components | ✅ Complete |
| **Workflows** | All major workflows | ✅ Complete |
| **Chat Interface** | Full chat functionality | ✅ Complete |
| **Error States** | All error scenarios | ✅ Complete |
| **Loading States** | All loading scenarios | ✅ Complete |

### Auto-Fix Pipeline (Unit Tests)

| Category | Coverage | Status |
|----------|----------|--------|
| **Config Schema** | config-schema.json, homeiq-default.yaml validation | ✅ Complete |
| **Scan Output** | BUGS marker extraction, fallback regex | ✅ Complete |
| **Prompt Files** | Prompt paths resolve to existing .md files | ✅ Complete |
| **Tests** | 18 unit tests in `tests/auto-fix-pipeline/` | ✅ Complete |

Run: `python -m pytest tests/auto-fix-pipeline -v`

## Detailed Coverage

### Health Dashboard

#### Pages/Tabs (17)

- ✅ Overview Tab
- ✅ Services Tab
- ✅ Groups Tab
- ✅ Dependencies Tab
- ✅ Configuration Tab
- ✅ Devices Tab
- ✅ Events Tab
- ✅ Data Feeds Tab
- ✅ Energy Tab
- ✅ Sports Tab
- ✅ Alerts Tab
- ✅ Device Health (Hygiene) Tab
- ✅ Automation Checks (Validation) Tab
- ✅ AI Performance (Evaluation) Tab
- ✅ Memory Brain Tab
- ✅ Logs Tab
- ✅ Analytics Tab

#### Components

- ✅ Navigation
- ✅ Modals
- ✅ Charts
- ✅ Forms
- ✅ Cards
- ✅ Filters
- ✅ Search
- ✅ Loading Spinners
- ✅ Error Boundaries

#### Interactions

- ✅ Theme Toggle
- ✅ Tab Switching
- ✅ Filters
- ✅ Search
- ✅ Keyboard Navigation
- ✅ Responsive Design

#### Accessibility

- ✅ ARIA Labels
- ✅ Keyboard Navigation
- ✅ Screen Reader Compatibility
- ✅ Color Contrast
- ✅ Focus Indicators
- ✅ Form Labels
- ✅ Heading Hierarchy

### AI Automation UI

#### Pages/Routes (9/9)

- ✅ Conversational Dashboard
- ✅ Patterns Page
- ✅ Synergies Page
- ✅ Deployed Page
- ✅ Discovery Page
- ✅ HA Agent Chat
- ✅ Settings Page
- ✅ Admin Page
- ✅ Navigation

#### Components

- ✅ Suggestion Cards
- ✅ Chat Interface
- ✅ Automation Preview
- ✅ Modals
- ✅ Navigation
- ✅ Filters
- ✅ Search
- ✅ Loading States
- ✅ Error States

#### Workflows

- ✅ Automation Creation Flow
- ✅ Conversation Flow
- ✅ Deployment Flow
- ✅ Refinement Flow

### Auto-Fix Pipeline (Unit Tests)

Config-driven bug-finding pipeline. See `auto-fix-pipeline/README.md`.

#### Config Schema (`test_config_schema.py`)

- ✅ Schema file exists
- ✅ Schema is valid JSON
- ✅ homeiq-default.yaml exists and is valid YAML
- ✅ Required sections: project, runner, scan, fix, mcp, paths, prompts
- ✅ output_format.markers: <<<BUGS>>>, <<<END_BUGS>>>
- ✅ budget_allocation sums to 1.0
- ✅ Validates against config-schema.json

#### Scan Output Extraction (`test_scan_output_extraction.py`)

- ✅ Extract via <<<BUGS>>> / <<<END_BUGS>>> markers
- ✅ Fallback extraction via JSON array regex
- ✅ Empty list and invalid JSON handling

#### Prompt Files (`test_prompt_files.py`)

- ✅ Config has prompts section
- ✅ All prompt paths resolve to existing files
- ✅ Prompt files are .md

## Test Statistics

### Total Tests

- **Health Dashboard**: ~150+ tests
- **AI Automation UI**: ~100+ tests
- **Auto-Fix Pipeline**: 18 unit tests
- **Total**: ~270+ tests

### Test Types

- **Smoke Tests**: ~20 tests (critical paths)
- **Regression Tests**: ~150 tests (full features)
- **Component Tests**: ~50 tests (individual components)
- **Integration Tests**: ~30 tests (workflows)
- **Accessibility Tests**: ~20 tests (A11y compliance)

### Browser Coverage

- ✅ Chromium (primary)
- ✅ Firefox
- ✅ WebKit (Safari)
- ✅ Mobile Chrome
- ✅ Mobile Safari

## Coverage Gaps

### Known Gaps

1. **WebSocket Real-Time Updates**: Limited testing of real-time WebSocket connections
2. **Performance Testing**: No performance benchmarks
3. **Visual Regression**: No visual regression testing
4. **Cross-Browser Edge Cases**: Some edge cases not tested in all browsers

### Future Improvements

1. Add visual regression testing
2. Add performance benchmarks
3. Expand WebSocket testing
4. Add more edge case coverage
5. Add visual diff testing

## Running Coverage Reports

```bash
# Generate coverage report
npm run test:e2e:report

# View HTML report
open playwright-report/index.html
```

## Coverage Goals

- **Minimum**: 80% coverage of critical paths
- **Target**: 90% coverage of all features
- **Current**: ~85% coverage

## Maintenance

### Updating Coverage

1. Add tests for new features
2. Update tests when UI changes
3. Remove obsolete tests
4. Update coverage documentation

### Coverage Monitoring

- Coverage tracked in CI/CD
- Reports generated on every run
- Coverage trends monitored over time
