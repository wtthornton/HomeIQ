# Docker Structure Guide - DO NOT BREAK THIS!

**Last Updated:** October 10, 2025  
**Status:** ✅ Working Configuration - VERIFIED

---

## ⚠️ CRITICAL WARNING

This document describes the **WORKING** Docker structure for the HA Ingestor project. These configurations have been tested and verified as operational. **DO NOT modify Dockerfiles or related configurations without understanding the implications documented here.**

---

## Working Directory Structure

Each service follows a specific directory structure that MUST be maintained:

```
services/
├── websocket-ingestion/
│   ├── Dockerfile                    ⚠️ CRITICAL - Uses "python -m src.main"
│   ├── src/
│   │   ├── main.py                   ← Entry point
│   │   └── ... (other modules)
│   └── requirements.txt
│
├── admin-api/
│   ├── Dockerfile                    ⚠️ CRITICAL - Requires PYTHONPATH
│   ├── src/
│   │   ├── simple_main.py            ← Entry point
│   │   └── ... (other modules)
│   └── requirements-prod.txt
│
├── enrichment-pipeline/
│   ├── Dockerfile
│   ├── src/
│   │   ├── main.py                   ← Entry point
│   │   └── ... (other modules)
│   └── requirements.txt
│
└── health-dashboard/
    ├── Dockerfile
    ├── nginx.conf                    ⚠️ CRITICAL - API proxy config
    ├── src/
    │   └── ... (React components)
    └── package.json
```

---

## Critical Dockerfile Configurations

### 1. WebSocket Ingestion Service

**File:** `services/websocket-ingestion/Dockerfile`

**CRITICAL CONFIGURATION:**

```dockerfile
# Run the application
CMD ["python", "-m", "src.main"]
```

**⚠️ DO NOT CHANGE TO:**
- ❌ `CMD ["python", "-m", "main"]` - Will cause ModuleNotFoundError
- ❌ `CMD ["python", "src/main.py"]` - May cause import issues
- ❌ `CMD ["python", "main.py"]` - Wrong path

**Why it must be `python -m src.main`:**
- The working directory is `/app`
- The main.py file is in `/app/src/main.py`
- Python module execution needs the full path from working directory
- The `-m` flag tells Python to run as a module, which handles imports correctly

**Directory Structure in Container:**
```
/app/
├── src/
│   ├── main.py          ← Entry point
│   └── (other modules)
├── shared/              ← Shared utilities
│   └── logging_config.py
└── requirements.txt
```

**Verification Command:**
```bash
docker logs homeiq-websocket --tail 20
# Should show: "Successfully connected to Home Assistant"
# Should NOT show: "ModuleNotFoundError: No module named 'src'"
```

---

### 2. Admin API Service

**File:** `services/admin-api/Dockerfile`

**CRITICAL CONFIGURATION:**

```dockerfile
# Set environment variables
ENV PYTHONPATH=/app:/app/src
ENV PATH=/home/appuser/.local/bin:$PATH

# ... later ...

# Run the application
CMD ["python", "src/simple_main.py"]
```

**⚠️ REQUIRED ENVIRONMENT VARIABLE:**
```dockerfile
ENV PYTHONPATH=/app:/app/src
```

**Why PYTHONPATH is required:**
- The service imports from `shared/` directory: `from shared.logging_config import ...`
- Without PYTHONPATH, Python cannot find the `shared` module
- PYTHONPATH tells Python where to look for modules

**Common Import Pattern:**
```python
# In src/simple_main.py
from shared.logging_config import (
    setup_logging,
    get_logger,
    log_request,
    log_response,
    RequestLogger
)
```

**Verification Command:**
```bash
docker logs homeiq-admin --tail 20
# Should show: "Started server process [1]"
# Should NOT show: "ModuleNotFoundError: No module named 'shared'"
```

---

### 3. Health Dashboard (Nginx)

**File:** `services/health-dashboard/nginx.conf`

**CRITICAL CONFIGURATION:**

```nginx
# Proxy API requests to admin-api service
location /api/ {
    proxy_pass http://admin-api:8004/api/v1/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection 'upgrade';
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_cache_bypass $http_upgrade;
    proxy_read_timeout 90;
}
```

**⚠️ WHY THIS IS CRITICAL:**
- Dashboard runs on port 3000 (nginx)
- Admin API runs on port 8004 (in Docker network as `admin-api:8004`)
- Dashboard frontend calls `/api/health` and `/api/stats`
- Nginx proxies `/api/*` to `http://admin-api:8004/api/v1/*`
- Without this, dashboard gets HTML error pages instead of JSON

**URL Mapping:**
```
Browser Request          → Nginx Proxy      → Admin API
────────────────────────────────────────────────────────
/api/health              → /api/v1/health   (admin-api:8004)
/api/stats?period=1h     → /api/v1/stats    (admin-api:8004)
```

**Verification:**
```bash
# From browser/dashboard perspective:
curl http://localhost:3000/api/health
# Should return JSON, not HTML

# Direct API check:
curl http://localhost:8003/api/v1/health
# Should also return JSON
```

