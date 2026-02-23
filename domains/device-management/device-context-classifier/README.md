# Device Context Classifier Service

Phase 2.1: Classify devices based on entity patterns.

## Overview

This service analyzes entities to infer device types:
- Fridge: temperature sensors + door sensor + light
- Car: location + battery + charging status
- 3D Printer: temperature + progress + status
- Thermostat: temperature + humidity + mode
- And more...

## Configuration

Environment variables:
- `DEVICE_CONTEXT_CLASSIFIER_PORT`: Service port (default: 8020, external: 8032)
- `HA_URL`: Home Assistant URL
- `HA_TOKEN`: Home Assistant access token
- `LOG_LEVEL`: Logging level (default: info)
- `RELOAD`: Enable auto-reload (default: false)

## Integration

This service is used by data-api to classify devices and update the Device model with device_type and device_category.

