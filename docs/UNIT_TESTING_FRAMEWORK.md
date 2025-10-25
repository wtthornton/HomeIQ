# HomeIQ Unit Testing Framework

A comprehensive unit testing framework that runs all unit tests and generates detailed coverage reports. This framework focuses on **unit tests only** - tests that run in isolation without external dependencies like databases, APIs, or services.

## 🎯 What This Framework Does

- **Identifies Unit Tests**: Automatically finds and runs only unit tests (excludes integration, e2e, visual tests)
- **Cross-Language Support**: Runs both Python and TypeScript/React unit tests
- **Coverage Reports**: Generates comprehensive coverage reports in multiple formats
- **Unified Results**: Provides a single summary of all unit test results
- **Easy Execution**: Simple commands to run all tests or specific subsets

## 🚀 Quick Start

### Run All Unit Tests
```bash
# Linux/Mac
./run-unit-tests.sh

# Windows PowerShell
.\run-unit-tests.ps1

# Direct Python execution
python scripts/run-unit-tests.py
```

### Run with Options
```bash
# Verbose output
./run-unit-tests.sh --verbose

# Python tests only
./run-unit-tests.sh --python-only

# TypeScript tests only
./run-unit-tests.sh --typescript-only

# Generate coverage reports only
./run-unit-tests.sh --coverage-only
```

## 📊 Test Results

After running tests, you'll find results in the `test-results/` directory:

```
test-results/
├── unit-test-results.json          # Detailed JSON results
├── unit-test-report.html           # HTML summary report
└── coverage/
    ├── python/                     # Python coverage reports
    │   ├── index.html              # HTML coverage report
    │   └── coverage.xml            # XML coverage data
    └── typescript/                 # TypeScript coverage reports
        ├── index.html              # HTML coverage report
        └── coverage.json           # JSON coverage data
```

## 🧪 What Tests Are Included

### Python Unit Tests
- **Safety Validator** (`test_safety_validator.py`) - Automation safety validation
- **Automation Parser** (`test_automation_parser.py`) - Configuration parsing
- **Database Models** (`test_database_models.py`) - SQLAlchemy models and CRUD
- **Co-occurrence Detector** (`test_co_occurrence_detector.py`) - Pattern detection
- **Calendar Parser** (`test_event_parser.py`) - Event parsing utilities
- **Weather Health** (`test_health_check.py`) - Health check logic
- **Automation Miner** (`test_parser.py`, `test_deduplicator.py`) - Mining utilities
- **Data Models** (`test_models.py`) - Data structure tests
- **Sports Calculator** (`test_stats_calculator.py`) - Statistics calculations

### TypeScript Unit Tests
- **API Usage Calculator** (`apiUsageCalculator.test.ts`) - Usage calculation logic
- **Team Preferences** (`useTeamPreferences.test.ts`) - React hook logic
- **Statistics Hook** (`useStatistics.test.ts`) - Statistics hook logic

## ❌ What Tests Are Excluded

The framework automatically excludes:
- **Integration Tests**: Tests that require external services (databases, APIs)
- **E2E Tests**: End-to-end tests that require full system
- **Visual Tests**: Screenshot and visual regression tests
- **Smoke Tests**: System-wide health checks
- **Deployment Tests**: Infrastructure and deployment tests

## 🔧 Configuration Files

### Python Configuration (`pytest-unit.ini`)
- Defines which Python test files to run
- Sets up coverage reporting
- Excludes integration/e2e test patterns
- Configures test discovery

### TypeScript Configuration (`vitest-unit.config.ts`)
- Defines which TypeScript test files to run
- Sets up Vitest with coverage
- Excludes integration/e2e test patterns
- Configures test environment

## 📈 Coverage Requirements

The framework enforces minimum coverage thresholds:
- **Python**: 70% minimum coverage
- **TypeScript**: 70% minimum coverage

Coverage reports include:
- **HTML Reports**: Interactive coverage reports
- **XML/JSON Data**: Machine-readable coverage data
- **Terminal Output**: Quick coverage summary

## 🛠️ Framework Architecture

```
UnitTestFramework
├── Python Test Runner
│   ├── Test Discovery
│   ├── Coverage Collection
│   └── Result Parsing
├── TypeScript Test Runner
│   ├── Vitest Configuration
│   ├── Coverage Collection
│   └── Result Parsing
├── Report Generator
│   ├── JSON Results
│   ├── HTML Summary
│   └── Coverage Reports
└── Unified Summary
    ├── Cross-language Results
    ├── Success/Failure Counts
    └── Coverage Aggregation
```

## 🎛️ Advanced Usage

### Custom Test Selection
You can modify the test lists in `scripts/run-unit-tests.py`:

```python
self.python_unit_tests = [
    'services/your-service/tests/test_your_unit_test.py',
    # Add more unit test files
]

self.typescript_unit_tests = [
    'services/your-service/src/__tests__/yourUnitTest.test.ts',
    # Add more unit test files
]
```

### Coverage Thresholds
Modify coverage requirements in the configuration files:

```ini
# pytest-unit.ini
--cov-fail-under=80  # Increase to 80%
```

```typescript
// vitest-unit.config.ts
thresholds: {
  global: {
    branches: 80,    // Increase to 80%
    functions: 80,
    lines: 80,
    statements: 80
  }
}
```

### Excluding Additional Tests
Add patterns to exclude in `scripts/run-unit-tests.py`:

```python
self.exclude_patterns = [
    'your_exclude_pattern',
    # Add more patterns
]
```

## 🔍 Troubleshooting

### Common Issues

1. **"No tests found"**
   - Check that test files match the patterns in configuration
   - Verify test files are in the correct directories

2. **"Import errors"**
   - Ensure all dependencies are installed
   - Check Python path configuration

3. **"Coverage not generated"**
   - Verify coverage tools are installed (`pytest-cov`, `vitest`)
   - Check that source files are in the correct locations

4. **"TypeScript tests fail"**
   - Ensure Node.js and npm are installed
   - Run `npm install` in the health-dashboard directory

### Debug Mode
Run with verbose output to see detailed execution:

```bash
python scripts/run-unit-tests.py --verbose
```

## 📝 Contributing

When adding new unit tests:

1. **Follow Naming Conventions**:
   - Python: `test_*.py` files
   - TypeScript: `*.test.ts` or `*.test.tsx` files

2. **Ensure Unit Test Criteria**:
   - No external dependencies
   - Fast execution (< 1 second per test)
   - Deterministic results
   - Isolated test cases

3. **Update Configuration**:
   - Add new test files to the appropriate lists
   - Update exclude patterns if needed

4. **Test Your Changes**:
   - Run the framework to ensure new tests are included
   - Verify coverage reports are generated correctly

## 📚 Related Documentation

- [Testing Strategy](docs/architecture/testing-strategy.md)
- [Code Quality Standards](docs/architecture/coding-standards.md)
- [Performance Patterns](docs/architecture/performance-patterns.md)

---

**Note**: This framework is designed specifically for unit tests. For integration tests, e2e tests, or visual tests, use the appropriate specialized test runners.
