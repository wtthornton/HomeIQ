# API Key Validation Tests

This directory contains comprehensive tests for validating API keys and tokens used by the HA Ingestor system.

## Test Script: `test_api_keys.py`

A comprehensive local testing script that validates:
- Home Assistant API tokens
- Weather API keys (OpenWeatherMap)
- Environment variable configuration
- Actual API connectivity

### Usage

#### Basic Usage
```bash
# Run tests with environment variables from .env file
python tests/test_api_keys.py

# Run with verbose output
python tests/test_api_keys.py --verbose

# Run with specific environment file
python tests/test_api_keys.py --env-file .env.production
```

#### Override Specific Values
```bash
# Test with specific Home Assistant configuration
python tests/test_api_keys.py --ha-url http://homeassistant.local:8123 --ha-token your_token_here

# Test with specific Weather API key
python tests/test_api_keys.py --weather-key your_openweathermap_key

# Test with all overrides
python tests/test_api_keys.py \
  --ha-url http://homeassistant.local:8123 \
  --ha-token your_ha_token \
  --weather-key your_weather_key
```

#### Output Formats
```bash
# Console output (default)
python tests/test_api_keys.py

# JSON output for scripting
python tests/test_api_keys.py --output json > test_results.json
```

### Environment Variables Required

The test script expects these environment variables:

```bash
# Home Assistant Configuration
HOME_ASSISTANT_URL=http://homeassistant.local:8123
HOME_ASSISTANT_TOKEN=your_long_lived_access_token_here

# Weather API Configuration  
WEATHER_API_KEY=your_openweathermap_api_key_here

# InfluxDB Configuration (optional for basic API tests)
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=your_influxdb_token
```

### Test Categories

#### 1. Environment Variables Test
- Validates all required environment variables are present
- Checks for proper configuration
- Masks sensitive values in output

#### 2. Home Assistant API Tests
- **Connection Test**: Basic connectivity to HA instance
- **WebSocket Test**: WebSocket endpoint availability  
- **Permissions Test**: Token permission validation across endpoints

#### 3. Weather API Tests
- **Key Validation**: Tests if API key is valid and active
- **Quota Test**: Checks API quota and rate limiting

### Example Output

```
================================================================================
API KEY VALIDATION TEST RESULTS
================================================================================

SUMMARY:
  Total Tests: 5
  Successful:  4 ✓
  Failed:      1 ✗
  Success Rate: 80.0%

DETAILED RESULTS:
--------------------------------------------------------------------------------

✓ PASS Environment Variables
  all_required_vars_present: True
  total_vars_checked: 5

✓ PASS Home Assistant Connection
  status_code: 200
  message: API running.
  version: 2024.1.0

✓ PASS Home Assistant WebSocket Connection
  websocket_endpoint: ws://homeassistant.local:8123/api/websocket
  status_code: 200
  note: WebSocket endpoint available (full connection test requires WebSocket client)

✓ PASS Home Assistant Token Permissions
  successful_endpoints: ['/api/', '/api/states', '/api/events', '/api/config']
  failed_endpoints: []
  permission_level: Read access confirmed

✗ FAIL Weather API Key Validation
  Error: Invalid API key - authentication failed

================================================================================
```

### Exit Codes

- `0`: All tests passed
- `1`: One or more tests failed

### Integration with CI/CD

The script can be integrated into CI/CD pipelines:

```bash
# In your CI pipeline
python tests/test_api_keys.py --output json > api_test_results.json

# Check exit code
if [ $? -eq 0 ]; then
    echo "All API tests passed"
else
    echo "API tests failed - check results"
    exit 1
fi
```

### Troubleshooting

#### Common Issues

1. **"Missing required environment variables"**
   - Ensure `.env` file exists with all required variables
   - Use `--env-file` to specify custom env file location

2. **"Connection timeout"**
   - Check if Home Assistant is running and accessible
   - Verify `HOME_ASSISTANT_URL` is correct
   - Ensure network connectivity

3. **"Invalid API key"**
   - Verify API keys are correct and active
   - Check if API keys have expired
   - Ensure proper permissions for API keys

4. **"Rate limit exceeded"**
   - Weather API has usage limits
   - Wait before retrying tests
   - Check OpenWeatherMap account quota

### Dependencies

Required Python packages:
```bash
pip install aiohttp requests python-dotenv
```

Or install from project requirements:
```bash
pip install -r services/admin-api/requirements.txt
```
