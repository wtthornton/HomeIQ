# HomeIQ Library Upgrade Plan - February 2026

## Executive Summary

This plan outlines a phased approach to upgrade all dependencies in the HomeIQ project to their latest stable, production-ready versions while ensuring compatibility across all services.

**Project Scope:**
- 45+ Python microservices with shared dependencies
- 2 Node.js/React frontend applications
- Mixed dependency versions causing potential compatibility issues

**Key Goals:**
- Standardize versions across all services
- Upgrade to latest stable production versions
- Ensure compatibility between dependent libraries
- Minimize breaking changes through careful sequencing

**Important:** This plan covers only third-party open-source dependencies (PyPI/npm packages). Internal tapps-agents framework components are excluded and will be updated separately.

---

## Current State Analysis

### Python Services Status

#### Critical Version Conflicts Identified

1. **FastAPI**: 0.115.0 (automation-linter) vs >=0.123.0 (7 services) - **8 versions behind**
2. **Pydantic**: Multiple versions (2.8.2, 2.9.2, 2.12.4) - **Inconsistent**
3. **pydantic-settings**: 2.1.0 (calendar-service) vs 2.12.0 (newer services) - **11 versions behind**
4. **httpx**: 0.27.x (2 services) vs 0.28.1 (6 services) - **Minor version split**
5. **aiosqlite**: 0.20.x vs 0.21.x - **Compatibility concerns with SQLAlchemy**

#### Services Requiring Priority Attention

1. **automation-linter** - Multiple outdated packages
2. **calendar-service** - Very old pydantic-settings version
3. **CLI tool** - Slightly behind on several packages

### Node.js Services Status

#### health-dashboard & ai-automation-ui

**Overall Status:** Reasonably current, mostly minor updates needed

**Key Findings:**
- React 18.3.1 (current stable, React 19 available but breaking)
- Vite 6.4.1 (Vite 7 available, requires Node.js 20.19+)
- All Radix UI packages up to date
- TypeScript 5.9.3 (latest: 5.8.x - actually ahead!)
- Most testing libraries current or near-current

---

## Recommended Upgrade Strategy

### Phase 1: Critical Compatibility Fixes (Week 1)

**Goal:** Fix version conflicts and update packages with known security/compatibility issues

#### Python Services

**Priority 1A: SQLAlchemy Ecosystem**
```
# Update these together to ensure compatibility
sqlalchemy: 2.0.35+ → 2.0.46
aiosqlite: 0.20.x/0.21.x → 0.22.1
alembic: 1.13.x/1.14.x → 1.18.3
```

**Services affected:** automation-miner, ai-pattern-service, ha-ai-agent-service

**Why first:** aiosqlite 0.22.0 changed from threading.Thread to futures, requiring SQLAlchemy 2.0.46+

**Priority 1B: FastAPI Core**
```
fastapi: → 0.119.0+ (with [standard] extra)
pydantic: → 2.12.0
pydantic-settings: → 2.12.0
httpx: → 0.28.1
uvicorn: → (included with fastapi[standard])
```

**Services affected:** All FastAPI services (8+ services)

**Critical service:** automation-linter (most outdated)

**Why critical:** FastAPI 0.119+ requires Python 3.9+ and fully embraces Pydantic v2

#### Node.js Services

**Priority 1C: Build Tools Compatibility**
```
@vitejs/plugin-react: 4.7.0 → 5.1.2
typescript-eslint: 8.48.0 → 8.53.0
```

**Services affected:** health-dashboard, ai-automation-ui

**Why first:** These are non-breaking updates that fix bugs and improve compatibility

**Risk Level:** LOW

---

### Phase 2: Standard Library Updates (Week 2)

**Goal:** Bring all common dependencies to consistent, latest stable versions

#### Python Services

**HTTP & Networking**
```
aiohttp: 3.13.2/3.13.3 → 3.13.3 (standardize)
websockets: 12.0 → 16.0 (BREAKING: requires Python 3.10+)
```

**Note:** websockets 16.0 requires Python 3.10 minimum. Check Python version across all services first.

