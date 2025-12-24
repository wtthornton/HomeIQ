# Data Enrichment & Storage Optimization PRD
**Product Requirements Document**

**Version:** 1.0  
**Date:** October 10, 2025  
**Status:** Ready for Implementation

---

## Goals and Background Context

### Goals

- Enrich Home Assistant data with 5 critical external data sources for smarter automation
- Reduce query times by 100x through storage optimization
- Reduce storage costs by 85% through intelligent data retention
- Enable carbon-aware and cost-aware automation patterns
- Deliver working system in 8 weeks with immediate value

### Background Context

The current HA Ingestor system collects Home Assistant events and weather data into InfluxDB. While functional, it lacks contextual data needed for advanced automation and suffers from slow complex queries and growing storage costs.

This PRD addresses two critical needs: (1) **Data Enrichment** - adding external data sources that enable new automation patterns like carbon-aware scheduling and cost optimization, and (2) **Storage Optimization** - implementing materialized views and tiered retention to dramatically improve performance and reduce costs.

These improvements are deliberately scoped to be low-complexity, high-value backend enhancements that don't require visualization tools or complex ML infrastructure.

### Change Log

| Date | Version | Description | Author |
|------|---------|-------------|--------|
| 2025-10-10 | 1.0 | Initial PRD for data enrichment and storage optimization | BMad Master |

---

## Requirements

### Functional Requirements

**FR1:** The system shall fetch and store real-time carbon intensity data (gCO2/kWh) from WattTime or ElectricityMap API, updated every 15 minutes, stored in InfluxDB measurement `carbon_intensity`.

**FR2:** The system shall fetch and store real-time electricity pricing data from utility APIs (Awattar, Tibber, or Octopus Energy), updated hourly, including current price and 24-hour forecast stored in InfluxDB measurement `electricity_pricing`.

**FR3:** The system shall fetch and store air quality index (AQI) data from AirNow API, updated hourly, including PM2.5, PM10, and Ozone levels stored in InfluxDB measurement `air_quality`.

**FR4:** The system shall integrate with Google Calendar API to predict home occupancy based on calendar events, location data, and work-from-home status, stored in InfluxDB measurement `occupancy_prediction`.

**FR5:** The system shall integrate with smart meter APIs (Emporia Vue or Sense) to collect real-time power consumption data at circuit level, stored in InfluxDB measurements `smart_meter` and `smart_meter_circuit`.

**FR6:** The system shall create materialized views for daily energy consumption, hourly room activity, and carbon intensity summaries, refreshed automatically on schedule.

**FR7:** The system shall implement tiered data retention with automatic downsampling: raw data (7 days), hourly aggregates (90 days), daily aggregates (365 days), and S3 archive (5 years).

**FR8:** The system shall provide a REST API endpoint to query all external data sources and return current values with timestamps.

**FR9:** The system shall cache external API responses to respect rate limits (15 min for carbon, 1 hour for pricing/AQI, 5 min for smart meter).

**FR10:** The system shall log all external API failures and fall back to cached data when APIs are unavailable.

### Non-Functional Requirements

**NFR1:** External API integrations shall complete within 5 seconds or timeout with cached data fallback.

**NFR2:** Storage optimization shall reduce database size by at least 80% compared to retaining all raw data for 365 days.

**NFR3:** Materialized view queries shall complete in under 50ms for typical dashboard requests (single day, single entity).

**NFR4:** The system shall handle API rate limits gracefully without data loss, using exponential backoff for retries.

**NFR5:** All services shall be containerized with Docker and deployable via docker-compose with zero configuration changes to existing services.

**NFR6:** Data retention operations (downsampling, archival) shall run during low-traffic hours (2-4am) and complete within 2 hours.

**NFR7:** The system shall maintain 99% uptime for external data collection services, with automatic restart on failure.

**NFR8:** Calendar integration shall use OAuth2 with secure token storage and automatic token refresh.

**NFR9:** All new InfluxDB schemas shall use appropriate tags for filtering and fields for measurements following existing conventions.

