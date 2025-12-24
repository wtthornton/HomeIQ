# 🚀 Home Assistant Ingestor - Production Deployment Guide

## 🎯 **Production Readiness Checklist**

### **✅ System Requirements**
- **CPU**: 4 cores minimum, 8 cores recommended
- **Memory**: 8GB minimum, 16GB recommended
- **Storage**: 100GB minimum, 500GB recommended (SSD preferred)
- **Network**: Stable internet connection, 10Mbps minimum
- **OS**: Linux (Ubuntu 20.04+ recommended), Docker 20.10+

### **✅ Security Requirements**
- **Firewall**: Configured with minimal required ports
- **SSL/TLS**: HTTPS enabled for web interface
- **Authentication**: Strong API keys and access tokens
- **Updates**: Regular security updates scheduled
- **Monitoring**: Security monitoring and alerting enabled

## 🔧 **Production Configuration**

### **Environment Variables**
```bash
# Production Environment
NODE_ENV=production
LOG_LEVEL=INFO

# Home Assistant Configuration
HA_URL=wss://your-ha-instance:8123/api/websocket
HA_ACCESS_TOKEN=your_secure_long_lived_token

# Weather API Configuration
WEATHER_API_KEY=your_openweathermap_api_key
WEATHER_LOCATION=your_city,country_code

# InfluxDB Configuration
INFLUXDB_URL=http://influxdb:8086
INFLUXDB_TOKEN=your_secure_influxdb_token
INFLUXDB_ORG=your_organization
INFLUXDB_BUCKET=home_assistant_prod

# API Configuration
API_KEY=your_secure_api_key_32_chars_minimum
ENABLE_AUTH=true
CORS_ORIGINS=https://your-domain.com

# Security Configuration
SSL_CERT_PATH=/etc/ssl/certs/your-cert.pem
SSL_KEY_PATH=/etc/ssl/private/your-key.pem
```

### **Docker Compose Production (Optimized)**
The production configuration now uses optimized Alpine-based images with multi-stage builds:

```yaml
# docker-compose.prod.yml - Optimized production configuration
services:
  websocket-ingestion:
    build:
      context: ./services/websocket-ingestion
      dockerfile: Dockerfile
    restart: unless-stopped
    environment:
      - LOG_LEVEL=INFO
      - HOME_ASSISTANT_URL=${HOME_ASSISTANT_URL}
      - HOME_ASSISTANT_TOKEN=${HOME_ASSISTANT_TOKEN}
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.5'
        reservations:
          memory: 128M
          cpus: '0.25'
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
      - /var/tmp
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  admin-api:
    build:
      context: ./services/admin-api
      dockerfile: Dockerfile
    restart: unless-stopped
    ports:
      - "8003:8004"
    environment:
      - LOG_LEVEL=INFO
      - ENABLE_AUTH=${ENABLE_AUTH:-true}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
        reservations:
          memory: 256M
          cpus: '0.25'
    security_opt:
      - no-new-privileges:true
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8004/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  health-dashboard:
    build:
      context: ./services/health-dashboard
      dockerfile: Dockerfile
    restart: unless-stopped
    ports:
      - "3000:80"
    environment:
      - VITE_API_BASE_URL=${DASHBOARD_API_BASE_URL:-http://localhost:8003/api/v1}
      - VITE_ENVIRONMENT=${ENVIRONMENT:-production}
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.25'
        reservations:
          memory: 128M
          cpus: '0.1'
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
      - /var/cache/nginx
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost/"]
      interval: 30s
      timeout: 10s
      retries: 3

  influxdb:
    image: influxdb:2.7
    restart: unless-stopped
    environment:
      - DOCKER_INFLUXDB_INIT_MODE=setup
      - DOCKER_INFLUXDB_INIT_USERNAME=${INFLUXDB_USERNAME}
      - DOCKER_INFLUXDB_INIT_PASSWORD=${INFLUXDB_PASSWORD}
      - DOCKER_INFLUXDB_INIT_ORG=${INFLUXDB_ORG}
      - DOCKER_INFLUXDB_INIT_BUCKET=${INFLUXDB_BUCKET}
      - DOCKER_INFLUXDB_INIT_ADMIN_TOKEN=${INFLUXDB_TOKEN}
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '2.0'
        reservations:
          memory: 1G
          cpus: '1.0'
    security_opt:
      - no-new-privileges:true
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8086/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## 🔒 **Security Configuration**

### **SSL/TLS Setup**
```bash
# Generate SSL certificate (Let's Encrypt recommended)
certbot certonly --standalone -d your-domain.com