**Testing Framework**
```
pytest: 8.3.x → 9.0.2
pytest-asyncio: 0.23.0/0.24.0 → 1.3.0 (BREAKING in 1.0.0)
pytest-cov: 4.1.0/5.0.0 → 5.0.0 (standardize)
pytest-httpx: → 0.30.0+
pytest-mock: 3.14.0 → 3.14.0 (current)
```

**Breaking changes in pytest-asyncio 1.0.0:** Review migration guide

**Utilities**
```
python-dotenv: 1.0.1/1.2.1 → 1.2.1 (standardize)
pyyaml: 6.0.1/6.0.2 → 6.0.3
tenacity: 8.2.3/8.3.0 → 9.1.2 (MAJOR VERSION)
jinja2: 3.1.4 → 3.1.6
click: 8.1.7 → 8.3.1
typer: 0.12.3 → 0.21.1
rich: 13.7.1 → 14.3.2
```

**Database Clients**
```
influxdb3-python: 0.3.0 → 0.17.0 (with [pandas] extra if needed)
```

**Parsing & Processing**
```
beautifulsoup4: 4.14.2 → 4.14.3
lxml: 6.0.2 → 6.0.2 (current)
rapidfuzz: 3.14.3 → 3.14.3 (current)
```

**Other**
```
python-multipart: 0.0.9 → 0.0.22
docker: 7.1.0 → 7.1.0 (current)
apscheduler: 3.10.0 → 3.11.2 (stay on 3.x, 4.x has breaking changes)
```

**MQTT** (Important package rename)
```
asyncio-mqtt: 0.16.1 → MIGRATE TO aiomqtt: 2.4.0
paho-mqtt: 1.6.0 → 2.1.0
```

**Action required:** Update imports from `asyncio_mqtt` to `aiomqtt` in ha-simulator and ai-pattern-service

#### Node.js Services

**Testing Libraries**
```
vitest: 4.0.15 → 4.0.17
@playwright/test: 1.56.1 → 1.58.1
@testing-library/react: 16.3.0 → 16.3.1
happy-dom: 20.0.11 → 20.5.0
msw: 2.12.1 → 2.12.8
```

**Other Updates**
```
react-use-websocket: 4.9.1 → 4.13.0
lucide-react: 0.562.0 → (check latest)
chart.js: 4.5.1 → (check latest 4.x)
react-chartjs-2: 5.3.0 → 5.3.1
```

**Risk Level:** LOW to MEDIUM

---

### Phase 3: ML/AI Libraries (Week 3)

**Goal:** Update ML/AI stack with awareness of breaking changes

**CRITICAL:** Major version upgrades require careful testing

```
numpy: 1.26.x → 2.4.2 (MAJOR VERSION - breaking changes)
pandas: 2.2.x → 3.0.0 (MAJOR VERSION - breaking changes)
scikit-learn: 1.5.x → 1.8.0
scipy: 1.16.3 → 1.17.0
```

**Services affected:** ml-service, ai-pattern-service

**Breaking Changes:**

**NumPy 2.0:**
- Changed dtypes, modified array semantics
- Most libraries now compatible, but test thoroughly
- Review migration guide: https://numpy.org/devdocs/numpy_2_0_migration_guide.html

**Pandas 3.0:**
- Dedicated string data type (backed by PyArrow) enabled by default
- Requires NumPy 2.x
- Minimum Python 3.10 recommended
- Review breaking changes: https://pandas.pydata.org/docs/dev/whatsnew/v3.0.0.html

**Recommendation:** Create test environment first, validate all ML models and pipelines

**OpenAI SDK**
```
openai: 1.54.0 → 2.16.0 (MAJOR VERSION)
tiktoken: 0.8.0 → 0.12.0
```

**Services affected:** ha-ai-agent-service

**Note:** OpenAI SDK 2.16.0 marks assistants API as deprecated

**Risk Level:** HIGH (extensive testing required)

---

### Phase 4: Frontend Major Updates (Week 4)

**Goal:** Plan and execute major version upgrades for frontend services

