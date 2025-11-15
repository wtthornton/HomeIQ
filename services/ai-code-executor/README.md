# AI Code Executor Service

Secure Python code execution sandbox for MCP (Model Context Protocol) code execution pattern.

## Overview

This service enables AI agents to write and execute Python code that calls HomeIQ services as MCP tools, achieving **90%+ token reduction** compared to traditional tool calling patterns.

### Token Savings Example

**Traditional Pattern:** 150,000 tokens
**MCP Code Execution:** 2,000 tokens
**Savings:** 98.7% (-148,000 tokens, -87% cost)

## Architecture

```
AI Agent (LangChain + GPT-4o-mini)
    ↓ generates Python code
AI Code Executor (this service)
    ↓ executes in secure sandbox
    ↓ calls MCP tools via HTTP
HomeIQ Services (Data API, AI Automation, Device Intelligence)
    ↓ returns data
AI Code Executor (returns summary only)
    ↓
AI Agent (interprets summary → generates automation)
```

## Security

Multiple layers of security protect against malicious code:

1. **RestrictedPython** - AST-level code restrictions (no `eval`, `exec`, `open`, `__import__`)
2. **Resource Limits** - 128MB memory, 30s timeout, 50% CPU max
3. **Whitelist Imports** - Only safe stdlib modules allowed
4. **Docker Isolation** - Runs in isolated container
5. **No Network Access** - Cannot access external internet

## Available MCP Tools

### Data API Tools

```python
import data

# Get all devices
devices = await data.get_devices()
# Returns: {"count": 99, "devices": [...]}

# Query device history
history = await data.query_device_history(
    entity_id="sensor.power",
    start_time="-7d",
    end_time="now"
)
# Returns: {"entity_id": "...", "data_points": 1000, "data": [...]}

# Search events
events = await data.search_events(
    entity_id="light.living_room",
    start_time="-24h",
    limit=100
)
# Returns: {"count": 50, "events": [...]}
```

### AI Automation Tools

```python
import automation

# Detect patterns
patterns = await automation.detect_patterns(
    start_time="-7d",
    end_time="now",
    pattern_types=["time-based", "co-occurrence"]
)
# Returns: {"patterns": [...]}
```

### Device Intelligence Tools

```python
import device

# Get device capabilities
caps = await device.get_device_capabilities(
    entity_id="light.living_room"
)
# Returns: {"capabilities": [...], "actions": [...]}
```

## Example Code

### Simple Query

```python
import data

# Get devices and filter lights
devices = await data.get_devices()
lights = [d for d in devices['devices']
          if d['entity_id'].startswith('light.')]

print(f"Found {len(lights)} lights")

# Return summary (not full data)
{
    "total_devices": devices['count'],
    "lights": len(lights),
    "sample_lights": [l['entity_id'] for l in lights[:3]]
}
```

### Complex Analysis

```python
import data
import automation

# Get power sensors
devices = await data.get_devices()
power_sensors = [d for d in devices['devices']
                 if 'power' in d['entity_id']]

print(f"Analyzing {len(power_sensors)} power sensors")

# Get history for first sensor
history = await data.query_device_history(
    entity_id=power_sensors[0]['entity_id'],
    start_time="-7d",
    end_time="now"
)

# Process locally (data doesn't go through LLM!)
high_usage = [h for h in history['data'] if h.get('value', 0) > 1000]

# Detect patterns
patterns = await automation.detect_patterns(
    start_time="-7d",
    end_time="now",
    pattern_types=["time-based"]
)

# Return concise summary
{
    "power_sensors": len(power_sensors),
    "data_points": history['data_points'],
    "high_usage_events": len(high_usage),
    "patterns_found": len(patterns.get('patterns', []))
}
```

## API Endpoints

### POST /execute

Execute Python code in secure sandbox.

**Request:**
```json
{
  "code": "import data\ndevices = await data.get_devices()\ndevices"
}
```

**Response:**
```json
{
  "success": true,
  "stdout": "",
  "stderr": "",
  "return_value": {"count": 99, "devices": [...]},
  "execution_time": 0.245,
  "memory_used_mb": 12.5,
  "error": null
}
```

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "ai-code-executor",
  "version": "1.0.0",
  "mcp_initialized": true
}
```

## Configuration

Environment variables (with defaults):

```bash
# Resource limits (NUC-optimized)
EXECUTION_TIMEOUT=30          # Max execution time (seconds)
MAX_MEMORY_MB=128             # Max memory per execution (MB)
MAX_CPU_PERCENT=50.0          # Max CPU usage (%)

# MCP workspace
MCP_WORKSPACE_DIR=/tmp/mcp_workspace