# Copy certificates to Docker volumes
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem /etc/ssl/certs/
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem /etc/ssl/private/
sudo chmod 600 /etc/ssl/private/privkey.pem
```

### **Firewall Configuration**
```bash
# UFW Firewall Setup
sudo ufw enable
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP (for Let's Encrypt)
sudo ufw allow 443/tcp   # HTTPS
sudo ufw deny 8080/tcp   # Block direct API access
sudo ufw deny 3000/tcp   # Block direct dashboard access
```

### **API Security**
```bash
# Generate secure API key
openssl rand -hex 32

# Generate secure InfluxDB token
influx auth create --org your_organization --all-access
```

## 📊 **Monitoring & Alerting**

### **System Monitoring**
```bash
# Install monitoring tools
sudo apt update
sudo apt install htop iotop nethogs

# Configure log rotation
sudo nano /etc/logrotate.d/docker-containers
```

### **Alert Configuration**
```json
{
  "alert_rules": [
    {
      "name": "high_cpu_usage",
      "metric": "cpu_usage_percent",
      "threshold": 80,
      "severity": "warning",
      "notification": "email"
    },
    {
      "name": "high_memory_usage",
      "metric": "memory_usage_percent",
      "threshold": 85,
      "severity": "critical",
      "notification": "email"
    },
    {
      "name": "disk_space_low",
      "metric": "disk_usage_percent",
      "threshold": 90,
      "severity": "critical",
      "notification": "email"
    }
  ]
}
```

### **Log Management**
```bash
# Configure log rotation
sudo nano /etc/docker/daemon.json
```
```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

## 🔄 **Backup Strategy**

### **Automated Backups**
```bash
#!/bin/bash
# backup.sh - Automated backup script

# Create backup directory
BACKUP_DIR="/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Backup InfluxDB
docker-compose exec influxdb influx backup "$BACKUP_DIR/influxdb"

# Backup configuration
cp .env "$BACKUP_DIR/"
cp docker-compose.yml "$BACKUP_DIR/"

# Backup logs
docker-compose logs > "$BACKUP_DIR/logs.txt"

# Compress backup
tar -czf "$BACKUP_DIR.tar.gz" "$BACKUP_DIR"
rm -rf "$BACKUP_DIR"

# Keep only last 7 days of backups
find /backups -name "*.tar.gz" -mtime +7 -delete
```

### **Backup Schedule**
```bash
# Add to crontab
crontab -e

# Daily backup at 2 AM
0 2 * * * /path/to/backup.sh

# Weekly full backup on Sunday at 1 AM
0 1 * * 0 /path/to/full-backup.sh
```

## 🚀 **Deployment Process**

### **Initial Deployment**
```bash
# 1. Clone repository
git clone <repository-url>
cd homeiq

# 2. Configure environment
cp infrastructure/env.production .env
nano .env  # Edit with production values

# 3. Generate SSL certificates
sudo certbot certonly --standalone -d your-domain.com

# 4. Start services
docker-compose -f docker-compose.prod.yml up -d

# 5. Verify deployment
docker-compose ps
curl -k https://your-domain.com/api/v1/health
```

### **Update Process**
```bash
# 1. Pull latest images
docker-compose pull

# 2. Backup current state
./scripts/backup.sh

# 3. Update services (rolling update)
docker-compose up -d --no-deps websocket-ingestion
docker-compose up -d --no-deps enrichment-pipeline
docker-compose up -d --no-deps data-retention
docker-compose up -d --no-deps admin-api
docker-compose up -d --no-deps health-dashboard

# 4. Verify update
docker-compose ps
curl -k https://your-domain.com/api/v1/health
```

## 📈 **Performance Optimization**

### **Resource Tuning**
```yaml
# docker-compose.prod.yml optimizations
services:
  influxdb:
    command:
      - --store=tsi1
      - --wal-fsync-delay=0s
      - --cache-max-memory-size=1g
      - --cache-snapshot-memory-size=128m
    ulimits:
      nofile:
        soft: 65536
        hard: 65536
```

### **Database Optimization**
```sql
-- InfluxDB optimization queries
CREATE RETENTION POLICY "1year" ON "home_assistant_prod" DURATION 365d REPLICATION 1 DEFAULT;
CREATE CONTINUOUS QUERY "downsample_hourly" ON "home_assistant_prod" BEGIN SELECT mean(*) INTO "home_assistant_prod"."1year"."events_1h" FROM "events" GROUP BY time(1h), * END;
```

## 🔍 **Health Checks**

### **Service Health Monitoring**
```bash
#!/bin/bash
# health-check.sh - Comprehensive health check

# Check Docker services
docker-compose ps | grep -v "Up"

# Check API endpoints
curl -f https://your-domain.com/api/v1/health || echo "API health check failed"

# Check database connectivity
docker-compose exec influxdb influx ping || echo "InfluxDB health check failed"

# Check disk space
df -h | awk '$5 > 90 {print "Disk space warning: " $0}'

# Check memory usage
free -m | awk 'NR==2{if($3/$2 > 0.9) print "Memory usage warning: " $3/$2*100 "%"}'
```

### **Automated Health Checks**
```bash
# Add to crontab
*/5 * * * * /path/to/health-check.sh
```

## 🚨 **Incident Response**

### **Emergency Procedures**
```bash
# 1. Stop all services
docker-compose down

# 2. Check system resources
df -h
free -m
docker system df

# 3. Check logs
docker-compose logs --tail=100

# 4. Restart services
docker-compose up -d

# 5. Verify recovery
curl -k https://your-domain.com/api/v1/health
```

### **Rollback Procedure**
```bash
# 1. Stop current services
docker-compose down

# 2. Restore from backup
./scripts/restore.sh latest

# 3. Start services
docker-compose up -d

# 4. Verify rollback
curl -k https://your-domain.com/api/v1/health
```

## 📞 **Support & Maintenance**

### **Regular Maintenance Tasks**
- **Daily**: Check system health and logs
- **Weekly**: Review performance metrics and alerts
- **Monthly**: Update Docker images and security patches
- **Quarterly**: Review and update backup strategies

### **Support Contacts**
- **System Administrator**: admin@your-domain.com
- **Technical Support**: support@your-domain.com
- **Emergency Contact**: +1-555-0123

---

**🚀 Your Home Assistant Ingestor is now ready for production deployment!**
