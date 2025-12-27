# Deployment Checklist
**Data Enrichment & Storage Optimization**

**Ready to Deploy:** ✅ YES  
**Date:** October 10, 2025

---

## 🎯 Pre-Deployment Checklist

### API Keys Required

- [ ] **WattTime** - Carbon intensity API token
  - Get from: https://www.watttime.org/api-documentation/
  - Free tier: 100 calls/day
  - Required for: Carbon-aware automation

- [ ] **AirNow** - Air quality API key
  - Get from: https://docs.airnowapi.org/
  - Free tier: 500 calls/hour
  - Required for: Health-aware automation

- [ ] **Google Calendar** (Optional)
  - Setup: https://console.cloud.google.com
  - Get OAuth credentials (client ID, secret, refresh token)
  - Required for: Occupancy prediction

- [ ] **AWS Account** (Optional)
  - Required for: S3 archival (long-term storage)
  - Cost: ~$1/year for 5 years of data
  - Can skip initially and add later

### Environment Configuration

- [ ] Copy `infrastructure/env.example` to `.env`
- [ ] Add `WATTTIME_API_TOKEN`
- [ ] Add `GRID_REGION` (your grid operator)
- [ ] Add `AIRNOW_API_KEY`
- [ ] Set `LATITUDE` and `LONGITUDE`
- [ ] (Optional) Add Google OAuth credentials
- [ ] (Optional) Add AWS S3 credentials

---

## 🚀 Deployment Steps

### Step 1: Build Services

```bash
# Build all new services
docker-compose build \
  carbon-intensity \
  electricity-pricing \
  air-quality \
  calendar \
  smart-meter \
  data-retention
```

**Expected time:** 5-10 minutes

### Step 2: Start Services

```bash
# Start all services
docker-compose up -d

# Or start incrementally for testing
docker-compose up -d carbon-intensity
docker-compose up -d electricity-pricing
docker-compose up -d air-quality
# ... etc
```

### Step 3: Verify Health

```bash
# Check all service health endpoints
curl http://localhost:8010/health | jq  # Carbon Intensity
curl http://localhost:8011/health | jq  # Electricity Pricing
curl http://localhost:8012/health | jq  # Air Quality
curl http://localhost:8013/health | jq  # Calendar
curl http://localhost:8014/health | jq  # Smart Meter
curl http://localhost:8080/health | jq  # Data Retention
```

**Expected:** All should return `"status": "healthy"` or `"degraded"` (degraded is OK before first API fetch)

### Step 4: Monitor Logs

```bash
# Watch logs for first 15 minutes
docker-compose logs -f carbon-intensity
docker-compose logs -f electricity-pricing
docker-compose logs -f air-quality

# Look for successful API calls and data writes to InfluxDB
```

**Expected messages:**
- "Carbon intensity: XXX.X gCO2/kWh"
- "Current price: X.XXX EUR/kWh"
- "AQI: XXX (Good|Moderate|Unhealthy)"

### Step 5: Verify Data in InfluxDB

```bash
# Access InfluxDB UI
open http://localhost:8086

# Login with credentials from .env
# Navigate to Data Explorer
```

**Query each measurement:**
```flux
from(bucket: "events")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "carbon_intensity")

from(bucket: "events")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "electricity_pricing")

from(bucket: "events")
  |> range(start: -1h)
  |> filter(fn: (r) => r._measurement == "air_quality")
```

**Expected:** Data points appearing every 15-60 minutes

### Step 6: Check Dashboard

```bash
open http://localhost:3000
```

**Verify:**
- [ ] "External Data Sources" section appears
- [ ] 5 data source cards displayed
- [ ] Success rates showing
- [ ] Last fetch timestamps updating
- [ ] Status badges showing "healthy" or "degraded"

---

## ✅ Post-Deployment Validation

### First Hour

- [ ] All services remain healthy after 1 hour
- [ ] No error spikes in logs
- [ ] Data appearing in InfluxDB
- [ ] Dashboard showing all 5 data sources
- [ ] No regressions in existing services

### First Day

