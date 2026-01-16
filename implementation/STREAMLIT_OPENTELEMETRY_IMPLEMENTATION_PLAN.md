# Streamlit + OpenTelemetry Observability Tools Implementation Plan

**Created:** 2026-01-16  
**Status:** Planning Complete  
**Priority:** High  
**Goal:** Implement Streamlit dashboards for observability, automation debugging, and operational excellence using OpenTelemetry

---

## Executive Summary

This plan outlines the implementation of Streamlit-based observability tools for HomeIQ that leverage existing OpenTelemetry infrastructure. These tools will provide internal/admin dashboards for distributed tracing visualization, automation debugging, and service performance monitoring.

**Key Principles:**
- ✅ Internal/admin tools only (do NOT replace React customer-facing dashboards)
- ✅ Integrate with existing HomeIQ infrastructure
- ✅ Follow HomeIQ service patterns (Docker, port configuration, health checks)
- ✅ Use existing shared libraries where possible

---

## Current State Analysis

### Existing OpenTelemetry Infrastructure

**Location:** `shared/observability/tracing.py`

**Current Setup:**
- ✅ OpenTelemetry tracing configured
- ✅ Jaeger UI available at http://localhost:16686
- ✅ OTLP endpoint: `OTLP_ENDPOINT=http://jaeger:4317`
- ✅ FastAPI automatic instrumentation
- ✅ Trace context propagation with correlation IDs
- ✅ Graceful degradation (console exporter fallback)

**Services Using OpenTelemetry:**
- `data-api`: Full OpenTelemetry tracing with correlation IDs
- `websocket-ingestion`: Event processing traces
- `ai-automation-service`: Automation execution traces
- All FastAPI services: Automatic endpoint instrumentation

### Existing Dashboards

**Customer-Facing (React/TypeScript):**
- Health Dashboard (port 3000): System monitoring, service management
- AI Automation UI (port 3001): Conversational automation interface

**These will NOT be replaced by Streamlit.**

---

## Implementation Goals

### 1. Trace Visualization Dashboard
- Visualize distributed traces across 30+ services
- Show service dependency graphs with performance metrics
- Display trace timelines with latency breakdowns
- Filter traces by service, endpoint, error status, correlation ID
- Correlate traces with InfluxDB metrics

### 2. Automation Debugging Dashboard
- Trace automation execution from trigger → validation → execution → confirmation
- Show "why" explanations (triggers matched, policies applied, actions taken)
- Visualize automation flows with timing breakdowns
- Filter by automation ID, home ID, or correlation ID
- Show automation success/failure rates with trace context

### 3. Service Performance Monitoring Dashboard
- Service health across all 30+ microservices
- Request latency percentiles (p50, p95, p99) from OpenTelemetry spans
- Error rates and trace error analysis
- Service dependency health (which services are slow/down)
- Resource utilization correlation (CPU/memory vs trace latency)

### 4. Real-Time Observability Dashboard
- Live trace streaming from Jaeger/OTLP
- Auto-refresh dashboard with latest traces
- Alert on trace anomalies (high latency, errors)
- Real-time service health monitoring
- Live automation execution tracking

---

## Architecture Design

### Service Structure

**New Service:** `observability-dashboard` (Streamlit)

**Port:** 8501 (Streamlit default)

**Technology Stack:**
- Python 3.11+
- Streamlit 1.28+
- OpenTelemetry Python SDK
- Jaeger Query API client
- InfluxDB client (existing)
- FastAPI client (for HomeIQ APIs)

**Service Location:**
```
services/observability-dashboard/
├── src/
│   ├── main.py                 # Streamlit app entry point
│   ├── pages/
│   │   ├── trace_visualization.py
│   │   ├── automation_debugging.py
│   │   ├── service_performance.py
│   │   └── real_time_monitoring.py
│   ├── services/
│   │   ├── jaeger_client.py    # Jaeger Query API client
│   │   ├── otlp_client.py      # OTLP collector client
│   │   ├── influxdb_client.py # InfluxDB metrics client
│   │   └── homeiq_api_client.py # HomeIQ API clients
│   ├── components/
│   │   ├── trace_viewer.py     # Trace visualization components
│   │   ├── service_graph.py    # Service dependency graph
│   │   ├── automation_flow.py  # Automation flow visualization
│   │   └── metrics_charts.py  # Metrics visualization
│   └── utils/
│       ├── trace_analysis.py   # Trace analysis utilities
│       ├── correlation.py      # Correlation ID utilities
│       └── filters.py          # Filter utilities
├── tests/
│   ├── test_jaeger_client.py
│   ├── test_trace_analysis.py
│   └── test_components.py
├── Dockerfile
├── requirements.txt
└── README.md
```

