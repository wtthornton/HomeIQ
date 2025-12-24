# Epic 31: Weather API Service Migration - SIMPLE

## Epic Goal

Migrate weather to standalone service (Port 8009) matching carbon-intensity and air-quality patterns - NO over-engineering.

## Epic Description

### Current Problem

Weather is the ONLY external API embedded in events. All others are standalone services.

### Simple Solution

Create weather-api service following **carbon-intensity-service pattern** (single-file, ~250 lines).

### Stories (SIMPLIFIED)

1. **Story 31.1:** Foundation ✅ COMPLETE
   - FastAPI service with main.py + health_check.py only
   - Docker deployment
   - ~12 files, 800 lines

2. **Story 31.2:** Data Collection ✅ COMPLETE (in main.py)
   - Fetch from OpenWeatherMap
   - Simple cache (dict + timestamp)
   - InfluxDB writes
   - Background loop
   - ~100 lines added to main.py

3. **Story 31.3:** Endpoints ✅ COMPLETE (in main.py)
   - GET /current-weather
   - GET /cache/stats
   - WeatherResponse model
   - ~30 lines added to main.py

4. **Story 31.4:** Disable Enrichment ✅ COMPLETE
   - Comment out weather_enrichment in websocket-ingestion
   - Set WEATHER_ENRICHMENT_ENABLED=false
   - ~6 lines changed

5. **Story 31.5:** Dashboard Widget ⏳ PENDING
   - Add simple weather card to DataSourcesTab
   - Inline fetch (no separate API module)
   - ~50 lines

**TOTAL:** One main.py file (~300 lines), simple dashboard changes

## Compatibility Requirements

- [x] Historical data preserved (no migration)
- [x] Single-file pattern (like carbon/air-quality)
- [x] No complex abstractions

## Definition of Done

- [x] weather-api service running on Port 8009
- [x] Weather enrichment disabled
- [ ] Dashboard shows weather widget
- [x] All in ~400 total lines of code (not 4,500!)

---

**Created:** October 19, 2025  
**Pattern:** Simple single-file service (carbon-intensity template)  
**Status:** 80% Complete (4/5 stories done)
