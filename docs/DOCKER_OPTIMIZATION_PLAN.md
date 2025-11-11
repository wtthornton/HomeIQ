# Docker Deployment Optimization Plan
## HA Ingestor - Q4 2025 Docker Enhancement Initiative

**Date:** October 13, 2025  
**Status:** Awaiting Approval  
**Estimated Effort:** 16-24 hours  
**Priority:** Medium-High  

---

## Executive Summary

This comprehensive optimization plan addresses Docker deployment efficiency, security, and performance for the HA Ingestor platform. Based on analysis of current infrastructure, official Docker documentation, and 2025 best practices, this plan will reduce image sizes by 40-60%, improve build times by 50-70%, enhance security posture, and streamline deployment workflows.

### Progress Log (Nov 2025)
- ✅ `services/ai-automation-service/Dockerfile` refactored to retain model caches under `/app/models` and prune Hugging Face artifacts after build.
- ✅ `services/ai-automation-service/docker/ner-service.Dockerfile` converted to CPU-only multi-stage build; image now ~1.6 GB (down from ~12.6 GB).
- ✅ `services/openvino-service/Dockerfile` upgraded to multi-stage builder pattern with dependency installs isolated in the first stage.

### Current State Assessment

**Strengths:**
- ✅ Multi-stage builds already implemented (Python services, health-dashboard)
- ✅ Alpine-based images for smaller footprint
- ✅ Non-root users configured for security
- ✅ Health checks implemented across all services
- ✅ Resource limits defined in docker-compose files
- ✅ Proper logging configuration
- ✅ `.dockerignore` files present

**Areas for Improvement:**
- ⚠️ Inconsistent dependency caching strategies
- ⚠️ Suboptimal layer ordering in some Dockerfiles
- ⚠️ Build cache not leveraged in CI/CD
- ⚠️ Missing cache mounts for package managers
- ⚠️ No image vulnerability scanning
- ⚠️ Inconsistent Python base image usage
- ⚠️ Missing Docker Compose override patterns
- ⚠️ No build-time optimizations for development vs production

---

## Optimization Categories

### 1. Build Performance Optimization (Priority: High)

#### 1.1 Implement BuildKit Cache Mounts

**Current Issue:** Python pip and npm installs download packages on every build, even when dependencies haven't changed.

**Solution:** Add BuildKit cache mounts to preserve package manager caches across builds.

**Example for Python Services:**
```dockerfile
# Enhanced Python service Dockerfile
FROM python:3.11-alpine AS builder

WORKDIR /app

# Install build dependencies
RUN apk add --no-cache gcc musl-dev linux-headers

# Copy requirements with cache mount for pip
COPY services/websocket-ingestion/requirements-prod.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --user -r requirements-prod.txt
```

**Benefits:**
- 60-80% faster dependency installation on subsequent builds
- Reduced network bandwidth usage
- Consistent build times even with large dependency trees

**Affected Services:** All Python services (websocket-ingestion, enrichment-pipeline, admin-api, data-retention, weather-api, carbon-intensity, electricity-pricing, air-quality, calendar, smart-meter)

---

#### 1.2 Optimize Layer Ordering

**Current Issue:** Some services copy all files before dependencies, invalidating cache on any code change.

**Solution:** Reorder layers to maximize cache hits:
1. Install system dependencies (rarely change)
2. Copy dependency manifests only (package.json, requirements.txt)
3. Install application dependencies
4. Copy application code (changes frequently)

**Example:**
```dockerfile
# Optimized layer ordering
FROM python:3.11-alpine AS builder

# 1. System dependencies (cached unless base image changes)
RUN apk add --no-cache gcc musl-dev linux-headers

# 2. Copy ONLY dependency files (cached unless dependencies change)
COPY requirements-prod.txt .

# 3. Install dependencies with cache mount (cached)
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --user -r requirements-prod.txt

# 4. Copy application code (invalidates only this layer and below)
COPY src/ ./src/
```

