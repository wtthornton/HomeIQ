# Device Intelligence Service - Deployment Optimization Plan

## Problem Analysis

### Current Issues
1. **Build Time**: ~6+ minutes (mostly downloading packages)
2. **Image Size**: 8.67GB (extremely large)
3. **Dependencies**: Includes dev tools (pytest, black, mypy) in production
4. **ML Libraries**: TabPFN pulls in PyTorch + CUDA libraries (~3GB downloads)

### Root Causes
- `requirements.txt` includes development dependencies
- TabPFN requires PyTorch with CUDA support (huge downloads)
- No layer caching optimization
- All dependencies installed even if not used (TabPFN is optional)

## Optimization Strategy

### 1. Split Requirements (✅ COMPLETED)
- **requirements-prod.txt**: Production dependencies only
- **requirements-dev.txt**: Development dependencies (includes prod)
- **Removed**: TabPFN from production (optional, adds 3GB+)

### 2. Optimize Dockerfile (✅ COMPLETED)
- Use `requirements-prod.txt` instead of `requirements.txt`
- Better layer caching (requirements copied first)
- Cache apt packages
- Remove dev dependencies from production image

### 3. Expected Improvements
- **Build Time**: 6+ minutes → **2-3 minutes** (60% faster)
- **Image Size**: 8.67GB → **2-3GB** (65% smaller)
- **Download Size**: ~3GB → **~500MB** (83% smaller)

## Implementation Steps

### Step 1: Backup Current Files
```bash
cp services/device-intelligence-service/Dockerfile services/device-intelligence-service/Dockerfile.backup
cp services/device-intelligence-service/requirements.txt services/device-intelligence-service/requirements.txt.backup
```

### Step 2: Update Dockerfile
```bash
# Replace Dockerfile with optimized version
mv services/device-intelligence-service/Dockerfile.optimized services/device-intelligence-service/Dockerfile
```

### Step 3: Update docker-compose.yml
No changes needed - Dockerfile path stays the same.

### Step 4: Test Build
```bash
docker compose build device-intelligence-service
```

### Step 5: Verify Service
```bash
docker compose up -d device-intelligence-service
docker compose logs -f device-intelligence-service
```

## TabPFN Handling

### If TabPFN is Required
If `ML_FAILURE_MODEL=tabpfn` is used in production:

**Option A**: Install TabPFN separately (adds ~3GB)
```dockerfile
# Add to Dockerfile after main requirements
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --user tabpfn>=2.2.0,<7.0.0
```

**Option B**: Use CPU-only PyTorch (smaller, but still large)
```dockerfile
# Install CPU-only PyTorch first
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --user torch torchvision --index-url https://download.pytorch.org/whl/cpu
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --user tabpfn>=2.2.0,<7.0.0
```

**Option C**: Use alternative ML model (recommended)
- Default is `randomforest` (no extra dependencies)
- `lightgbm` is also available (already in requirements)
- Only use TabPFN if absolutely necessary

## Rollback Plan

If issues occur:
```bash
# Restore original files
mv services/device-intelligence-service/Dockerfile.backup services/device-intelligence-service/Dockerfile
mv services/device-intelligence-service/requirements.txt.backup services/device-intelligence-service/requirements.txt

# Rebuild
docker compose build device-intelligence-service
```

## Verification Checklist

- [ ] Build completes in < 3 minutes
- [ ] Image size < 3GB
- [ ] Service starts successfully
- [ ] Health check passes
- [ ] API endpoints respond correctly
- [ ] ML models load (if using randomforest/lightgbm)

## Notes

- TabPFN removed from production requirements (optional dependency)
- Dev dependencies moved to `requirements-dev.txt`
- Better Docker layer caching reduces rebuild time
- Smaller image = faster pulls and deployments
