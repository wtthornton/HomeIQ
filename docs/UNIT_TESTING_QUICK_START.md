# 🧪 Unit Testing Framework - Quick Start Guide

## 🚀 Quick Commands

### Run All Unit Tests
```bash
# Simple execution (recommended)
python scripts/simple-unit-tests.py

# Cross-platform scripts
./run-unit-tests.sh                    # Linux/Mac
.\run-unit-tests.ps1                   # Windows
```

### Run Specific Test Types
```bash
# Python tests only
python scripts/simple-unit-tests.py --python-only

# TypeScript tests only
python scripts/simple-unit-tests.py --typescript-only
```

## 📊 What You'll See

### Visual Progress
```
================================================================================
HomeIQ Unit Testing Framework
================================================================================
Started: 2025-10-25 09:19:44
Results: C:\cursor\ha-ingestor\test-results
================================================================================
[INFO] [09:19:44] Starting Python unit tests...
[PASS] [09:19:45] Python tests completed successfully

================================================================================
UNIT TEST SUMMARY
================================================================================
[PASS] Python Tests: 150/150 passed (100.0%)
[PASS] TypeScript Tests: 10/11 passed (90.9%)
[PASS] Overall: 160/161 passed (99.4%)
[PASS] All unit tests passed!
Duration: 45.2 seconds
================================================================================
Coverage Reports:
   Python: test-results/coverage/python/index.html
   TypeScript: test-results/coverage/typescript/index.html
================================================================================
```

## 📁 Coverage Reports

After running tests, check these locations:

- **Python Coverage**: `test-results/coverage/python/index.html`
- **TypeScript Coverage**: `test-results/coverage/typescript/index.html`
- **Summary Report**: `test-results/unit-test-report.html`

## 🎯 What Tests Are Included

### Python Unit Tests (272+ tests)
- **Admin API**: Alerting, auth, config, devices, events, health, logging, metrics, monitoring, stats
- **AI Automation**: Safety validator, automation parser, co-occurrence detector
- **Calendar Service**: Event parser
- **Data API**: Models
- **Sports Data**: Stats calculator
- **WebSocket Ingestion**: Event processing, connection management
- **And many more services...**

### TypeScript Unit Tests
- **API Usage Calculator**: Utility function tests
- **Team Preferences Hook**: React hook tests
- **Statistics Hook**: Statistics hook tests

## ❌ What Tests Are Excluded

The framework automatically excludes:
- **Integration Tests**: Tests requiring external services
- **E2E Tests**: End-to-end tests requiring full system
- **Visual Tests**: Screenshot and visual regression tests
- **Smoke Tests**: System-wide health checks
- **Deployment Tests**: Infrastructure tests

## 🔧 Troubleshooting

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
```bash
# Run with verbose output
python scripts/simple-unit-tests.py --verbose
```

## 📚 Full Documentation

For complete documentation, see:
- [Unit Testing Framework Guide](docs/UNIT_TESTING_FRAMEWORK.md)
- [Development Environment Setup](docs/development-environment-setup.md)

## 🎉 Success!

If you see `[PASS] All unit tests passed!` - you're good to go! The framework has successfully run all unit tests and generated coverage reports.

---

**Need help?** Check the troubleshooting section above or refer to the full documentation.
