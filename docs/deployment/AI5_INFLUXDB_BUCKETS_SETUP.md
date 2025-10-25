# InfluxDB Buckets Setup for Epic AI-5

**Epic:** AI-5 - Incremental Pattern Processing Architecture  
**Story:** AI5.1 - Multi-Layer Storage Design & Schema  
**Date:** October 24, 2025

---

## Overview

Epic AI-5 requires two new InfluxDB buckets for pattern aggregates:

1. **pattern_aggregates_daily** - Daily pattern aggregates (90-day retention)
2. **pattern_aggregates_weekly** - Weekly/monthly aggregates (365-day retention)

---

## Bucket Specifications

### Layer 2: Daily Aggregates

**Bucket Name:** `pattern_aggregates_daily`  
**Retention:** 90 days  
**Organization:** homeiq  
**Description:** Daily pattern aggregates for 10 detector types

**Measurements:**
- `time_based_daily` - TimeOfDayPatternDetector
- `co_occurrence_daily` - CoOccurrencePatternDetector
- `sequence_daily` - SequenceDetector
- `room_based_daily` - RoomBasedDetector
- `duration_daily` - DurationDetector
- `anomaly_daily` - AnomalyDetector

**Estimated Size:** ~9K records (90 days × 10 detectors × ~10 records/day)

---

### Layer 3: Weekly/Monthly Aggregates

**Bucket Name:** `pattern_aggregates_weekly`  
**Retention:** 365 days (52 weeks)  
**Organization:** homeiq  
**Description:** Weekly and monthly pattern aggregates for long-term analysis

**Measurements:**
- `session_weekly` - SessionDetector
- `day_type_weekly` - DayTypeDetector
- `contextual_monthly` - ContextualDetector
- `seasonal_monthly` - SeasonalDetector

**Estimated Size:** ~1K records (52 weeks × 4 detectors × ~5 records/week)

---

## Setup Methods

### Method 1: Automated Script (Recommended)

Use the provided setup script:

```bash
# Set environment variables
export INFLUXDB_URL="http://localhost:8086"
export INFLUXDB_TOKEN="homeiq-token"
export INFLUXDB_ORG="homeiq"

# Run setup script
bash scripts/setup_influxdb_ai5_buckets.sh
```

### Method 2: Manual via InfluxDB UI

1. Navigate to InfluxDB UI: http://localhost:8086
2. Go to Load Data → Buckets
3. Click "Create Bucket"
4. Enter bucket details:
   - **Name:** `pattern_aggregates_daily`
   - **Retention Period:** 90 days
   - **Organization:** homeiq
5. Click "Create"
6. Repeat for `pattern_aggregates_weekly` (365-day retention)

### Method 3: InfluxDB CLI

```bash
# Create daily aggregates bucket
influx bucket create \
  --name pattern_aggregates_daily \
  --org homeiq \
  --retention 90d

# Create weekly aggregates bucket
influx bucket create \
  --name pattern_aggregates_weekly \
  --org homeiq \
  --retention 365d
```

### Method 4: InfluxDB API

```bash
# Get organization ID
ORG_ID=$(influx org find -n homeiq --json | jq -r '.[0].id')

# Create daily bucket
curl -X POST http://localhost:8086/api/v2/buckets \
  -H "Authorization: Token homeiq-token" \
  -H "Content-Type: application/json" \
  -d '{
    "orgID": "'$ORG_ID'",
    "name": "pattern_aggregates_daily",
    "description": "Daily pattern aggregates (Epic AI-5)",
    "retentionRules": [{"type": "expire", "everySeconds": 7776000}]
  }'

# Create weekly bucket
curl -X POST http://localhost:8086/api/v2/buckets \
  -H "Authorization: Token homeiq-token" \
  -H "Content-Type: application/json" \
  -d '{
    "orgID": "'$ORG_ID'",
    "name": "pattern_aggregates_weekly",
    "description": "Weekly/monthly aggregates (Epic AI-5)",
    "retentionRules": [{"type": "expire", "everySeconds": 31536000}]
  }'
```

---

## Verification

After creating buckets, verify they exist:

```bash
# List all buckets
influx bucket list

# Or via InfluxDB UI
# Navigate to Load Data → Buckets
```

Expected output:
```
pattern_aggregates_daily    90d     homeiq
pattern_aggregates_weekly   365d    homeiq
```

---

## Integration

Once buckets are created, the `PatternAggregateClient` can be used:

```python
from clients.pattern_aggregate_client import PatternAggregateClient

# Initialize client
client = PatternAggregateClient(
    url="http://influxdb:8086",
    token="homeiq-token",
    org="homeiq",
    bucket_daily="pattern_aggregates_daily",
    bucket_weekly="pattern_aggregates_weekly"
)

# Write daily aggregate
client.write_time_based_daily(
    date="2025-10-24",
    entity_id="light.living_room",
    domain="light",
    hourly_distribution=[0, 0, 0, 0, 0, 2, 5, 8, 12, 15, 18, 20, 22, 25, 28, 30, 25, 20, 15, 10, 5, 2, 1, 0],
    peak_hours=[8, 9, 10, 14, 15, 16, 19, 20],
    frequency=12.5,
    confidence=0.85,
    occurrences=300
)
```

---

## Troubleshooting

### Bucket Already Exists
If you see "bucket already exists" error:
- Bucket may have been created previously
- Verify with `influx bucket list`
- Use existing bucket or delete and recreate

### Permission Denied
If you see "permission denied" error:
- Verify token has write permissions
- Check organization is correct
- Ensure InfluxDB API is accessible

### Connection Refused
If you see "connection refused" error:
- Verify InfluxDB is running: `docker ps | grep influxdb`
- Check InfluxDB URL is correct
- Ensure network access to InfluxDB container

---

## Next Steps

After buckets are created:

1. ✅ Verify buckets exist
2. Run integration tests with PatternAggregateClient
3. Begin Story AI5.3: Convert detectors to incremental processing
4. Monitor storage usage in InfluxDB UI

---

**Document Status:** Complete  
**Created:** October 24, 2025  
**Last Updated:** October 24, 2025