**Benefits:**
- 70% faster builds when only code changes
- Developers get faster feedback cycles
- CI/CD pipelines run significantly faster

---

#### 1.3 Node.js Build Optimization

**Current Issue:** Dashboard builds install all dependencies on every build.

**Recommended Enhancement:**
```dockerfile
# Enhanced health-dashboard Dockerfile
FROM node:18-alpine AS deps
WORKDIR /app

# Copy package files only
COPY package*.json ./

# Install dependencies with cache mount
RUN --mount=type=cache,target=/root/.npm \
    npm ci --prefer-offline && npm cache clean --force

FROM node:18-alpine AS builder
WORKDIR /app

# Copy node_modules from deps stage
COPY --from=deps /app/node_modules ./node_modules

# Copy source code
COPY . .

# Build with cache mount for build artifacts
RUN --mount=type=cache,target=/app/.vite \
    npm run build
```

**Benefits:**
- 50-70% faster npm install on subsequent builds
- Reduced network calls to npm registry
- Better layer caching for unchanged dependencies

---

#### 1.4 Implement Build Cache Backends

**Solution:** Configure BuildKit to export/import cache to/from registry or GitHub Actions cache.

**For CI/CD (GitHub Actions):**
```yaml
- name: Build and push
  uses: docker/build-push-action@v6
  with:
    context: .
    file: services/websocket-ingestion/Dockerfile
    push: true
    tags: user/homeiq-websocket:latest
    cache-from: type=gha
    cache-to: type=gha,mode=max
```

**For Local Development:**
```bash
# Export cache to registry
docker buildx build \
  --push \
  --cache-to type=registry,ref=user/homeiq-cache:websocket,mode=max \
  --cache-from type=registry,ref=user/homeiq-cache:websocket \
  -t user/homeiq-websocket:latest \
  -f services/websocket-ingestion/Dockerfile .
```

**Benefits:**
- Cache persists across CI/CD runs
- Team members share build cache
- Faster builds on clean environments

---

### 2. Image Size Optimization (Priority: High)

#### 2.1 Standardize Python Base Images

**Current Issue:** Inconsistent Python versions and image variants across services.

**Recommendation:** Standardize on `python:3.12-alpine` for all Python services (upgrade from 3.11).

**Benefits:**
- Python 3.12 is 10-15% faster than 3.11
- Smaller base image (~45MB vs ~165MB for standard python:3.12)
- Better security with latest Python version
- Consistent behavior across all services

**Migration Path:**
1. Update all Dockerfiles to use `python:3.12-alpine`
2. Test compatibility (Python 3.12 is mostly backward compatible with 3.11)
3. Update CI/CD pipelines

---

#### 2.2 Implement .dockerignore Best Practices

**Current State:** `.dockerignore` files exist but could be more comprehensive.

**Enhanced `.dockerignore` Template:**
```plaintext
# Version control
.git/
.gitignore
.github/

# Documentation
*.md
!README.md
docs/
implementation/

# Development files
.vscode/
.idea/
*.swp
*.swo
*~

# Python artifacts
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Testing
.pytest_cache/
.coverage
.tox/
htmlcov/
test-reports/
test-results/

# Environment
.env
.env.*
!.env.example
*.env

# Logs
*.log
logs/
ha_events.log

# Node (for dashboard)
node_modules/
npm-debug.log*
yarn-debug.log*

# Docker
Dockerfile*
docker-compose*.yml
!Dockerfile
.dockerignore

# IDE
.vscode/
.idea/

# OS files
.DS_Store
Thumbs.db

# Temporary files
tmp/
temp/
*.tmp
```

**Benefits:**
- Faster builds (smaller context sent to Docker daemon)
- Reduced image size
- Fewer cache invalidations

---

#### 2.3 Multi-Stage Build Enhancements