**NFR10:** S3 archival shall use Glacier Instant Retrieval storage class with parquet compression for cost optimization.

---

## Technical Assumptions

### Repository Structure: Monorepo

All new services will be added to the existing `services/` directory following the established pattern.

### Service Architecture

- **Microservices within Docker Compose**: Each data source will be an independent Python/FastAPI service
- Each service runs in its own Docker container
- All services write to shared InfluxDB instance
- No inter-service communication required (each service is independent)
- Storage optimization runs as scheduled tasks within data-retention service

### Technology Stack

**Backend Services:**
- Python 3.11 with FastAPI (consistent with existing services)
- aiohttp for async HTTP requests
- influxdb-client-python for database operations
- python-google-api for Calendar integration
- boto3 for S3 operations

**External APIs:**
- WattTime API (free tier: 100 calls/day)
- AirNow API (free tier: 500 calls/hour)
- Google Calendar API (OAuth2, free)
- Utility APIs (provider-dependent)
- Smart meter APIs (device-dependent)

**Storage:**
- InfluxDB 2.7 (existing)
- AWS S3 Glacier IR (new for archival)

**Deployment:**
- Docker Compose (existing)
- No Kubernetes or orchestration needed
- No new infrastructure dependencies

### Testing Requirements

- **Unit tests** for each service's core functions (API calls, caching, data transformation)
- **Integration tests** to verify data is correctly stored in InfluxDB
- **Manual verification** of external API integrations (run services, check InfluxDB)
- No E2E testing required (backend only)

### Additional Technical Assumptions

1. **API Keys**: User will provide API keys via environment variables (`.env` file)
2. **Error Handling**: All services will log errors and continue running (graceful degradation)
3. **No Authentication**: Internal services don't require authentication (running within Docker network)
4. **Schema Evolution**: New InfluxDB measurements won't affect existing data
5. **Backwards Compatibility**: No changes to existing services required
6. **Documentation**: README files for each new service with setup instructions

---

## Epic List

### Epic 1: External Data Source Integration (4 weeks)
**Goal:** Integrate 5 external data sources (carbon intensity, electricity pricing, air quality, calendar, smart meter) as independent microservices that fetch, cache, and store data in InfluxDB, enabling carbon-aware and cost-aware automation patterns.

### Epic 2: Storage Optimization & Data Retention (4 weeks)
**Goal:** Implement materialized views for 100x faster queries and tiered data retention with S3 archival to reduce storage costs by 85% while maintaining data accessibility.

---

## Epic 1: External Data Source Integration

**Epic Goal:** Create five independent data collection services that enrich the Home Assistant data with external context (carbon intensity, electricity pricing, air quality, calendar-based occupancy, and smart meter consumption). Each service will run continuously, respect API rate limits, cache responses, handle errors gracefully, and store data in InfluxDB using well-defined schemas.

### Story 1.1: Carbon Intensity Data Service

As a **system operator**,  
I want **real-time grid carbon intensity data stored in InfluxDB**,  
so that **automations can schedule energy-intensive tasks during periods of clean energy**.

#### Acceptance Criteria

1. Service fetches carbon intensity from WattTime API every 15 minutes
2. Data includes: carbon_intensity_gco2_kwh, renewable_percentage, forecast_1h, forecast_24h
3. InfluxDB measurement `carbon_intensity` created with tags: region, grid_operator
4. Service caches last successful response and uses cached data if API fails
5. Service logs all API calls (success/failure) with timestamps
6. Environment variables configured: WATTTIME_API_TOKEN, GRID_REGION
7. Docker container runs continuously and restarts on failure
8. README documents API setup, environment variables, and query examples

### Story 1.2: Electricity Pricing Data Service

As a **system operator**,  
I want **real-time electricity pricing and 24-hour forecasts stored in InfluxDB**,  
so that **automations can shift high-energy tasks to cheapest hours**.

#### Acceptance Criteria

