# 🚀 Alpha Deployment - Quick Start Guide

**Status:** ✅ Ready for Alpha Testing  
**Date:** November 16, 2025

---

## ⚡ Quick Deploy (5 Minutes)

### Step 1: Configure Environment

```bash
# Copy environment template
cp infrastructure/env.example infrastructure/.env

# Edit with your Home Assistant details
# Windows: notepad infrastructure\.env
# Linux/Mac: nano infrastructure/.env
```

**Minimum Required Settings:**
```bash
# Home Assistant (REQUIRED)
HOME_ASSISTANT_URL=http://192.168.1.86:8123  # Your HA IP
HOME_ASSISTANT_TOKEN=your_long_lived_access_token_here

# InfluxDB (uses defaults if not set)
INFLUXDB_URL=http://localhost:8086
INFLUXDB_USERNAME=admin
INFLUXDB_PASSWORD=admin123
INFLUXDB_ORG=ha-ingestor
INFLUXDB_BUCKET=home_assistant_events
INFLUXDB_TOKEN=homeiq-token
```

**Optional (can add later):**
- Weather API key
- WattTime credentials
- Other external services

---

### Step 2: Start Services

```bash
# Start all services
docker compose up -d

# Watch logs (optional)
docker compose logs -f
```

**Expected:** 24-25 containers starting (24 services + InfluxDB)

---

### Step 3: Verify Deployment

```bash
# Check service status
docker compose ps

# Or use verification script (Linux/Mac)
./scripts/verify-deployment.sh

# Or PowerShell (Windows)
.\scripts\verify-deployment.ps1
```

**Expected Output:**
- All services showing "healthy" or "running"
- Health Dashboard: http://localhost:3000
- AI Automation UI: http://localhost:3001

---

## 🎯 Quick Verification Checklist

### ✅ Service Health
```bash
# Check all containers are running
docker ps --format "table {{.Names}}\t{{.Status}}"

# Should see ~25 containers, all "Up" or "healthy"
```

### ✅ Web Interfaces
- [ ] **Health Dashboard**: http://localhost:3000
  - Should show system overview
  - Services tab should list all services
  
- [ ] **AI Automation UI**: http://localhost:3001
  - Should load dashboard
  - "Ask AI" tab should be accessible

### ✅ API Endpoints
```bash
# Admin API
curl http://localhost:8003/health
# Expected: {"status":"healthy"}

# Data API
curl http://localhost:8006/health
# Expected: {"status":"healthy"}

# WebSocket Ingestion
curl http://localhost:8001/health
# Expected: {"status":"healthy"}
```

### ✅ Home Assistant Connection
```bash
# Check WebSocket connection (should see events flowing)
docker compose logs websocket-ingestion | grep -i "connected\|event"
```

---

## 🔧 Common Alpha Setup Issues

### Issue: "0 Devices" in Dashboard
**Fix:**
```bash
# Check Data API is running
docker ps | grep data-api

# Rebuild dashboard with correct API URL
docker compose up -d --build health-dashboard
```

### Issue: WebSocket Connection Failed
**Fix:**
1. Verify `HOME_ASSISTANT_URL` in `.env` is correct
2. Verify `HOME_ASSISTANT_TOKEN` is valid
3. Check Home Assistant is accessible:
   ```bash
   curl http://192.168.1.86:8123/api/  # Replace with your HA IP
   ```

### Issue: Services Not Starting
**Fix:**
```bash
# Check logs for specific service
docker compose logs [service-name]

# Common issues:
# - Port conflicts (check if ports 3000, 3001, 8001, etc. are in use)
# - Missing environment variables
# - Docker resource limits
```

---

## 📊 Alpha Testing Focus Areas

### Core Functionality
- [ ] Home Assistant event ingestion working
- [ ] Health Dashboard displays data
- [ ] AI Automation UI loads and functions
- [ ] Data API returns device/entity data

### AI Features (Alpha)
- [ ] "Ask AI" tab creates automations
- [ ] Pattern detection working
- [ ] Device validation functioning

### Data Flow
- [ ] Events flowing from HA → InfluxDB
- [ ] Devices/entities queryable via Data API
- [ ] Historical data accessible

---

## 🛑 Stopping Services

```bash
# Stop all services
docker compose down

# Stop and remove volumes (clean slate)
docker compose down -v
```

---

## 📝 Alpha Testing Notes

### Known Limitations (Acceptable for Alpha)
- ⚠️ No automated security tests (AI Code Executor)
- ⚠️ No automated regression tests
- ⚠️ Manual testing only
- ⚠️ Some test coverage gaps

### What to Test
1. **Basic Functionality**: All services start and stay healthy
2. **Home Assistant Integration**: Events flowing, devices visible
3. **UI Functionality**: Dashboards load, basic interactions work
4. **AI Features**: Automation creation, pattern detection
5. **Data Persistence**: Data survives service restarts

### What to Report
- Service crashes or restarts
- UI errors or broken features
- Data not appearing
- Performance issues
- Any unexpected behavior

---

## 🚀 Next Steps After Alpha

Once alpha testing is complete:
1. **Security Tests**: Implement Issue #5 (AI Code Executor security)
2. **Smoke Tests**: Add basic automated tests
3. **Integration Tests**: Add end-to-end test coverage
4. **CI/CD**: Set up automated deployment pipeline

---

## 📚 Additional Resources

- **Full Deployment Guide**: [docs/DEPLOYMENT_GUIDE.md](../docs/DEPLOYMENT_GUIDE.md)
- **Troubleshooting**: [docs/TROUBLESHOOTING_GUIDE.md](../docs/TROUBLESHOOTING_GUIDE.md)
- **Architecture**: [docs/architecture/](../docs/architecture/)
- **Deployment Status**: [implementation/DEPLOYMENT_STATUS.md](DEPLOYMENT_STATUS.md)

---

## ✅ Alpha Deployment Checklist

- [ ] Environment file configured (`.env`)
- [ ] Home Assistant URL and token set
- [ ] Docker and Docker Compose installed
- [ ] Services started (`docker compose up -d`)
- [ ] All services healthy (`docker compose ps`)
- [ ] Health Dashboard accessible (http://localhost:3000)
- [ ] AI Automation UI accessible (http://localhost:3001)
- [ ] Home Assistant connection verified
- [ ] Events flowing to InfluxDB
- [ ] Ready for alpha testing! 🎉

---

**Happy Testing!** 🚀

If you encounter issues, check the logs first:
```bash
docker compose logs [service-name]
```