**Current State:** Multi-stage builds implemented but can be optimized further.

**Enhanced Pattern for Python Services:**
```dockerfile
# syntax=docker/dockerfile:1
FROM python:3.12-alpine AS base
WORKDIR /app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Builder stage - Install dependencies
FROM base AS builder
RUN apk add --no-cache gcc musl-dev linux-headers
COPY requirements-prod.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir --user -r requirements-prod.txt

# Development stage - Include dev tools
FROM base AS development
RUN apk add --no-cache curl iputils busybox-extras
COPY --from=builder /root/.local /root/.local
COPY . .
ENV PATH=/root/.local/bin:$PATH
CMD ["python", "-m", "src.main"]

# Production stage - Minimal runtime
FROM base AS production
RUN apk add --no-cache curl && \
    addgroup -g 1001 -S appgroup && \
    adduser -S appuser -u 1001 -G appgroup
    
COPY --from=builder /root/.local /home/appuser/.local
COPY services/websocket-ingestion/src/ ./src/
COPY shared/ ./shared/

RUN chown -R appuser:appgroup /app /home/appuser/.local && \
    mkdir -p /app/logs && \
    chown -R appuser:appgroup /app/logs

ENV PYTHONPATH=/app:/app/src
ENV PATH=/home/appuser/.local/bin:$PATH
USER appuser

EXPOSE 8001
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

CMD ["python", "-m", "main"]
```

**Benefits:**
- Separate development and production targets
- Smaller production images (no build tools)
- Faster development iterations

---

### 3. Security Enhancements (Priority: High)

#### 3.1 Implement Image Vulnerability Scanning

**Solution:** Add Trivy scanning to CI/CD pipeline.

**GitHub Actions Integration:**
```yaml
name: Docker Security Scan

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Build image
        run: |
          docker build -t homeiq:test \
            -f services/websocket-ingestion/Dockerfile .
      
      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: 'homeiq:test'
          format: 'sarif'
          output: 'trivy-results.sarif'
          severity: 'CRITICAL,HIGH'
      
      - name: Upload Trivy results to GitHub Security
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: 'trivy-results.sarif'
```

**Benefits:**
- Automated vulnerability detection
- Early detection of security issues
- Compliance with security standards

---

#### 3.2 Enhance Container Security Context

**Current State:** Non-root users implemented, but can be enhanced.

**Recommended Enhancements:**
```yaml
# Enhanced docker-compose.yml security
services:
  websocket-ingestion:
    security_opt:
      - no-new-privileges:true
      - seccomp:unconfined  # Only if needed for specific syscalls
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE  # Only if binding to privileged ports
    read_only: true  # Where possible
    tmpfs:
      - /tmp
      - /var/tmp
```

**Benefits:**
- Reduced attack surface
- Prevents privilege escalation
- Follows principle of least privilege

---

#### 3.3 Secrets Management

**Current State:** Secrets in environment files (good), but can be enhanced.

**Recommended Enhancement:**
```yaml
# docker-compose.prod.yml
services:
  websocket-ingestion:
    secrets:
      - influxdb_token
      - home_assistant_token
    environment:
      - INFLUXDB_TOKEN_FILE=/run/secrets/influxdb_token
      - HOME_ASSISTANT_TOKEN_FILE=/run/secrets/home_assistant_token

secrets:
  influxdb_token:
    file: ./secrets/influxdb_token.txt
  home_assistant_token:
    file: ./secrets/home_assistant_token.txt
```

**Benefits:**
- Secrets not in environment variables
- Better security posture
- Secrets not visible in `docker inspect`

---

### 4. Development Workflow Optimization (Priority: Medium)

#### 4.1 Implement Docker Compose Override Pattern

**Solution:** Use compose override files for different environments.

**File Structure:**
```
docker-compose.yml           # Base configuration (shared)
docker-compose.override.yml  # Local development (git-ignored)
docker-compose.prod.yml      # Production overrides
docker-compose.dev.yml       # Development overrides (committed)
docker-compose.test.yml      # Testing overrides
```