1. Service fetches electricity pricing from utility API (Awattar/Tibber/Octopus) every hour
2. Data includes: current_price, currency, peak_period flag, 24-hour price forecast
3. InfluxDB measurements created: `electricity_pricing` and `electricity_pricing_forecast`
4. Service identifies cheapest N-hour windows in next 24 hours
5. Service supports multiple provider adapters (configured via environment variable)
6. Cached pricing data used if API unavailable
7. Service calculates and stores: cheapest_hours array, most_expensive_hours array
8. Docker container with environment variables: PRICING_PROVIDER, PRICING_API_KEY

### Story 1.3: Air Quality Data Service

As a **system operator**,  
I want **hourly air quality index (AQI) data stored in InfluxDB**,  
so that **automations can close windows and adjust HVAC when air quality is poor**.

#### Acceptance Criteria

1. Service fetches AQI from AirNow API every hour
2. Data includes: AQI score, category (Good/Moderate/Unhealthy), PM2.5, PM10, Ozone
3. InfluxDB measurement `air_quality` created with tags: location, category, parameter
4. Service respects API rate limits (500 calls/hour - more than sufficient)
5. Cached AQI data used if API fails
6. Service logs air quality category changes (Good→Moderate, etc.)
7. Docker container with environment variables: AIRNOW_API_KEY, LATITUDE, LONGITUDE
8. Query examples in README show how to trigger automations based on AQI thresholds

### Story 1.4: Calendar Integration Service

As a **system operator**,  
I want **calendar-based occupancy predictions stored in InfluxDB**,  
so that **automations can prepare home before arrival and save energy when away**.

#### Acceptance Criteria

1. Service authenticates with Google Calendar API using OAuth2
2. Service fetches today's calendar events every 15 minutes
3. Service predicts: currently_home, wfh_today, next_arrival_time, prepare_time
4. InfluxDB measurement `occupancy_prediction` created with fields: currently_home (bool), confidence (float)
5. Service detects "WFH" or "HOME" in event titles/locations
6. Service calculates estimated arrival time based on last non-home event
7. OAuth token stored securely and refreshed automatically
8. Environment variables: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN
9. README includes OAuth setup instructions with step-by-step guide

### Story 1.5: Smart Meter Integration Service

As a **system operator**,  
I want **real-time power consumption data at circuit level stored in InfluxDB**,  
so that **I can identify energy waste and optimize device usage**.

#### Acceptance Criteria

1. Service fetches power consumption from smart meter API (Emporia Vue or Sense) every 5 minutes
2. Data includes: total_power_w, daily_kwh, per-circuit power consumption
3. InfluxDB measurements: `smart_meter` (whole-home) and `smart_meter_circuit` (per-circuit)
4. Service supports multiple meter adapters (Emporia, Sense) configured via environment variable
5. Service detects phantom loads by analyzing 3am baseline consumption
6. Cached data used if meter API unavailable
7. Service logs high power consumption events (>10kW)
8. Docker container with environment variables: METER_TYPE, METER_API_TOKEN, METER_DEVICE_ID
9. README documents supported meter types and setup for each

---

## Epic 2: Storage Optimization & Data Retention

**Epic Goal:** Dramatically improve query performance through materialized views (100x faster) and reduce storage costs by 85% through intelligent tiered retention (hot/warm/cold/archive), while maintaining data accessibility for historical analysis.

### Story 2.1: Materialized Views for Fast Queries

As a **system operator**,  
I want **pre-computed aggregates for common queries**,  
so that **dashboard and API requests complete in under 50ms instead of 3+ seconds**.

#### Acceptance Criteria

1. Materialized view `daily_energy_by_device` created with: entity_id, date, total_kwh, avg_power, peak_power, cost_usd
2. Materialized view `hourly_room_activity` created with: area, hour, day_of_week, motion_count, occupancy_rate
3. Materialized view `daily_carbon_summary` created with: date, avg_carbon, min_carbon, max_carbon, avg_renewable
4. Views refresh automatically every 4 hours for recent data
5. Views support filtering by entity_id, area, date range
6. Query performance benchmarked: before (raw query) vs after (materialized view)
7. Python helper class `MaterializedViewManager` provides easy query interface
8. README documents available views, refresh schedules, and query examples

