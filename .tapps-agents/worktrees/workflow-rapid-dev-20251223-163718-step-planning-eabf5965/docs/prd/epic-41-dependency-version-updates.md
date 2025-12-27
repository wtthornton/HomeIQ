# Epic 41: Dependency Version Updates & CPU/NUC Compatibility Verification

**Status:** 📋 **PLANNING**  
**Type:** Infrastructure & Maintenance  
**Priority:** High  
**Effort:** 4 Stories (8-12 hours estimated)  
**Created:** January 2025  
**Target Completion:** January 2025

---

## Epic Goal

Update all project dependencies to their latest stable versions compatible with Intel NUC (CPU-only) deployments, resolve version conflicts across services, and verify CPU/NUC compatibility for all libraries. This epic addresses technical debt from version inconsistencies and ensures optimal performance and security.

**Version Reference**: All target versions are defined in `docs/architecture/tech-stack.md`. This epic ensures all services match those versions.

---

## Existing System Context

### Current Dependency Status

**Critical Issues Found:**
1. **NumPy Version Conflict**: 
   - `ai-automation-service`: `numpy>=1.26.0,<1.27.0`
   - `ml-service`: `numpy==2.3.4`
   - `openvino-service`: `numpy==2.3.4`
   - **Impact**: Potential runtime errors if services share dependencies

2. **FastAPI/Uvicorn Version Mismatch**:
   - Listed as `0.121.2` and `0.38.0` (likely typos or non-existent versions)
   - **Action**: Verify actual installed versions

3. **Multiple PyTorch Versions**:
   - `2.2.2+cpu`, `2.3.1+cpu`, `2.4.0`
   - **Action**: Standardize on one version (2.4.0 recommended)

4. **Node.js 18 vs 20**:
   - Current: Node 18-alpine
   - Latest LTS: Node 20.11.0
   - **Action**: Upgrade to Node 20 LTS

5. **Inconsistent Library Versions**:
   - `influxdb-client`: 1.48.0 vs 1.49.0
   - `pandas`: 2.2.0 vs 2.3.3
   - `scikit-learn`: 1.4.2 vs 1.5.0

### Technology Stack (Current)

**Reference**: See `docs/architecture/tech-stack.md` for definitive version specifications.

**Databases:**
- InfluxDB: 2.7 → **Target: 2.7.12** ✅ (latest 2.x, updated in docker-compose.yml, see `docs/architecture/tech-stack.md`)
- SQLite: 3.45+ → **Target: 3.51.0** (latest stable, see `docs/architecture/tech-stack.md`)

**Base Images:**
- Python: 3.12-alpine / 3.12-slim ✅ (current, latest)
- Node.js: 18-alpine → **Target: 20.11.0 LTS**
- Nginx: alpine (latest) ✅

**Python Web Framework:**
- FastAPI: 0.121.2 → **Target: 0.115.x** (verify actual version)
- Uvicorn: 0.38.0 → **Target: 0.32.x** (verify actual version)
- Pydantic: 2.12.4 ✅ (current, latest)

**Data Processing:**
- pandas: 2.2.0 / 2.3.3 → **Target: 2.2.0+** (standardize)
- numpy: 1.26.0 / 2.3.4 → **Target: 1.26.x** (resolve conflict - use 1.26.x for compatibility)
- scipy: 1.14.0 / 1.16.3 → **Target: 1.16.3+** (standardize)

**Machine Learning:**
- scikit-learn: 1.4.2 / 1.5.0 → **Target: 1.5.0+** (latest stable)
- PyTorch: 2.2.2+cpu / 2.3.1+cpu / 2.4.0 → **Target: 2.4.0+cpu** (standardize, CPU-only)
- transformers: 4.40.0 / 4.45.2 / 4.46.1 → **Target: 4.46.1+** (latest stable)
- sentence-transformers: 3.0.0 / 3.3.1 → **Target: 3.3.1+** (latest stable)
- OpenVINO: 2024.4.0 / 2024.5.0 → **Target: 2024.5.0+** (latest 2024.x)
- optimum-intel: 1.20.0 / 1.21.0 → **Target: 1.21.0+** (latest stable)

**HTTP & Networking:**
- aiohttp: 3.10.0 / 3.13.2 → **Target: 3.13.2** (latest stable)
- httpx: 0.27.0 / 0.27.2 / 0.28.1 → **Target: 0.28.1** (latest stable)
- websockets: 12.0 ✅ (current, latest)

**Frontend:**
- React: 18.3.1 ✅ (current, latest 18.x)
- Vite: 5.4.8 ✅ (current, latest)
- TypeScript: 5.6.3 ✅ (current, latest)
- Playwright: 1.48.2 → **Target: 1.56.1** (latest stable)
- Puppeteer: Latest → **Target: 24.30.0** (verify version)

---

## Enhancement Details

### Version Update Strategy

