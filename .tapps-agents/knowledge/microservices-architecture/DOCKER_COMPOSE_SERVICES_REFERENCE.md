# Docker Compose Services Reference

## 🎯 **Overview**

This document provides a comprehensive reference for all Docker Compose services in the HA Ingestor system, including their configurations, dependencies, and troubleshooting information.

---

## 🏗️ **Service Architecture**

```
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│   Health Dashboard  │    │     Admin API       │    │  WebSocket Ingestion│
│   (Port 3000)       │◄──►│   (Port 8003)       │◄──►│   (Port 8001)       │
│   nginx + React     │    │   FastAPI Gateway   │    │   Home Assistant    │
└─────────────────────┘    └─────────────────────┘    └─────────────────────┘
          │                           │                           │
          │                           ▼                           ▼
          │                ┌─────────────────────┐    ┌─────────────────────┐
          │                │  Enrichment Pipeline│◄───│  External Data Svcs │
          │                │   (Port 8002)       │    │  - Weather (8000)   │
          │                │   Multi-Source Data │    │  - Carbon (8010)    │
          │                └─────────────────────┘    │  - Pricing (8011)   │
          │                           │                │  - Air Quality(8012)│
          │                           ▼                │  - Calendar (8013)  │
          │                ┌─────────────────────┐    │  - Smart Meter(8014)│
          │                │   Data Retention    │    └─────────────────────┘
          │                │   (Port 8080)       │
          │                │   Tiered Storage +  │
          │                │   S3 Archival       │
          │                └─────────────────────┘
          │                           │
          │                           ▼
          │                ┌─────────────────────┐
          │                │      InfluxDB       │
          │                │   (Port 8086)       │
          │                │   Time Series DB    │
          │                └─────────────────────┘
          │                           │
          └───────────────────────────┘
```

---

## 🚀 **Service Details**

### Health Dashboard (`health-dashboard`)

**Purpose:** React-based frontend dashboard with nginx proxy

**Configuration:**
```yaml
health-dashboard:
  build:
    context: ./services/health-dashboard
    dockerfile: Dockerfile
  container_name: homeiq-dashboard
  restart: unless-stopped
  ports:
    - "3000:80"
  environment:
    - VITE_API_BASE_URL=http://localhost:8003/api/v1
    - VITE_WS_URL=ws://localhost:8001/ws
    - VITE_ENVIRONMENT=production
  depends_on:
    admin-api:
      condition: service_healthy
```

**Key Features:**
- Multi-stage Docker build (Node.js → nginx)
- nginx proxy for API calls to admin-api
- React frontend with TypeScript
- Health monitoring dashboard

**Health Check:**
```bash
curl http://localhost:3000/health
```

**Troubleshooting:**
- **502 Errors**: Check nginx proxy configuration
- **API Failures**: Verify admin-api service connectivity
- **Build Issues**: Check Node.js dependencies

---

### Admin API (`admin-api`)

**Purpose:** Centralized API gateway aggregating all services

**Configuration:**
```yaml
admin-api:
  build:
    context: ./services/admin-api
    dockerfile: Dockerfile
  container_name: homeiq-admin
  restart: unless-stopped
  ports:
    - "8003:8004"
  environment:
    - PYTHONPATH=/app:/app/src
    - LOG_LEVEL=INFO
  depends_on:
    websocket-ingestion:
      condition: service_healthy
    enrichment-pipeline:
      condition: service_healthy
    influxdb:
      condition: service_healthy
```

**Key Features:**
- FastAPI-based REST API
- Service health aggregation
- Statistics and metrics collection
- CORS support for frontend

**Health Check:**
```bash
curl http://localhost:8003/health
curl http://localhost:8003/api/v1/health
```

**Endpoints:**
- `/health` - Comprehensive health status
- `/api/v1/health` - Simplified health for dashboard
- `/api/v1/stats` - System statistics

---

### WebSocket Ingestion (`websocket-ingestion`)

**Purpose:** Connects to Home Assistant WebSocket API for real-time events

**Configuration:**
```yaml
websocket-ingestion:
  build:
    context: ./services/websocket-ingestion
    dockerfile: Dockerfile
  container_name: homeiq-websocket
  restart: unless-stopped
  ports:
    - "8001:8001"
  environment:
    - HOME_ASSISTANT_URL=${HOME_ASSISTANT_URL}
    - HOME_ASSISTANT_TOKEN=${HOME_ASSISTANT_TOKEN}
    - LOG_LEVEL=INFO
```

**Key Features:**
- Home Assistant WebSocket client
- Automatic reconnection with exponential backoff
- Event subscription management
- Health monitoring with subscription status

**Health Check:**
```bash
curl http://localhost:8001/health
```

**Troubleshooting:**
- **Connection Issues**: Check Home Assistant URL and token
- **Authentication Failures**: Verify token permissions
- **No Events**: Check subscription status and Home Assistant configuration

