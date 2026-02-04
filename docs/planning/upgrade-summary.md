# HomeIQ Library Upgrade Plan - Executive Summary

**Date:** February 4, 2026
**Status:** Ready for Review

---

## Overview

A comprehensive analysis of 45+ Python microservices and 2 Node.js/React applications has been completed, identifying upgrade paths to the latest stable, production-ready versions with full compatibility assurance.

**Scope Note:** This plan covers only third-party open-source libraries from PyPI (Python) and npm (Node.js). Internal tapps-agents components are explicitly excluded and will be updated separately.

---

## Current State - Critical Issues

### Python Services

**Version Conflicts Identified:**

1. **FastAPI**: 8 versions behind in automation-linter (0.115.0 vs 0.123.0+)
2. **Pydantic**: Inconsistent across services (2.8.2, 2.9.2, 2.12.4)
3. **pydantic-settings**: calendar-service 11 versions behind (2.1.0 vs 2.12.0)
4. **httpx**: Split between 0.27.x and 0.28.1+
5. **SQLAlchemy/aiosqlite**: Compatibility risk between versions

**Services Needing Priority Attention:**
- automation-linter (most outdated)
- calendar-service (very old pydantic-settings)
- CLI tool (slightly behind on several packages)

### Node.js Services (health-dashboard & ai-automation-ui)

**Overall Status:** Reasonably current, mostly minor updates needed

**Key Updates Available:**
- React 18 → 19 (major, breaking changes)
- Vite 6 → 7 (requires Node.js 20.19+)
- Minor updates for testing libraries and build tools

---

## Recommended Upgrade Path

### 4-Phase Strategy (4 Weeks)

#### **Phase 1: Critical Compatibility Fixes** (Week 1)
**Risk Level:** LOW-MEDIUM
**Impact:** Resolve version conflicts, fix compatibility issues

**Python:**
- SQLAlchemy 2.0.35+ → 2.0.46
- aiosqlite 0.20.x/0.21.x → 0.22.1
- FastAPI 0.115.0 → 0.119.0+
- Pydantic → 2.12.0 (standardize)
- httpx → 0.28.1+ (standardize)

**Node.js:**
- @vitejs/plugin-react: 4.7.0 → 5.1.2
- typescript-eslint: 8.48.0 → 8.53.0

**Services Affected:** 15+ Python services, 2 Node.js services

---

#### **Phase 2: Standard Library Updates** (Week 2)
**Risk Level:** LOW-MEDIUM
**Impact:** Standardize versions, apply security updates

**Python:**
- pytest 8.3.x → 9.0.2
- pytest-asyncio 0.23.0 → 1.3.0 (BREAKING)
- tenacity 8.2.3 → 9.1.2 (MAJOR)
- asyncio-mqtt → aiomqtt 2.4.0 (package rename)
- python-dotenv → 1.2.1 (standardize)
- influxdb3-python 0.3.0 → 0.17.0

**Node.js:**
- vitest 4.0.15 → 4.0.17
- @playwright/test 1.56.1 → 1.58.1
- happy-dom 20.0.11 → 20.5.0
- msw 2.12.1 → 2.12.8

**Services Affected:** 30+ Python services, 2 Node.js services

---

#### **Phase 3: ML/AI Libraries** (Week 3)
**Risk Level:** HIGH
**Impact:** Major version upgrades with breaking changes

**CRITICAL UPDATES:**
- NumPy 1.26.x → 2.4.2 (MAJOR - breaking changes)
- Pandas 2.2.x → 3.0.0 (MAJOR - breaking changes, requires NumPy 2.x)
- scikit-learn 1.5.x → 1.8.0
- scipy 1.16.3 → 1.17.0
- OpenAI SDK 1.54.0 → 2.16.0 (MAJOR)
- tiktoken 0.8.0 → 0.12.0

**Services Affected:** ml-service, ai-pattern-service, ha-ai-agent-service

**Requirements:**
- Python 3.10+ (recommended for Pandas 3.0)
- Extensive testing of all ML pipelines
- Model validation and accuracy checks

---

#### **Phase 4: Frontend Major Updates** (Week 4)
**Risk Level:** HIGH (if aggressive path chosen)
**Impact:** Access to latest features, performance improvements

**Option A: Conservative (Recommended)**
- Stay on React 18, Vite 6, Tailwind 3
- Apply all minor/patch updates from Phases 1-2
- Focus on stability

**Option B: Aggressive**
- React 18 → 19 (MAJOR - breaking changes)
- Vite 6 → 7 (requires Node.js 20.19+)
- Tailwind 3 → 4 (MAJOR - breaking changes)

**Recommendation:** Start with Option A, plan Option B for future sprint

---

## Key Breaking Changes to Watch

### High-Risk Updates

1. **Pandas 3.0**
   - Dedicated string data type (PyArrow-backed) by default
   - Requires NumPy 2.x and Python 3.10+
   - Significant API changes

2. **NumPy 2.x**
   - Changed dtypes, array semantics
   - Most libraries now compatible
   - Requires thorough testing

3. **React 19**
   - New concurrent rendering improvements
   - `ref` as prop (no more `forwardRef`)
   - New hooks: `use()`, `useFormStatus()`, `useOptimistic()`

4. **Vite 7**
   - Node.js 20.19+ / 22.12+ required
   - Browser target: 'baseline-widely-available'
   - Changed default dev server host

5. **pytest-asyncio 1.x**
   - Breaking changes from 0.x series
   - New async testing patterns

