# 2025 Docker Release & Deployment Recommendations for HomeIQ

**Date:** December 23, 2025  
**Project:** HomeIQ  
**Context:** Microservices architecture with 30+ services, Docker Compose deployment

---

## Executive Summary

Based on 2025 best practices and current industry standards, this document provides recommendations for:
1. **Container Registry Selection** (GitHub Container Registry recommended)
2. **Image Tagging Strategy** (Semantic versioning + commit SHA)
3. **CI/CD Pipeline Enhancement** (Automated builds and releases)
4. **Security & Compliance** (Image scanning, SBOM generation)
5. **Multi-Architecture Support** (ARM64 for NUC deployment)

---

## 1. Container Registry Recommendations

### ✅ **Recommended: GitHub Container Registry (ghcr.io)**

**Why GitHub Container Registry:**
- ✅ **Integrated with GitHub** - No separate account needed
- ✅ **Free for public repos** - Unlimited storage and bandwidth
- ✅ **Fine-grained permissions** - Package-level access control
- ✅ **Automatic security scanning** - Built-in vulnerability detection
- ✅ **SBOM support** - Software Bill of Materials generation
- ✅ **Better for CI/CD** - Native GitHub Actions integration
- ✅ **No rate limits** - Unlike Docker Hub free tier

**Alternative: Docker Hub**
- ⚠️ Rate limits on free tier (200 pulls/6 hours)
- ⚠️ Requires separate account management
- ✅ Better public discoverability
- ✅ More familiar to developers

**Recommendation:** Use **GitHub Container Registry (ghcr.io)** for HomeIQ

### Implementation

```yaml
# .github/workflows/docker-release.yml
name: Docker Release

on:
  push:
    tags:
      - 'v*.*.*'
  workflow_dispatch:
    inputs:
      version:
        description: 'Semantic version (e.g., 1.2.3)'
        required: true

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      
      - name: Log in to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ghcr.io/${{ github.repository_owner }}/homeiq-${{ matrix.service }}
          tags: |
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=semver,pattern={{major}}
            type=sha,prefix={{branch}}-
            type=raw,value=latest,enable={{is_default_branch}}
      
      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          file: services/${{ matrix.service }}/Dockerfile
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
          platforms: linux/amd64,linux/arm64
```

---

## 2. Image Tagging Strategy

### Current State
- Using `latest` tag only
- Commit SHA tagging (`3aaef97e`) manually

### ✅ **Recommended: Semantic Versioning + Multi-Tag Strategy**

**Tag Strategy:**
```bash
# Semantic version tags
ghcr.io/wtthornton/homeiq-ai-automation-ui:1.2.3      # Full version
ghcr.io/wtthornton/homeiq-ai-automation-ui:1.2        # Minor version
ghcr.io/wtthornton/homeiq-ai-automation-ui:1          # Major version
ghcr.io/wtthornton/homeiq-ai-automation-ui:latest      # Latest (main branch only)

# Build metadata tags
ghcr.io/wtthornton/homeiq-ai-automation-ui:master-3aaef97e  # Branch + SHA
ghcr.io/wtthornton/homeiq-ai-automation-ui:3aaef97e        # SHA only
```

### Benefits
- ✅ **Rollback capability** - Pin to specific versions
- ✅ **Environment promotion** - dev → staging → prod
- ✅ **A/B testing** - Run multiple versions simultaneously
- ✅ **Audit trail** - Track which commit is in production

### Implementation

```bash
# Create version tag
git tag -a v1.2.3 -m "Release version 1.2.3: Fix TypeScript errors and port conflicts"
git push origin v1.2.3

# GitHub Actions will automatically:
# 1. Build images for all services
# 2. Tag with semantic versions
# 3. Push to ghcr.io
# 4. Generate release notes
```

---

## 3. CI/CD Pipeline Enhancements

### Current State
- ✅ GitHub Actions workflow exists (`.github/workflows/docker-build.yml`)
- ⚠️ Only builds, doesn't push
- ⚠️ Triggers on `main`/`develop`, but project uses `master`
- ⚠️ No automated releases

### ✅ **Recommended Enhancements**

#### 3.1 Automated Release Workflow