---

### Enrichment Pipeline (`enrichment-pipeline`)

**Purpose:** Processes and enriches Home Assistant events with weather data

**Configuration:**
```yaml
enrichment-pipeline:
  build:
    context: ./services/enrichment-pipeline
    dockerfile: Dockerfile
  container_name: homeiq-enrichment
  restart: unless-stopped
  ports:
    - "8002:8002"
  environment:
    - WEATHER_API_KEY=${WEATHER_API_KEY}
    - INFLUXDB_URL=${INFLUXDB_URL}
    - INFLUXDB_TOKEN=${INFLUXDB_TOKEN}
    - INFLUXDB_ORG=${INFLUXDB_ORG}
    - INFLUXDB_BUCKET=${INFLUXDB_BUCKET}
```

**Key Features:**
- Event processing and validation
- Weather data enrichment
- InfluxDB integration
- Error handling and retry logic

**Health Check:**
```bash
curl http://localhost:8002/health
```

---

### Data Retention (`data-retention`)

**Purpose:** Manages data lifecycle, cleanup, and backup operations

**Configuration:**
```yaml
data-retention:
  build:
    context: ./services/data-retention
    dockerfile: Dockerfile
  container_name: homeiq-data-retention-dev
  restart: unless-stopped
  ports:
    - "8080:8080"
  environment:
    - INFLUXDB_URL=${INFLUXDB_URL}
    - INFLUXDB_TOKEN=${INFLUXDB_TOKEN}
    - INFLUXDB_ORG=${INFLUXDB_ORG}
    - INFLUXDB_BUCKET=${INFLUXDB_BUCKET}
  volumes:
    - data_retention_backups:/backups
```

**Key Features:**
- Automated data cleanup
- Backup and restore operations
- Data retention policies
- Storage optimization

**Health Check:**
```bash
curl http://localhost:8080/health
```

---

### Weather API (`weather-api`)

**Purpose:** Fetches weather data from OpenWeatherMap API

**Configuration:**
```yaml
weather-api:
  build:
    context: ./services/weather-api
    dockerfile: Dockerfile
  container_name: homeiq-weather-dev
  restart: unless-stopped
  ports:
    - "8001/tcp"
  environment:
    - WEATHER_API_KEY=${WEATHER_API_KEY}
    - LOG_LEVEL=INFO
```

**Key Features:**
- OpenWeatherMap API integration
- Caching for performance
- Error handling and rate limiting
- Internal service (no external access)

**Health Check:**
```bash
# Internal health check only
docker-compose exec weather-api curl http://localhost:8001/health
```

---

### InfluxDB (`influxdb`)

**Purpose:** Time-series database for storing Home Assistant events

**Configuration:**
```yaml
influxdb:
  image: influxdb:2.7
  container_name: homeiq-influxdb
  restart: unless-stopped
  ports:
    - "8086:8086"
  environment:
    - DOCKER_INFLUXDB_INIT_MODE=setup
    - DOCKER_INFLUXDB_INIT_USERNAME=${INFLUXDB_USERNAME}
    - DOCKER_INFLUXDB_INIT_PASSWORD=${INFLUXDB_PASSWORD}
    - DOCKER_INFLUXDB_INIT_ORG=${INFLUXDB_ORG}
    - DOCKER_INFLUXDB_INIT_BUCKET=${INFLUXDB_BUCKET}
    - DOCKER_INFLUXDB_INIT_ADMIN_TOKEN=${INFLUXDB_TOKEN}
  volumes:
    - influxdb_data:/var/lib/influxdb2
    - influxdb_config:/etc/influxdb2
```

**Key Features:**
- Time-series data storage
- Web interface for data exploration
- Query API for analytics
- Backup and restore capabilities

**Health Check:**
```bash
curl http://localhost:8086/health
```

**Web Interface:**
- URL: `http://localhost:8086`
- Username: From `INFLUXDB_USERNAME` environment variable
- Password: From `INFLUXDB_PASSWORD` environment variable

---

## 🔗 **Service Dependencies**

### Dependency Chain

```
health-dashboard → admin-api → websocket-ingestion
                                ↓
                   enrichment-pipeline → influxdb
                                ↓
                   weather-api (internal)
                                ↓
                   data-retention → influxdb
```

### Startup Order

1. **InfluxDB** - Database service (no dependencies)
2. **Weather API** - Internal service (no dependencies)
3. **WebSocket Ingestion** - Depends on Home Assistant connectivity
4. **Enrichment Pipeline** - Depends on InfluxDB and Weather API
5. **Data Retention** - Depends on InfluxDB
6. **Admin API** - Depends on all other services
7. **Health Dashboard** - Depends on Admin API

---

## 🛠️ **Service Management**