6. **aiomqtt (formerly asyncio-mqtt)**
   - Package renamed
   - Update imports: `asyncio_mqtt` → `aiomqtt`

---

## Python Version Requirements

**Current Minimum:** Python 3.8 (many packages dropping support)
**Recommended Target:** Python 3.10 or 3.11
**Required for Full Compatibility:** Python 3.10+

**Packages Requiring Python 3.10+:**
- websockets 16.0
- Pandas 3.0 (recommended)

**Action Required:** Audit all services for Python version, upgrade infrastructure if needed

---

## Node.js Version Requirements

**Current for Vite 6:** Node.js 18+
**Required for Vite 7:** Node.js 20.19+ or 22.12+
**Recommended:** Node.js 24.13.0 LTS (supported until April 2028)

---

## Implementation Timeline

| Week | Phase | Risk | Effort | Services Affected |
|------|-------|------|--------|-------------------|
| 1 | Critical Compatibility Fixes | LOW-MED | 3-5 days | 15+ services |
| 2 | Standard Library Updates | LOW-MED | 4-5 days | 30+ services |
| 3 | ML/AI Libraries | HIGH | 5 days | 3 services |
| 4 | Frontend Major Updates | MED-HIGH | 4-5 days | 2 services |
| 5 | Production Deployment | LOW | 5 days | All services |

**Total Duration:** 4-5 weeks
**Recommended Buffer:** +1 week for unforeseen issues

---

## Success Criteria

### Technical
- [ ] All services upgraded to target versions
- [ ] Zero critical bugs introduced
- [ ] Test coverage maintained or improved (80%+)
- [ ] No security vulnerabilities in dependencies

### Performance
- [ ] API response times within 5% of baseline
- [ ] Frontend load times within 10% of baseline
- [ ] ML model inference time maintained or improved
- [ ] Database query performance maintained

### Operational
- [ ] Zero unplanned downtime
- [ ] All rollback procedures tested
- [ ] Documentation updated
- [ ] Team trained on changes

---

## Risk Mitigation

### High-Risk Areas
1. **ML/AI Stack** - Extensive testing, isolated environment first
2. **Database Layer** - Test migrations thoroughly, backup all data
3. **Frontend Major Versions** - Consider conservative path initially
4. **MQTT Migration** - Package rename requires code changes

### Mitigation Strategies
- Phased rollout with staging validation
- Comprehensive testing at each phase
- Rollback procedures documented and tested
- 48-72 hour burn-in periods between phases
- Monitoring and alerting in place

---

## Compatibility Matrix

### Python Tested Combinations
- fastapi 0.119.0+ ⟷ pydantic 2.12.0 ⟷ uvicorn (bundled)
- sqlalchemy 2.0.46 ⟷ aiosqlite 0.22.1 ⟷ alembic 1.18.3
- numpy 2.4.2 ⟷ pandas 3.0.0 ⟷ scipy 1.17.0 ⟷ scikit-learn 1.8.0

### Node.js Tested Combinations
- react 18.3.1 ⟷ react-dom 18.3.1 ⟷ @types/react 18.3.x
- vite 6.4.1 ⟷ @vitejs/plugin-react 4.7.0+ ⟷ Node 18+
- vite 7.3.1 ⟷ @vitejs/plugin-react 5.1.2 ⟷ Node 20.19+

---

## Resource Requirements

### Team
- 1-2 Backend Engineers (Python services)
- 1 Frontend Engineer (Node.js services)
- 1 ML Engineer (ML/AI libraries)
- 1 DevOps Engineer (deployment, monitoring)
- 1 QA Engineer (testing validation)

### Infrastructure
- Staging environment for testing
- Isolated ML testing environment
- CI/CD pipeline updates
- Monitoring and alerting setup

### Time Allocation
- Planning & Setup: 1 week
- Implementation: 4 weeks
- Deployment: 1 week
- Validation: 1 week
- **Total**: 7 weeks (with buffer)

---

## Next Steps

1. **Review this plan** with stakeholders
2. **Verify Python version** across all services (target 3.10+)
3. **Verify Node.js version** (target 20.19+ for Vite 7, or 24.x LTS)
4. **Set up staging environments** for testing
5. **Review and approve timeline**
6. **Assign team members** to phases
7. **Schedule kickoff meeting**
8. **Begin Phase 1** implementation

---

## Documentation

**Full Detailed Plan:** See `library-upgrade-plan.md` for:
- Complete version listings
- Detailed implementation steps
- Testing procedures
- Automation scripts
- Rollback procedures
- Service-specific requirements templates

---

## Questions for Review

1. **Python Version:** Are all services ready for Python 3.10+? (Required for full compatibility)
2. **Node.js Version:** Can we upgrade to Node.js 20.19+ or 24.x LTS? (Required for Vite 7)
3. **Timeline:** Does the 4-5 week implementation timeline work for your schedule?
4. **Risk Tolerance:** Phase 4 - Conservative (React 18) or Aggressive (React 19) path?
5. **ML Services:** Are ML pipelines ready for comprehensive testing during Phase 3?
6. **Resources:** Can we allocate 1-2 engineers per phase for implementation?

---

## Contact

For questions about this plan:
- Review full documentation: `library-upgrade-plan.md`
- Check package-specific migration guides (linked in main doc)
- Test all changes in staging environment first

---

**Prepared by:** Claude Code
**Date:** February 4, 2026
**Status:** Ready for Stakeholder Review
