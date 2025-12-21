# HomeIQ Version Audit Report
**Date:** January 2025  
**Scope:** Runtime and library versions across all services

## Executive Summary

This report identifies runtime and library versions that need updating across the HomeIQ project. Key findings:
- **4 device services** still using Python 3.11 (should upgrade to 3.12)
- **Node.js 18** used in some Dockerfiles (EOL April 2025)
- **InfluxDB 2.7.12** may have newer versions available
- **Mixed pip versions** (all using pip 25.2 - current)
- **Various Python package version inconsistencies** across services

---

## 1. Runtime Versions

### 1.1 Python Runtime Versions

#### ❌ **REQUIRES UPDATE: Python 3.11 Services**

The following services are still using Python 3.11 and should be upgraded to 3.12 for consistency and security:

| Service | Current Version | Recommended | Priority | Dockerfile Location |
|---------|----------------|-------------|----------|-------------------|
| `device-health-monitor` | 3.11-slim | 3.12-slim | **HIGH** | `services/device-health-monitor/Dockerfile` |
| `device-context-classifier` | 3.11-slim | 3.12-slim | **HIGH** | `services/device-context-classifier/Dockerfile` |
| `device-database-client` | 3.11-slim | 3.12-slim | **HIGH** | `services/device-database-client/Dockerfile` |
| `device-recommender` | 3.11-slim | 3.12-slim | **HIGH** | `services/device-recommender/Dockerfile` |
| `device-setup-assistant` | 3.11-slim | 3.12-slim | **HIGH** | `services/device-setup-assistant/Dockerfile` |

**Action Required:**
- Update `FROM python:3.11-slim` to `FROM python:3.12-slim` in all 5 Dockerfiles above
- Test each service after upgrade

#### ✅ **UP TO DATE: Python 3.12 Services**

Most services are correctly using Python 3.12:
- `websocket-ingestion` ✅
- `data-api` ✅
- `admin-api` ✅
- `ai-automation-service` ✅
- `ai-core-service` ✅
- `ml-service` ✅
- `openvino-service` ✅
- And 20+ other services ✅

#### ⚠️ **NOTICE: Development Dockerfiles**

Some dev Dockerfiles still use Python 3.11:
- `services/data-api/Dockerfile.dev` → 3.11-alpine (should be 3.12)
- `services/data-retention/Dockerfile.dev` → 3.11-slim (should be 3.12)
- `services/admin-api/Dockerfile.dev` → 3.11-slim (should be 3.12)
- `services/websocket-ingestion/Dockerfile.dev` → 3.11-slim (should be 3.12)

**Action:** Update dev Dockerfiles to match production versions (3.12).

---

### 1.2 Node.js Runtime Versions

#### ⚠️ **REQUIRES UPDATE: Node.js 18 (EOL April 2025)**

| Service | Current Version | Recommended | Priority | Location |
|---------|----------------|-------------|----------|----------|
| References in README files | 18-alpine | 20.11.0-alpine or 22.x LTS | **HIGH** | `services/health-dashboard/README.md`, `services/ai-automation-ui/README.md` |

**Note:** Actual Dockerfiles use Node.js 20.11.0, but README examples show Node 18.

#### ✅ **UP TO DATE: Node.js 20.11.0**

Production Dockerfiles correctly use Node.js 20.11.0:
- `services/health-dashboard/Dockerfile` ✅
- `services/ai-automation-ui/Dockerfile` ✅

**Recommendation:** Consider upgrading to Node.js 22 LTS when stable (2025).

---

### 1.3 Other Runtime Versions

#### ✅ **InfluxDB**

- **Current:** `influxdb:2.7.12` (docker-compose.yml line 5)
- **Status:** Recent version, check for 2.8.x or later in 2025
- **Action:** Monitor for InfluxDB 2.8.x releases

#### ✅ **pip Version**

- **Current:** `pip==25.2` (all Dockerfiles)
- **Status:** Latest version ✅
- **Action:** None required

---

## 2. Python Library Versions

### 2.1 Web Framework Libraries

#### FastAPI

| Service | Current | Recommended | Status |
|---------|---------|-------------|--------|
| Most services | `>=0.123.0,<0.124.0` | `>=0.115.0,<0.116.0` or latest stable | ⚠️ **Check if 0.124.0+ available** |

**Action:** Verify latest FastAPI stable version (likely 0.115.x or higher).

#### Uvicorn

| Service | Current | Recommended | Status |
|---------|---------|-------------|--------|
| Most services | `>=0.32.0,<0.33.0` | Latest stable | ⚠️ **Check for newer versions** |

**Action:** Check for uvicorn 0.33.0+ or latest stable.

---

### 2.2 Data Validation Libraries