- [ ] Carbon intensity: ~96 data points (every 15 min)
- [ ] Electricity pricing: ~24 data points (hourly)
- [ ] Air quality: ~24 data points (hourly)
- [ ] Calendar: ~96 predictions (every 15 min, if configured)
- [ ] Smart meter: ~288 data points (every 5 min)

### First Week

- [ ] No service restarts due to errors
- [ ] Success rates >95% for all services
- [ ] Storage metrics available: `curl http://localhost:8080/retention/stats`
- [ ] Materialized views refreshed daily

---

## 🔧 Troubleshooting

### Service Won't Start

```bash
# Check logs
docker-compose logs {service-name}

# Common issues:
# - Missing API key: Add to .env
# - Invalid credentials: Verify API keys
# - Network issues: Check Docker network
```

### No Data in InfluxDB

```bash
# Check service logs for API call success
docker-compose logs carbon-intensity | grep "Carbon intensity"

# Verify InfluxDB connection
docker-compose logs carbon-intensity | grep "InfluxDB"

# Check InfluxDB is healthy
curl http://localhost:8086/health
```

### Dashboard Not Showing Data Sources

```bash
# Check if services are accessible from dashboard container
docker exec -it homeiq-dashboard sh
curl http://carbon-intensity:8010/health
curl http://electricity-pricing:8011/health

# Check browser console for CORS or network errors
# Open http://localhost:3000 and press F12
```

### OAuth Issues (Calendar)

```bash
# Check OAuth token validity
docker-compose logs calendar | grep "OAuth"

# Re-generate refresh token if expired
# See services/calendar-service/README.md for OAuth setup
```

---

## 📊 Success Metrics

After 1 week of operation, verify:

- [ ] **Data Collection:**
  - All 5 data sources showing >95% success rate
  - Regular data appearing in InfluxDB
  - No extended outages

- [ ] **Performance:**
  - Dashboard loads in <2 seconds
  - Health endpoints respond in <100ms
  - No timeouts or slowdowns

- [ ] **Storage:**
  - Database size growing predictably
  - Materialized views refreshing successfully
  - Retention operations running nightly

- [ ] **Existing System:**
  - WebSocket ingestion still working
  - Weather enrichment still working
  - Admin API still working
  - No regressions

---

## 🎯 Next Steps After Deployment

### Week 1: Monitor

- Watch logs daily
- Check dashboard multiple times per day
- Verify data quality
- Note any API failures or patterns

### Week 2: Optimize

- Review API fetch intervals (adjust if needed)
- Check if all data sources are necessary
- Fine-tune caching durations
- Benchmark query performance

### Week 3: Automate

- Create first carbon-aware automation
- Implement cost-aware scheduling
- Set up air quality responses
- Test occupancy predictions (if calendar configured)

### Week 4: Measure

- Calculate actual storage savings
- Measure query performance improvement
- Track API costs (should be $0 with free tiers)
- Document automation value

---

## 💰 Expected Results (30 Days)

**Data Collection:**
- 135,000+ carbon intensity data points
- 720+ pricing forecasts
- 720+ air quality readings
- 8,640+ smart meter readings
- 0+ calendar predictions (if configured)

**Storage:**
- Raw data: ~2-3 GB
- Query performance: 35ms average
- No storage issues

**Value:**
- Enable 3-5 new automation patterns
- Foundation for future ML/AI features
- Data-driven insights available

---

## 📞 Support

**Documentation:**
- General: `docs/DATA_ENRICHMENT_DEPLOYMENT_GUIDE.md`
- Architecture: `docs/DATA_ENRICHMENT_ARCHITECTURE.md`
- Implementation: `docs/IMPLEMENTATION_COMPLETE_SUMMARY.md`

**Service-Specific:**
- Each service has README in `services/{service-name}/README.md`

**Context7 KB:**
- `docs/kb/context7-cache/` - All research and patterns

---

**Deployment Status:** ✅ Ready  
**Risk Level:** Low  
**Rollback:** Easy (remove services from docker-compose.yml)  
**Recommendation:** Deploy to production 🚀