```yaml
# .github/workflows/release.yml
name: Release

on:
  push:
    tags:
      - 'v*.*.*'
  workflow_dispatch:
    inputs:
      version:
        description: 'Semantic version'
        required: true
      services:
        description: 'Comma-separated service list (empty = all)'
        required: false

jobs:
  release:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        service:
          - ai-automation-ui
          - ai-automation-service-new
          - websocket-ingestion
          - data-api
          # ... all services
    steps:
      - uses: actions/checkout@v4
      
      - name: Build and push
        # ... (see full workflow above)
      
      - name: Generate SBOM
        uses: anchore/sbom-action@v0
        with:
          image: ghcr.io/${{ github.repository_owner }}/homeiq-${{ matrix.service }}:${{ github.ref_name }}
          format: spdx-json
      
      - name: Security scan
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ghcr.io/${{ github.repository_owner }}/homeiq-${{ matrix.service }}:${{ github.ref_name }}
          format: 'sarif'
          output: 'trivy-results.sarif'
```

#### 3.2 Update Branch Configuration

**Issue:** Workflow triggers on `main`/`develop`, but project uses `master`

**Fix:**
```yaml
# .github/workflows/docker-build.yml
on:
  push:
    branches: [ master, main, develop ]  # Add 'master'
```

#### 3.3 Matrix Build Strategy

**Current:** Sequential builds  
**Recommended:** Parallel matrix builds with caching

```yaml
strategy:
  fail-fast: false
  matrix:
    service:
      - ai-automation-ui
      - ai-automation-service-new
      # ... all services
    include:
      - service: ai-automation-ui
        dockerfile: services/ai-automation-ui/Dockerfile
      - service: ai-automation-service-new
        dockerfile: services/ai-automation-service-new/Dockerfile
```

---

## 4. Security & Compliance (2025 Best Practices)

### 4.1 Image Scanning

**Recommended Tools:**
- ✅ **Trivy** - Comprehensive vulnerability scanning
- ✅ **Snyk** - Dependency scanning
- ✅ **Grype** - Fast vulnerability scanning

**Implementation:**
```yaml
- name: Scan image
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: ghcr.io/${{ github.repository_owner }}/homeiq-${{ matrix.service }}:${{ github.ref_name }}
    format: 'table'
    exit-code: '1'
    severity: 'CRITICAL,HIGH'
    output: 'trivy-results.txt'
```

### 4.2 SBOM Generation

**Why:** Software Bill of Materials required for compliance (CISA, NIST)

**Implementation:**
```yaml
- name: Generate SBOM
  uses: anchore/sbom-action@v0
  with:
    image: ghcr.io/${{ github.repository_owner }}/homeiq-${{ matrix.service }}:${{ github.ref_name }}
    format: spdx-json
    output-file: sbom-${{ matrix.service }}.json
```

### 4.3 Sign Images (Cosign)

**Why:** Verify image authenticity and prevent tampering

```yaml
- name: Sign image
  uses: sigstore/cosign-installer@v3
  
- name: Sign with keyless
  run: |
    cosign sign --yes \
      ghcr.io/${{ github.repository_owner }}/homeiq-${{ matrix.service }}:${{ github.ref_name }}
```

---

## 5. Multi-Architecture Support

### Current State
- Building for `linux/amd64` only
- HomeIQ runs on Intel NUC (AMD64), but ARM64 support enables:
  - Future Raspberry Pi deployments
  - Apple Silicon development
  - Cloud ARM instances (cost savings)

### ✅ **Recommended: Multi-Architecture Builds**

```yaml
- name: Build and push
  uses: docker/build-push-action@v5
  with:
    platforms: linux/amd64,linux/arm64
    push: true
    tags: ${{ steps.meta.outputs.tags }}
```

**Benefits:**
- ✅ Future-proof for ARM deployments
- ✅ Cost savings on ARM cloud instances
- ✅ Better developer experience (Apple Silicon)

---

## 6. Docker Compose Production Deployment

### Current State
- Using `docker-compose.yml` for all environments
- No separate production configuration

### ✅ **Recommended: Environment-Specific Compose Files**

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  ai-automation-ui:
    image: ghcr.io/wtthornton/homeiq-ai-automation-ui:${VERSION:-latest}
    restart: always
    # Production-specific config
    
  ai-automation-service-new:
    image: ghcr.io/wtthornton/homeiq-ai-automation-service-new:${VERSION:-latest}
    restart: always
    # Production-specific config
```

**Deployment:**
```bash
# Set version
export VERSION=1.2.3

# Pull and deploy
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

---

## 7. Image Optimization (2025 Best Practices)

### 7.1 Multi-Stage Builds
✅ Already implemented in most services