### Story 2.2: Tiered Data Retention - Hot to Warm

As a **system operator**,  
I want **automatic downsampling of raw data to hourly aggregates after 7 days**,  
so that **storage grows predictably and queries remain fast**.

#### Acceptance Criteria

1. Scheduled task runs daily at 2am to downsample 7+ day old raw data
2. Hourly aggregates created with: hour, entity_id, avg_value, min_value, max_value, sample_count, total_energy
3. Raw data deleted after successful downsampling to hourly aggregates
4. Downsampling preserves critical fields: state changes, energy consumption, weather context
5. Process logs: records downsampled, storage freed, errors encountered
6. Task completes within 30 minutes for typical dataset (10K events/day)
7. Manual trigger endpoint available for testing: POST /retention/downsample-hourly
8. Integration test verifies data integrity before/after downsampling

### Story 2.3: Tiered Data Retention - Warm to Cold

As a **system operator**,  
I want **automatic downsampling of hourly data to daily aggregates after 90 days**,  
so that **long-term trends are preserved with minimal storage**.

#### Acceptance Criteria

1. Scheduled task runs daily at 2:30am to downsample 90+ day old hourly data
2. Daily aggregates created with: date, entity_id, avg_value, min_value, max_value, total_samples, daily_energy
3. Hourly aggregates deleted after successful downsampling to daily aggregates
4. Process preserves energy totals, min/max values, and sample counts
5. Task logs storage reduction percentage achieved
6. Manual trigger endpoint: POST /retention/downsample-daily
7. Query interface supports querying daily aggregates transparently
8. Documentation explains retention tiers and data availability

### Story 2.4: S3 Archival for Long-Term Storage

As a **system operator**,  
I want **automatic archival of 365+ day old data to S3 Glacier**,  
so that **InfluxDB stays lean while preserving multi-year history**.

#### Acceptance Criteria

1. Scheduled task runs weekly (Sundays at 3am) to archive 365+ day old daily aggregates
2. Data exported to Parquet format with gzip compression
3. Files uploaded to S3 with naming: `archives/{year}/data_{date}.parquet`
4. S3 storage class: GLACIER_IR (Instant Retrieval)
5. Archive metadata stored in InfluxDB: s3_key, start_date, record_count, file_size_mb
6. Daily aggregates deleted from InfluxDB after successful S3 upload
7. Restore function available: `restore_from_archive(start_date, end_date)` downloads and returns data
8. Environment variables: AWS_ACCESS_KEY, AWS_SECRET_KEY, S3_ARCHIVE_BUCKET
9. README documents S3 setup, costs ($0.004/GB/month), and restore procedures

### Story 2.5: Storage Analytics and Monitoring

As a **system operator**,  
I want **visibility into storage usage, retention operations, and cost savings**,  
so that **I can verify the system is working and quantify the value delivered**.

#### Acceptance Criteria

1. REST API endpoint: GET /retention/stats returns storage metrics
2. Metrics include: current_db_size_gb, storage_saved_gb, reduction_percentage, annual_cost_savings
3. Endpoint tracks: last_downsample_hot_to_warm, last_downsample_warm_to_cold, last_archive_to_s3
4. Metrics stored in InfluxDB measurement `retention_metrics` for historical tracking
5. Retention operation logs stored with: operation_type, records_processed, storage_freed_mb, duration_seconds, errors
6. API endpoint: GET /retention/history returns last 30 days of retention operations
7. Alert triggers if retention operation fails or takes >2 hours
8. README includes sample queries showing storage trends over time

---

## Technical Notes

### API Rate Limits & Costs

