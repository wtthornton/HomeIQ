# 🖥️ Home Assistant Ingestor - CLI Reference

## 📋 **Command Overview**

### **Docker Compose Commands**
```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# Restart specific service
docker-compose restart <service-name>

# View service status
docker-compose ps

# View service logs
docker-compose logs <service-name>

# Follow logs in real-time
docker-compose logs -f <service-name>
```

## 🔍 **Health Check Commands**

### **System Health**

**Linux/Mac (Bash):**
```bash
# Check overall system health
curl http://localhost:8080/api/v1/health

# Check specific service health
curl http://localhost:8080/api/v1/health/websocket-ingestion
curl http://localhost:8080/api/v1/health/enrichment-pipeline
curl http://localhost:8080/api/v1/health/data-retention
```

**Windows (PowerShell):**
```powershell
# ⚠️ IMPORTANT: Do NOT use curl in PowerShell - use Invoke-RestMethod instead

# ✅ CORRECT - Check overall system health
Invoke-RestMethod -Uri "http://localhost:8080/api/v1/health"

# ✅ CORRECT - Check specific service health
Invoke-RestMethod -Uri "http://localhost:8080/api/v1/health/websocket-ingestion"
Invoke-RestMethod -Uri "http://localhost:8080/api/v1/health/enrichment-pipeline"
Invoke-RestMethod -Uri "http://localhost:8080/api/v1/health/data-retention"

# ❌ WRONG - This does NOT work in PowerShell
# curl -s http://localhost:8080/api/v1/health | ConvertFrom-Json
```

**See:** `docs/POWERSHELL_BEST_PRACTICES.md` for complete PowerShell command reference

### **Service Status**
```bash
# Check all services
docker-compose ps

# Check service resource usage
docker stats

# Check service logs
docker-compose logs --tail=100 <service-name>
```

## 📊 **Monitoring Commands**

### **Log Management**
```bash
# View all logs
docker-compose logs

# Filter logs by service
docker-compose logs websocket-ingestion
docker-compose logs enrichment-pipeline
docker-compose logs admin-api

# Filter logs by level
docker-compose logs | grep ERROR
docker-compose logs | grep WARNING

# Follow logs in real-time
docker-compose logs -f --tail=50
```

### **Metrics and Statistics**

**Linux/Mac (Bash):**
```bash
# Get system statistics
curl http://localhost:8080/api/v1/stats

# Get current metrics
curl http://localhost:8080/api/v1/monitoring/metrics/current

# Get metrics summary
curl http://localhost:8080/api/v1/monitoring/metrics/summary
```

**Windows (PowerShell):**
```powershell
# ✅ CORRECT - Get system statistics
Invoke-RestMethod -Uri "http://localhost:8080/api/v1/stats"

# ✅ CORRECT - Get current metrics
Invoke-RestMethod -Uri "http://localhost:8080/api/v1/monitoring/metrics/current"

# ✅ CORRECT - Get metrics summary
Invoke-RestMethod -Uri "http://localhost:8080/api/v1/monitoring/metrics/summary"
```

## 🔧 **Configuration Commands**

### **Configuration Management**

**Linux/Mac (Bash):**
```bash
# View current configuration
curl http://localhost:8080/api/v1/config

# Update configuration
curl -X PUT http://localhost:8080/api/v1/config \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <api-key>" \
  -d '{"setting": "value"}'
```

### **Environment Variables**
```bash
# Check environment variables
docker-compose config

# Validate configuration
docker-compose config --quiet
```

## 📈 **Data Management Commands**

### **Data Export**
```bash
# Export recent events (JSON)
curl "http://localhost:8080/api/v1/events/recent?limit=1000" \
  -H "Authorization: Bearer <api-key>" > events.json

# Export events (CSV)
curl "http://localhost:8080/api/v1/monitoring/export/logs?format=csv&limit=1000" \
  -H "Authorization: Bearer <api-key>" > events.csv

# Export metrics (JSON)
curl "http://localhost:8080/api/v1/monitoring/export/metrics?format=json" \
  -H "Authorization: Bearer <api-key>" > metrics.json
```

