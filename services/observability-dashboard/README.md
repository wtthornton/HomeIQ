# Observability Dashboard Service

**Streamlit-based internal admin tool for OpenTelemetry observability**

**Port:** 8501  
**Technology:** Python 3.11+, Streamlit, OpenTelemetry, Plotly  
**Container:** homeiq-observability-dashboard  
**Purpose:** Internal/admin observability tools (NOT customer-facing)

## Overview

The Observability Dashboard provides internal/admin dashboards for:
- **Distributed Trace Visualization** - Visualize traces across 30+ services
- **Automation Debugging** - Debug automation execution with end-to-end traces
- **Service Performance Monitoring** - Monitor service health and performance
- **Real-Time Observability** - Live trace streaming and monitoring

**Note:** This is an internal tool only. Customer-facing dashboards remain in React (health-dashboard, ai-automation-ui).

## Architecture

### Service Structure

```
services/observability-dashboard/
├── src/
│   ├── main.py                 # Streamlit app entry point
│   ├── pages/                  # Dashboard pages
│   │   ├── trace_visualization.py
│   │   ├── automation_debugging.py
│   │   ├── service_performance.py
│   │   └── real_time_monitoring.py
│   ├── services/               # API clients
│   │   └── jaeger_client.py    # Jaeger Query API client
│   ├── components/             # Visualization components
│   └── utils/                  # Utility functions
├── tests/                      # Test suite
├── Dockerfile                  # Container definition
└── requirements.txt            # Python dependencies
```

### Integration Points

- **Jaeger** (http://jaeger:16686) - Distributed tracing backend
- **InfluxDB** (http://influxdb:8086) - Metrics storage
- **data-api** (http://data-api:8006) - Historical events and metrics
- **admin-api** (http://admin-api:8004) - Service health and configuration

## Environment Variables

```bash
# Jaeger Configuration
JAEGER_URL=http://jaeger:16686
JAEGER_API_URL=http://jaeger:16686/api
OTLP_ENDPOINT=http://jaeger:4317

# InfluxDB Configuration
INFLUXDB_URL=http://influxdb:8086
INFLUXDB_TOKEN=${INFLUXDB_TOKEN}
INFLUXDB_ORG=${INFLUXDB_ORG}
INFLUXDB_BUCKET=${INFLUXDB_BUCKET}

# HomeIQ API Configuration
DATA_API_URL=http://data-api:8006
ADMIN_API_URL=http://admin-api:8004
```

## Usage

### Access Dashboard

```bash
# Dashboard available at
http://localhost:8501
```

### Docker Compose

```bash
# Start service
docker-compose up observability-dashboard

# View logs
docker-compose logs -f observability-dashboard
```

## Development

### Local Development

```bash
# Install dependencies
pip install -r services/observability-dashboard/requirements.txt

# Run Streamlit locally
cd services/observability-dashboard
streamlit run src/main.py --server.port=8501
```

### Testing

```bash
# Run tests
pytest services/observability-dashboard/tests/
```

## Implementation Status

### Phase 1: Foundation ✅
- [x] Service structure created
- [x] Docker configuration
- [x] Basic Streamlit app with navigation
- [x] Health check endpoint
- [x] Added to docker-compose.yml

### Phase 2: Jaeger Integration (In Progress)
- [x] Jaeger Query API client
- [ ] Trace visualization dashboard page
- [ ] Service dependency graph
- [ ] Trace filtering functionality
- [ ] Metrics correlation

### Phase 3: Automation Debugging (Planned)
- [ ] Automation trace filtering
- [ ] Automation flow visualization
- [ ] "Why" explanation display
- [ ] Automation performance metrics

### Phase 4: Service Performance (Planned)
- [ ] Service health aggregation
- [ ] Latency percentile charts
- [ ] Error rate analysis
- [ ] Resource correlation

### Phase 5: Real-Time Observability (Planned)
- [ ] Live trace streaming
- [ ] Auto-refresh functionality
- [ ] Anomaly detection
- [ ] Real-time alerting

## Related Documentation

- **Implementation Plan:** `implementation/STREAMLIT_OPENTELEMETRY_IMPLEMENTATION_PLAN.md`
- **OpenTelemetry Setup:** `shared/observability/tracing.py`
- **HomeIQ Architecture:** `docs/architecture/`