**Usage:**
```bash
# Development (automatic override)
docker-compose up

# Production (explicit)
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up

# Testing
docker-compose -f docker-compose.yml -f docker-compose.test.yml up
```

**Benefits:**
- Single source of truth for common config
- Environment-specific overrides
- No duplication across compose files

---

#### 4.2 Add Development Hot-Reload Support

**Enhancement for Development:**
```dockerfile
# Add development stage with hot-reload
FROM base AS development
RUN apk add --no-cache curl
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV WATCHFILES_FORCE_POLLING=true
WORKDIR /app
CMD ["watchfiles", "python -m src.main", "src/"]
```

**Benefits:**
- Faster development cycles
- No container rebuilds for code changes
- Better developer experience

---

### 5. CI/CD Pipeline Optimization (Priority: Medium)

#### 5.1 Implement Buildx Bake for Multi-Service Builds

**Solution:** Use Docker Bake for building multiple services efficiently.

**docker-bake.hcl:**
```hcl
group "default" {
  targets = ["websocket", "enrichment", "admin-api", "dashboard"]
}

target "websocket" {
  context = "."
  dockerfile = "services/websocket-ingestion/Dockerfile"
  tags = ["homeiq/websocket:latest"]
  cache-from = ["type=gha"]
  cache-to = ["type=gha,mode=max"]
}

target "enrichment" {
  context = "."
  dockerfile = "services/enrichment-pipeline/Dockerfile"
  tags = ["homeiq/enrichment:latest"]
  cache-from = ["type=gha"]
  cache-to = ["type=gha,mode=max"]
}

target "admin-api" {
  context = "."
  dockerfile = "services/admin-api/Dockerfile"
  tags = ["homeiq/admin-api:latest"]
  cache-from = ["type=gha"]
  cache-to = ["type=gha,mode=max"]
}

target "dashboard" {
  context = "services/health-dashboard"
  dockerfile = "Dockerfile"
  tags = ["homeiq/dashboard:latest"]
  cache-from = ["type=gha"]
  cache-to = ["type=gha,mode=max"]
}
```

**Usage:**
```bash
# Build all services with shared cache
docker buildx bake

# Build specific service
docker buildx bake websocket

# Build and push all
docker buildx bake --push
```

**Benefits:**
- Parallel builds across services
- Shared build cache
- Consistent build configuration
- Faster CI/CD pipelines

---

#### 5.2 GitHub Actions Workflow Optimization

**Enhanced CI/CD Workflow:**
```yaml
name: Build and Push Docker Images

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        service:
          - websocket-ingestion
          - enrichment-pipeline
          - admin-api
          - health-dashboard
          - data-retention
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      
      - name: Login to Docker Hub
        if: github.event_name != 'pull_request'
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}
      
      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ github.repository }}/${{ matrix.service }}
          tags: |
            type=ref,event=branch
            type=ref,event=pr
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=sha
      
      - name: Build and push
        uses: docker/build-push-action@v6
        with:
          context: .
          file: services/${{ matrix.service }}/Dockerfile
          push: ${{ github.event_name != 'pull_request' }}
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
          platforms: linux/amd64,linux/arm64  # Multi-arch support
```

**Benefits:**
- Matrix builds for parallel execution
- Automatic semantic versioning
- Multi-architecture support
- Efficient cache utilization

---

### 6. Monitoring and Observability (Priority: Low-Medium)

#### 6.1 Enhanced Health Checks

**Recommendation:** Add more detailed health checks.

```dockerfile
# Enhanced health check with timeout and detailed output
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8001/health?detailed=true || exit 1
```

**Benefits:**
- Better failure detection
- More context for debugging
- Improved orchestration decisions

---

#### 6.2 Add Build Metrics

**Solution:** Instrument builds to collect metrics.

