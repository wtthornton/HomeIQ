# Entity Filtering System (Epic 45.2)

## Overview

The entity filtering system allows system administrators to configure which entities are captured and stored in InfluxDB, reducing storage costs by excluding low-value entities (battery levels, diagnostic sensors, etc.).

## Features

- **Opt-out mode (default)**: Include all entities except those matching filter patterns
- **Opt-in mode**: Include only entities matching filter patterns
- **Multiple filter types**: Entity ID patterns (regex/glob), domain, device class, area
- **Exception patterns**: Override filter rules for specific entities
- **Statistics tracking**: Monitor filter performance
- **Runtime configuration**: Reload filter config without service restart

## Configuration

### Environment Variable

Set `ENTITY_FILTER_CONFIG` as a JSON string:

```bash
ENTITY_FILTER_CONFIG='{"mode":"exclude","patterns":[{"entity_id":"sensor.*_battery"},{"device_class":"battery"}],"exceptions":[{"entity_id":"sensor.important_battery"}]}'
```

### Config File

Create `config/entity_filter.json`:

```json
{
  "mode": "exclude",
  "patterns": [
    {
      "entity_id": "sensor.*_battery"
    },
    {
      "domain": "diagnostic"
    },
    {
      "device_class": "battery"
    },
    {
      "area_id": "garage"
    }
  ],
  "exceptions": [
    {
      "entity_id": "sensor.important_battery"
    }
  ]
}
```

### Configuration Options

- **mode**: `"exclude"` (opt-out) or `"include"` (opt-in)
- **patterns**: List of filter patterns
  - `entity_id`: Glob pattern (e.g., `"sensor.*_battery"`)
  - `domain`: Exact domain match (e.g., `"diagnostic"`)
  - `device_class`: Exact device class match (e.g., `"battery"`)
  - `area_id`: Exact area ID match (e.g., `"garage"`)
- **exceptions**: List of exception patterns (always override filter)

## Filter Patterns

### Entity ID Patterns

Use glob patterns for entity IDs:
- `sensor.*_battery` - Matches all battery sensors
- `sensor.*_voltage` - Matches all voltage sensors
- `binary_sensor.*_motion` - Matches all motion binary sensors

### Domain Filtering

Filter by entity domain:
```json
{"domain": "diagnostic"}
```

### Device Class Filtering

Filter by device class:
```json
{"device_class": "battery"}
```

### Area Filtering

Filter by area/room:
```json
{"area_id": "garage"}
```

## Examples

### Exclude Battery Sensors

```json
{
  "mode": "exclude",
  "patterns": [
    {"entity_id": "sensor.*_battery"},
    {"device_class": "battery"}
  ]
}
```

### Include Only Sensor Domain

```json
{
  "mode": "include",
  "patterns": [
    {"domain": "sensor"}
  ]
}
```

### Exclude with Exceptions

```json
{
  "mode": "exclude",
  "patterns": [
    {"entity_id": "sensor.*_battery"}
  ],
  "exceptions": [
    {"entity_id": "sensor.important_battery"}
  ]
}
```

## API Endpoints

### Get Filter Statistics

```bash
GET /api/v1/filter/stats
```

Response:
```json
{
  "enabled": true,
  "statistics": {
    "filtered_count": 1234,
    "passed_count": 5678,
    "exception_count": 5,
    "total_processed": 6917,
    "filter_rate": 0.178,
    "uptime_seconds": 3600,
    "mode": "exclude",
    "patterns_count": 2,
    "exceptions_count": 1
  }
}
```

## Implementation Details

### Filter Application

The filter is applied in `websocket-ingestion` service before events are added to the batch processor:

1. Event received from Home Assistant
2. Event processed and validated
3. **Filter applied** (Epic 45.2)
4. If included, event added to batch
5. Batch written to InfluxDB

### Performance

- Filter checks are fast (<1ms per event)
- Regex patterns are compiled at startup
- Statistics tracked in-memory
- No external dependencies

## Best Practices

1. **Start with opt-out mode**: Include all entities, then exclude low-value ones
2. **Use specific patterns**: Prefer entity_id patterns over domain filters when possible
3. **Monitor statistics**: Check filter stats regularly to ensure desired behavior
4. **Use exceptions sparingly**: Only for truly important entities
5. **Test patterns**: Verify filter behavior before deploying to production

## Troubleshooting

### Filter Not Working

1. Check filter configuration is loaded:
   ```bash
   curl http://localhost:8001/api/v1/filter/stats
   ```

2. Verify patterns match entity IDs:
   - Check entity IDs in Home Assistant
   - Test patterns with regex tester

3. Check logs for filter initialization:
   ```
   Entity filter initialized: mode=exclude, patterns=2
   ```

### Too Many Entities Filtered

1. Review filter patterns
2. Add exceptions for important entities
3. Switch to opt-in mode if needed

### Filter Statistics Not Updating

1. Verify filter is enabled
2. Check events are being processed
3. Restart service if needed

## Related Documentation

- [Epic 45: Tiered Statistics Model](../prd/epic-45-tiered-statistics-model.md)
- [WebSocket Ingestion Service](../../services/websocket-ingestion/README.md)