#### Option A: Conservative (Recommended for Production)

Stay on current major versions, apply all minor/patch updates:

```json
{
  "react": "^18.3.1",
  "react-dom": "^18.3.1",
  "vite": "^6.4.1",
  "typescript": "^5.9.3",
  "tailwindcss": "^3.4.18"
}
```

**Risk Level:** LOW
**Benefit:** Stability, minimal testing required

#### Option B: Aggressive (For New Development/Testing)

Upgrade to latest major versions:

```json
{
  "react": "^19.2.4",
  "react-dom": "^19.2.4",
  "@types/react": "^19.2.8",
  "@types/react-dom": "^19.2.3",
  "vite": "^7.3.1",
  "tailwindcss": "^4.x"
}
```

**Prerequisites:**
- Node.js 20.19+ or 22.12+ (for Vite 7)
- Extensive testing of React 19 changes
- Tailwind CSS v4 migration (different import system)

**React 19 Breaking Changes:**
- Improved concurrent rendering
- New `use()` hook for reading promises/context
- Automatic batching improvements
- `ref` as prop (no more `forwardRef` needed)
- New `useFormStatus`, `useFormState`, `useOptimistic` hooks
- Server Components support

**Vite 7 Breaking Changes:**
- Node.js 20.19+ / 22.12+ required
- Browser target: 'baseline-widely-available' (Chrome 125+, Edge 125+, Firefox 119+, Safari 17.5+)
- Changed default dev server host from 'localhost' to '127.0.0.1'

**Tailwind CSS v4 Breaking Changes:**
- Autoprefixer no longer required (handled automatically)
- New import system: `@import "tailwindcss";` instead of separate directives
- Configuration via CSS variables instead of `tailwind.config.js`

**Risk Level:** HIGH
**Benefit:** Access to latest features, better performance

**Recommendation:** Start with Option A, plan Option B for future sprint

---

## Python Version Requirements

**Critical Decision Point:** Many newer package versions require Python 3.10+

### Current Minimum Requirements by Package:
- websockets 16.0: Python 3.10+
- pandas 3.0: Python 3.10+ (recommended)
- Most other packages: Python 3.8+

### Recommended Python Versions:
- **Minimum**: Python 3.10 (for full compatibility)
- **Target**: Python 3.11 or 3.12 (best performance and compatibility)
- **Avoid**: Python 3.8 (end of life, packages dropping support)

**Action Required:** Audit all services for Python version, upgrade infrastructure if needed

---

## Compatibility Matrix

### Python Core Stack (Tested Combinations)

| Package | Version | Compatible With |
|---------|---------|-----------------|
| fastapi | 0.119.0+ | pydantic 2.12.0+, uvicorn (bundled), httpx 0.28.1+ |
| pydantic | 2.12.0 | pydantic-settings 2.12.0, fastapi 0.119.0+ |
| sqlalchemy | 2.0.46 | aiosqlite 0.22.1, alembic 1.18.3 |
| numpy | 2.4.2 | pandas 3.0.0, scipy 1.17.0, scikit-learn 1.8.0 |
| pandas | 3.0.0 | numpy 2.x, Python 3.10+ |
| pytest | 9.0.2 | pytest-asyncio 1.3.0, pytest-cov 5.0.0 |

### Node.js Core Stack (Tested Combinations)

| Package | Version | Compatible With | Node.js Version |
|---------|---------|-----------------|-----------------|
| react | 18.3.1 | react-dom 18.3.1, @types/react 18.3.x | 16+ |
| react | 19.2.4 | react-dom 19.2.4, @types/react 19.2.x | 16+ |
| vite | 6.4.1 | @vitejs/plugin-react 4.7.0+, Node 18+ | 18+ |
| vite | 7.3.1 | @vitejs/plugin-react 5.1.2, Node 20.19+ | 20.19+ / 22.12+ |
| typescript | 5.8.x | typescript-eslint 8.53.0 | Any |

---

## Implementation Plan

### Pre-Implementation Checklist