# Logging
LOG_LEVEL=INFO
```

## Performance Metrics

Typical performance on Intel NUC:

- **Execution time:** 50-500ms (depends on MCP tool calls)
- **Memory usage:** 20-100MB (typical)
- **CPU usage:** 10-30% (one core)
- **Token savings:** 90-99% vs traditional pattern
- **Cost savings:** 87-99% per automation

## Monitoring

Prometheus metrics available at `/metrics`:

- `code_executions_total{status}` - Total executions (success/failure/timeout/security_blocked)
- `code_execution_duration_seconds` - Execution time histogram
- `code_execution_memory_mb` - Memory usage histogram
- `code_executions_active` - Currently executing code

## Development

### Local Development

```bash
cd services/ai-code-executor

# Install dependencies
pip install -r requirements.txt

# Run service
uvicorn src.main:app --reload --port 8030

# Run tests
pytest tests/ -v
```

### Docker Build

```bash
# Build image
docker build -t homeiq-code-executor -f services/ai-code-executor/Dockerfile .

# Run container
docker run -p 8030:8030 homeiq-code-executor

# Test
curl http://localhost:8030/health
```

## Troubleshooting

### Execution Timeout

**Symptom:** Code execution fails with timeout error

**Solution:**
- Increase `EXECUTION_TIMEOUT` (carefully!)
- Optimize MCP tool calls (reduce data fetching)
- Add progress print statements to track execution

### Memory Limit Exceeded

**Symptom:** Execution fails with memory error

**Solution:**
- Reduce data processing in code
- Filter data at the source (MCP tool level)
- Increase `MAX_MEMORY_MB` (carefully - impacts NUC resources)

### Security Blocked

**Symptom:** Code rejected before execution

**Solution:**
- Review code for dangerous patterns (`open`, `eval`, `__import__`, etc.)
- Use MCP tools instead of direct file/network access
- If legitimate, contact maintainer to whitelist pattern

### MCP Tool Connection Failed

**Symptom:** HTTP error when calling MCP tool

**Solution:**
- Check that target service is running: `docker compose ps`
- Check service health: `curl http://data-api:8006/health`
- Check docker network: `docker network inspect homeiq-network`
- Review service logs: `docker compose logs data-api`

## Security Notes

**DO NOT:**
- Expose this service to public internet
- Execute untrusted code without review
- Increase resource limits without understanding implications
- Disable security features

**DO:**
- Keep it behind firewall
- Monitor execution metrics
- Review generated code in logs
- Set up alerts for `security_blocked` executions

## Files Structure

```
services/ai-code-executor/
├── src/
│   ├── main.py                    # FastAPI application
│   ├── config.py                  # Service configuration
│   ├── executor/
│   │   ├── sandbox.py             # Secure Python sandbox
│   │   └── mcp_sandbox.py         # MCP-enhanced sandbox
│   ├── mcp/
│   │   ├── filesystem_generator.py # Tool filesystem generator
│   │   └── homeiq_tools.py        # HomeIQ tool definitions
│   ├── security/
│   │   └── code_validator.py      # Pre-execution validation
│   └── monitoring/
│       └── metrics.py             # Prometheus metrics
├── tests/
│   ├── test_sandbox.py            # Sandbox security tests
│   ├── test_mcp_integration.py    # MCP integration tests
│   └── test_security.py           # Security tests
├── requirements.txt               # Python dependencies
├── Dockerfile                     # Container definition
└── README.md                      # This file
```

## Related Documentation

- [MCP Implementation Plan](/docs/implementation/MCP_CODE_EXECUTION_PLAN.md)
- [Docker Compose Update](/DOCKER_COMPOSE_UPDATE.md)
- [LangChain Integration](/services/ai-automation-service/src/langchain_integration/mcp_chains.py)

## Support

For issues, questions, or improvements:
1. Check troubleshooting section above
2. Review logs: `docker compose logs ai-code-executor`
3. Check metrics: `curl http://localhost:8030/metrics`
4. Create GitHub issue with logs and error details

---

**Version:** 1.0.0
**Last Updated:** November 15, 2025
**Maintainer:** HomeIQ Development Team

## Version History

### 1.1 (November 15, 2025)
- Documentation verified for 2025 standards
- MCP (Model Context Protocol) pattern documented
- Security layers comprehensive reference
- Token savings examples (90%+ reduction)
- Troubleshooting guide expanded

### 1.0 (November 2025)
- Secure Python code execution sandbox
- MCP tool integration (Data API, AI Automation, Device Intelligence)
- RestrictedPython security (no eval, exec, open, __import__)
- Resource limits (128MB, 30s timeout, 50% CPU)
- Docker isolation
- Prometheus metrics

---

**Last Updated:** November 15, 2025
**Version:** 1.1
**Status:** Production Ready ✅
**Port:** 8030
**Security:** Multi-layer sandbox (RestrictedPython + Docker + Resource Limits)
**Performance:** 90-99% token savings vs traditional tool calling
