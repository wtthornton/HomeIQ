# Docker Build Context Issue

**Date:** January 2025  
**Status:** ⚠️ Issue Discovered

## Problem

Docker builds are failing because of a mismatch between Dockerfile expectations and docker-compose.yml build contexts.

### Root Cause

**Dockerfiles expect root context:**
- Dockerfiles use `COPY ../shared/ ./shared/` which requires the build context to be the **root directory**
- This allows access to the `shared/` directory at the project root

**docker-compose.yml uses service context:**
- docker-compose.yml sets `context: ./services/{service-name}` 
- This restricts the build context to the service directory only
- `../shared/` is **outside** this context and cannot be accessed

### Error Example

```bash
docker build -f services/websocket-ingestion/Dockerfile services/websocket-ingestion

ERROR: failed to calculate checksum of ref: "/shared": not found
```

## Solution Options

### Option 1: Change Build Context to Root (Recommended)

**Update docker-compose.yml:**
```yaml
websocket-ingestion:
  build:
    context: .  # Root directory
    dockerfile: services/websocket-ingestion/Dockerfile
```

**Update Dockerfiles:**
```dockerfile
# Change from:
COPY ../shared/ ./shared/
COPY src/ ./src/

# To:
COPY shared/ ./shared/
COPY services/websocket-ingestion/src/ ./src/
```

**Pros:**
- ✅ Allows access to shared directory
- ✅ Consistent with Dockerfile expectations
- ✅ Works with current Dockerfile structure

**Cons:**
- ⚠️ Requires updating all Dockerfiles
- ⚠️ Larger build context (includes entire project)

### Option 2: Copy Shared Code into Services

**Create a build script that:**
1. Copies `shared/` into each service directory before build
2. Dockerfiles use `COPY shared/ ./shared/`
3. Clean up copied files after build

**Pros:**
- ✅ Smaller build contexts
- ✅ No docker-compose.yml changes needed

**Cons:**
- ⚠️ Requires build orchestration script
- ⚠️ Shared code duplication during builds
- ⚠️ More complex build process

### Option 3: Use Docker BuildKit Dependencies

**Use BuildKit's dependency feature:**
```dockerfile
# syntax=docker/dockerfile:1.4
FROM ... AS shared
COPY shared/ ./shared/

FROM ... AS production
COPY --from=shared /app/shared ./shared/
```

**Pros:**
- ✅ Clean separation
- ✅ No context changes needed

**Cons:**
- ⚠️ Requires BuildKit
- ⚠️ More complex Dockerfile structure

## Recommended Approach

**Option 1** is recommended because:
1. It aligns with how Dockerfiles are currently written
2. It's the simplest solution
3. Modern Docker handles large contexts efficiently with layer caching

## Implementation Steps

1. **Update docker-compose.yml** - Change all service build contexts to root
2. **Update Dockerfiles** - Change paths to work with root context:
   - `COPY ../shared/` → `COPY shared/`
   - `COPY src/` → `COPY services/{service}/src/`
3. **Test builds** - Verify all services build correctly
4. **Update .dockerignore** - Ensure unnecessary files are excluded from context

## Affected Services

All services that use `COPY ../shared/`:
- websocket-ingestion
- data-api
- device-intelligence-service
- ai-training-service
- ai-query-service
- ai-pattern-service
- device-setup-assistant
- device-recommender
- device-database-client
- device-context-classifier
- device-health-monitor
- data-retention
- log-aggregator
- (and others)

## Next Steps

1. ✅ **Issue identified** - Build context mismatch documented
2. ⏳ **Decision needed** - Choose solution approach
3. ⏳ **Implementation** - Update docker-compose.yml and Dockerfiles
4. ⏳ **Testing** - Verify all builds work correctly
5. ⏳ **Documentation** - Update build instructions

## Related Files

- `docker-compose.yml` - Build context configuration
- `services/*/Dockerfile` - Dockerfile COPY commands
- `.dockerignore` - Context exclusion patterns

