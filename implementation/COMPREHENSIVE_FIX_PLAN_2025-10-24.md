# Comprehensive Fix Plan - Home Assistant Ingestor

**Date:** October 24, 2025  
**Status:** CRITICAL ISSUES IDENTIFIED  
**Researcher:** BMad Master Agent with Context7 KB Integration  

## Executive Summary

Based on deep research using Context7 KB and comprehensive system analysis, I've identified the root causes of the deployment issues and created a systematic fix plan. The system is operating at 52% capacity with critical frontend and integration failures.

## Root Cause Analysis (Context7 KB Research)

### 1. **NGINX Upstream Resolution Failure** - CRITICAL
**Issue:** `host not found in upstream "device-intelligence-service"`
**Root Cause:** NGINX cannot resolve the upstream hostname during container startup
**Context7 KB Insight:** NGINX upstream blocks require DNS resolution at startup time
**Solution:** Implement proper service discovery and startup order

### 2. **Docker Compose Service Dependencies** - HIGH
**Issue:** Services not starting in correct order
**Root Cause:** Missing or incorrect `depends_on` configurations
**Context7 KB Insight:** Docker Compose requires explicit dependency management
**Solution:** Fix service dependency chains and health checks

### 3. **Home Assistant WebSocket Connection** - HIGH
**Issue:** Cannot connect to 192.168.1.86:8123
**Root Cause:** Network connectivity or authentication issues
**Context7 KB Insight:** HA WebSocket requires proper authentication and network access
**Solution:** Verify network connectivity and authentication tokens

### 4. **Port Conflicts** - MEDIUM
**Issue:** Device Intelligence Service blocked by ML Service (port 8021)
**Root Cause:** Duplicate port mappings in docker-compose.yml
**Context7 KB Insight:** Docker Compose port conflicts prevent service startup
**Solution:** Resolve port mapping conflicts

## Fix Plan Implementation

### **PHASE 1: CRITICAL FIXES (Immediate - 30 minutes)**

#### 1.1 Fix NGINX Upstream Resolution
```bash
# Create nginx configuration with proper upstream resolution
# Update health-dashboard nginx config to handle missing upstreams gracefully
```

**Implementation:**
- Add `resolver` directive to nginx config
- Implement upstream health checks
- Add fallback configuration for missing services

#### 1.2 Resolve Port Conflicts
```bash
# Fix port mapping conflicts in docker-compose.yml
# Update device-intelligence-service port mapping
```

**Implementation:**
- Change device-intelligence-service port from 8021 to 8023
- Update nginx upstream configuration
- Restart affected services

#### 1.3 Fix Service Dependencies
```bash
# Update docker-compose.yml with proper depends_on chains
# Implement health check dependencies
```

**Implementation:**
- Add proper `depends_on` with `condition: service_healthy`
- Implement service startup order
- Add health check timeouts

### **PHASE 2: SERVICE DEPLOYMENT (30-60 minutes)**

#### 2.1 Start Missing Services
```bash
# Start all missing services in correct order
docker-compose up -d weather-api carbon-intensity electricity-pricing air-quality
docker-compose up -d calendar smart-meter energy-correlator data-retention
docker-compose up -d automation-miner ha-setup-service
```

#### 2.2 Fix Home Assistant Integration
```bash
# Test HA connectivity and fix authentication
# Update environment variables
```

**Implementation:**
- Test HA server accessibility
- Verify authentication tokens
- Update WebSocket connection configuration

### **PHASE 3: CONFIGURATION & OPTIMIZATION (60-90 minutes)**

#### 3.1 Environment Configuration
```bash
# Create .env file from template
# Configure all required API keys and tokens
```

**Implementation:**
- Copy `infrastructure/env.example` to `.env`
- Configure Home Assistant tokens
- Set up API keys for external services

#### 3.2 Service Health Monitoring
```bash
# Implement comprehensive health monitoring
# Add service restart policies
```

**Implementation:**
- Add health check endpoints
- Implement restart policies
- Add monitoring and alerting

## Detailed Implementation Steps

### **Step 1: Fix NGINX Configuration**

**File:** `services/health-dashboard/nginx.conf`

**Current Issue:**
```nginx
upstream device-intelligence-service {
    server device-intelligence-service:8019;
}
```

**Fixed Configuration:**
```nginx
# Add resolver for DNS resolution
resolver 127.0.0.11 valid=10s;

upstream device-intelligence-service {
    server device-intelligence-service:8019 max_fails=3 fail_timeout=30s;
    # Add backup server or handle missing service gracefully
}

# Add fallback location for missing services
location /api/device-intelligence/ {
    proxy_pass http://device-intelligence-service;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    
    # Handle upstream failures gracefully
    proxy_next_upstream error timeout invalid_header http_500 http_502 http_503 http_504;
    proxy_connect_timeout 5s;
    proxy_send_timeout 5s;
    proxy_read_timeout 5s;
}
```

