# 🚀 Home Assistant Data Ingestor & API Hub - Deployment Guide

## 📋 **System Overview**

### **What You're Deploying**

**Primary System**: API Data Hub for Home Automation
- Provides RESTful APIs for Home Assistant automations
- Event-driven webhooks for instant notifications  
- Time-series data storage (InfluxDB) for analytics
- Multi-source data integration (HA events, sports, weather, energy, etc.)

**Secondary System**: Admin Monitoring Dashboard
- Web interface for system health monitoring
- Configuration management
- Service control and deployment
- API usage tracking

**Deployment Model**: Single-home, self-hosted
- One deployment per home
- Local network or VPN access
- Not designed for public internet

### **Prerequisites**
- Docker 20.10+ and Docker Compose 2.0+
- 4GB RAM minimum (8GB recommended)
- 20GB storage minimum (50GB recommended)
- Stable internet connection
- Home Assistant instance with long-lived access token
- **Use Case**: Home automation API hub (not user-facing app)

---

## 🚀 **Recommended: Interactive Deployment Wizard**

### **Step 1: Run the Deployment Wizard**

The easiest and fastest way to deploy:

```bash
# Clone repository
git clone <repository-url>
cd homeiq

# Run interactive deployment wizard
./scripts/deploy-wizard.sh
```

The wizard will guide you through:
1. **Deployment Option Selection**
   - Same machine as Home Assistant (localhost)
   - Separate machine on local network
   - Remote access via Nabu Casa
   - Custom configuration

2. **Home Assistant Configuration**
   - URL configuration with smart defaults
   - Access token setup
   - Optional connection testing

3. **System Resource Detection**
   - Automatic RAM, CPU, disk space checks
   - Docker and Docker Compose verification
   - Warning system for insufficient resources

4. **Secure Configuration Generation**
   - Automatic `.env` file creation
   - Secure random password generation
   - Credentials file for easy reference

### **Step 2: Validate Your Setup (Recommended)**

Before starting services, validate your configuration:

```bash
./scripts/validate-ha-connection.sh
```

This will test:
- ✅ TCP/IP connectivity
- ✅ HTTP/HTTPS endpoint
- ✅ WebSocket connection
- ✅ Authentication
- ✅ API access

### **Step 3: Deploy**

```bash
# Start all services
docker-compose up -d

# Verify deployment
docker-compose ps

# View logs
docker-compose logs -f
```

### **Step 4: Access Dashboard**

```bash
# Open in browser
open http://localhost:3000
```

**📖 Detailed Guide:** See [`docs/DEPLOYMENT_WIZARD_GUIDE.md`](DEPLOYMENT_WIZARD_GUIDE.md) for complete wizard documentation.

---

## 📝 **Alternative: Manual Deployment**

If you prefer manual configuration:

### **Manual Deployment Commands**
```bash
# Clone repository
git clone <repository-url>
cd homeiq

# Copy and configure environment
cp infrastructure/env.example .env
nano .env  # Edit with your configuration

# Start the system (development)
docker-compose -f docker-compose.dev.yml up -d

# Or start production system
docker-compose -f docker-compose.prod.yml --env-file infrastructure/env.production up -d

# Verify deployment
docker-compose ps
docker-compose logs -f
```

### **🚀 Optimized Deployment (Recommended)**
The system now uses optimized Alpine-based Docker images with 71% size reduction:

```bash
# Build and start optimized system
docker-compose -f docker-compose.prod.yml build
docker-compose -f docker-compose.prod.yml up -d

# Validate optimized images
./scripts/validate-optimized-images.sh  # Linux/macOS
.\scripts\validate-optimized-images.ps1  # Windows
```

## ⚠️ **Critical: API Configuration**

### **Health Dashboard API Configuration**

The health dashboard requires proper configuration of two API clients:

1. **Admin API** (port 8003) - System monitoring and container management
2. **Data API** (port 8006) - Devices, entities, events, sports data

**Required Environment Variables:**
```yaml
health-dashboard:
  environment:
    - VITE_API_BASE_URL=http://localhost:8003  # Admin API
    - VITE_DATA_API_URL=http://localhost:8006   # Data API (CRITICAL)
    - VITE_WS_URL=ws://localhost:8001/ws
```

**If dashboard shows "0 Devices":**
1. Check `VITE_DATA_API_URL` is set to `http://localhost:8006`
2. Verify data-api is running: `docker ps | grep data-api`
3. Test API: `curl http://localhost:8006/api/devices?limit=5`
4. Rebuild dashboard: `docker-compose up -d --build health-dashboard`