---

## Service Dependencies

### Docker Compose Dependency Chain

```
┌─────────────────────────────────────────────────────────┐
│                      InfluxDB                           │
│                    (Port: 8086)                         │
└──────────────────────────┬──────────────────────────────┘
                           │
           ┌───────────────┴────────────────┐
           ↓                                ↓
┌──────────────────────┐         ┌──────────────────────┐
│ Enrichment Pipeline  │         │ WebSocket Ingestion  │
│    (Port: 8002)      │         │    (Port: 8001)      │
└──────────┬───────────┘         └──────────┬───────────┘
           │                                ↓
           │                     ┌──────────────────────┐
           │                     │     Admin API        │
           └────────────────────→│    (Port: 8004)      │
                                 └──────────┬───────────┘
                                            ↓
                                 ┌──────────────────────┐
                                 │  Health Dashboard    │
                                 │    (Port: 3000)      │
                                 └──────────────────────┘
```

**Startup Order:**
1. InfluxDB (must be healthy first)
2. Enrichment Pipeline (depends on InfluxDB)
3. WebSocket Ingestion (depends on InfluxDB and Enrichment)
4. Admin API (depends on WebSocket, Enrichment, InfluxDB)
5. Health Dashboard (depends on Admin API)

**Why Order Matters:**
- Each service checks dependencies during health checks
- If dependencies aren't ready, health checks fail
- Docker won't start dependent services until dependencies are healthy

---

## Common Pitfalls and How to Avoid Them

### ❌ PITFALL 1: Changing Dockerfile CMD without testing

**Symptom:**
```
ModuleNotFoundError: No module named 'X'
```

**Prevention:**
1. Never change `CMD` in Dockerfiles without understanding module structure
2. Always test with `docker compose build <service>` and `docker compose up -d <service>`
3. Check logs immediately: `docker logs <container-name> --tail 20`

**Recovery:**
```bash
# Revert to working configuration
git checkout -- services/*/Dockerfile
# Rebuild and restart
docker compose build
docker compose up -d
```

---

### ❌ PITFALL 2: Removing PYTHONPATH environment variable

**Symptom:**
```
ModuleNotFoundError: No module named 'shared'
```

**Prevention:**
1. The `shared/` directory contains common utilities used by all services
2. Services MUST have PYTHONPATH set to find shared modules
3. Check all services that import from `shared/`:
   - admin-api ✅ (requires PYTHONPATH)
   - websocket-ingestion ✅ (imports from shared)
   - enrichment-pipeline ✅ (imports from shared)

**Working Configuration:**
```dockerfile
ENV PYTHONPATH=/app:/app/src
```

---

### ❌ PITFALL 3: Removing Nginx API proxy configuration

**Symptom:**
- Dashboard shows "HTTP 500: Internal Server Error"
- Console shows: `SyntaxError: Unexpected token '<', "<!doctype "... is not valid JSON`
- API calls return HTML error pages instead of JSON

**Prevention:**
1. Dashboard MUST have nginx proxy to reach Admin API
2. Never remove the `location /api/` block from nginx.conf
3. The proxy maps dashboard's `/api/*` to admin-api's `/api/v1/*`

**Verification:**
```bash
# Test API through dashboard proxy
curl http://localhost:3000/api/health
# Should return JSON

# If broken, you'll get HTML error page
```

---

### ❌ PITFALL 4: Incorrect port mappings

**Current Port Mapping:**
```
Service                  Container Port  → Host Port
────────────────────────────────────────────────────
influxdb                 8086           → 8086
enrichment-pipeline      8002           → 8002
websocket-ingestion      8001           → 8001
admin-api                8004           → 8003  ⚠️ NOTE: Different!
health-dashboard         80             → 3000  ⚠️ NOTE: Container uses 80
```

**⚠️ IMPORTANT:**
- Admin API container runs on port 8004 internally
- But exposed as port 8003 on host: `0.0.0.0:8003->8004/tcp`
- Dashboard container runs nginx on port 80 internally
- But exposed as port 3000 on host: `0.0.0.0:3000->80/tcp`

**Inside Docker Network:**
```
admin-api:8004           ← Services communicate via container name
enrichment-pipeline:8002
websocket-ingestion:8001
influxdb:8086
```

**From Host Machine:**
```
localhost:8003           ← Use host port
localhost:8002
localhost:8001
localhost:8086
localhost:3000
```

---

## Health Check Configurations

### WebSocket Ingestion Health Check

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1
```

**What it checks:**
- Service responds on port 8001
- `/health` endpoint returns 200 OK
- Starts checking after 30 seconds (start-period)
- Checks every 30 seconds
- Fails after 3 retries

### Admin API Health Check

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8004/health || exit 1
```

**Note:** Uses internal port 8004, not host port 8003

---

## Rebuild and Deploy Procedure

### Safe Rebuild Process