**Phase 1: Critical Conflicts (Story 41.1)**
- Resolve NumPy version conflict (standardize on 1.26.x)
- Verify FastAPI/Uvicorn actual versions
- Standardize PyTorch to 2.4.0+cpu across all services

**Phase 2: Database Updates (Story 41.2)**
- Update InfluxDB to 2.7.12 (latest 2.x stable)
- Update SQLite to 3.51.0 (via aiosqlite driver update)
- Update docker-compose.yml with new InfluxDB version

**Phase 3: Python Library Standardization (Story 41.3)**
- Standardize pandas to 2.2.0+ across all services
- Standardize scikit-learn to 1.5.0+ across all services
- Update transformers, sentence-transformers, OpenVINO to latest stable
- Update aiohttp, httpx to latest stable versions
- Update influxdb-client to 1.49.0 across all services

**Phase 4: Node.js & Frontend Updates (Story 41.4)**
- Upgrade Node.js base image from 18-alpine to 20.11.0 LTS
- Update Playwright to 1.56.1
- Verify Puppeteer version (24.30.0)
- Update all package.json files

### CPU/NUC Compatibility Verification

**Critical Requirements:**
- ✅ All PyTorch builds must be CPU-only (`+cpu` suffix or CPU index)
- ✅ No CUDA dependencies in any service
- ✅ OpenVINO optimized for Intel hardware (NUC compatible)
- ✅ All ML libraries must support CPU-only execution
- ✅ Verify Alpine Linux compatibility for all Python packages

**Verification Checklist:**
- [ ] All PyTorch installations use CPU-only wheels
- [ ] No NVIDIA/CUDA dependencies in requirements.txt files
- [ ] OpenVINO versions compatible with Intel NUC hardware
- [ ] All packages have Alpine Linux wheels available
- [ ] Memory constraints verified (256M-2G per service)
- [ ] Docker images build successfully on NUC hardware

---

## Stories

### Story 41.1: Resolve Critical Version Conflicts

**Priority:** High  
**Effort:** 2-3 hours  
**Status:** 📋 Planning

**Tasks:**
1. Audit all requirements.txt files for NumPy versions
2. Standardize NumPy to 1.26.x across all services (resolve 2.3.4 conflict)
3. Verify FastAPI/Uvicorn actual installed versions
4. Standardize PyTorch to 2.4.0+cpu across all services
5. Update ai-automation-service, ml-service, openvino-service requirements
6. Test service startup and dependency resolution

**Acceptance Criteria:**
- [ ] All services use NumPy 1.26.x (no 2.x versions)
- [ ] FastAPI/Uvicorn versions verified and corrected
- [ ] All services use PyTorch 2.4.0+cpu
- [ ] All services start successfully with updated dependencies
- [ ] No dependency conflicts in pip install

**Files to Update:**
- `services/ai-automation-service/requirements.txt`
- `services/ml-service/requirements.txt`
- `services/openvino-service/requirements.txt`
- `services/websocket-ingestion/requirements.txt`
- `services/data-api/requirements.txt`
- `services/admin-api/requirements.txt`

---

### Story 41.2: Database Version Updates

**Priority:** High  
**Effort:** 1-2 hours  
**Status:** 📋 Planning

**Tasks:**
1. Update InfluxDB Docker image from 2.7 to 2.7.12 in docker-compose.yml
2. Verify InfluxDB 2.7.12 compatibility with existing data
3. Update aiosqlite to latest version (supports SQLite 3.51.0)
4. Test database migrations and queries
5. Update documentation with new versions

**Acceptance Criteria:**
- [ ] InfluxDB updated to 2.7.12 in docker-compose.yml
- [ ] Existing data accessible after upgrade
- [ ] SQLite 3.51.0 features available via aiosqlite
- [ ] All database queries work correctly
- [ ] Documentation updated with new versions

**Files to Update:**
- `docker-compose.yml`
- `docker-compose.prod.yml`
- `services/data-api/requirements.txt`
- `docs/architecture/tech-stack.md`

---

### Story 41.3: Python Library Standardization

**Priority:** Medium  
**Effort:** 2-3 hours  
**Status:** 📋 Planning

**Tasks:**
1. Standardize pandas to 2.2.0+ across all services
2. Standardize scikit-learn to 1.5.0+ across all services
3. Update transformers to 4.46.1+ (latest stable)
4. Update sentence-transformers to 3.3.1+ (latest stable)
5. Update OpenVINO to 2024.5.0+ (latest 2024.x)
6. Update optimum-intel to 1.21.0+ (latest stable)
7. Update aiohttp to 3.13.2 (latest stable)
8. Update httpx to 0.28.1 (latest stable)
9. Update influxdb-client to 1.49.0 (latest stable)
10. Update scipy to 1.16.3+ (standardize)

**Acceptance Criteria:**
- [ ] All services use consistent library versions
- [ ] No version conflicts between services
- [ ] All services start successfully
- [ ] ML/AI services function correctly with updated libraries
- [ ] API services function correctly with updated HTTP clients