### Starting Services

```bash
# Start all services
docker-compose up -d

# Start specific service
docker-compose up -d websocket-ingestion

# Start with dependencies
docker-compose up -d --build health-dashboard
```

### Stopping Services

```bash
# Stop all services
docker-compose down

# Stop specific service
docker-compose stop websocket-ingestion

# Stop and remove containers
docker-compose down --remove-orphans
```

### Restarting Services

```bash
# Restart all services
docker-compose restart

# Restart specific service
docker-compose restart websocket-ingestion

# Restart with rebuild
docker-compose up -d --build websocket-ingestion
```

### Viewing Logs

```bash
# View all logs
docker-compose logs

# View specific service logs
docker-compose logs websocket-ingestion

# Follow logs in real-time
docker-compose logs -f admin-api

# View last N lines
docker-compose logs --tail=50 websocket-ingestion
```

---

## 🔍 **Health Monitoring**

### Service Health Checks

```bash
# Check all services status
docker-compose ps

# Check service health endpoints
curl http://localhost:3000/health    # Dashboard
curl http://localhost:8003/health    # Admin API
curl http://localhost:8001/health    # WebSocket
curl http://localhost:8002/health    # Enrichment
curl http://localhost:8080/health    # Data Retention
curl http://localhost:8086/health    # InfluxDB
```

### Resource Monitoring

```bash
# Check resource usage
docker stats

# Check specific service resources
docker stats homeiq-websocket

# Check disk usage
docker system df
```

---

## 🚨 **Troubleshooting**

### Common Issues

#### Service Won't Start

```bash
# Check service logs
docker-compose logs SERVICE_NAME

# Check service status
docker-compose ps SERVICE_NAME

# Check dependencies
docker-compose ps
```

#### Port Conflicts

```bash
# Check port usage
netstat -tulpn | grep :PORT_NUMBER

# Change port in docker-compose.yml
ports:
  - "NEW_PORT:CONTAINER_PORT"
```

#### Memory Issues

```bash
# Check memory usage
docker stats

# Restart service with memory limit
docker-compose up -d --scale SERVICE_NAME=0
docker-compose up -d SERVICE_NAME
```

#### Network Issues

```bash
# Check Docker networks
docker network ls
docker network inspect homeiq_default

# Test connectivity between services
docker-compose exec SERVICE_NAME ping OTHER_SERVICE
```

### Service-Specific Troubleshooting

#### WebSocket Ingestion Issues

```bash
# Check Home Assistant connectivity
docker-compose exec websocket-ingestion curl -H "Authorization: Bearer $TOKEN" $HA_URL/api/

# Check authentication
docker-compose logs websocket-ingestion | grep -i auth

# Check subscription status
curl http://localhost:8001/health | jq '.subscription'
```

#### Dashboard 502 Errors

```bash
# Check nginx configuration
docker-compose exec health-dashboard cat /etc/nginx/conf.d/default.conf

# Check admin-api connectivity
curl http://localhost:8003/health

# Check dashboard logs
docker-compose logs health-dashboard
```

#### InfluxDB Connection Issues

```bash
# Check InfluxDB status
docker-compose logs influxdb

# Test InfluxDB connectivity
curl http://localhost:8086/health

# Check database initialization
docker-compose logs influxdb | grep -i init
```

---

## 📊 **Performance Optimization**

### Resource Limits

```yaml
# Add to service configuration
deploy:
  resources:
    limits:
      cpus: '0.5'
      memory: 512M
    reservations:
      cpus: '0.25'
      memory: 256M
```

### Scaling Services

```bash
# Scale specific service
docker-compose up -d --scale enrichment-pipeline=2

# Check scaled services
docker-compose ps
```

### Volume Optimization

```bash
# Check volume usage
docker volume ls
docker volume inspect homeiq_influxdb_data

# Clean up unused volumes
docker volume prune
```

---

## 🔒 **Security Considerations**

### Environment Variables

```bash
# Use secure environment files
cp .env.example .env
chmod 600 .env

# Never commit sensitive data
echo ".env" >> .gitignore
```

### Network Security

```yaml
# Use internal networks for sensitive services
networks:
  internal:
    internal: true
  external:
    driver: bridge
```

### Container Security

```yaml
# Run as non-root user
user: "1001:1001"

# Read-only filesystem
read_only: true
tmpfs:
  - /tmp
  - /var/run
```

---

## 📚 **Related Documentation**

- [API Endpoints Reference](API_ENDPOINTS_REFERENCE.md)
- [WebSocket Troubleshooting Guide](WEBSOCKET_TROUBLESHOOTING.md)
- [Dashboard 502 Fix Summary](DASHBOARD_502_FIX_SUMMARY.md)
- [Docker Structure Guide](DOCKER_STRUCTURE_GUIDE.md)
- [Main README](README.md)