- [ ] Verify Python version across all services (minimum 3.10 recommended)
- [ ] Verify Node.js version (minimum 20.19 for Vite 7)
- [ ] Review current test coverage (aim for 80%+ before major upgrades)
- [ ] Set up staging environment for testing
- [ ] Create backup/snapshot of current production state
- [ ] Document current dependency versions
- [ ] Create rollback plan

### Phase 1: Critical Compatibility Fixes (Week 1)

**Day 1-2: SQLAlchemy Ecosystem**
1. Update requirements.txt for affected services:
   - automation-miner
   - ai-pattern-service
   - ha-ai-agent-service

```txt
# Critical compatibility updates
sqlalchemy[asyncio]==2.0.46
aiosqlite==0.22.1
alembic==1.18.3
```

2. Test database migrations and queries
3. Run full test suite for each service
4. Deploy to staging environment

**Day 3-4: FastAPI Core Stack**
1. Update requirements.txt for all FastAPI services (prioritize automation-linter):

```txt
fastapi[standard]>=0.119.0,<0.120.0
pydantic==2.12.0
pydantic-settings==2.12.0
httpx>=0.28.1,<0.29.0
# uvicorn included with fastapi[standard]
```

2. Update calendar-service (has very old pydantic-settings 2.1.0)
3. Test all API endpoints
4. Run integration tests
5. Deploy to staging environment

**Day 5: Node.js Build Tools**
1. Update package.json for health-dashboard and ai-automation-ui:

```json
{
  "devDependencies": {
    "@vitejs/plugin-react": "^5.1.2",
    "typescript-eslint": "^8.53.0"
  }
}
```

2. Run `npm install` or `npm update`
3. Test build process: `npm run build`
4. Run test suite: `npm test`
5. Deploy to staging environment

**Weekend: Validation & Monitoring**
- Monitor staging environment for issues
- Review logs for errors or warnings
- Performance testing
- User acceptance testing (if applicable)

### Phase 2: Standard Library Updates (Week 2)

**Day 1-2: HTTP & Testing Libraries**

Create shared requirements file for common dependencies:

**`requirements-common.txt`**
```txt
# HTTP & Networking
aiohttp==3.13.3
httpx>=0.28.1,<0.29.0

# Testing
pytest==9.0.2
pytest-asyncio==1.3.0
pytest-cov==5.0.0
pytest-httpx>=0.30.0

# Utilities
python-dotenv==1.2.1
pyyaml==6.0.3
tenacity==9.1.2
jinja2==3.1.6
rich==14.3.2
```

**Services to update:** All services using these packages

**Action:**
1. Update requirements.txt to reference common file or copy versions
2. Review pytest-asyncio 1.0 migration guide
3. Run test suites for all services
4. Deploy to staging in batches (5-10 services per deployment)

**Day 3: MQTT Migration (Breaking Change)**

**Services affected:** ha-simulator, ai-pattern-service

**Old (asyncio-mqtt):**
```python
from asyncio_mqtt import Client
```

**New (aiomqtt):**
```python
from aiomqtt import Client
```

**Update requirements.txt:**
```txt
# Remove
asyncio-mqtt==0.16.1

# Add
aiomqtt==2.4.0
paho-mqtt==2.1.0
```

**Action:**
1. Update imports in affected files
2. Test MQTT connections and message handling
3. Run integration tests
4. Deploy to staging

**Day 4-5: Node.js Testing & Utilities**

Update package.json:
```json
{
  "dependencies": {
    "react-use-websocket": "^4.13.0",
    "lucide-react": "^0.562.0"
  },
  "devDependencies": {
    "vitest": "^4.0.17",
    "@playwright/test": "^1.58.1",
    "@testing-library/react": "^16.3.1",
    "happy-dom": "^20.5.0",
    "msw": "^2.12.8"
  }
}
```

**Action:**
1. Run `npm update`
2. Run test suite: `npm test`
3. Run e2e tests: `npm run test:e2e`
4. Deploy to staging

**Weekend: Validation & Monitoring**
- Full regression testing
- Performance benchmarking
- Log analysis