#### Pydantic

| Service | Current | Recommended | Status |
|---------|---------|-------------|--------|
| `websocket-ingestion` | `==2.12.4` | Latest 2.x | ⚠️ **Pinned version** |
| `data-api` | `==2.12.4` | Latest 2.x | ⚠️ **Pinned version** |
| `device-intelligence-service` | `==2.12.4` | Latest 2.x | ⚠️ **Pinned version** |
| `ai-automation-service` | `>=2.9.0,<3.0.0` | Latest 2.x | ✅ **Flexible range** |

**Action:** 
- Unpin `pydantic==2.12.4` to `>=2.12.4,<3.0.0` for flexibility
- Check for Pydantic 2.13.0+ updates

---

### 2.3 Database Libraries

#### SQLAlchemy

| Service | Current | Recommended | Status |
|---------|---------|-------------|--------|
| `data-api` | `==2.0.44` | Latest 2.0.x | ⚠️ **Pinned version** |
| `device-intelligence-service` | `==2.0.44` | Latest 2.0.x | ⚠️ **Pinned version** |
| `ai-automation-service` | `>=2.0.35,<3.0.0` | Latest 2.0.x | ✅ **Flexible range** |

**Action:** 
- Check for SQLAlchemy 2.0.45+ updates
- Consider using ranges instead of pinned versions for patch updates

#### aiosqlite

| Service | Current | Recommended | Status |
|---------|---------|-------------|--------|
| `data-api` | `==0.21.0` | Latest 0.21.x | ⚠️ **Pinned version** |
| `device-intelligence-service` | `==0.21.0` | Latest 0.21.x | ⚠️ **Pinned version** |
| `ai-automation-service` | `>=0.20.0,<0.21.0` | `>=0.21.0,<0.22.0` | ⚠️ **Outdated range** |

**Action:** 
- Update `ai-automation-service` range to `>=0.21.0,<0.22.0`
- Check for aiosqlite 0.22.0+ updates

---

### 2.4 HTTP Client Libraries

#### httpx

| Service | Current | Recommended | Status |
|---------|---------|-------------|--------|
| Most services | `>=0.28.1,<0.29.0` | Latest 0.29.x or 0.30.x | ⚠️ **May be outdated** |

**Action:** Check for httpx 0.29.0+ or 0.30.0+ releases.

#### aiohttp

| Service | Current | Recommended | Status |
|---------|---------|-------------|--------|
| `websocket-ingestion` | `==3.13.2` | Latest 3.13.x | ⚠️ **Pinned version** |
| `data-api` | `==3.13.2` | Latest 3.13.x | ⚠️ **Pinned version** |
| `device-intelligence-service` | `==3.13.2` | Latest 3.13.x | ⚠️ **Pinned version** |
| `ai-automation-service` | `>=3.13.2,<4.0.0` | Latest 3.13.x | ✅ **Flexible range** |

**Action:** 
- Unpin `aiohttp==3.13.2` to `>=3.13.2,<4.0.0` for patch updates
- Check for aiohttp 3.14.0+ updates

---

### 2.5 Machine Learning Libraries

#### PyTorch

| Service | Current | Recommended | Status |
|---------|---------|-------------|--------|
| `ai-automation-service` | `>=2.4.0,<3.0.0` | Latest 2.5.x or 2.6.x | ⚠️ **Check for updates** |

**Action:** Check for PyTorch 2.5.0+ or 2.6.0+ updates (CPU-only).

#### transformers

| Service | Current | Recommended | Status |
|---------|---------|-------------|--------|
| `ai-automation-service` | `>=4.46.1,<5.0.0` | Latest 4.x | ⚠️ **Check for updates** |

**Action:** Check for transformers 4.47.0+ updates.

#### scikit-learn

| Service | Current | Recommended | Status |
|---------|---------|-------------|--------|
| `ai-automation-service` | `>=1.5.0,<2.0.0` | Latest 1.5.x | ⚠️ **Check for updates** |
| `device-intelligence-service` | `>=1.5.0,<2.0.0` | Latest 1.5.x | ⚠️ **Check for updates** |

**Action:** Check for scikit-learn 1.5.1+ updates.

---

### 2.6 Testing Libraries

#### pytest

| Service | Current | Recommended | Status |
|---------|---------|-------------|--------|
| `websocket-ingestion` | `==8.3.3` | Latest 8.x or 9.x | ⚠️ **Pinned version** |
| `data-api` | `==8.3.3` | Latest 8.x or 9.x | ⚠️ **Pinned version** |
| `device-intelligence-service` | `==8.3.3` | Latest 8.x or 9.x | ⚠️ **Pinned version** |
| `ai-automation-service` | `>=8.3.0,<9.0.0` | Latest 8.x or 9.x | ✅ **Flexible range** |

