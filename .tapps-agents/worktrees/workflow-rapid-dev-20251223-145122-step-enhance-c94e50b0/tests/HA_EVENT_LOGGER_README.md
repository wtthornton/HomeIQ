# HA Event Logger - Baseline Measurement Tool

This simple test script connects directly to your Home Assistant instance and logs all incoming events to establish a baseline of expected event volume.

## Purpose

- **Establish Baseline**: Measure how many events your HA instance generates
- **Verify Connection**: Test direct HA WebSocket connectivity
- **Event Analysis**: See what types of events and entities are most active
- **Performance Planning**: Understand expected data volume for the ingestion system

## Quick Start

### 1. Set Your HA Access Token

**PowerShell:**
```powershell
$env:HA_ACCESS_TOKEN = "your_long_lived_access_token_here"
```

**Command Prompt:**
```cmd
set HA_ACCESS_TOKEN=your_long_lived_access_token_here
```

### 2. Run the Test

**PowerShell (Recommended):**
```powershell
.\tests\run_ha_event_logger.ps1
```

**Command Prompt:**
```cmd
tests\run_ha_event_logger.bat
```

**Direct Python:**
```bash
python tests/ha_event_logger.py
```

## Configuration Options

### Environment Variables

- `HA_ACCESS_TOKEN` - **Required** - Your HA long-lived access token
- `HA_WEBSOCKET_URL` - Default: `ws://homeassistant.local:8123/api/websocket`
- `LOG_DURATION_MINUTES` - Default: `5` minutes

### PowerShell Parameters

```powershell
.\tests\run_ha_event_logger.ps1 -HaUrl "ws://your-ha:8123/api/websocket" -DurationMinutes 10 -HaToken "your_token"
```

## Sample Output

```
🔍 HA Event Logger - Baseline Measurement Tool
============================================================
🔗 HA URL: ws://homeassistant.local:8123/api/websocket
⏱️  Duration: 5 minutes
📊 This will establish baseline event volume from your HA instance

🚀 Starting HA Event Logger...
2025-01-06 13:45:00 - INFO - ✅ Connected to Home Assistant successfully
2025-01-06 13:45:01 - INFO - 📨 [13:45:01.123] Event #1: state_changed
2025-01-06 13:45:01 - INFO -    🏠 Entity: sensor.temperature_living_room
2025-01-06 13:45:02 - INFO - 📨 [13:45:02.456] Event #2: state_changed
2025-01-06 13:45:02 - INFO -    🏠 Entity: light.kitchen_ceiling
...

============================================================
📊 EVENT LOGGING SUMMARY
============================================================
⏱️  Duration: 0:05:00
📨 Total Events: 247
📈 Events per minute: 49.4
📈 Events per second: 0.82

🏷️  Event Types:
   state_changed: 198 (80.2%)
   automation_triggered: 23 (9.3%)
   service_executed: 15 (6.1%)
   scene_reloaded: 8 (3.2%)
   config_entry_reloaded: 3 (1.2%)

🏠 Top Entities:
   sensor.temperature_living_room: 45 (18.2%)
   light.kitchen_ceiling: 23 (9.3%)
   binary_sensor.motion_detector: 18 (7.3%)
   switch.coffee_maker: 12 (4.9%)
   sensor.humidity_bathroom: 11 (4.5%)
============================================================
```

## What This Tells Us

### Event Volume Baseline
- **Events per minute**: How active your HA instance is
- **Events per second**: Peak processing requirements
- **Total events**: Expected daily/hourly volume

### Event Type Distribution
- **state_changed**: Most common, represents entity state updates
- **automation_triggered**: Shows automation activity
- **service_executed**: API/service calls
- **scene_reloaded**: Configuration changes

### Entity Activity
- **Most active entities**: Which devices/sensors generate the most events
- **Event patterns**: Helps identify high-frequency vs low-frequency entities

## Integration with HA Ingestor

This baseline helps you:

1. **Validate Ingestor Performance**: Compare actual ingestion rates with baseline
2. **Tune Processing**: Adjust batch sizes and processing intervals
3. **Capacity Planning**: Estimate storage and processing requirements
4. **Debug Data Flow**: Identify if events are being lost or delayed

## Troubleshooting

### Connection Issues
- Verify HA is accessible at the specified URL
- Check that the access token is valid and has WebSocket permissions
- Ensure HA WebSocket API is enabled

### No Events
- Some HA instances have very low activity
- Try increasing the duration to 10-15 minutes
- Check if your HA has automations or active sensors

### Permission Errors
- Ensure the access token has appropriate permissions
- Try creating a new long-lived access token in HA

## Files Generated

- `ha_events.log` - Detailed event log file
- Console output - Real-time event summary
- Summary report - Final statistics and analysis