### Phase 3: ML/AI Libraries (Week 3)

**CRITICAL: High-risk updates requiring extensive testing**

**Day 1-2: NumPy 2.x Migration**

**Services affected:** ml-service, ai-pattern-service

**Action:**
1. Create isolated test environment
2. Update requirements.txt:
```txt
numpy==2.4.2
```
3. Run all ML model tests
4. Check for dtype warnings/errors
5. Review NumPy 2.0 migration guide: https://numpy.org/devdocs/numpy_2_0_migration_guide.html
6. Fix any compatibility issues
7. Benchmark performance (NumPy 2.x is faster)

**Day 3-4: Pandas 3.0 Migration (MAJOR)**

**Prerequisites:** NumPy 2.4.2 must be installed first

**Action:**
1. Verify Python 3.10+ on affected services
2. Update requirements.txt:
```txt
pandas==3.0.0
```
3. Review breaking changes: https://pandas.pydata.org/docs/dev/whatsnew/v3.0.0.html
4. Key changes to address:
   - String data type backed by PyArrow (default)
   - Deprecated functions removed
   - Changed default behaviors
5. Update data processing code
6. Run all data pipeline tests
7. Validate output data integrity
8. Performance testing

**Day 5: Other ML Libraries**

Update requirements.txt:
```txt
scipy==1.17.0
scikit-learn==1.8.0
```

**Action:**
1. Update packages
2. Run all ML model training/inference tests
3. Validate model performance metrics
4. Benchmark training time and inference speed

**Weekend: OpenAI SDK Update**

**Service affected:** ha-ai-agent-service

Update requirements.txt:
```txt
openai==2.16.0
tiktoken==0.12.0
```

**Action:**
1. Review OpenAI SDK 2.x migration guide
2. Update API calls (breaking changes in v2)
3. Note: Assistants API marked as deprecated in 2.16.0
4. Test all OpenAI integrations
5. Monitor token usage with new tiktoken version
6. Deploy to staging

**Week End: Full ML Pipeline Validation**
- End-to-end ML pipeline tests
- Model accuracy/performance validation
- Data integrity checks
- Staging environment deployment
- 48-hour burn-in period

### Phase 4: Frontend Major Updates (Week 4)

**Recommended: Conservative Approach**

**Action:**
- Review all updates from Phases 1-2
- Final validation of Node.js services
- Production deployment planning
- No major version upgrades this phase

**Alternative: Aggressive Approach (If Required)**

**Day 1-2: Node.js & Build Tool Upgrades**
1. Verify Node.js version 20.19+ or 22.12+
2. Update NVM or Node version manager
3. Update CI/CD pipelines for new Node version

**Day 3-4: React 19 Migration**

**Action:**
1. Review React 19 migration guide: https://react.dev/blog/2025/10/01/react-19-2
2. Update package.json:
```json
{
  "dependencies": {
    "react": "^19.2.4",
    "react-dom": "^19.2.4"
  },
  "devDependencies": {
    "@types/react": "^19.2.8",
    "@types/react-dom": "^19.2.3"
  }
}
```
3. Key changes to implement:
   - Remove `forwardRef` (ref is now a prop)
   - Update to new hooks: `use()`, `useFormStatus()`, etc.
   - Test concurrent rendering behavior
   - Update error handling
4. Run full test suite
5. Visual regression testing
6. User acceptance testing

**Day 5: Vite 7 Migration**

**Prerequisites:** Node.js 20.19+ / 22.12+

Update package.json:
```json
{
  "devDependencies": {
    "vite": "^7.3.1",
    "@vitejs/plugin-react": "^5.1.2"
  }
}
```

Update vite.config.ts:
```typescript
// Review browser targets
export default defineConfig({
  build: {
    target: 'baseline-widely-available'
    // Or specify custom targets
  }
})
```

**Action:**
1. Update configuration
2. Test build process
3. Verify browser compatibility
4. Test dev server
5. Performance testing