```bash
# Add build timing to CI/CD
time docker buildx build \
  --progress=plain \
  --cache-from type=gha \
  --cache-to type=gha,mode=max \
  -f services/websocket-ingestion/Dockerfile .
```

**Benefits:**
- Track build performance over time
- Identify optimization opportunities
- Measure impact of changes

---

### 7. Resource Optimization (Priority: Medium)

#### 7.1 Right-Size Resource Limits

**Current State:** Resource limits defined but could be optimized based on actual usage.

**Recommendation:** Add resource monitoring and adjust limits.

```yaml
# Enhanced resource limits based on profiling
services:
  websocket-ingestion:
    deploy:
      resources:
        limits:
          memory: 384M  # Reduced from 512M after profiling
          cpus: '0.5'
        reservations:
          memory: 192M  # Reduced from 256M
          cpus: '0.25'
```

**Action Items:**
1. Profile actual memory/CPU usage under load
2. Adjust limits based on 90th percentile usage + 20% buffer
3. Monitor for OOM kills and throttling

---

### 8. Documentation and Maintenance (Priority: Low)

#### 8.1 Document Build Process

**Create:** `docs/DOCKER_BUILD_GUIDE.md`

**Contents:**
- Build optimization techniques
- Cache management
- Multi-stage build patterns
- Troubleshooting common issues

#### 8.2 Create Docker Compose Reference

**Create:** `docs/DOCKER_COMPOSE_REFERENCE.md`

**Contents:**
- Environment-specific configurations
- Override patterns
- Service dependencies
- Volume management

---

## Implementation Roadmap

### Phase 1: Quick Wins (Week 1-2)
**Effort:** 8-12 hours  
**Impact:** High

1. ✅ Add BuildKit cache mounts to all Python services
2. ✅ Optimize layer ordering in all Dockerfiles
3. ✅ Enhance .dockerignore files
4. ✅ Implement build cache backends for CI/CD
5. ✅ Standardize on Python 3.12-alpine

**Expected Results:**
- 50-70% faster build times
- 30-40% smaller images
- Immediate developer experience improvement

---

### Phase 2: Security & Quality (Week 3-4)
**Effort:** 6-8 hours  
**Impact:** High

1. ✅ Add Trivy vulnerability scanning
2. ✅ Enhance security contexts
3. ✅ Implement Docker secrets management
4. ✅ Add multi-stage development/production targets

**Expected Results:**
- Improved security posture
- Automated vulnerability detection
- Better separation of dev/prod environments

---

### Phase 3: Workflow Optimization (Week 5-6)
**Effort:** 4-6 hours  
**Impact:** Medium

1. ✅ Implement Docker Compose override pattern
2. ✅ Add development hot-reload support
3. ✅ Create docker-bake.hcl for multi-service builds
4. ✅ Optimize GitHub Actions workflows

**Expected Results:**
- Faster development cycles
- Better CI/CD efficiency
- Parallel builds

---

### Phase 4: Documentation & Monitoring (Week 7-8)
**Effort:** 2-4 hours  
**Impact:** Low-Medium

1. ✅ Create comprehensive Docker documentation
2. ✅ Add build metrics collection
3. ✅ Profile and right-size resource limits
4. ✅ Create troubleshooting guides

**Expected Results:**
- Better team knowledge sharing
- Data-driven optimization
- Reduced support burden

---

## Success Metrics

### Build Performance
- **Target:** 50-70% reduction in build times
- **Measurement:** CI/CD pipeline duration, local build times
- **Baseline:** Current build times across all services

### Image Size
- **Target:** 30-40% reduction in image sizes
- **Measurement:** `docker images` output for all services
- **Baseline:** Current image sizes

### Security
- **Target:** Zero critical/high vulnerabilities
- **Measurement:** Trivy scan results
- **Baseline:** Initial vulnerability scan