### 7.2 BuildKit Cache Mounts
```dockerfile
# Use BuildKit cache mounts for faster builds
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --no-cache-dir -r requirements.txt
```

### 7.3 Distroless/Minimal Base Images
```dockerfile
# Use distroless for Python services
FROM gcr.io/distroless/python3-debian12:latest
# Or Alpine for smaller images
FROM python:3.12-alpine
```

### 7.4 Layer Optimization
```dockerfile
# Order matters - put frequently changing layers last
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .  # This changes most often, so put it last
```

---

## 8. Monitoring & Observability

### 8.1 Image Metadata Labels
```dockerfile
LABEL org.opencontainers.image.title="HomeIQ AI Automation UI"
LABEL org.opencontainers.image.description="AI-powered automation interface"
LABEL org.opencontainers.image.version="${VERSION}"
LABEL org.opencontainers.image.created="${BUILD_DATE}"
LABEL org.opencontainers.image.revision="${GIT_COMMIT}"
LABEL org.opencontainers.image.source="https://github.com/wtthornton/HomeIQ"
```

### 8.2 Health Checks
✅ Already implemented in docker-compose.yml

### 8.3 Image Size Monitoring
```yaml
- name: Check image size
  run: |
    SIZE=$(docker image inspect ghcr.io/... --format='{{.Size}}')
    echo "Image size: $SIZE bytes"
    # Fail if > 1GB
    if [ $SIZE -gt 1073741824 ]; then
      echo "Image too large!"
      exit 1
    fi
```

---

## 9. Rollback Strategy

### Current State
- No automated rollback mechanism
- Manual container restart required

### ✅ **Recommended: Automated Rollback**

```bash
# Rollback script
#!/bin/bash
VERSION=$1
SERVICE=$2

# Update docker-compose.prod.yml with previous version
sed -i "s|image:.*$SERVICE.*|image: ghcr.io/wtthornton/homeiq-$SERVICE:$VERSION|" docker-compose.prod.yml

# Redeploy
docker compose -f docker-compose.prod.yml up -d $SERVICE
```

---

## 10. Cost Optimization

### 10.1 Registry Storage
- ✅ **GitHub Container Registry:** Free for public repos
- ⚠️ **Docker Hub:** Free tier has storage limits

### 10.2 Image Cleanup
```yaml
- name: Cleanup old images
  run: |
    # Keep only last 10 versions
    docker image prune -a --filter "until=720h" -f
```

### 10.3 Build Cache Optimization
```yaml
cache-from: type=gha
cache-to: type=gha,mode=max
```

---

## Implementation Priority

### Phase 1: Immediate (This Week)
1. ✅ Switch to GitHub Container Registry
2. ✅ Implement semantic versioning
3. ✅ Update GitHub Actions workflow for `master` branch
4. ✅ Add automated image pushing

### Phase 2: Short Term (This Month)
1. ✅ Add security scanning (Trivy)
2. ✅ Generate SBOMs
3. ✅ Multi-architecture builds
4. ✅ Image signing (Cosign)

### Phase 3: Medium Term (Next Quarter)
1. ✅ Automated rollback mechanism
2. ✅ Production-specific compose files
3. ✅ Image size monitoring
4. ✅ Cost optimization strategies

---

## Quick Start: Release Your First Version

```bash
# 1. Update version in code (if needed)
# 2. Commit changes
git add .
git commit -m "Prepare release v1.2.3"

# 3. Create and push tag
git tag -a v1.2.3 -m "Release v1.2.3: Fix TypeScript errors and port conflicts"
git push origin v1.2.3

# 4. GitHub Actions will automatically:
#    - Build all service images
#    - Tag with semantic versions
#    - Push to ghcr.io
#    - Run security scans
#    - Generate SBOMs

# 5. Deploy to production
export VERSION=1.2.3
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

---

## References

- [GitHub Container Registry Documentation](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- [Docker Best Practices 2025](https://docs.docker.com/develop/dev-best-practices/)
- [OCI Image Specification](https://github.com/opencontainers/image-spec)
- [Trivy Security Scanner](https://github.com/aquasecurity/trivy)
- [Cosign Image Signing](https://github.com/sigstore/cosign)

---

**Next Steps:**
1. Review and approve recommendations
2. Create GitHub Actions workflow for releases
3. Set up GitHub Container Registry authentication
4. Create first semantic version tag
5. Test deployment process