```bash
# 1. Check current status
docker compose ps

# 2. Stop specific service
docker compose stop <service-name>

# 3. Rebuild service
docker compose build <service-name>

# 4. Start service
docker compose up -d <service-name>

# 5. Check logs immediately
docker logs homeiq-<service-name> --tail 50

# 6. Verify health
docker compose ps | grep <service-name>
# Should show "healthy" status
```

### Full System Rebuild

```bash
# 1. Stop all services
docker compose down

# 2. Rebuild all services
docker compose build

# 3. Start all services
docker compose up -d

# 4. Monitor startup
docker compose ps
watch -n 2 'docker compose ps'

# 5. Check logs for each service
docker logs homeiq-websocket --tail 20
docker logs homeiq-admin --tail 20
docker logs homeiq-dashboard --tail 20
```

---

## Verification Checklist

After any changes, verify ALL of the following:

### ✅ Service Health Status
```bash
docker compose ps
# All services should show "(healthy)"
```

### ✅ WebSocket Service
```bash
docker logs homeiq-websocket --tail 20
# Should show: "Successfully connected to Home Assistant"
# Should NOT show: ModuleNotFoundError
```

### ✅ Admin API Service
```bash
docker logs homeiq-admin --tail 20
# Should show: "Uvicorn running on http://0.0.0.0:8004"
# Should NOT show: ModuleNotFoundError

curl http://localhost:8003/api/v1/health
# Should return JSON with status
```

### ✅ Dashboard
```bash
# Check dashboard loads
curl http://localhost:3000
# Should return HTML

# Check API proxy works
curl http://localhost:3000/api/health
# Should return JSON, not HTML
```

### ✅ Browser Test
1. Open http://localhost:3000
2. Dashboard should load without errors
3. Check browser console (F12) - no errors
4. Should show system health metrics
5. Auto-refresh every 30 seconds

---

## Files That Must Not Be Broken

### Critical Files - DO NOT MODIFY WITHOUT TESTING

1. **`services/websocket-ingestion/Dockerfile`**
   - Critical line: `CMD ["python", "-m", "src.main"]`

2. **`services/admin-api/Dockerfile`**
   - Critical line: `ENV PYTHONPATH=/app:/app/src`

3. **`services/health-dashboard/nginx.conf`**
   - Critical block: `location /api/` proxy configuration

4. **`docker-compose.yml`**
   - Port mappings (8004→8003 for admin-api)
   - Dependency chains (depends_on with conditions)
   - Health check configurations

---

## Emergency Rollback Procedure

If something breaks:

```bash
# 1. Immediately revert all changes
git status
git diff
git checkout -- .

# 2. Rebuild affected services
docker compose build

# 3. Restart services
docker compose down
docker compose up -d

# 4. Verify everything works
docker compose ps
docker logs homeiq-websocket --tail 20
docker logs homeiq-admin --tail 20

# 5. Test dashboard
curl http://localhost:3000/api/health
```

---

## Testing Changes Before Committing

### Required Tests Before Any Dockerfile Change

```bash
# 1. Build the specific service
docker compose build <service-name>

# 2. Stop and remove old container
docker compose stop <service-name>
docker compose rm -f <service-name>

# 3. Start new container
docker compose up -d <service-name>

# 4. Wait for startup
sleep 10

# 5. Check health
docker compose ps | grep <service-name>

# 6. Check logs for errors
docker logs homeiq-<service-name> --tail 50 | grep -i error

# 7. Test API endpoint
curl http://localhost:<port>/health

# 8. If ANY of the above fail, REVERT IMMEDIATELY
```

---

## Summary of Working Configuration

### ✅ What Works (DO NOT CHANGE)

1. **WebSocket Service:**
   - CMD: `python -m src.main`
   - Working directory: `/app`
   - Entry point: `/app/src/main.py`

2. **Admin API:**
   - PYTHONPATH: `/app:/app/src`
   - CMD: `python src/simple_main.py`
   - Imports: `from shared.logging_config import ...`

3. **Dashboard:**
   - Nginx proxy: `/api/` → `http://admin-api:8004/api/v1/`
   - Port mapping: `80` (container) → `3000` (host)

4. **Port Mappings:**
   - InfluxDB: 8086→8086
   - Enrichment: 8002→8002
   - WebSocket: 8001→8001
   - Admin API: 8004→8003 ⚠️
   - Dashboard: 80→3000 ⚠️

### 🔴 What Breaks It

1. Changing `CMD ["python", "-m", "src.main"]` to anything else
2. Removing `ENV PYTHONPATH=/app:/app/src`
3. Removing nginx API proxy configuration
4. Changing port mappings
5. Removing dependency chains in docker-compose.yml

---

## Contact and Support

If you need to modify Docker configurations:

1. **Read this document first**
2. **Understand why the current config works**
3. **Test changes in isolation**
4. **Keep backup of working state**
5. **Document any changes made**

**Remember:** If it's working, don't "fix" it!

---

**Document Version:** 1.0  
**Last Verified Working:** October 10, 2025  
**Status:** ✅ All services healthy and operational

