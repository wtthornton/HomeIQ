# Epic 40: Quick Reference Card

**Epic 40: Dual Deployment Configuration**  
**Status:** ✅ Complete

---

## 🚀 Quick Commands

### Test Deployment
```bash
cp infrastructure/env.test .env
# Edit .env with your test configuration
bash scripts/setup_test_environment.sh
docker-compose --profile test up -d
```

### Production Deployment
```bash
cp infrastructure/env.production .env
# Edit .env with your production configuration
docker-compose up -d
```

### Switch Deployments
```bash
docker-compose down
docker-compose --profile test up -d    # Test
# OR
docker-compose up -d                    # Production
```

---

## 📋 Key Configuration

### Test Environment
- **InfluxDB Bucket**: `home_assistant_events_test`
- **InfluxDB Org**: `homeiq-test`
- **SQLite DB**: `./data/test/metadata.db`
- **External APIs**: ❌ Disabled
- **Data Generation**: ✅ Enabled

### Production Environment
- **InfluxDB Bucket**: `home_assistant_events`
- **InfluxDB Org**: `homeiq`
- **SQLite DB**: `./data/metadata.db`
- **External APIs**: ✅ Enabled
- **Data Generation**: ❌ Blocked

---

## 🔍 Service Profiles

### Test Profile Services
- `home-assistant-test` (Port 8124)
- `websocket-ingestion-test` (Port 8002)

### Production Profile Services
- `weather-api` (Port 8009)
- `carbon-intensity` (Port 8010)
- `electricity-pricing` (Port 8011)
- `air-quality` (Port 8012)
- `smart-meter` (Port 8014)

---

## ⚠️ Important Notes

1. **Mutually Exclusive**: Test and production cannot run simultaneously on 8GB NUC
2. **Resource Usage**: Test ~5GB, Production ~5.5GB
3. **Validation**: Data generation services exit if `DEPLOYMENT_MODE=production`
4. **Environment File**: Always copy from `infrastructure/env.test` or `infrastructure/env.production`

---

## 🛠️ Troubleshooting

**Test services not starting?**
- Check: `docker-compose --profile test config | grep "home-assistant-test"`
- Verify: `.env` has `DEPLOYMENT_MODE=test`

**Production services blocked?**
- Expected: Data generation services blocked in production
- Use test deployment for data generation

**InfluxDB test bucket missing?**
- Run: `bash scripts/setup_test_environment.sh`
- Or manually create bucket via InfluxDB UI

---

## 📚 Full Documentation

- **Deployment Guide**: `docs/EPIC_40_DEPLOYMENT_GUIDE.md`
- **Epic PRD**: `docs/prd/epic-40-dual-deployment-configuration.md`
- **Completion Summary**: `implementation/EPIC_40_COMPLETE.md`

---

**Last Updated:** January 2025

