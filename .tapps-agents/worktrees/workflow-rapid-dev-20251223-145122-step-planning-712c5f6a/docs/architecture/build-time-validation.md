# Build-Time Validation Guide

**Last Updated:** November 28, 2025  
**Epic:** Epic 44 - Development Experience Build-Time Validation  
**Status:** ✅ Complete

---

## Overview

This guide explains the build-time validation tools added in Epic 44 to catch errors early in the development cycle. These tools help prevent runtime import failures and improve development velocity.

---

## Tools Overview

### 1. Static Type Checking (mypy)

**Purpose:** Catch type errors before runtime

**Location:** `pyproject.toml` (mypy configuration)

**Usage:**
```bash
# Run type checking
mypy services/

# Check specific service
mypy services/device-intelligence-service/

# Check with strict mode (future)
mypy --strict services/
```

**Configuration:**
- Python 3.11+ support
- Async/await patterns enabled
- Gradual adoption (lenient initially, tighten over time)
- Per-module overrides for tests and scripts

**Current Status:**
- ✅ Configured in `pyproject.toml`
- ✅ Supports Python 3.11+ async/await
- 📋 Type hints being added gradually to critical modules

---

### 2. Import Validation

**Purpose:** Validate all imports before deployment

**Script:** `scripts/validate_imports.py`

**Usage:**
```bash
# Validate all services
python scripts/validate_imports.py

# Validate specific service
python scripts/validate_imports.py --service device-intelligence-service

# Skip specific service
python scripts/validate_imports.py --skip ai-automation-service

# Skip validation (for testing)
python scripts/validate_imports.py --skip-import-check
```

**What it does:**
- Finds all Python files in a service
- Extracts import statements
- Validates imports can be resolved
- Reports broken imports with clear error messages

**Integration:**
- Can be run during Docker build
- Can be added to CI/CD pipeline
- Can be run manually before deployment

---

### 3. Service Startup Tests

**Purpose:** Validate services can start without errors

**Script:** `scripts/test_service_startup.py`

**Usage:**
```bash
# Test all services
python scripts/test_service_startup.py

# Test specific service
python scripts/test_service_startup.py --service websocket-ingestion

# Skip specific service
python scripts/test_service_startup.py --skip weather-api

# Test without Docker (services already running)
python scripts/test_service_startup.py --no-docker

# Skip startup tests
python scripts/test_service_startup.py --skip-startup-tests
```

**What it does:**
- Checks if services can start (Docker containers)
- Validates configuration loading
- Tests health check endpoints
- Reports startup failures with clear messages

**Service Configuration:**
- Port numbers
- Health endpoint paths
- Startup timeouts
- Critical vs optional classification

**Integration:**
- Can be run in CI/CD pipeline
- Can be run before deployment
- Can be run manually for testing

---

## Integration with Docker Build

### Adding to Dockerfile

Add import validation to your Dockerfile:

```dockerfile
# Validate imports before building
RUN python scripts/validate_imports.py --service <service-name> || exit 1
```

### Adding to docker-compose.yml

Add startup tests to docker-compose:

```yaml
services:
  validation:
    build: .
    command: python scripts/test_service_startup.py
    depends_on:
      - websocket-ingestion
      - device-intelligence-service
      # ... other services
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Build-Time Validation

on: [push, pull_request]

jobs:
  type-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install mypy
      - run: mypy services/

  import-validation:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements-quality.txt
      - run: python scripts/validate_imports.py

  startup-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install aiohttp
      - run: docker compose up -d
      - run: python scripts/test_service_startup.py
      - run: docker compose down
```

---

## Gradual Adoption Strategy

### Phase 1: Critical Services (Current)

**Focus:**
- Services that had import errors (device-intelligence-service, websocket-ingestion)
- Public APIs and interfaces
- New code

**Approach:**
- Lenient mypy configuration
- Type hints added incrementally
- Import validation enabled
- Startup tests for critical services

### Phase 2: Expand Coverage

**Focus:**
- All critical services
- More strict type checking
- Comprehensive startup tests

**Approach:**
- Increase mypy strictness
- Add type hints to more modules
- Expand startup test coverage

### Phase 3: Full Coverage

**Focus:**
- All services
- Strict type checking
- Complete test coverage

**Approach:**
- Strict mypy configuration
- Type hints everywhere
- All services tested

---

## Troubleshooting

### Type Checking Issues

**Problem:** Too many type errors

**Solution:**
- Start with lenient configuration
- Add `# type: ignore` comments where needed
- Gradually add type hints
- Use per-module overrides

**Problem:** Missing type stubs

**Solution:**
- Install type stubs: `pip install types-requests types-aiohttp`
- Use `ignore_missing_imports = true` for problematic modules
- Add to mypy overrides

### Import Validation Issues

**Problem:** False positives for relative imports

**Solution:**
- Relative imports are noted but not fully validated
- They're validated at runtime
- This is expected behavior

**Problem:** Third-party packages not found

**Solution:**
- Ensure virtual environment is activated
- Install dependencies before validation
- Use `--skip` for problematic services

### Startup Test Issues

**Problem:** Services take too long to start

**Solution:**
- Increase timeout in SERVICE_CONFIGS
- Check service logs for issues
- Verify Docker containers are healthy

**Problem:** Health endpoints not responding

**Solution:**
- Verify service is actually running
- Check port configuration
- Verify health endpoint path

---

## Best Practices

### Type Checking

1. **Start Lenient:** Begin with lenient configuration
2. **Add Gradually:** Add type hints incrementally
3. **Focus on APIs:** Prioritize public interfaces
4. **Use Overrides:** Use per-module overrides for legacy code

### Import Validation

1. **Run Before Build:** Validate imports during Docker build
2. **Fix Immediately:** Don't ignore import errors
3. **Test Locally:** Run validation before committing
4. **CI/CD Integration:** Add to CI/CD pipeline

### Startup Tests

1. **Test Critical First:** Focus on critical services
2. **Use Timeouts:** Set appropriate timeouts
3. **Check Logs:** Review service logs on failure
4. **Automate:** Run in CI/CD pipeline

---

## Related Documentation

- **Epic 44:** Development Experience Build-Time Validation
- **Coding Standards:** `docs/architecture/coding-standards.md`
- **Tech Stack:** `docs/architecture/tech-stack.md`
- **Production Readiness:** `docs/architecture/production-readiness-components.md`

---

## Configuration Files

- **mypy:** `pyproject.toml` (tool.mypy section)
- **Import Validation:** `scripts/validate_imports.py`
- **Startup Tests:** `scripts/test_service_startup.py`
- **Quality Tools:** `requirements-quality.txt`

---

**Document Created:** November 28, 2025  
**Epic:** Epic 44  
**Status:** ✅ Complete

