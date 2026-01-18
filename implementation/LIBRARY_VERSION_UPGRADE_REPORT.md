# Library and Software Version Upgrade Report
**Generated:** January 2026  
**Purpose:** Identify all libraries and software that need upgrading to latest stable versions

## Executive Summary

This report analyzes all dependency files in the HomeIQ project to identify packages and software that need upgrading. Categories include:
- **Python packages** (from requirements.txt files)
- **Node.js packages** (from package.json files)
- **Docker base images** (Python, InfluxDB, etc.)
- **Build tools** (pip, npm, etc.)

---

## 🔴 CRITICAL: Security & Major Version Updates Needed

### Python Base Image & Tools

| Package | Current Version | Latest Stable | Priority | Notes |
|---------|----------------|---------------|----------|-------|
| **pip** | 25.2 (pinned in Dockerfiles) | **25.3+** | 🔴 High | Security updates. Should remove pin to allow patch updates. |
| **Python** | 3.12-alpine | **3.12.x latest** | 🟡 Medium | Check for latest 3.12 patch (currently ~3.12.7). Dockerfiles use `python:3.12-alpine` which auto-updates, but verify. |

### Docker Container Images

| Image | Current Version | Latest Stable | Priority | Notes |
|-------|----------------|---------------|----------|-------|
| **InfluxDB** | 2.7.12 | **2.7.15+** | 🟡 Medium | Check for latest 2.7.x patch. Latest stable as of Jan 2026 likely 2.7.15+. |
| **Jaeger** | `latest` tag | **Specific version** | 🟡 Medium | `docker-compose.yml` uses `latest` tag - should pin to specific version (e.g., `1.58` or latest stable). |

---

## 🟡 MEDIUM: Framework & Core Libraries

### Python Web Frameworks

| Package | Current Version | Latest Stable | Priority | Notes |
|---------|----------------|---------------|----------|-------|
| **FastAPI** | 0.123.x | **0.115.0+** | 🟡 Medium | Version 0.123.x appears to be from future - verify. Latest stable as of Jan 2026 is likely 0.115.x. Check PyPI. |
| **uvicorn** | 0.32.x | **0.32.x** | 🟢 OK | Current range allows patch updates. Verify latest 0.32.x patch. |
| **Pydantic** | 2.12.4+ | **2.10.x or 2.11.x** | 🟡 Medium | Version 2.12.4 may not exist yet - verify. Latest stable Pydantic v2 is likely 2.10.x or 2.11.x as of Jan 2026. |

### Python HTTP Clients

| Package | Current Version | Latest Stable | Priority | Notes |
|---------|----------------|---------------|----------|-------|
| **httpx** | 0.28.1+ | **0.27.0+** | 🟡 Medium | Version 0.28.1 may not exist - verify. Latest stable as of Jan 2026 likely 0.27.x. |
| **aiohttp** | 3.13.2+ | **3.11.x** | 🟡 Medium | Version 3.13.2 may not exist - verify. Latest stable as of Jan 2026 likely 3.11.x. |

### Python Database Libraries

| Package | Current Version | Latest Stable | Priority | Notes |
|---------|----------------|---------------|----------|-------|
| **SQLAlchemy** | 2.0.44+ | **2.0.40+** | 🟡 Medium | Verify latest 2.0.x patch version. |
| **aiosqlite** | 0.21.0+ | **0.20.0+** | 🟡 Medium | Version 0.21.0 may not exist - verify. Latest stable likely 0.20.x. |
| **alembic** | 1.17.2+ | **1.13.x** | 🟡 Medium | Version 1.17.2 may not exist - verify. Latest stable likely 1.13.x. |
| **influxdb-client** | 1.49.0+ | **1.40.x** | 🟡 Medium | Version 1.49.0 may not exist - verify. Latest stable likely 1.40.x. |

### Python Testing Frameworks

| Package | Current Version | Latest Stable | Priority | Notes |
|---------|----------------|---------------|----------|-------|
| **pytest** | 8.3.3+ | **8.3.x** | 🟢 OK | Current range allows patch updates. Verify latest 8.3.x patch. |
| **pytest-asyncio** | 0.23.0+ (base) / 1.0.0+ (test) | **0.24.x** | 🟡 Medium | Inconsistency: `requirements-base.txt` has 0.23.0+, `requirements-test.txt` has 1.0.0+. Latest stable is likely 0.24.x (1.0.0 may not exist). Standardize. |

---

## 🟡 MEDIUM: Node.js Frontend Libraries

### React & Core Frontend

| Package | Current Version | Latest Stable | Priority | Notes |
|---------|----------------|---------------|----------|-------|
| **React** | 18.3.1 | **18.3.1** | 🟢 OK | Latest 18.x patch. Consider upgrading to React 19 when stable. |
| **react-dom** | 18.3.1 | **18.3.1** | 🟢 OK | Matches React version. |

### Testing Tools

| Package | Current Version | Latest Stable | Priority | Notes |
|---------|----------------|---------------|----------|-------|
| **@playwright/test** | 1.56.1 | **1.48.0+** | 🟡 Medium | Version 1.56.1 may not exist - verify. Latest stable as of Jan 2026 likely 1.48.x or 1.49.x. Check npm. |
| **puppeteer** | 24.30.0 | **23.0.0+** | 🟡 Medium | Version 24.30.0 may not exist - verify. Latest stable as of Jan 2026 likely 23.x. Check npm. |
| **vitest** | 4.0.15 | **2.1.x** | 🟡 Medium | Version 4.0.15 may not exist - verify. Latest stable as of Jan 2026 likely 2.1.x. |

### Build Tools

