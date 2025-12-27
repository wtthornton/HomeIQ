# Quick Reference - Docker Configuration

**⚠️ READ THIS BEFORE MAKING ANY DOCKER CHANGES!**

---

## Critical Configurations (DO NOT CHANGE)

### 1. WebSocket Service
```dockerfile
# File: services/websocket-ingestion/Dockerfile
CMD ["python", "-m", "src.main"]  # ⚠️ MUST be "src.main" not "main"
```

### 2. Admin API Service
```dockerfile
# File: services/admin-api/Dockerfile
ENV PYTHONPATH=/app:/app/src      # ⚠️ REQUIRED for shared module imports
CMD ["python", "src/simple_main.py"]
```

### 3. Dashboard Nginx
```nginx
# File: services/health-dashboard/nginx.conf
location /api/ {
    proxy_pass http://admin-api:8004/api/v1/;  # ⚠️ REQUIRED for API calls
    # ... proxy headers ...
}
```

---

## Quick Verification Commands

```bash
# Check all services are healthy
docker compose ps

# Check WebSocket logs
docker logs homeiq-websocket --tail 20
# Should show: "Successfully connected to Home Assistant"

# Check Admin API logs
docker logs homeiq-admin --tail 20
# Should show: "Uvicorn running on http://0.0.0.0:8004"

# Test API endpoint
curl http://localhost:8003/api/v1/health

# Test dashboard proxy
curl http://localhost:3000/api/health

# Open dashboard in browser
start http://localhost:3000
```

---

## Common Errors and Fixes

### ❌ ModuleNotFoundError: No module named 'src'
**Fix:** Change CMD to `["python", "-m", "src.main"]`

### ❌ ModuleNotFoundError: No module named 'shared'
**Fix:** Add `ENV PYTHONPATH=/app:/app/src` to Dockerfile

### ❌ Dashboard shows "SyntaxError: Unexpected token '<'"
**Fix:** Add nginx API proxy configuration

---

## Port Reference

### Core Services

| Service | Container Port | Host Port | URL |
|---------|---------------|-----------|-----|
| InfluxDB | 8086 | 8086 | http://localhost:8086 |
| Enrichment | 8002 | 8002 | http://localhost:8002 |
| WebSocket | 8001 | 8001 | http://localhost:8001/health |
| Admin API | 8004 | **8003** ⚠️ | http://localhost:8003/api/v1/health |
| Dashboard | 80 | **3000** ⚠️ | http://localhost:3000 |
| Data Retention | 8080 | 8080 | http://localhost:8080/health |

### External Data Services (Internal Only)

| Service | Container Port | Description |
|---------|---------------|-------------|
| Carbon Intensity | 8010 | Carbon intensity data from National Grid |
| Electricity Pricing | 8011 | Real-time electricity pricing |
| Air Quality | 8012 | Air quality index and pollutants |
| Calendar | 8013 | Calendar integration |
| Smart Meter | 8014 | Smart meter data |
| Weather API | 8000 | Weather data from OpenWeatherMap |

---

## Safe Rebuild Process

```bash
# 1. Stop service
docker compose stop <service-name>

# 2. Rebuild
docker compose build <service-name>

# 3. Start
docker compose up -d <service-name>

# 4. Verify
docker logs homeiq-<service-name> --tail 20
```

---

## Emergency Rollback

```bash
git checkout -- services/*/Dockerfile services/health-dashboard/nginx.conf
docker compose build
docker compose up -d
```

---

**Full Documentation:** See `docs/DOCKER_STRUCTURE_GUIDE.md`