### Integration Points

**1. Jaeger Integration**
- Query Jaeger Query API (http://jaeger:16686/api)
- Endpoints:
  - `/api/traces` - Get traces
  - `/api/services` - List services
  - `/api/dependencies` - Service dependencies
  - `/api/trace/{traceId}` - Get specific trace

**2. InfluxDB Integration**
- Query metrics via existing InfluxDB client patterns
- Correlate metrics with traces using correlation IDs
- Time-series queries for performance trends

**3. HomeIQ API Integration**
- `data-api` (port 8006): Historical events and metrics
- `admin-api` (port 8004): Service health and configuration
- Use existing API clients from shared libraries

**4. OpenTelemetry Direct Integration**
- OTLP gRPC client for direct trace queries
- Span analysis and visualization
- Trace context propagation

---

## Implementation Phases

### Phase 1: Foundation & Infrastructure (Week 1)

**Tasks:**
1. Create `observability-dashboard` service structure
2. Set up Docker configuration
3. Configure port mapping (8501)
4. Add to docker-compose.yml
5. Create basic Streamlit app with navigation
6. Set up health check endpoint
7. Configure environment variables

**Deliverables:**
- Service structure created
- Docker configuration complete
- Basic Streamlit app running
- Health check working

**Acceptance Criteria:**
- Service starts successfully in Docker
- Health check returns 200 OK
- Basic Streamlit UI accessible at http://localhost:8501

---

### Phase 2: Jaeger Integration & Trace Visualization (Week 2)

**Tasks:**
1. Implement Jaeger Query API client
2. Create trace query utilities
3. Build trace visualization components
4. Implement trace filtering (service, endpoint, error status, correlation ID)
5. Create service dependency graph visualization
6. Add trace timeline visualization with latency breakdowns
7. Integrate with InfluxDB for metrics correlation

**Deliverables:**
- Jaeger client implementation
- Trace visualization dashboard page
- Service dependency graph
- Trace filtering functionality
- Metrics correlation

**Acceptance Criteria:**
- Can query and display traces from Jaeger
- Service dependency graph shows all services
- Trace filtering works correctly
- Metrics correlation displays correctly

---

### Phase 3: Automation Debugging Dashboard (Week 3)

**Tasks:**
1. Implement automation trace filtering (by automation ID, home ID, correlation ID)
2. Create automation flow visualization component
3. Build "why" explanation display (triggers, policies, actions)
4. Implement automation success/failure rate analysis
5. Add automation timing breakdown visualization
6. Create automation trace search functionality

**Deliverables:**
- Automation debugging dashboard page
- Automation flow visualization
- "Why" explanation display
- Automation performance metrics

**Acceptance Criteria:**
- Can filter traces by automation ID
- Automation flow visualization shows complete execution path
- "Why" explanations display correctly
- Automation metrics are accurate

---

### Phase 4: Service Performance Monitoring (Week 4)

**Tasks:**
1. Implement service health aggregation from traces
2. Calculate latency percentiles (p50, p95, p99) from spans
3. Build error rate analysis from traces
4. Create service dependency health visualization
5. Implement resource utilization correlation
6. Add service performance trends over time

**Deliverables:**
- Service performance monitoring dashboard page
- Service health visualization
- Latency percentile charts
- Error rate analysis
- Resource correlation charts

**Acceptance Criteria:**
- Service health displays correctly for all services
- Latency percentiles are accurate
- Error rates match actual service errors
- Resource correlation works correctly

---

### Phase 5: Real-Time Observability (Week 5)

**Tasks:**
1. Implement WebSocket connection to Jaeger for live traces
2. Create auto-refresh dashboard functionality
3. Build trace anomaly detection (high latency, errors)
4. Implement real-time alerting
5. Add live service health monitoring
6. Create live automation execution tracking

**Deliverables:**
- Real-time observability dashboard page
- Live trace streaming
- Auto-refresh functionality
- Anomaly detection and alerting

**Acceptance Criteria:**
- Live traces update automatically
- Anomaly detection works correctly
- Alerts trigger on high latency/errors
- Real-time monitoring is responsive

---

### Phase 6: Testing & Documentation (Week 6)

**Tasks:**
1. Write unit tests for all components
2. Write integration tests for Jaeger/InfluxDB clients
3. Create end-to-end tests for dashboard pages
4. Write comprehensive README
5. Document API integrations
6. Create user guide for each dashboard

**Deliverables:**
- Test suite with >80% coverage
- Comprehensive README
- API integration documentation
- User guides for each dashboard

**Acceptance Criteria:**
- All tests pass
- Test coverage >80%
- Documentation is complete and accurate
- User guides are clear and helpful

---

## Technical Specifications

### Dependencies

**Core:**
- `streamlit>=1.28.0` - Streamlit framework
- `opentelemetry-api>=1.21.0` - OpenTelemetry API
- `opentelemetry-sdk>=1.21.0` - OpenTelemetry SDK
- `opentelemetry-exporter-otlp-proto-grpc>=1.21.0` - OTLP exporter

**Data & Visualization:**
- `pandas>=2.0.0` - Data manipulation
- `plotly>=5.17.0` - Interactive charts
- `networkx>=3.2.0` - Service dependency graphs
- `influxdb-client>=1.38.0` - InfluxDB client (existing)

**API Clients:**
- `httpx>=0.25.0` - HTTP client for Jaeger API
- `aiohttp>=3.9.0` - Async HTTP client
- `websockets>=12.0` - WebSocket client for live traces

**Utilities:**
- `python-dotenv>=1.0.0` - Environment variables
- `pydantic>=2.5.0` - Data validation

### Environment Variables

```bash
# Service Configuration
SERVICE_PORT=8501
SERVICE_NAME=observability-dashboard

# Jaeger Configuration
JAEGER_URL=http://jaeger:16686
JAEGER_API_URL=http://jaeger:16686/api
OTLP_ENDPOINT=http://jaeger:4317

# InfluxDB Configuration
INFLUXDB_URL=http://influxdb:8086
INFLUXDB_TOKEN=${INFLUXDB_TOKEN}
INFLUXDB_ORG=${INFLUXDB_ORG}
INFLUXDB_BUCKET=homeiq_metrics

# HomeIQ API Configuration
DATA_API_URL=http://data-api:8006
ADMIN_API_URL=http://admin-api:8004

# Streamlit Configuration
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=0.0.0.0
STREAMLIT_THEME_BASE=dark
```

### Docker Configuration

**Dockerfile:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY src/ ./src/

# Expose Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8501/_stcore/health')"

# Run Streamlit
CMD ["streamlit", "run", "src/main.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

**docker-compose.yml Entry:**
```yaml
observability-dashboard:
  build:
    context: ./services/observability-dashboard
    dockerfile: Dockerfile
  container_name: homeiq-observability-dashboard
  ports:
    - "8501:8501"
  environment:
    - JAEGER_URL=http://jaeger:16686
    - JAEGER_API_URL=http://jaeger:16686/api
    - OTLP_ENDPOINT=http://jaeger:4317
    - INFLUXDB_URL=http://influxdb:8086
    - INFLUXDB_TOKEN=${INFLUXDB_TOKEN}
    - INFLUXDB_ORG=${INFLUXDB_ORG}
    - INFLUXDB_BUCKET=homeiq_metrics
    - DATA_API_URL=http://data-api:8006
    - ADMIN_API_URL=http://admin-api:8004
  depends_on:
    - jaeger
    - influxdb
    - data-api
    - admin-api
  networks:
    - homeiq-network
  restart: unless-stopped
```

---

## Implementation Details

### 1. Jaeger Client Implementation

**File:** `services/observability-dashboard/src/services/jaeger_client.py`

**Key Functions:**
- `get_traces(service=None, operation=None, limit=100, start_time=None, end_time=None)`
- `get_trace(trace_id)`
- `get_services()`
- `get_dependencies(start_time, end_time)`
- `search_traces(query_params)`

**Implementation Notes:**
- Use Jaeger Query API (REST)
- Handle pagination for large result sets
- Cache service list (refresh every 5 minutes)
- Error handling with retries

### 2. Trace Visualization Component

**File:** `services/observability-dashboard/src/components/trace_viewer.py`

**Features:**
- Timeline visualization using Plotly
- Span details on hover/click
- Filter by service, operation, error status
- Search by trace ID or correlation ID
- Export trace data (JSON)

### 3. Service Dependency Graph

**File:** `services/observability-dashboard/src/components/service_graph.py`

**Features:**
- Network graph using NetworkX and Plotly
- Node size based on request volume
- Edge thickness based on call frequency
- Color coding for service health
- Click to filter traces by service

### 4. Automation Flow Visualization

**File:** `services/observability-dashboard/src/components/automation_flow.py`

**Features:**
- Flowchart showing automation execution steps
- Timing breakdown for each step
- Status indicators (success, failure, pending)
- "Why" explanations for each decision point
- Filter by automation ID, home ID, correlation ID

### 5. Metrics Correlation

**File:** `services/observability-dashboard/src/utils/correlation.py`

**Features:**
- Correlate traces with InfluxDB metrics using correlation IDs
- Display metrics alongside trace spans
- Show resource utilization (CPU, memory) during trace execution
- Performance trends over time

---

## Testing Strategy

### Unit Tests

**Coverage Areas:**
- Jaeger client functions
- Trace analysis utilities
- Filter utilities
- Component rendering
- Data transformation

**Target Coverage:** >80%

### Integration Tests

**Test Scenarios:**
- Jaeger API integration
- InfluxDB query integration
- HomeIQ API integration
- End-to-end trace visualization
- Automation flow visualization

### End-to-End Tests

**Test Scenarios:**
- Complete trace visualization workflow
- Automation debugging workflow
- Service performance monitoring workflow
- Real-time observability workflow

---

## Quality Standards

### Code Quality Thresholds

- **Overall Score:** ≥70 (≥80 for critical components)
- **Security Score:** ≥7.0/10
- **Maintainability Score:** ≥7.0/10
- **Test Coverage:** ≥80%

### Performance Requirements

- **Dashboard Load Time:** <2 seconds
- **Trace Query Response:** <1 second
- **Real-Time Update Latency:** <500ms
- **Concurrent Users:** Support 10+ concurrent users

### Security Requirements

- Internal tool only (no external access)
- Authentication via HomeIQ admin API (if needed)
- No sensitive data exposure
- Secure API communication

---

## Success Metrics

### Development Metrics

- **Implementation Time:** 6 weeks
- **Code Quality Score:** ≥75
- **Test Coverage:** ≥80%
- **Documentation Completeness:** 100%

### Operational Metrics

- **Dashboard Uptime:** >99%
- **Query Response Time:** <1 second (p95)
- **User Adoption:** >80% of ops team using weekly
- **Issue Resolution Time:** 50% reduction in debugging time

---

## Risk Mitigation

### Technical Risks

**Risk:** Jaeger API changes or deprecation
- **Mitigation:** Abstract Jaeger client behind interface, support OTLP direct queries

**Risk:** Performance issues with large trace datasets
- **Mitigation:** Implement pagination, caching, and data sampling

**Risk:** Streamlit limitations for complex visualizations
- **Mitigation:** Use Plotly for advanced charts, consider React components if needed

### Operational Risks

**Risk:** Service dependency on Jaeger availability
- **Mitigation:** Graceful degradation, fallback to cached data

**Risk:** High resource usage from real-time updates
- **Mitigation:** Configurable refresh intervals, user-controlled auto-refresh

---

## Next Steps

1. **Review and Approve Plan** - Get stakeholder approval
2. **Set Up Development Environment** - Create service structure
3. **Begin Phase 1** - Foundation & Infrastructure
4. **Weekly Progress Reviews** - Track implementation progress
5. **Iterative Development** - Build and test incrementally

---

## Related Documentation

- **OpenTelemetry Setup:** `shared/observability/tracing.py`
- **HomeIQ Service Patterns:** `docs/architecture/`
- **Docker Configuration:** `docker-compose.yml`
- **Expert Knowledge Bases:**
  - `.tapps-agents/knowledge/streamlit-dashboards/`
  - `.tapps-agents/knowledge/observability-opentelemetry/`

---

## Conclusion

This implementation plan provides a comprehensive roadmap for building Streamlit-based observability tools that leverage HomeIQ's existing OpenTelemetry infrastructure. The phased approach ensures incremental delivery of value while maintaining code quality and following HomeIQ service patterns.

**Key Success Factors:**
- ✅ Integration with existing infrastructure
- ✅ Internal tools only (no customer-facing changes)
- ✅ Following HomeIQ patterns
- ✅ Comprehensive testing and documentation
- ✅ Iterative development with regular reviews