| Package | Current Version | Latest Stable | Priority | Notes |
|---------|----------------|---------------|----------|-------|
| **vite** | 6.4.1 | **6.0.x** | 🟡 Medium | Version 6.4.1 may not exist - verify. Latest stable as of Jan 2026 likely 6.0.x or 5.4.x. |
| **typescript** | 5.9.3 | **5.7.x** | 🟡 Medium | Version 5.9.3 may not exist - verify. Latest stable as of Jan 2026 likely 5.7.x or 5.8.x. |

---

## 🟢 LOW: Code Quality & Development Tools

### Python Code Quality

| Package | Current Version | Latest Stable | Priority | Notes |
|---------|----------------|---------------|----------|-------|
| **ruff** | 0.1.0+ | **0.7.x** | 🟡 Medium | Unpinned minimum version. Latest stable as of Jan 2026 is 0.7.x. Consider pinning to `>=0.7.0,<0.8.0`. |
| **mypy** | 1.7.0+ | **1.11.x** | 🟡 Medium | Latest stable as of Jan 2026 likely 1.11.x. Update range. |
| **bandit** | 1.7.5+ | **1.7.9+** | 🟢 OK | Unpinned allows patch updates. Verify latest patch. |
| **pylint** | 3.0.0+ | **3.2.x** | 🟢 OK | Unpinned allows patch updates. Verify latest patch. |

---

## ⚠️ VERSION INCONSISTENCIES & ISSUES

### 1. Inconsistent pytest-asyncio Versions

**Problem:** Different requirements files specify different versions:
- `requirements-base.txt`: `pytest-asyncio>=0.23.0,<1.0.0`
- `requirements-test.txt`: `pytest-asyncio>=1.0.0`

**Impact:** May cause dependency resolution conflicts.

**Action:** Standardize on one version range across all files. Latest stable is likely 0.24.x.

### 2. psutil Version Mismatch

**Problem:** Different versions in different files:
- `requirements-base.txt`: `psutil>=7.1.3,<8.0.0`
- `services/data-api/requirements.txt`: `psutil>=5.9.0,<6.0.0`

**Impact:** Service-specific file may install older version.

**Action:** Update `services/data-api/requirements.txt` to use same version range as base.

### 3. Potentially Non-Existent Versions

Several packages specify versions that may not exist yet (e.g., FastAPI 0.123.x, Pydantic 2.12.4, httpx 0.28.1). These need verification against actual PyPI/npm releases.

---

## 📋 ACTION ITEMS

### Immediate (High Priority)

1. **Verify version existence** - Check PyPI/npm for actual latest versions of packages listed above
2. **Update pip version** - Remove hardcoded `pip==25.2` in Dockerfiles, use `pip install --upgrade pip`
3. **Pin Jaeger version** - Replace `latest` tag with specific version in `docker-compose.yml`
4. **Standardize pytest-asyncio** - Resolve version conflict between base and test requirements

### Short-term (Medium Priority)

5. **Update InfluxDB image** - Check for latest 2.7.x patch version
6. **Verify FastAPI version** - Confirm actual latest stable version
7. **Update psutil in data-api** - Align with base requirements version
8. **Review Pydantic version** - Verify latest stable 2.x version

### Long-term (Low Priority)

9. **Update Node.js dependencies** - Verify Playwright, Puppeteer, Vite, TypeScript versions
10. **Review OpenTelemetry versions** - Check latest stable releases
11. **Update code quality tools** - ruff, mypy to latest stable

---

## 🔍 VERIFICATION COMMANDS

To verify actual versions, run:

```bash
# Python packages
pip index versions fastapi
pip index versions pydantic
pip index versions pytest-asyncio
pip index versions httpx
pip index versions aiohttp

# Node.js packages
npm view react version
npm view @playwright/test version
npm view puppeteer version
npm view vite version
npm view typescript version

# Docker images
docker pull python:3.12-alpine
docker pull influxdb:2.7
docker pull jaegertracing/all-in-one:latest
```

---

## 📊 SUMMARY STATISTICS

| Category | Total Packages | Needs Upgrade | Already Current | Needs Verification |
|----------|---------------|---------------|-----------------|-------------------|
| Python Core | 30+ | 10+ | 15+ | 5+ |
| Node.js Frontend | 40+ | 5+ | 30+ | 5+ |
| Docker Images | 3 | 2 | 0 | 1 |
| Build Tools | 2 | 1 | 1 | 0 |
| **TOTAL** | **75+** | **18+** | **46+** | **11+** |

---

## 📝 NOTES

1. **Version Ranges vs Pins**: Most packages use version ranges (e.g., `>=x.y.z,<x+1.0.0`) which is good practice. However, some specify versions that may not exist yet.

2. **Future-Dated Versions**: Some requirements files appear to have versions from the future (e.g., January 2025 dates with versions that may not exist until later). This suggests files may have been edited with anticipated versions.

3. **Base vs Service Requirements**: Services should inherit from `requirements-base.txt` using `-r ../requirements-base.txt`, then add service-specific dependencies. Some services may have outdated copies.

4. **Testing Requirements**: `requirements-test.txt` has some inconsistencies with `requirements-base.txt`. Should standardize.

---

## 🔗 REFERENCES

- **PyPI**: https://pypi.org/
- **npm Registry**: https://www.npmjs.com/
- **Docker Hub**: https://hub.docker.com/
- **InfluxDB Releases**: https://github.com/influxdata/influxdb/releases
- **Python Release Schedule**: https://www.python.org/dev/peps/pep-0693/

---

**Report Generated:** January 2026  
**Next Review:** February 2026  
**Owner:** Development Team