### Developer Experience
- **Target:** Sub-10-second code change to running container
- **Measurement:** Time from code save to container restart
- **Baseline:** Current development workflow timing

---

## Risk Assessment

### Low Risk
- BuildKit cache mounts (backward compatible)
- Layer ordering optimization (no functionality change)
- .dockerignore enhancements (no runtime impact)

### Medium Risk
- Python 3.12 upgrade (requires testing)
- Security context changes (may require adjustments)
- Resource limit changes (monitor for OOM/throttling)

### Mitigation Strategies
1. Implement changes incrementally
2. Test thoroughly in development environment
3. Monitor production metrics closely
4. Maintain rollback capability
5. Document all changes

---

## Cost-Benefit Analysis

### Time Investment
- **Initial Implementation:** 16-24 hours
- **Testing & Validation:** 4-8 hours
- **Documentation:** 2-4 hours
- **Total:** 22-36 hours

### Expected Returns
- **Build Time Savings:** 5-10 minutes per build × 20 builds/day = 100-200 min/day
- **Developer Productivity:** 2-3 hours/week per developer
- **CI/CD Cost Reduction:** 30-40% reduction in build minutes
- **Reduced Image Pull Times:** 1-2 minutes per deployment

### ROI Timeline
- **Break-even:** 2-3 weeks
- **6-month savings:** 80-120 hours of developer time
- **Annual savings:** 160-240 hours + reduced infrastructure costs

---

## Questions for Stakeholders

1. **Scope:** Should we include all 13 services or prioritize core services first?
2. **Timing:** Any deployment freezes or critical periods to avoid?
3. **Python 3.12:** Any known compatibility issues with current codebase?
4. **Multi-arch:** Do we need ARM64 support for any deployment targets?
5. **CI/CD:** Using GitHub Actions, or different CI/CD platform?
6. **Registry:** Docker Hub, GitHub Container Registry, or private registry?

---

## Next Steps

1. **Review & Approve:** Stakeholder review of this plan
2. **Scope Finalization:** Determine which phases to implement
3. **Timeline Agreement:** Confirm implementation schedule
4. **Kickoff:** Begin Phase 1 implementation
5. **Progress Tracking:** Weekly progress updates

---

## References

- [Docker Best Practices Documentation](https://docs.docker.com/build/building/best-practices/)
- [BuildKit Cache Documentation](https://docs.docker.com/build/cache/)
- [Multi-stage Build Patterns](https://docs.docker.com/build/building/multi-stage/)
- [Docker Compose Best Practices](https://docs.docker.com/compose/compose-file/)
- [Alpine Linux Security](https://alpinelinux.org/about/)

---

## Appendix A: Before/After Comparison

### Websocket Ingestion Service

**Current Dockerfile (58 lines):**
- Build time: ~2-3 minutes (clean build)
- Image size: ~105 MB
- Cache efficiency: Medium

**Optimized Dockerfile (estimated):**
- Build time: ~45 seconds (cached), ~2 minutes (clean)
- Image size: ~85 MB
- Cache efficiency: High
- Improvement: 50% faster builds, 20% smaller image

### Health Dashboard

**Current Dockerfile (64 lines):**
- Build time: ~4-5 minutes (clean build)
- Image size: ~135 MB
- Cache efficiency: Medium

**Optimized Dockerfile (estimated):**
- Build time: ~1.5 minutes (cached), ~3 minutes (clean)
- Image size: ~95 MB
- Improvement: 60-70% faster builds, 30% smaller image

---

## Appendix B: Sample Optimized Dockerfiles

See implementation files for complete optimized Dockerfiles for:
- Python services (websocket-ingestion, enrichment-pipeline, admin-api)
- Node.js service (health-dashboard)
- Specialized services (data-retention, external data services)

---

**Document Version:** 1.0  
**Last Updated:** October 13, 2025  
**Author:** @dev (Developer Agent)  
**Reviewers:** Pending