**Files to Update:**
- All `services/*/requirements.txt` files
- `docs/architecture/tech-stack.md`

---

### Story 41.4: Node.js & Frontend Updates

**Priority:** Medium  
**Effort:** 2-3 hours  
**Status:** 📋 Planning

**Tasks:**
1. Update Node.js base image from 18-alpine to 20.11.0 LTS
2. Update health-dashboard Dockerfile
3. Update ai-automation-ui Dockerfile
4. Update Playwright to 1.56.1 in package.json files
5. Verify Puppeteer version (24.30.0) in package.json
6. Test frontend builds and E2E tests
7. Update documentation

**Acceptance Criteria:**
- [ ] Node.js 20.11.0 LTS in all Dockerfiles
- [ ] Frontend builds successfully
- [ ] E2E tests pass with updated Playwright
- [ ] Puppeteer version verified and updated
- [ ] Documentation updated

**Files to Update:**
- `services/health-dashboard/Dockerfile`
- `services/ai-automation-ui/Dockerfile`
- `services/health-dashboard/package.json`
- `package.json` (root)
- `tests/e2e/package.json`
- `docs/architecture/tech-stack.md`

---

## CPU/NUC Compatibility Verification

### Verification Checklist

**PyTorch & ML Libraries:**
- [ ] All PyTorch installations use `--extra-index-url https://download.pytorch.org/whl/cpu`
- [ ] No CUDA dependencies in any requirements.txt
- [ ] PyTorch version uses `+cpu` suffix or CPU-only wheel
- [ ] OpenVINO versions compatible with Intel NUC (2024.x series)
- [ ] All ML services tested on CPU-only environment

**Alpine Linux Compatibility:**
- [ ] All Python packages have Alpine-compatible wheels
- [ ] No packages require compilation on Alpine
- [ ] Docker images build successfully on Alpine base
- [ ] Memory usage within NUC constraints (256M-2G per service)

**Hardware Optimization:**
- [ ] OpenVINO optimized for Intel hardware
- [ ] NumPy uses optimized BLAS libraries for Intel
- [ ] All services tested on actual NUC hardware (if available)

---

## Testing Strategy

### Unit Tests
- Run existing test suites after each version update
- Verify no breaking changes in API contracts
- Test ML model inference with updated libraries

### Integration Tests
- Test service-to-service communication
- Verify database connectivity with updated versions
- Test WebSocket connections

### E2E Tests
- Run Playwright E2E tests with updated versions
- Verify frontend functionality with Node.js 20
- Test all dashboard tabs

### Performance Tests
- Verify no performance regressions
- Check memory usage with updated libraries
- Test ML inference performance

---

## Risk Assessment

### High Risk
- **NumPy 1.26.x vs 2.3.4**: Breaking changes possible, requires thorough testing
- **InfluxDB 2.7.12**: Minor version update, low risk but verify data compatibility
- **Node.js 18 → 20**: Major version upgrade, test all frontend functionality

### Medium Risk
- **PyTorch standardization**: Multiple services affected, test ML inference
- **FastAPI/Uvicorn verification**: May require code changes if versions incorrect

### Low Risk
- **Library version standardization**: Patch/minor updates, low breaking change risk
- **SQLite 3.51.0**: Backward compatible, low risk

---

## Success Criteria

1. ✅ All version conflicts resolved
2. ✅ All dependencies updated to latest stable versions
3. ✅ All services verified CPU/NUC compatible
4. ✅ All tests passing
5. ✅ Documentation updated
6. ✅ No performance regressions
7. ✅ All services start successfully

---

## Dependencies

**Blocks:**
- None (can start immediately)

**Blocked By:**
- None

**Related Epics:**
- Epic 32: Code Quality Refactoring (established quality standards)
- Epic 31: Weather API Service Migration (similar dependency update pattern)

---

## Implementation Notes

### Version Update Pattern

1. **Update requirements.txt** with new version
2. **Test locally** with `pip install -r requirements.txt`
3. **Build Docker image** and verify
4. **Run tests** to verify compatibility
5. **Update documentation** with new version
6. **Commit changes** with clear commit message

### CPU/NUC Verification Pattern

1. **Check requirements.txt** for CPU-only indicators
2. **Verify PyTorch** uses CPU index or +cpu suffix
3. **Check Dockerfile** for CPU-only builds
4. **Test on NUC** (if available) or verify Alpine compatibility
5. **Document** CPU/NUC compatibility in tech-stack.md

---

## Documentation Updates

**Files to Update:**
- `docs/architecture/tech-stack.md` ✅ (already updated)
- `docs/architecture/source-tree.md` (if needed)
- `README.md` (if dependency versions mentioned)
- All service-specific README files (if present)

---

**Last Updated:** January 2025  
**Epic Owner:** BMAD Master  
**Status:** 📋 Planning - Ready for Story Breakdown