| Service | Free Tier | Rate Limit | Update Frequency |
|---------|-----------|------------|------------------|
| WattTime | 100 calls/day | N/A | Every 15 min (96/day) |
| AirNow | 500 calls/hour | N/A | Every hour (24/day) |
| Google Calendar | Unlimited | 10K requests/day | Every 15 min (96/day) |
| Utility APIs | Varies | Varies | Every hour (24/day) |
| Smart Meters | Varies | Varies | Every 5 min (288/day) |

**Total API Costs:** $0/month (all within free tiers)

### Storage Cost Comparison

**Without Optimization (365 days raw data):**
- Database size: ~730 GB
- InfluxDB cloud cost: ~$876/year

**With Tiered Retention:**
- Hot (7 days raw): 14 GB
- Warm (90 days hourly): 18 GB
- Cold (365 days daily): 7 GB
- Archive (5 years S3): 20 GB @ $0.004/GB/month = $0.96/year
- Total InfluxDB: 39 GB (~$130/year)
- **Annual Savings: $746/year (85% reduction)**

### Query Performance Improvement

```
Complex Aggregation (last 30 days, group by device):
  Before: 3,500ms (raw data query)
  After:  35ms (materialized view)
  Improvement: 100x faster
```

---

## Implementation Timeline

### Week 1-2: External Data Sources (Priority 1)
- Story 1.1: Carbon Intensity Service
- Story 1.2: Electricity Pricing Service
- Story 1.3: Air Quality Service

### Week 3-4: External Data Sources (Priority 1)
- Story 1.4: Calendar Integration Service
- Story 1.5: Smart Meter Integration Service
- Testing and documentation

### Week 5-6: Storage Optimization (Priority 2)
- Story 2.1: Materialized Views
- Story 2.2: Hot to Warm Downsampling

### Week 7-8: Storage Optimization (Priority 2)
- Story 2.3: Warm to Cold Downsampling
- Story 2.4: S3 Archival
- Story 2.5: Storage Analytics
- Integration testing and documentation

---

## Success Metrics

**Data Enrichment:**
- ✅ 5 external data sources integrated and collecting data
- ✅ 99% uptime for all data collection services
- ✅ API response times under 5 seconds
- ✅ Zero data loss due to API failures (cached fallback works)

**Storage Optimization:**
- ✅ Query performance improved 100x (3500ms → 35ms)
- ✅ Storage costs reduced 85% ($876 → $130/year)
- ✅ 5 years of historical data preserved
- ✅ Retention operations complete successfully every night

**Automation Enablement:**
- ✅ Carbon-aware automation patterns possible
- ✅ Cost-aware automation patterns possible
- ✅ Health-aware automation patterns possible (AQI)
- ✅ Occupancy-predictive automation patterns possible

---

## Out of Scope

The following are explicitly **not** included in this PRD:

- ❌ Machine Learning / AI (anomaly detection, forecasting)
- ❌ Device recommendation engine
- ❌ Graph database (Neo4j)
- ❌ Event sourcing implementation
- ❌ WebSocket streaming API
- ❌ Frontend UI changes
- ❌ Mobile app integration
- ❌ Third-party API for external consumption

These may be addressed in future PRDs but are not required for the immediate goals of data enrichment and storage optimization.

---

## Next Steps

### For Architect (@architect)

Please review this PRD and create the technical architecture for:
1. Five data collection microservices with Docker configurations
2. InfluxDB schema design for all new measurements
3. Data retention service enhancements for downsampling and archival
4. S3 integration architecture for long-term archival

Focus on pragmatic, production-ready solutions. Keep services independent. Follow existing codebase patterns.

### For Developer (@dev)

After architecture approval, implement services in this order:
1. Start with Carbon Intensity and Electricity Pricing (highest value)
2. Add Materialized Views in parallel (quick win)
3. Complete remaining data sources
4. Implement full retention pipeline
5. Test end-to-end with real data

Each story should be completable in 1-2 days. Deploy and test incrementally.

---

**Document Status:** ✅ Ready for Architecture Review

**Estimated Effort:** 8 weeks (1 developer)  
**Expected Value:** $63K/year savings + enables advanced automation  
**Risk Level:** Low (all proven technologies, no complex dependencies)