See [`HEALTH_DASHBOARD_API_CONFIGURATION.md`](HEALTH_DASHBOARD_API_CONFIGURATION.md) for detailed troubleshooting.

---

## 🏈 **Epic 12: Sports Data Configuration** (NEW)

### **Sports Data Service with InfluxDB Persistence**

Epic 12 adds sports data persistence, historical queries, and Home Assistant automation webhooks.

**Environment Variables (`infrastructure/env.sports.template`):**

```bash
# InfluxDB Persistence (Story 12.1)
INFLUXDB_ENABLED=true                          # Enable/disable persistence
INFLUXDB_URL=http://influxdb:8086              # InfluxDB server
INFLUXDB_TOKEN=your-influxdb-token             # Auth token
INFLUXDB_DATABASE=sports_data                  # Database name
INFLUXDB_RETENTION_DAYS=730                    # 2 years retention

# Circuit Breaker (Story 12.1)
CIRCUIT_BREAKER_FAILURE_THRESHOLD=3            # Failures before circuit opens
CIRCUIT_BREAKER_TIMEOUT_SECONDS=60             # Recovery timeout

# Event Detection (Story 12.3)
# Event detector runs automatically (15s interval)
# No additional configuration needed
```

**Quick Setup:**

```bash
# 1. Copy sports environment template
cp infrastructure/env.sports.template .env.sports

# 2. Edit .env.sports and set your InfluxDB token
# INFLUXDB_TOKEN=your-actual-token-here

# 3. Start services
docker-compose up -d sports-data influxdb

# 4. Verify deployment
curl http://localhost:8005/health

# 5. Register webhook (optional - for HA automations)
curl -X POST "http://localhost:8005/api/v1/webhooks/register" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "http://homeassistant.local:8123/api/webhook/game_events",
    "events": ["game_started", "score_changed", "game_ended"],
    "secret": "your-secure-secret-min-16-chars",
    "team": "ne",
    "sport": "nfl"
  }'
```

**Features:**
- ✅ InfluxDB persistence (2-year retention)
- ✅ Historical query endpoints
- ✅ HA automation endpoints (<50ms)
- ✅ Event-driven webhooks (HMAC-signed)
- ✅ Background event detection (15s interval)

**Home Assistant Integration:**
See `services/sports-data/README.md` for complete automation examples.

---

## 🔧 **Configuration**

### **Required Environment Variables**
```bash
# Home Assistant Configuration
HA_URL=ws://your-ha-instance:8123/api/websocket
HA_ACCESS_TOKEN=your_long_lived_access_token

# Network Resilience Configuration (NEW - Optional)
# Service automatically recovers from network outages
WEBSOCKET_MAX_RETRIES=-1              # -1 = infinite retry (recommended)
WEBSOCKET_MAX_RETRY_DELAY=300         # Max 5 minutes between retries

# Weather API Configuration
WEATHER_API_KEY=your_openweathermap_api_key
WEATHER_LOCATION=your_city,country_code

# External Data Services (Optional - Enable as needed)
CARBON_INTENSITY_API_KEY=your_carbon_intensity_api_key
CARBON_INTENSITY_REGION=GB  # UK region code
ELECTRICITY_PRICING_PROVIDER=octopus  # octopus, agile, etc.
ELECTRICITY_PRICING_API_KEY=your_pricing_api_key
AIR_QUALITY_API_KEY=your_air_quality_api_key
# Calendar Service (Home Assistant Integration)
CALENDAR_ENTITIES=calendar.primary  # Comma-separated HA calendar entity IDs
CALENDAR_FETCH_INTERVAL=900  # Fetch interval in seconds (default: 15 min)
SMART_METER_PROTOCOL=smets2  # smets2, p1, etc.
SMART_METER_CONNECTION=your_meter_connection

# InfluxDB Configuration
INFLUXDB_URL=http://influxdb:8086
INFLUXDB_TOKEN=your_influxdb_token
INFLUXDB_ORG=your_organization
INFLUXDB_BUCKET=home_assistant

# API Configuration
API_KEY=your_secure_api_key
ENABLE_AUTH=true

# Data Retention Configuration (Enhanced)
CLEANUP_INTERVAL_HOURS=24
MONITORING_INTERVAL_MINUTES=5
COMPRESSION_INTERVAL_HOURS=24
BACKUP_INTERVAL_HOURS=24
BACKUP_DIR=/backups

# Tiered Storage Configuration
ENABLE_TIERED_RETENTION=true
HOT_RETENTION_DAYS=7
WARM_RETENTION_DAYS=30
COLD_RETENTION_DAYS=365

# S3 Archival Configuration (Optional)
ENABLE_S3_ARCHIVAL=false
S3_BUCKET=your-s3-bucket
S3_ACCESS_KEY=your-s3-access-key
S3_SECRET_KEY=your-s3-secret-key
S3_REGION=us-east-1
```