**Weekend: Full System Testing**
- Complete regression testing
- Cross-browser testing
- Performance benchmarking
- Load testing
- Security scanning
- Staging deployment
- 72-hour burn-in period

---

## Post-Implementation

### Week 5: Production Deployment

**Phased Rollout Strategy:**

**Day 1: Backend Services (Low Traffic)**
- Deploy Phase 1 & 2 updates to low-traffic Python services
- Monitor for 24 hours

**Day 2: Backend Services (Core Services)**
- Deploy to core Python services
- Monitor for 24 hours

**Day 3: Frontend Services**
- Deploy health-dashboard updates
- Deploy ai-automation-ui updates
- Monitor for 24 hours

**Day 4-5: Final Services**
- Deploy remaining services
- Monitor for 48 hours

**Weekend: Full System Monitoring**
- Review all metrics
- Check error rates
- Performance analysis
- User feedback collection

### Ongoing Maintenance

**Weekly:**
- Monitor for security advisories
- Review dependency updates
- Check for CVEs in dependencies

**Monthly:**
- Review minor/patch updates
- Update dependencies with security fixes
- Test in staging environment

**Quarterly:**
- Major version review
- Plan next upgrade cycle
- Update this document

---

## Rollback Procedures

### If Issues Arise During Implementation

**Immediate Rollback Triggers:**
- Critical bugs in production
- Security vulnerabilities introduced
- Performance degradation >20%
- Data integrity issues
- Failed integration tests

**Rollback Steps:**

1. **Identify affected service(s)**
2. **Restore from backup/snapshot**
   - Use git tags/branches for code
   - Restore requirements.txt/package.json
3. **Redeploy previous version**
4. **Verify service health**
5. **Document issue for analysis**
6. **Create fix plan**

**Per-Phase Rollback:**
- Each phase is independent
- Can rollback individual phases without affecting others
- Use git tags: `pre-phase-1-upgrade`, `pre-phase-2-upgrade`, etc.

---

## Testing Strategy

### Unit Tests
- Run full test suite before and after each upgrade
- Aim for >80% code coverage
- Add tests for any modified code

### Integration Tests
- Test service-to-service communication
- Verify database connections
- Test external API integrations

### E2E Tests
- Test complete user workflows
- Verify UI functionality
- Test critical business processes

### Performance Tests
- Benchmark response times
- Load testing for high-traffic services
- Memory usage monitoring

### Security Tests
- Dependency vulnerability scanning
- OWASP Top 10 checks
- API security testing

---

## Risk Assessment

### High Risk (Extensive Testing Required)
- **NumPy 2.x**: Breaking changes in array semantics
- **Pandas 3.0**: Major version with breaking changes
- **React 19**: New concurrent rendering, API changes
- **Vite 7**: Node.js version requirement, target changes
- **pytest-asyncio 1.x**: Breaking changes in async test handling
- **OpenAI SDK 2.x**: API changes, deprecated features

### Medium Risk (Thorough Testing Required)
- **SQLAlchemy 2.0.46 + aiosqlite 0.22.1**: Threading model change
- **FastAPI 0.119+**: Pydantic v2 requirement, Python 3.9+ required
- **websockets 16.0**: Python 3.10+ requirement
- **tenacity 9.x**: Major version upgrade
- **aiomqtt migration**: Package rename, import changes

### Low Risk (Standard Testing)
- **Build tool updates**: typescript-eslint, @vitejs/plugin-react
- **Testing library updates**: vitest, playwright, msw
- **Utility updates**: rich, click, typer
- **Minor version updates**: Most libraries with minor/patch updates

---

## Success Metrics

### Technical Metrics
- [ ] All services upgraded to target versions
- [ ] Zero critical bugs introduced
- [ ] Test coverage maintained or improved
- [ ] Build times within 10% of baseline
- [ ] No security vulnerabilities in dependencies

### Performance Metrics
- [ ] API response times within 5% of baseline
- [ ] Database query performance maintained or improved
- [ ] Frontend load times within 10% of baseline
- [ ] Memory usage within acceptable limits
- [ ] ML model inference time maintained or improved

