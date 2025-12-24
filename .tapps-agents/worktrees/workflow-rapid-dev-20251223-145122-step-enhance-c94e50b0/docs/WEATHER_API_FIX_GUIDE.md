# Weather API Fix Guide

## 🚨 **Issue Identified**

The Weather Enrichment service is currently **disabled** because the `WEATHER_API_KEY` environment variable is not configured. This results in:
- ❌ 0 Weather API Calls
- ❌ 0 Cache Hits  
- ❌ No weather data enrichment for Home Assistant events

## 🔍 **Root Cause Analysis**

### Dashboard Evidence
From the dashboard at `http://localhost:3000/`, the Weather Enrichment section shows:
- **Weather Service**: ✅ Enabled (healthy)
- **API Calls**: 0 calls (Min: 0, Max: 0, Count: 0)
- **Cache Hits**: 0 hits (Min: 0, Max: 0, Count: 0)

### Service Logs Evidence
```json
{
  "timestamp": "2025-10-10T21:12:23.634124Z",
  "level": "INFO",
  "service": "websocket-ingestion",
  "message": "Weather enrichment service disabled",
  "reason": "no_api_key_or_disabled"
}
```

### Code Analysis
The weather enrichment service is properly implemented and integrated:

1. **Service Implementation**: ✅ `services/websocket-ingestion/src/weather_enrichment.py`
2. **Integration**: ✅ Properly integrated in `services/websocket-ingestion/src/main.py`
3. **Configuration**: ❌ Missing `WEATHER_API_KEY` environment variable

## 🛠️ **Fix Implementation**

### Step 1: Obtain OpenWeatherMap API Key

1. **Visit**: [OpenWeatherMap API](https://openweathermap.org/api)
2. **Sign up** for a free account
3. **Get API key** from: [API Keys Page](https://home.openweathermap.org/api_keys)
4. **Note**: Free tier provides:
   - 60 calls/minute
   - 1,000 calls/day
   - Perfect for development and small deployments

### Step 2: Configure Environment Variables

**Option A: Use Setup Script (Recommended)**
```powershell
.\scripts\setup-weather-config.ps1
```

**Option B: Manual Configuration**
1. Copy environment template:
   ```bash
   cp infrastructure/env.example .env
   ```

2. Edit `.env` file and update:
   ```bash
   # Weather API Configuration - REQUIRED FOR WEATHER ENRICHMENT
   WEATHER_API_KEY=your_actual_api_key_here
   WEATHER_API_URL=https://api.openweathermap.org/data/2.5
   WEATHER_DEFAULT_LOCATION=London,UK
   WEATHER_ENRICHMENT_ENABLED=true
   WEATHER_CACHE_MINUTES=15
   WEATHER_RATE_LIMIT_PER_MINUTE=50
   WEATHER_RATE_LIMIT_PER_DAY=900
   WEATHER_REQUEST_TIMEOUT=10
   
   # Enable weather service
   ENABLE_WEATHER_API=true
   ```

### Step 3: Restart Services

```bash
# Restart the websocket ingestion service
docker-compose restart websocket-ingestion

# Or restart all services
docker-compose restart
```

### Step 4: Verify Fix

1. **Check Service Logs**:
   ```bash
   docker-compose logs websocket-ingestion | Select-String -Pattern "weather" -CaseSensitive:$false
   ```

2. **Expected Log Output**:
   ```json
   {
     "level": "INFO",
     "message": "Weather enrichment service initialized",
     "operation": "weather_service_startup",
     "location": "London,UK"
   }
   ```

3. **Check Dashboard**: Visit `http://localhost:3000/`
   - Weather API Calls should start incrementing
   - Cache Hits should begin appearing
   - Weather Service should show active status

## 📊 **Expected Results After Fix**

### Dashboard Metrics
- **Weather API Calls**: Should show increasing numbers
- **Cache Hits**: Should show cache utilization
- **Weather Service**: Should remain "Enabled" and "healthy"

### Service Behavior
- Weather data will be fetched for each Home Assistant event
- Data will be cached for 15 minutes (configurable)
- Rate limiting will respect OpenWeatherMap quotas
- Fallback to cached data if API is unavailable

### Event Enrichment
Home Assistant events will be enriched with weather data:
```json
{
  "event_type": "state_changed",
  "data": {
    "entity_id": "sensor.temperature",
    "new_state": {...},
    "weather": {
      "temperature": 22.5,
      "humidity": 65,
      "description": "clear sky",
      "location": "London,UK"
    },
    "weather_enriched": true,
    "weather_location": "London,UK"
  }
}
```

## 🔧 **Configuration Options**

### Weather Service Settings
```bash
# Location for weather data
WEATHER_DEFAULT_LOCATION=London,UK

# Cache configuration
WEATHER_CACHE_MINUTES=15

# Rate limiting (respects OpenWeatherMap free tier)
WEATHER_RATE_LIMIT_PER_MINUTE=50
WEATHER_RATE_LIMIT_PER_DAY=900

# Request timeout
WEATHER_REQUEST_TIMEOUT=10

# Enable/disable enrichment
WEATHER_ENRICHMENT_ENABLED=true
```

### Advanced Configuration
```bash
# Use different weather API endpoint
WEATHER_API_URL=https://api.openweathermap.org/data/2.5

# Custom cache size
WEATHER_CACHE_SIZE=1000

# Fallback behavior
WEATHER_FALLBACK_TO_CACHE=true
```

## 🚨 **Troubleshooting**

### Issue: Still showing 0 API calls after configuration

**Check**:
1. Verify API key is correct in `.env`
2. Check service logs for errors
3. Ensure `WEATHER_ENRICHMENT_ENABLED=true`
4. Restart services after configuration changes

### Issue: API errors (401, 429)

**401 Unauthorized**:
- API key is missing or incorrect
- API key not yet activated (wait a few hours)

**429 Too Many Requests**:
- Rate limit exceeded
- Increase `WEATHER_CACHE_MINUTES` to reduce API calls

### Issue: Service not starting

**Check**:
1. Environment variables are properly set
2. No syntax errors in `.env` file
3. Docker services are running
4. Network connectivity to OpenWeatherMap API

## 📈 **Performance Optimization**

### Cache Strategy
- Weather data cached for 15 minutes by default
- Reduces API calls by ~96% (1 call per 15 minutes vs every event)
- Fallback to cached data if API unavailable

### Rate Limiting
- Configurable rate limits respect OpenWeatherMap quotas
- Automatic request throttling
- Error handling and retry logic

### Monitoring
- Dashboard shows real-time API call metrics
- Cache hit/miss ratios for optimization
- Error rates and response times

## 🎯 **Success Criteria**

✅ **Weather API Calls** > 0  
✅ **Cache Hits** > 0  
✅ **Weather Service** status = "Enabled" and "healthy"  
✅ **Service logs** show "Weather enrichment service initialized"  
✅ **Events** contain weather data in dashboard  

---

## 📞 **Support**

If you encounter issues:
1. Check service logs: `docker-compose logs websocket-ingestion`
2. Verify environment configuration
3. Test API key manually: `curl "https://api.openweathermap.org/data/2.5/weather?q=London,UK&appid=YOUR_API_KEY"`
4. Review this guide for troubleshooting steps