### **Backup and Restore**
```bash
# Create backup
curl -X POST http://localhost:8080/api/v1/backup \
  -H "Authorization: Bearer <api-key>" \
  -d '{"backup_type": "full"}'

# List backups
curl http://localhost:8080/api/v1/backups \
  -H "Authorization: Bearer <api-key>"

# Restore from backup
curl -X POST http://localhost:8080/api/v1/restore \
  -H "Authorization: Bearer <api-key>" \
  -d '{"backup_id": "backup-id"}'
```

## 🚨 **Alert Management Commands**

### **Alert Operations**
```bash
# Get active alerts
curl http://localhost:8080/api/v1/monitoring/alerts/active \
  -H "Authorization: Bearer <api-key>"

# Acknowledge alert
curl -X POST http://localhost:8080/api/v1/monitoring/alerts/<alert-id>/acknowledge \
  -H "Authorization: Bearer <api-key>"

# Resolve alert
curl -X POST http://localhost:8080/api/v1/monitoring/alerts/<alert-id>/resolve \
  -H "Authorization: Bearer <api-key>"
```

### **Alert Configuration**
```bash
# Get alert rules
curl http://localhost:8080/api/v1/monitoring/config/alert-rules \
  -H "Authorization: Bearer <api-key>"

# Create alert rule
curl -X POST http://localhost:8080/api/v1/monitoring/config/alert-rules \
  -H "Authorization: Bearer <api-key>" \
  -H "Content-Type: application/json" \
  -d '{"name": "high_cpu", "metric_name": "cpu_usage", "threshold": 80}'
```

## 🛠️ **Maintenance Commands**

### **Service Management**
```bash
# Start specific service
docker-compose up -d <service-name>

# Stop specific service
docker-compose stop <service-name>

# Restart specific service
docker-compose restart <service-name>

# Scale service
docker-compose up -d --scale <service-name>=2
```

### **Cleanup Operations**
```bash
# Clean up old logs
curl -X DELETE "http://localhost:8080/api/v1/monitoring/logs/cleanup?days_to_keep=30" \
  -H "Authorization: Bearer <api-key>"

# Compress old logs
curl -X POST http://localhost:8080/api/v1/monitoring/logs/compress \
  -H "Authorization: Bearer <api-key>"

# Clean up old backups
curl -X DELETE "http://localhost:8080/api/v1/backups/cleanup?days_to_keep=30" \
  -H "Authorization: Bearer <api-key>"
```

## 🔍 **Troubleshooting Commands**

### **Diagnostic Commands**
```bash
# Check service connectivity
docker-compose exec websocket-ingestion ping influxdb
docker-compose exec enrichment-pipeline ping admin-api

# Check service resources
docker-compose exec <service-name> ps aux
docker-compose exec <service-name> df -h

# Check network connectivity
docker-compose exec <service-name> netstat -tulpn
```

### **Debug Commands**
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
docker-compose up -d

# View detailed logs
docker-compose logs --details <service-name>

# Check service configuration
docker-compose exec <service-name> env | grep -E "(HA_|WEATHER_|INFLUXDB_)"
```

## 📊 **Performance Monitoring**

### **Resource Monitoring**
```bash
# Monitor resource usage
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"

# Check disk usage
docker system df

# Check volume usage
docker volume ls
docker volume inspect <volume-name>
```

### **Performance Analysis**
```bash
# Get performance metrics
curl http://localhost:8080/api/v1/monitoring/metrics/current

# Get system statistics
curl http://localhost:8080/api/v1/stats

# Get processing statistics
curl http://localhost:8080/api/v1/events/stats
```

## 🔒 **Security Commands**

### **Authentication**
```bash
# Test API authentication
curl -H "Authorization: Bearer <api-key>" http://localhost:8080/api/v1/health

# Generate new API key
# (Update in .env file and restart services)
```

### **Security Validation**
```bash
# Check for security updates
docker-compose pull

# Validate configuration security
docker-compose config | grep -E "(password|token|key)"

# Check service permissions
docker-compose exec <service-name> ls -la /app
```

## 📚 **Help and Documentation**

### **Getting Help**
```bash
# Docker Compose help
docker-compose --help

# Service-specific help
docker-compose exec <service-name> --help

# API documentation
open http://localhost:8080/docs
```

### **Documentation Access**
- **API Docs**: http://localhost:8080/docs
- **Health Dashboard**: http://localhost:3000
- **Monitoring Dashboard**: http://localhost:8080/api/v1/monitoring/dashboard/overview

---

**🖥️ Use these CLI commands to manage your Home Assistant Ingestor system effectively!**