**Action:** 
- Check for pytest 8.3.4+ or 9.0.0+ updates
- Consider un-pinning for patch updates

---

## 3. Node.js Library Versions

### 3.1 React Ecosystem

#### React & React DOM

| Package | Location | Current | Recommended | Status |
|---------|----------|---------|-------------|--------|
| `react` | `health-dashboard` | `^18.3.1` | React 19 (if stable) or latest 18.x | ⚠️ **Check for React 19** |
| `react` | `ai-automation-ui` | `^18.3.1` | React 19 (if stable) or latest 18.x | ⚠️ **Check for React 19** |

**Action:** 
- Check React 19 release status (may be stable in 2025)
- Update to latest React 18.x patch versions if React 19 not ready

---

### 3.2 Build Tools

#### Vite

| Package | Location | Current | Recommended | Status |
|---------|----------|---------|-------------|--------|
| `vite` | `health-dashboard` | `^5.4.8` | Latest 5.x or 6.x | ⚠️ **Check for updates** |
| `vite` | `ai-automation-ui` | `^6.4.1` | Latest 6.x | ✅ **Recent version** |

**Action:** 
- Update `health-dashboard` to Vite 6.x to match `ai-automation-ui`
- Check for Vite 6.5.0+ updates

#### TypeScript

| Package | Location | Current | Recommended | Status |
|---------|----------|---------|-------------|--------|
| `typescript` | `health-dashboard` | `^5.6.3` | Latest 5.7.x or 5.8.x | ⚠️ **Check for updates** |
| `typescript` | `ai-automation-ui` | `^5.9.3` | Latest 5.10.x | ⚠️ **Check for updates** |

**Action:** Update to latest TypeScript 5.x patch versions.

---

### 3.3 Testing Libraries

#### Playwright

| Package | Location | Current | Recommended | Status |
|---------|----------|---------|-------------|--------|
| `@playwright/test` | Root `package.json` | `^1.56.1` | Latest 1.57.x or 1.58.x | ⚠️ **Check for updates** |
| `@playwright/test` | `health-dashboard` | `^1.56.1` | Latest 1.57.x or 1.58.x | ⚠️ **Check for updates** |

**Action:** Update to latest Playwright 1.x patch versions.

---

## 4. Version Consistency Issues

### 4.1 Pinned vs. Ranged Versions

**Issue:** Mixed version pinning strategies across services.

**Examples:**
- `websocket-ingestion`: Pins `pydantic==2.12.4`, `aiohttp==3.13.2`
- `ai-automation-service`: Uses ranges `pydantic>=2.9.0,<3.0.0`, `aiohttp>=3.13.2,<4.0.0`

**Recommendation:** 
- Use version ranges for patch updates (e.g., `>=2.12.4,<3.0.0`)
- Pin major.minor for security-critical dependencies
- Document version pinning strategy in development guide

---

### 4.2 Version Misalignment

**Issue:** Same libraries with different versions across services.

**Examples:**
- `pytest`: `==8.3.3` (pinned) vs `>=8.3.0,<9.0.0` (ranged)
- `pydantic`: `==2.12.4` (pinned) vs `>=2.9.0,<3.0.0` (ranged)
- `aiosqlite`: `==0.21.0` (pinned) vs `>=0.20.0,<0.21.0` (outdated range)

**Recommendation:**
- Standardize version constraints across all services
- Create a shared `requirements-base.txt` with common dependencies
- Use service-specific `requirements.txt` files that extend base

---

## 5. Priority Recommendations

### 🔴 **HIGH PRIORITY (Security & Compatibility)**

1. **Upgrade Python 3.11 services to 3.12** (5 services)
   - `device-health-monitor`
   - `device-context-classifier`
   - `device-database-client`
   - `device-recommender`
   - `device-setup-assistant`

2. **Update development Dockerfiles** (4 files)
   - Match production Python versions (3.12)

3. **Update Node.js references**
   - Remove Node 18 references from README files
   - Document Node.js 20.11.0 or 22 LTS as standard

---

### 🟡 **MEDIUM PRIORITY (Maintenance)**

4. **Unpin Python library versions**
   - Change `==` to `>=` ranges for patch updates
   - Keep major.minor pinned for stability
   - Examples: `pydantic`, `aiohttp`, `pytest`, `sqlalchemy`

5. **Update outdated version ranges**
   - `ai-automation-service`: Update `aiosqlite>=0.20.0,<0.21.0` to `>=0.21.0,<0.22.0`

6. **Standardize version constraints**
   - Create shared base requirements file
   - Align versions across services

---