### Operational Metrics
- [ ] Zero unplanned downtime during upgrades
- [ ] Rollback procedures tested and documented
- [ ] All services deployed to production
- [ ] Documentation updated
- [ ] Team trained on new features/changes

---

## Resources & References

### Python Package Documentation
- [FastAPI Releases](https://fastapi.tiangolo.com/release-notes/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [SQLAlchemy Releases](https://github.com/sqlalchemy/sqlalchemy/releases)
- [NumPy 2.0 Migration Guide](https://numpy.org/devdocs/numpy_2_0_migration_guide.html)
- [Pandas 3.0 What's New](https://pandas.pydata.org/docs/dev/whatsnew/v3.0.0.html)
- [pytest Changelog](https://docs.pytest.org/en/stable/changelog.html)
- [aiomqtt Documentation](https://sbtinstruments.github.io/aiomqtt/)

### Node.js Package Documentation
- [React 19 Release](https://react.dev/blog/2025/10/01/react-19-2)
- [Vite 7 Announcement](https://vite.dev/blog/announcing-vite7)
- [TypeScript Releases](https://devblogs.microsoft.com/typescript/)
- [Tailwind CSS v4](https://tailwindcss.com/docs)

### Testing & Best Practices
- [Python Testing Best Practices](https://docs.pytest.org/en/stable/goodpractices.html)
- [React Testing Library](https://testing-library.com/docs/react-testing-library/intro/)
- [Playwright Best Practices](https://playwright.dev/docs/best-practices)

---

## Appendix A: Service-Specific Requirements Files

### Template: requirements.txt (Python FastAPI Service)

```txt
# Web Framework & Server
fastapi[standard]>=0.119.0,<0.120.0
pydantic==2.12.0
pydantic-settings==2.12.0

# HTTP Clients
httpx>=0.28.1,<0.29.0
aiohttp==3.13.3

# Database (if used)
sqlalchemy[asyncio]==2.0.46
aiosqlite==0.22.1
alembic==1.18.3

# Database Clients (if used)
influxdb3-python==0.17.0

# Testing
pytest==9.0.2
pytest-asyncio==1.3.0
pytest-cov==5.0.0
pytest-httpx>=0.30.0

# Utilities
python-dotenv==1.2.1
pyyaml==6.0.3
tenacity==9.1.2

# Logging
python-json-logger>=2.0.0

# Validation
python-multipart==0.0.22
```

### Template: package.json (Node.js/React Service)

```json
{
  "name": "service-name",
  "version": "1.0.0",
  "type": "module",
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "@radix-ui/react-*": "^1.x.x",
    "lucide-react": "^0.562.0",
    "chart.js": "^4.5.1",
    "react-chartjs-2": "^5.3.1",
    "react-use-websocket": "^4.13.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^5.1.2",
    "@types/react": "^18.3.5",
    "@types/react-dom": "^18.3.2",
    "typescript": "^5.9.3",
    "typescript-eslint": "^8.53.0",
    "vite": "^6.4.1",
    "vitest": "^4.0.17",
    "@playwright/test": "^1.58.1",
    "@testing-library/react": "^16.3.1",
    "@testing-library/jest-dom": "^6.9.1",
    "happy-dom": "^20.5.0",
    "msw": "^2.12.8",
    "eslint": "^9.17.0",
    "tailwindcss": "^3.4.18",
    "autoprefixer": "^10.4.22",
    "postcss": "^8.4.49"
  }
}
```

---

## Appendix B: Automation Scripts

### Script: update_python_service.sh

```bash
#!/bin/bash
# Update Python service dependencies

SERVICE_PATH=$1
PHASE=$2

if [ -z "$SERVICE_PATH" ] || [ -z "$PHASE" ]; then
    echo "Usage: $0 <service_path> <phase>"
    echo "Example: $0 services/automation-linter phase1"
    exit 1
fi

cd "$SERVICE_PATH" || exit 1

echo "Updating $SERVICE_PATH for $PHASE"

case $PHASE in
    phase1)
        # Critical compatibility fixes
        pip install --upgrade sqlalchemy==2.0.46 aiosqlite==0.22.1 alembic==1.18.3
        pip install --upgrade 'fastapi[standard]>=0.119.0,<0.120.0' pydantic==2.12.0 pydantic-settings==2.12.0 'httpx>=0.28.1,<0.29.0'
        ;;
    phase2)
        # Standard library updates
        pip install --upgrade aiohttp==3.13.3 pytest==9.0.2 pytest-asyncio==1.3.0 pytest-cov==5.0.0
        pip install --upgrade python-dotenv==1.2.1 pyyaml==6.0.3 tenacity==9.1.2
        ;;
    phase3)
        # ML/AI libraries
        pip install --upgrade numpy==2.4.2 pandas==3.0.0 scipy==1.17.0 scikit-learn==1.8.0
        ;;
    *)
        echo "Unknown phase: $PHASE"
        exit 1
        ;;
esac

echo "Running tests..."
pytest

echo "Update complete for $SERVICE_PATH ($PHASE)"
```

### Script: update_node_service.sh

```bash
#!/bin/bash
# Update Node.js service dependencies

SERVICE_PATH=$1
PHASE=$2

if [ -z "$SERVICE_PATH" ] || [ -z "$PHASE" ]; then
    echo "Usage: $0 <service_path> <phase>"
    echo "Example: $0 services/health-dashboard phase1"
    exit 1
fi

cd "$SERVICE_PATH" || exit 1

echo "Updating $SERVICE_PATH for $PHASE"

case $PHASE in
    phase1)
        # Build tools compatibility
        npm install @vitejs/plugin-react@^5.1.2 typescript-eslint@^8.53.0 --save-dev
        ;;
    phase2)
        # Testing & utilities
        npm install vitest@^4.0.17 @playwright/test@^1.58.1 @testing-library/react@^16.3.1 --save-dev
        npm install happy-dom@^20.5.0 msw@^2.12.8 --save-dev
        npm install react-use-websocket@^4.13.0 --save
        ;;
    phase4-aggressive)
        # Major version upgrades
        npm install react@^19.2.4 react-dom@^19.2.4 --save
        npm install @types/react@^19.2.8 @types/react-dom@^19.2.3 --save-dev
        npm install vite@^7.3.1 @vitejs/plugin-react@^5.1.2 --save-dev
        ;;
    *)
        echo "Unknown phase: $PHASE"
        exit 1
        ;;
esac

echo "Running tests..."
npm test

echo "Running build..."
npm run build

echo "Update complete for $SERVICE_PATH ($PHASE)"
```

---

## Appendix C: Compatibility Testing Checklist

### Python Service Checklist

- [ ] Import all modules successfully
- [ ] Database connections work (SQLAlchemy, aiosqlite)
- [ ] API endpoints return expected responses
- [ ] Authentication/authorization working
- [ ] Background jobs/tasks execute correctly
- [ ] WebSocket connections stable
- [ ] MQTT connections stable (if applicable)
- [ ] ML models load and run (if applicable)
- [ ] Data processing pipelines complete successfully
- [ ] Integration tests pass
- [ ] Performance within acceptable range

### Node.js Service Checklist

- [ ] Application builds without errors
- [ ] Development server starts successfully
- [ ] All routes render correctly
- [ ] Component interactions work as expected
- [ ] Form submissions successful
- [ ] WebSocket connections stable
- [ ] API calls return expected data
- [ ] State management working correctly
- [ ] Routing/navigation functional
- [ ] UI components render properly across browsers
- [ ] Responsive design intact
- [ ] Unit tests pass
- [ ] E2E tests pass
- [ ] Build size within acceptable limits
- [ ] Performance metrics acceptable

---

## Document Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-04 | Claude | Initial comprehensive upgrade plan |

---

## Contact & Support

For questions or issues during implementation:
- Review this document first
- Check official package documentation
- Review migration guides for major versions
- Test in staging environment before production
- Document all issues and resolutions
- Update this plan with lessons learned

---

**End of Document**
