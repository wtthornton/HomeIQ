# Device Intelligence Database Updates Guide

This guide explains the database schema changes and how to apply them.

## Overview

The Device Intelligence Service database schema has been enhanced with new fields to support richer device metadata. The changes fix issues where manufacturer, model, and integration fields were showing as "Unknown".

## Schema Changes

### New Fields Added to Devices Table

1. **device_class** (String, indexed)
   - Device type classification (light, sensor, switch, etc.)
   - Automatically extracted from entity domains

2. **config_entry_id** (String, indexed)
   - Home Assistant config entry ID
   - Links device to HA configuration

3. **connections_json** (Text)
   - Physical connections (MAC, IP, etc.) as JSON string
   - Stores device connection information

4. **identifiers_json** (Text)
   - Device identifiers as JSON string
   - Important for Zigbee and other integrations

5. **zigbee_ieee** (String, indexed)
   - IEEE address for Zigbee devices
   - Unique identifier for Zigbee devices

6. **is_battery_powered** (Boolean)
   - Power source indicator
   - Automatically determined from power_source field

### Fixes Applied

1. **area_name** storage - Now properly stored in database (was calculated but never saved)
2. **integration** logic - Fixed to use proper null check instead of `or`
3. **device_class** extraction - Automatically extracted from entity domains or Zigbee capabilities

## How to Apply Updates

### Option 1: Using the Python Script (Recommended)

1. Run the recreate database script:
   ```bash
   cd services/device-intelligence-service
   python scripts/recreate_database.py
   ```

2. This will:
   - Drop all existing tables
   - Recreate tables with the new schema
   - Preserve database connection settings

### Option 2: Using the API Endpoint

1. Start the service:
   ```bash
   cd services/device-intelligence-service
   python -m src.main
   ```

2. Call the recreate tables endpoint:
   ```bash
   curl -X POST http://localhost:8007/api/admin/database/recreate-tables
   ```

3. Restart the service if needed

### Option 3: Manual Database Recreation

1. Start the service with database initialization
2. The tables will be automatically created on first startup
3. For existing databases, manually drop and recreate tables

## After Applying Updates

1. **Restart the service** to pick up the new schema

2. **Run discovery** to populate devices with new fields:
   ```bash
   # Trigger discovery via API
   curl -X POST http://localhost:8007/api/discovery/force-refresh
   ```

3. **Verify data** by querying the database:
   ```sql
   SELECT name, manufacturer, model, integration, area_name, device_class, is_battery_powered
   FROM devices
   LIMIT 10;
   ```

## Expected Results

After running discovery with the updated schema:

- ✅ `manufacturer` = actual manufacturer or "Unknown" if not in HA
- ✅ `model` = actual model number or "Unknown" if not in HA
- ✅ `integration` = correct integration name (e.g., "hue") or "unknown" if not in HA
- ✅ `area_name` = correct area name (e.g., "office") or NULL if not set
- ✅ `device_class` = device type (e.g., "light", "sensor")
- ✅ `is_battery_powered` = true/false based on power source
- ✅ `config_entry_id` = HA config entry ID (when available)
- ✅ `connections_json` = Physical connections as JSON (when available)
- ✅ `identifiers_json` = Device identifiers as JSON (when available)

## Debug Logging

To see what Home Assistant actually returns for devices, check the logs for:

```
Device {name}: manufacturer={manufacturer}, integration={integration}
```

This debug logging will help diagnose why some devices show "Unknown" values.

## Files Modified

1. `src/clients/ha_client.py` - Added debug logging
2. `src/core/device_parser.py` - Added device class extraction
3. `src/core/discovery_service.py` - Fixed storage logic
4. `src/models/database.py` - Enhanced schema
5. `src/core/database.py` - Added recreate_tables function
6. `src/main.py` - Added database management API
7. `src/api/database_management.py` - New database management endpoints

## Important Notes

1. **Data Loss Warning**: Recreating tables will DELETE ALL existing data
2. **Backup First**: Always backup your database before recreating tables
3. **Development Only**: Table recreation is primarily for development and schema migrations
4. **Production**: Use proper migration tools in production environments

## Troubleshooting

If you encounter errors:

1. Check that the database file exists and is writable
2. Ensure the service has proper permissions
3. Verify all dependencies are installed
4. Check logs for specific error messages
5. Try the API status endpoint: `GET /api/admin/database/status`

## Support

For issues or questions:
- Check the implementation document: `implementation/DEVICE_INTELLIGENCE_FIELDS_IMPLEMENTATION.md`
- Review the analysis document: `implementation/analysis/DEVICE_INTELLIGENCE_FIELD_POPULATION_ANALYSIS.md`
- Examine the plan: `fix-device-intelligence-fields.plan.md`