## 🌐 **Access Points**

### **Development Environment**
- **Health Dashboard**: http://localhost:3000
- **Admin API**: http://localhost:8000
- **Data Retention API**: http://localhost:8080
- **WebSocket Ingestion**: http://localhost:8001
- **Enrichment Pipeline**: http://localhost:8002
- **InfluxDB**: http://localhost:8086

### **Production Environment**
- **Health Dashboard**: http://localhost:3000
- **Admin API**: http://localhost:8003
- **Data Retention API**: http://localhost:8080
- **WebSocket Ingestion**: http://localhost:8001
- **Enrichment Pipeline**: http://localhost:8002
- **InfluxDB**: http://localhost:8086
- **API Documentation**: http://localhost:8003/docs
- **Health Checks**: http://localhost:8003/api/v1/health

## 📊 **System Architecture**

### **Core Services**
- **websocket-ingestion** - Home Assistant event capture (Alpine-based, ~60MB)
- **enrichment-pipeline** - Multi-source data enrichment and validation (Alpine-based, ~70MB)
- **data-retention** - Enhanced data lifecycle, tiered retention, S3 archival (Alpine-based, ~65MB)
- **admin-api** - System administration API (Alpine-based, ~50MB)
- **health-dashboard** - Web-based administration interface (Alpine-based, ~80MB)
- **influxdb** - Time-series database (Official image)

### **External Data Services**
- **carbon-intensity-service** - Carbon intensity data integration (Alpine-based, ~40MB)
- **electricity-pricing-service** - Real-time electricity pricing (Alpine-based, ~40MB)
- **air-quality-service** - Air quality monitoring (Alpine-based, ~40MB)
- **calendar-service** - Home Assistant calendar integration for occupancy prediction (Alpine-based, ~40MB, 28MB smaller!)
- **smart-meter-service** - Smart meter data integration (Alpine-based, ~45MB)
- **weather-api** - Weather data integration (Alpine-based, ~40MB)

### **Docker Optimizations**
- **Multi-stage builds** for all services
- **Alpine Linux base images** (71% size reduction)
- **Non-root users** for security
- **Production requirements** separated from development
- **Health checks** configured for all services

### **Networking**
- **homeiq-network** - Internal service communication
- **Port 3000** - Health dashboard frontend
- **Port 8000/8003** - Admin API (dev/prod)
- **Port 8080** - Data retention API
- **Port 8086** - InfluxDB

## 🔍 **Monitoring & Maintenance**

### **Health Monitoring**
```bash
# Check service health
curl http://localhost:8080/api/v1/health

# View service logs
docker-compose logs -f websocket-ingestion
docker-compose logs -f enrichment-pipeline
docker-compose logs -f admin-api
```

### **System Management**
```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Restart specific service
docker-compose restart websocket-ingestion

# View resource usage
docker stats
```

## 🛠️ **Troubleshooting**

### **Common Issues**
1. **WebSocket Connection Failed** - Check HA_URL and HA_ACCESS_TOKEN
2. **Weather API Errors** - Verify WEATHER_API_KEY and location
3. **InfluxDB Connection Issues** - Check database configuration
4. **High Memory Usage** - Monitor resource limits and adjust if needed

### **Log Analysis**
```bash
# View all logs
docker-compose logs

# Filter by service
docker-compose logs websocket-ingestion | grep ERROR

# Follow logs in real-time
docker-compose logs -f --tail=100
```

## 📈 **Performance Optimization**

### **Resource Limits**
- **CPU**: 2 cores minimum, 4 cores recommended
- **Memory**: 4GB minimum, 8GB recommended
- **Storage**: 20GB minimum, 50GB recommended

### **Scaling Considerations**
- Monitor InfluxDB performance for high-volume data
- Adjust log retention policies based on storage capacity
- Configure alert thresholds based on system capacity

## 🔒 **Security**

### **Authentication**
- API key authentication for admin operations
- Token-based Home Assistant authentication
- Secure environment variable management

### **Network Security**
- Internal service communication only
- No external ports exposed except admin interface
- CORS configuration for web interface

## 📚 **Documentation**

- **User Guide**: Complete user manual
- **API Documentation**: OpenAPI/Swagger specs
- **CLI Reference**: Command-line tools
- **Troubleshooting**: Common issues and solutions

---

**🎉 Your Home Assistant Ingestor is now deployed and ready for production use!**
