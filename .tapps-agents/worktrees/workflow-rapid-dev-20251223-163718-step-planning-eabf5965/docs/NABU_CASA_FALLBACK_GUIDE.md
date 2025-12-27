# Nabu Casa Fallback Guide

This guide explains how to configure and use the Nabu Casa fallback functionality for the HA Ingestor service.

## Overview

The enhanced websocket service supports automatic fallback between multiple Home Assistant instances:

1. **Primary**: HA Simulator (for development)
2. **Fallback**: Nabu Casa Cloud (your production Home Assistant)
3. **Additional**: Local Home Assistant instances (optional)

## Configuration

### 1. Set Up Nabu Casa Token

First, you need to create a long-lived access token in your Home Assistant instance:

1. Go to your Home Assistant instance: https://lwzisze94hrpqde9typkwgu5pptxdkoh.ui.nabu.casa
2. Navigate to **Profile** → **Long-lived access tokens**
3. Create a new token and copy it
4. Set it as an environment variable:

```bash
# Linux/Mac
export NABU_CASA_TOKEN=your_long_lived_access_token_here

# Windows PowerShell
$env:NABU_CASA_TOKEN = "your_long_lived_access_token_here"
```

### 2. Environment Variables

The following environment variables control the fallback behavior:

```bash
# Primary connection (HA Simulator)
HOME_ASSISTANT_URL=http://ha-simulator:8123
HOME_ASSISTANT_TOKEN=dev_simulator_token

# Nabu Casa fallback
NABU_CASA_URL=https://lwzisze94hrpqde9typkwgu5pptxdkoh.ui.nabu.casa
NABU_CASA_TOKEN=your_nabu_casa_long_lived_access_token_here

# Local Home Assistant fallback (optional)
LOCAL_HA_URL=http://localhost:8123
LOCAL_HA_TOKEN=your_local_ha_long_lived_access_token_here
```

## Testing the Connection

### 1. Test Nabu Casa Connection

Before deploying, test your Nabu Casa connection:

```bash
# Test with token as argument
python tests/run_nabu_casa_test.py your_token_here

# Or set environment variable first
export NABU_CASA_TOKEN=your_token_here
python tests/run_nabu_casa_test.py your_token_here
```

### 2. Test Fallback Functionality

Test the complete fallback system:

```bash
python tests/test_fallback_functionality.py
```

## Deployment

### Option 1: Use Enhanced Service (Recommended)

Deploy with fallback support:

```bash
# Linux/Mac
./scripts/deploy-with-fallback.sh

# Windows PowerShell
.\scripts\deploy-with-fallback.ps1
```

### Option 2: Manual Deployment

1. Set your Nabu Casa token:
```bash
export NABU_CASA_TOKEN=your_token_here
```

2. Update the websocket service command in `docker-compose.dev.yml`:
```yaml
websocket-ingestion:
  command: ["python", "src/websocket_with_fallback.py"]
```

3. Deploy:
```bash
docker-compose -f docker-compose.dev.yml up -d
```

## How It Works

### Connection Priority

The service tries connections in this order:

1. **Primary** (Priority 1): HA Simulator
2. **Fallback** (Priority 2): Nabu Casa Cloud
3. **Additional** (Priority 3+): Local Home Assistant instances

### Fallback Logic

1. **Initial Connection**: Tries primary connection first
2. **Failure Handling**: If primary fails, automatically tries fallback
3. **Reconnection**: If current connection fails, tries all available connections
4. **Health Monitoring**: Continuously monitors connection health
5. **Automatic Recovery**: Attempts to reconnect to higher-priority connections

### Health Monitoring

The service provides detailed health information:

```bash
curl http://localhost:8000/health
```

Response includes:
- Current connection status
- Which instance is connected
- Event counts and statistics
- Fallback attempt counts
- Available connections

## Monitoring and Troubleshooting

### Check Service Status

```bash
docker-compose -f docker-compose.dev.yml ps
```

### View Logs

```bash
# All services
docker-compose -f docker-compose.dev.yml logs -f

# Just websocket service
docker-compose -f docker-compose.dev.yml logs -f websocket-ingestion
```

### Health Check

```bash
curl http://localhost:8000/health | jq
```

### Common Issues

#### 1. Authentication Failed
```
❌ Authentication failed with Nabu Casa Fallback
```
**Solution**: Check your `NABU_CASA_TOKEN` is correct and not expired.

#### 2. Connection Timeout
```
❌ Failed to connect to Nabu Casa Fallback: Connection timeout
```
**Solution**: Check network connectivity and firewall settings.

#### 3. No Fallback Available
```
❌ All Home Assistant connections failed
```
**Solution**: Ensure at least one connection is properly configured.

## Security Considerations

1. **Token Security**: Store tokens securely, never commit to version control
2. **Network Security**: Use HTTPS/WSS for cloud connections
3. **Access Control**: Limit token permissions in Home Assistant
4. **Monitoring**: Monitor connection attempts and failures

## Performance Impact

- **Minimal Overhead**: Fallback logic adds minimal performance impact
- **Fast Failover**: Typical failover time is 5-10 seconds
- **Resource Usage**: Slightly higher memory usage due to connection management
- **Network Usage**: Only one active connection at a time

## Advanced Configuration

### Custom Connection Priorities

You can modify the priority order by changing the environment variables:

```bash
# Make Nabu Casa primary
export HOME_ASSISTANT_URL=https://lwzisze94hrpqde9typkwgu5pptxdkoh.ui.nabu.casa
export HOME_ASSISTANT_TOKEN=your_nabu_casa_token
export NABU_CASA_URL=http://ha-simulator:8123
export NABU_CASA_TOKEN=dev_simulator_token
```

### Multiple Fallback Connections

Add additional fallback connections:

```bash
# Local Home Assistant
export LOCAL_HA_URL=http://192.168.1.100:8123
export LOCAL_HA_TOKEN=your_local_token

# Another cloud instance
export CLOUD_HA_URL=https://another-instance.ui.nabu.casa
export CLOUD_HA_TOKEN=another_token
```

## Support

For issues or questions:

1. Check the logs: `docker-compose -f docker-compose.dev.yml logs -f websocket-ingestion`
2. Test individual connections: `python tests/run_nabu_casa_test.py your_token`
3. Verify configuration: `python tests/test_fallback_functionality.py`
4. Check health status: `curl http://localhost:8000/health`