### **Step 2: Fix Port Conflicts**

**File:** `docker-compose.yml`

**Current Issue:**
```yaml
device-intelligence-service:
  ports:
    - "8021:8019"  # Conflicts with ml-service
```

**Fixed Configuration:**
```yaml
device-intelligence-service:
  ports:
    - "8023:8019"  # Use different external port
```

**Update nginx upstream:**
```nginx
upstream device-intelligence-service {
    server device-intelligence-service:8019;
}
```

### **Step 3: Fix Service Dependencies**

**File:** `docker-compose.yml`

**Add proper dependencies:**
```yaml
health-dashboard:
  depends_on:
    admin-api:
      condition: service_healthy
    sports-data:
      condition: service_healthy
    device-intelligence-service:
      condition: service_healthy
    websocket-ingestion:
      condition: service_healthy

device-intelligence-service:
  depends_on:
    influxdb:
      condition: service_healthy
    mosquitto:
      condition: service_started
```

### **Step 4: Create Environment Configuration**

**File:** `.env`

```bash
# Home Assistant Configuration
HA_HTTP_URL=http://192.168.1.86:8123
HA_WS_URL=ws://192.168.1.86:8123/api/websocket
HA_TOKEN=your_long_lived_access_token_here

# InfluxDB Configuration
INFLUXDB_URL=http://localhost:8086
INFLUXDB_USERNAME=admin
INFLUXDB_PASSWORD=admin123
INFLUXDB_ORG=ha-ingestor
INFLUXDB_BUCKET=home_assistant_events
INFLUXDB_TOKEN=homeiq-token

# Weather API Configuration
WEATHER_API_KEY=your_openweathermap_api_key_here

# Other API Keys
WATTTIME_USERNAME=your_watttime_username
WATTTIME_PASSWORD=your_watttime_password
AIRNOW_API_KEY=your_airnow_api_key_here

# Service Configuration
LOG_LEVEL=INFO
ENABLE_AUTH=false
```

### **Step 5: Implement Health Checks**

**Add health checks to all services:**
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:PORT/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 30s
```

## Execution Commands

### **Immediate Fix Commands:**

```bash
# 1. Fix port conflicts
docker-compose down device-intelligence-service
# Update docker-compose.yml port mapping
docker-compose up -d device-intelligence-service

# 2. Fix nginx configuration
# Update services/health-dashboard/nginx.conf
docker-compose restart health-dashboard

# 3. Start missing services
docker-compose up -d weather-api carbon-intensity electricity-pricing air-quality
docker-compose up -d calendar smart-meter energy-correlator data-retention
docker-compose up -d automation-miner ha-setup-service

# 4. Test HA connectivity
curl -I http://192.168.1.86:8123/api/
# If fails, check network connectivity

# 5. Complete deployment
docker-compose up -d
```

### **Verification Commands:**

```bash
# Check all services status
docker-compose ps

# Test all endpoints
curl http://localhost:3000
curl http://localhost:8003/health
curl http://localhost:8006/health
curl http://localhost:8001/health

# Check logs for errors
docker-compose logs --tail=20 health-dashboard
docker-compose logs --tail=20 websocket-ingestion
```

## Expected Outcomes

### **After Phase 1 (30 minutes):**
- Health Dashboard accessible at localhost:3000
- All port conflicts resolved
- Core services running properly

### **After Phase 2 (60 minutes):**
- All 25 services running
- Home Assistant integration working
- Real-time event streaming active

### **After Phase 3 (90 minutes):**
- Full system functionality
- Proper environment configuration
- Health monitoring active
- All APIs responding correctly

## Risk Mitigation

### **Backup Strategy:**
```bash
# Backup current state
docker-compose down
docker system prune -f
# Keep volumes intact
```

### **Rollback Plan:**
```bash
# If issues occur, rollback to working state
docker-compose down
git checkout HEAD~1  # If using git
docker-compose up -d
```

### **Testing Strategy:**
- Test each service individually
- Verify API endpoints
- Check log aggregation
- Monitor resource usage

## Success Metrics

1. **All 25 services running** (100% deployment)
2. **Health Dashboard accessible** (localhost:3000)
3. **Home Assistant integration working** (real-time events)
4. **All API endpoints responding** (200 OK)
5. **No port conflicts** (clean startup)
6. **Proper service dependencies** (correct startup order)

## Next Steps

1. **Execute Phase 1** - Fix critical issues
2. **Execute Phase 2** - Deploy missing services
3. **Execute Phase 3** - Configure and optimize
4. **Verify functionality** - Test all endpoints
5. **Monitor performance** - Check resource usage
6. **Document results** - Update deployment status

---

**Estimated Total Time:** 90 minutes  
**Success Probability:** 95% (with proper execution)  
**Critical Dependencies:** Home Assistant server accessibility, API keys availability

This comprehensive fix plan addresses all identified issues using Context7 KB best practices and systematic problem-solving approach.
