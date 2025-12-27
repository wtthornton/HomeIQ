# Docker Optimization Quick Reference
## HA Ingestor - At-a-Glance Guide

**Quick Access:** For detailed information, see [Docker Optimization Plan](DOCKER_OPTIMIZATION_PLAN.md)

---

## 🚀 Top 5 Quick Wins

### Latest Completed Actions (November 2025)
- ✅ `ner-service` rebuilt with CPU-only multi-stage Dockerfile; image reduced from ~12.6 GB to ~1.6 GB (models cached in `/app/model-cache`).
- ✅ `ai-automation-service` now stores transformer caches in `/app/models` and prunes Hugging Face caches during build; image holds steady at ~6.1 GB despite bundled models.
- ✅ `openvino-service` converted to multi-stage build with pip installs in builder layer; final runtime image trimmed while keeping INT8 model support.

Use the sections below to continue iterating on additional services.

### 1. Add BuildKit Cache Mounts (Immediate ~60% Speed Boost)

```dockerfile
# Before
RUN pip install -r requirements.txt

# After
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt
```

**Time to Implement:** 5 minutes per service  
**Impact:** 60-80% faster dependency installs

---

### 2. Optimize Layer Ordering (50-70% Faster Builds)

```dockerfile
# ❌ BAD - Invalidates cache on any file change
COPY . .
RUN pip install -r requirements.txt

# ✅ GOOD - Only rebuilds when dependencies change
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt
COPY . .
```

**Time to Implement:** 10 minutes per service  
**Impact:** Cached builds in seconds vs minutes

---

### 3. Enhance .dockerignore (Faster Context Transfer)

```plaintext
# Add these to all .dockerignore files
__pycache__/
*.py[cod]
.pytest_cache/
.coverage
docs/
implementation/
*.md
!README.md
test-reports/
test-results/
```

**Time to Implement:** 5 minutes per service  
**Impact:** 30-50% faster build context transfer

---

### 4. Use Python 3.12 Alpine (Smaller, Faster)

```dockerfile
# Before
FROM python:3.11-alpine

# After  
FROM python:3.12-alpine
```

**Time to Implement:** 2 minutes per service  
**Impact:** 10-15% performance boost, better security

---

### 5. Enable GitHub Actions Build Cache

```yaml
- name: Build and push
  uses: docker/build-push-action@v6
  with:
    cache-from: type=gha
    cache-to: type=gha,mode=max
```

**Time to Implement:** 10 minutes (one-time)  
**Impact:** 50-70% faster CI/CD builds

---

## 📊 Expected Improvements

| Metric | Current | After Optimization | Improvement |
|--------|---------|-------------------|-------------|
| Clean Build Time | 3-5 min | 2-3 min | ~40% |
| Cached Build Time | 2-3 min | 30-60 sec | ~70% |
| Image Size (Python) | 105 MB | 85 MB | ~20% |
| Image Size (Node) | 135 MB | 95 MB | ~30% |
| CI/CD Pipeline | 15-20 min | 8-12 min | ~50% |

---

## 🎯 Implementation Priority

### High Priority (Week 1)
1. ✅ Add cache mounts to Python services
2. ✅ Optimize layer ordering
3. ✅ Update .dockerignore files
4. ✅ Standardize on Python 3.12

### Medium Priority (Week 2-3)
1. ✅ Add vulnerability scanning
2. ✅ Enhance security contexts
3. ✅ Implement Docker Bake

### Low Priority (Week 4+)
1. ✅ Add development hot-reload
2. ✅ Profile resource limits
3. ✅ Complete documentation

---

## 🔧 Common Commands

### Build with Cache
```bash
# Export cache locally
docker buildx build \
  --cache-from type=local,src=/tmp/.buildx-cache \
  --cache-to type=local,dest=/tmp/.buildx-cache \
  -t my-image:latest .

# Use GitHub Actions cache
docker buildx build \
  --cache-from type=gha \
  --cache-to type=gha,mode=max \
  -t my-image:latest .
```

### Build All Services
```bash
# Using Docker Bake
docker buildx bake

# Build specific service
docker buildx bake websocket
```

### Clean Build Cache
```bash
# Prune build cache
docker buildx prune

# Prune with age filter
docker buildx prune --filter until=24h
```

---

## 🛡️ Security Checklist

- [ ] Use specific version tags (no `latest`)
- [ ] Run as non-root user
- [ ] Add security_opt: no-new-privileges
- [ ] Set resource limits
- [ ] Use read-only filesystems where possible
- [ ] Scan images with Trivy
- [ ] Use multi-stage builds
- [ ] Minimize attack surface (Alpine base)

---

## 📝 Before You Start

1. **Backup:** Commit current working state
2. **Test Environment:** Ensure dev environment is working
3. **Baseline:** Record current build times and image sizes
4. **Plan:** Choose services to optimize (start with core services)
5. **Validate:** Test each change before moving to next service

---

## 🧪 Testing Checklist

After each optimization:

- [ ] Build succeeds without errors
- [ ] Image size is smaller or same
- [ ] Container starts successfully
- [ ] Health checks pass
- [ ] All service endpoints respond
- [ ] No new security vulnerabilities
- [ ] Resource usage within limits

---

## 📚 Key Documentation

- **Full Plan:** [Docker Optimization Plan](DOCKER_OPTIMIZATION_PLAN.md)
- **Docker Structure:** [Docker Structure Guide](DOCKER_STRUCTURE_GUIDE.md)
- **Deployment:** [Deployment Guide](DEPLOYMENT_GUIDE.md)
- **Troubleshooting:** [Quick Reference](QUICK_REFERENCE_DOCKER.md)

---

## 🆘 Troubleshooting

### Build Cache Not Working
```bash
# Ensure BuildKit is enabled
export DOCKER_BUILDKIT=1

# Use buildx
docker buildx build --progress=plain .
```

### Image Too Large
```bash
# Analyze layers
docker history my-image:latest

# Check what's in the image
docker run --rm my-image:latest du -sh /*
```

### Slow npm installs
```bash
# Add to Dockerfile
RUN --mount=type=cache,target=/root/.npm npm ci --prefer-offline
```

---

## 💡 Pro Tips

1. **Order Matters:** Most-stable layers first, most-changing layers last
2. **Cache is Key:** Use `--mount=type=cache` for package managers
3. **Multi-stage:** Separate build and runtime environments
4. **Target Specific:** Use `--target` to build specific stages
5. **Measure Everything:** Track build times before and after changes
6. **Small Commits:** Optimize one service at a time
7. **Test Locally:** Validate before pushing to CI/CD

---

## 📈 Success Metrics Dashboard

Track these metrics weekly:

```bash
# Build time
time docker build -t test .

# Image size
docker images | grep homeiq

# Cache hit rate (look for CACHED in output)
docker build --progress=plain . 2>&1 | grep -c CACHED

# Vulnerability count
trivy image my-image:latest --severity HIGH,CRITICAL
```

---

## 🎓 Learning Resources

- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [BuildKit Documentation](https://docs.docker.com/build/buildkit/)
- [Multi-stage Builds](https://docs.docker.com/build/building/multi-stage/)
- [Cache Management](https://docs.docker.com/build/cache/)

---

**Last Updated:** October 13, 2025  
**Version:** 1.0  
**Maintained by:** @dev

