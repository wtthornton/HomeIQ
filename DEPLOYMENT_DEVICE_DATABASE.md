# Device Database Services Deployment Guide

**Date:** January 20, 2025  
**Status:** Ready for Deployment

---

## Quick Deploy

### Option 1: Deploy All Services (Recommended)

```bash
# Build and start all new services
docker compose up -d --build device-health-monitor device-context-classifier device-setup-assistant device-database-client device-recommender

# Run database migration (adds new device fields)
docker compose run --rm data-api alembic upgrade head

# Restart data-api to pick up new endpoints
docker compose restart data-api
```

### Option 2: Use Deployment Script

**Windows (PowerShell):**
```powershell
.\scripts\deploy-device-database-services.ps1
```

**Linux/Mac:**
```bash
chmod +x scripts/deploy-device-database-services.sh
./scripts/deploy-device-database-services.sh
```

---

## Manual Deployment Steps

### 1. Run Database Migration

The Device model has been extended with new fields. Run the migration:

```bash
docker compose run --rm data-api alembic upgrade head
```

This will apply migration `006_add_device_intelligence_fields.py` which adds:
- `device_type` and `device_category` (indexed)
- Power consumption fields (`power_consumption_idle_w`, `power_consumption_active_w`, `power_consumption_max_w`)
- Device Database fields (`setup_instructions_url`, `troubleshooting_notes`, `device_features_json`, `community_rating`, etc.)

### 2. Build New Services

```bash
docker compose build \
  device-health-monitor \
  device-context-classifier \
  device-setup-assistant \
  device-database-client \
  device-recommender
```

### 3. Start Services

```bash
docker compose up -d \
  device-health-monitor \
  device-context-classifier \
  device-setup-assistant \
  device-database-client \
  device-recommender
```

### 4. Verify Deployment

Check service health:

```bash
# Check individual services
curl http://localhost:8019/health  # device-health-monitor
curl http://localhost:8032/health  # device-context-classifier
curl http://localhost:8021/health  # device-setup-assistant
curl http://localhost:8022/health  # device-database-client
curl http://localhost:8023/health  # device-recommender

# Check via docker
docker compose ps | grep device-
```

### 5. Restart Data API

Restart data-api to ensure it picks up the new endpoints:

```bash
docker compose restart data-api
```

---

## Service Ports

| Service | External Port | Internal Port | Health Check |
|---------|---------------|---------------|--------------|
| device-health-monitor | 8019 | 8019 | http://localhost:8019/health |
| device-context-classifier | 8032 | 8020 | http://localhost:8032/health |
| device-setup-assistant | 8021 | 8021 | http://localhost:8021/health |
| device-database-client | 8022 | 8022 | http://localhost:8022/health |
| device-recommender | 8023 | 8023 | http://localhost:8023/health |

---

## Environment Variables

Add these to your `.env` file (optional):

```bash
# Device Database Client (optional - for external Device Database API)
DEVICE_DATABASE_API_URL=https://api.devicedatabase.org
DEVICE_DATABASE_API_KEY=your-api-key

# Device Cache Directory
DEVICE_CACHE_DIR=data/device_cache

# Service Ports (defaults shown)
DEVICE_HEALTH_MONITOR_PORT=8019
DEVICE_CONTEXT_CLASSIFIER_PORT=8020
DEVICE_SETUP_ASSISTANT_PORT=8021
DEVICE_DATABASE_CLIENT_PORT=8022
DEVICE_RECOMMENDER_PORT=8023
```

---

## Testing the Deployment

### 1. Test Health Endpoints

```bash
# Via Data API
curl http://localhost:8006/api/devices/health-summary

# Direct service
curl http://localhost:8019/health
```

### 2. Test Device Classification

```bash
# Get a device ID first
curl http://localhost:8006/api/devices | jq '.devices[0].device_id'

# Classify the device (replace {device_id})
curl -X POST http://localhost:8006/api/devices/{device_id}/classify
```

### 3. Test Device Health

```bash
# Get device health (replace {device_id})
curl http://localhost:8006/api/devices/{device_id}/health
```

### 4. Test Setup Assistant

```bash
# Get setup guide (replace {device_id})
curl http://localhost:8006/api/devices/{device_id}/setup-guide

# Check for setup issues
curl http://localhost:8006/api/devices/{device_id}/setup-issues
```

### 5. Test Capability Discovery

```bash
# Discover capabilities (replace {device_id})
curl -X POST http://localhost:8006/api/devices/{device_id}/discover-capabilities
```

### 6. Test Recommendations

```bash
# Get device recommendations
curl "http://localhost:8006/api/devices/recommendations?device_type=light"

# Compare devices
curl "http://localhost:8006/api/devices/compare?device_ids=device1,device2"

# Find similar devices
curl http://localhost:8006/api/devices/similar/{device_id}
```

---

## Troubleshooting

### Services Not Starting

1. **Check logs:**
   ```bash
   docker compose logs device-health-monitor
   docker compose logs device-context-classifier
   ```

2. **Verify environment variables:**
   ```bash
   docker compose config | grep -A 10 device-health-monitor
   ```

3. **Check port conflicts:**
   ```bash
   netstat -an | findstr "8019 8020 8021 8022 8023"
   ```

### Migration Fails

1. **Check database file exists:**
   ```bash
   ls -la data/metadata.db
   ```

2. **Run migration manually:**
   ```bash
   docker compose run --rm data-api alembic upgrade head
   ```

3. **Check migration status:**
   ```bash
   docker compose run --rm data-api alembic current
   ```

### API Endpoints Not Available

1. **Restart data-api:**
   ```bash
   docker compose restart data-api
   ```

2. **Check data-api logs:**
   ```bash
   docker compose logs data-api | tail -n 50
   ```

3. **Verify endpoints are registered:**
   ```bash
   curl http://localhost:8006/docs
   ```

---

## Next Steps

After deployment:

1. **Classify existing devices:**
   - Use `POST /api/devices/{device_id}/classify` for each device
   - Or wait for automatic classification during device discovery

2. **Discover capabilities:**
   - Use `POST /api/devices/{device_id}/discover-capabilities` for devices
   - Capabilities will be stored in `device_features_json` field

3. **Monitor device health:**
   - Check `GET /api/devices/health-summary` regularly
   - Review `GET /api/devices/maintenance-alerts` for issues

4. **Use device-specific templates:**
   - Device-specific automation templates are automatically included in suggestion generation
   - Check AI Automation Service suggestions for device-specific automations

---

## Rollback

If you need to rollback:

```bash
# Stop new services
docker compose stop device-health-monitor device-context-classifier device-setup-assistant device-database-client device-recommender

# Remove services
docker compose rm -f device-health-monitor device-context-classifier device-setup-assistant device-database-client device-recommender

# Rollback migration (if needed)
docker compose run --rm data-api alembic downgrade -1
```

**Note:** The new device fields are nullable, so existing functionality will continue to work even if services are stopped.

---

## Support

For issues:
- Check service logs: `docker compose logs {service-name}`
- Review API documentation: http://localhost:8006/docs
- See troubleshooting guide: `docs/TROUBLESHOOTING_GUIDE.md`