### 🟢 **LOW PRIORITY (Optimization)**

7. **Check for library updates**
   - FastAPI (check 0.124.0+ availability)
   - Uvicorn (check 0.33.0+ availability)
   - React (check React 19 status)
   - Vite (update health-dashboard to 6.x)
   - TypeScript (update to latest 5.x patches)
   - Playwright (update to latest 1.x patches)

8. **Monitor InfluxDB updates**
   - Check for InfluxDB 2.8.x releases

---

## 6. Action Plan

### Phase 1: Critical Updates (Week 1)
- [ ] Upgrade 5 Python 3.11 services to 3.12
- [ ] Update 4 development Dockerfiles to Python 3.12
- [ ] Test all upgraded services

### Phase 2: Standardization (Week 2)
- [ ] Create shared `requirements-base.txt`
- [ ] Unpin patch-level versions (use ranges)
- [ ] Update outdated version ranges
- [ ] Document version management strategy

### Phase 3: Library Updates (Week 3-4)
- [ ] Audit and update Python libraries
- [ ] Update Node.js dependencies
- [ ] Test thoroughly after updates

---

## 7. Testing Requirements

After each update phase:
1. **Unit Tests**: Run `python scripts/simple-unit-tests.py`
2. **Integration Tests**: Run service health checks
3. **End-to-End Tests**: Run `npm run test:e2e` for UI services
4. **Docker Builds**: Verify all services build successfully
5. **Deployment Test**: Deploy to staging and verify functionality

---

## 8. Version Management Best Practices

### Recommended Strategy

1. **Use version ranges** for patch updates: `>=x.y.z,<x+1.0.0`
2. **Pin major.minor** for critical dependencies: Document in comments
3. **Regular audits**: Review versions quarterly
4. **Automated updates**: Consider Dependabot or Renovate for dependency updates
5. **Shared base**: Create `requirements-base.txt` for common dependencies

### Example Version Constraints

```python
# ✅ GOOD: Flexible patch updates
fastapi>=0.123.0,<0.124.0
pydantic>=2.12.4,<3.0.0

# ⚠️ ACCEPTABLE: Pinned for critical dependencies (document why)
pydantic==2.12.4  # Pinned due to breaking changes in 2.13.0

# ❌ BAD: Too restrictive
pydantic==2.12.4  # Without justification

# ❌ BAD: Too permissive
pydantic>=2.9.0  # No upper bound
```

---

## 9. Automated Update Tools

Consider implementing:
- **Dependabot**: Automated dependency update PRs
- **Renovate**: More configurable than Dependabot
- **pip-audit**: Security vulnerability scanning
- **npm audit**: Node.js security scanning

---

## 10. References

- Python 3.12 Release: https://www.python.org/downloads/
- Node.js 22 LTS: https://nodejs.org/
- InfluxDB Releases: https://github.com/influxdata/influxdb/releases
- FastAPI Releases: https://github.com/tiangolo/fastapi/releases
- React 19: https://react.dev/blog

---

## Appendix: Complete Service Version Matrix

| Service | Python | Node.js | Key Libraries | Status |
|---------|--------|---------|---------------|--------|
| `websocket-ingestion` | 3.12 ✅ | N/A | FastAPI 0.123, Pydantic 2.12.4 (pinned) | ⚠️ Unpin versions |
| `data-api` | 3.12 ✅ | N/A | FastAPI 0.123, SQLAlchemy 2.0.44 (pinned) | ⚠️ Unpin versions |
| `device-intelligence-service` | 3.12 ✅ | N/A | FastAPI 0.123, Pydantic 2.12.4 (pinned) | ⚠️ Unpin versions |
| `ai-automation-service` | 3.12 ✅ | N/A | FastAPI 0.123, Pydantic >=2.9.0 | ✅ Good |
| `device-health-monitor` | 3.11 ❌ | N/A | FastAPI | 🔴 **UPGRADE** |
| `device-context-classifier` | 3.11 ❌ | N/A | FastAPI | 🔴 **UPGRADE** |
| `device-database-client` | 3.11 ❌ | N/A | FastAPI | 🔴 **UPGRADE** |
| `device-recommender` | 3.11 ❌ | N/A | FastAPI | 🔴 **UPGRADE** |
| `device-setup-assistant` | 3.11 ❌ | N/A | FastAPI | 🔴 **UPGRADE** |
| `health-dashboard` | N/A | 20.11.0 ✅ | React 18.3.1, Vite 5.4.8 | ⚠️ Update Vite to 6.x |
| `ai-automation-ui` | N/A | 20.11.0 ✅ | React 18.3.1, Vite 6.4.1 | ✅ Good |

---

**Report Generated:** January 2025  
**Next Review:** April 2025

