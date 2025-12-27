# HomeIQ Custom Workflows Guide

**Version:** 1.0.0  
**Last Updated:** January 2025  
**Status:** Active

---

## Table of Contents

- [Overview](#overview)
- [When to Create Custom Workflows](#when-to-create-custom-workflows)
- [HomeIQ Architecture Patterns](#homeiq-architecture-patterns)
- [Workflow YAML Structure](#workflow-yaml-structure)
- [HomeIQ-Specific Workflow Patterns](#homeiq-specific-workflow-patterns)
- [Creating a Custom Workflow](#creating-a-custom-workflow)
- [Testing and Validation](#testing-and-validation)
- [Examples](#examples)
- [Best Practices](#best-practices)

---

## Overview

This guide explains how to create custom workflows for HomeIQ that encode HomeIQ-specific patterns and practices. Custom workflows ensure consistent, high-quality development across the 30+ microservice architecture.

### Available HomeIQ Custom Workflows

1. **`homeiq-microservice-creation.yaml`** - Create new microservice with Docker, InfluxDB, Epic 31 patterns
2. **`homeiq-service-integration.yaml`** - Integrate service with existing infrastructure
3. **`homeiq-quality-audit.yaml`** - Multi-service quality audit with parallel execution

**Location:** `workflows/custom/`

---

## When to Create Custom Workflows

Create a custom workflow when:

1. ✅ **Pattern Recognition**: Same sequence of steps used 3+ times
2. ✅ **HomeIQ-Specific Patterns**: Patterns unique to HomeIQ (microservices, Epic 31 architecture)
3. ✅ **Multi-Service Operations**: Coordinated operations across multiple services
4. ✅ **Complex Conditional Logic**: Workflows with branches, gates, or loops
5. ✅ **Standardization Need**: Need to enforce consistent process

### Pattern Recognition Process

1. **Identify Pattern**: Notice repeated sequence of operations
2. **Document Pattern**: Write down the steps in order
3. **Create Workflow YAML**: Convert to workflow YAML format
4. **Test Workflow**: Execute workflow on one instance
5. **Refine**: Adjust based on execution results
6. **Share**: Keep in `workflows/custom/` if HomeIQ-specific, move to `workflows/presets/` if generally useful

---

## HomeIQ Architecture Patterns

### Epic 31 Architecture (MUST FOLLOW)

**Critical Pattern:** Direct InfluxDB writes, no enrichment-pipeline

**Event Flow:**
```
External Service/API
    ↓
Service (Direct InfluxDB Write)
    ↓
InfluxDB (Port 8086)
    ↓
data-api (Port 8006) - Query Endpoint
    ↓
Dashboard/Client
```

**Key Rules:**
- ✅ Services write **directly** to InfluxDB (no intermediate services)
- ✅ Query data via **data-api** endpoints (no direct InfluxDB reads from services)
- ✅ **NO** service-to-service HTTP dependencies
- ✅ **NO** enrichment-pipeline (deprecated in Epic 31)
- ✅ Standalone service pattern

**Reference:** `.cursor/rules/epic-31-architecture.mdc`

### Docker Patterns

**Standard Dockerfile:**
```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:${PORT}/health || exit 1

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "${PORT}"]
```

**docker-compose.yml Pattern:**
```yaml
services:
  service-name:
    build: ./services/service-name
    ports:
      - "800X:8000"  # Port mapping
    environment:
      - INFLUXDB_URL=http://influxdb:8086
      - INFLUXDB_TOKEN=${INFLUXDB_TOKEN}
      - INFLUXDB_BUCKET=home_assistant_events
    depends_on:
      - influxdb
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Quality Standards

**Minimum Thresholds:**
- **Overall Score**: 70+ (80+ for critical services)
- **Security**: 7.0+/10
- **Maintainability**: 7.0+/10
- **Test Coverage**: 80% target

**Current Gaps:**
- websocket-ingestion: 0% test coverage (critical)
- ai-automation-service: 0% test coverage (critical)

### Service Communication Patterns

**InfluxDB Writes:**
```python
# ✅ CORRECT (Epic 31)
from influxdb_client import InfluxDBClient

client = InfluxDBClient(url=influxdb_url, token=token)
write_api = client.write_api()

write_api.write(
    bucket=bucket,
    record=Point("measurement_name")
        .tag("tag_key", "tag_value")
        .field("field_key", field_value)
        .time(time)
)

# ❌ INCORRECT (Pre-Epic 31)
# await http_client.post("http://enrichment-pipeline:8002/events", event)
```

**data-api Queries:**
```python
# ✅ CORRECT (Query via data-api)
import httpx

async with httpx.AsyncClient() as client:
    response = await client.get(
        f"http://data-api:8006/api/v1/events",
        params={"start": start_time, "end": end_time}
    )
    events = response.json()

# ❌ INCORRECT (Direct InfluxDB reads from service)
# query_api = influxdb_client.query_api()
# results = query_api.query(query)
```

---

## Workflow YAML Structure

### Basic Structure

```yaml
workflow:
  id: workflow-id
  name: "Workflow Name"
  description: "Workflow description"
  version: "1.0.0"
  
  type: greenfield | brownfield
  auto_detect: true | false
  
  settings:
    quality_gates: true | false
    code_scoring: true | false
    context_tier_default: 1 | 2 | 3
  
  steps:
    - id: step_id
      agent: agent_name
      action: action_name
      context_tier: 1 | 2 | 3
      instructions: |
        Detailed instructions for the agent
      requires: []
      creates:
        - artifact1.md
        - artifact2/
      next: next_step_id
```

### Step Properties

**Required Properties:**
- `id` - Unique step identifier
- `agent` - Agent to execute (architect, implementer, reviewer, tester, etc.)
- `action` - Action to perform (design_system, write_code, review_code, write_tests, etc.)
- `context_tier` - Context level (1=minimal, 2=moderate, 3=full)

**Optional Properties:**
- `instructions` - Detailed instructions for the agent (HomeIQ-specific patterns)
- `requires` - List of artifacts/files this step depends on
- `creates` - List of artifacts/files this step creates
- `next` - Next step ID(s) (string for sequential, list for parallel)
- `scoring` - Quality scoring configuration
- `gate` - Quality gate configuration

### Quality Gates

```yaml
- id: review
  agent: reviewer
  action: review_code
  scoring:
    enabled: true
    thresholds:
      overall_min: 70
      security_min: 7.0
      maintainability_min: 7.0
  gate:
    condition: "scoring.passed == true"
    on_pass: testing
    on_fail: implementation  # Loopback to fix issues
```

### Parallel Execution

```yaml
steps:
  - id: step1
    next: [step2a, step2b, step2c]  # Parallel execution
  - id: step2a
    requires: [step1]
    next: step3
  - id: step2b
    requires: [step1]
    next: step3
  - id: step2c
    requires: [step1]
    next: step3
```

---

## HomeIQ-Specific Workflow Patterns

### Pattern 1: Microservice Creation

**Steps:**
1. Architecture design (Epic 31 patterns)
2. API design (RESTful, health checks)
3. Docker setup (Dockerfile, docker-compose.yml)
4. InfluxDB integration (direct writes)
5. Service implementation
6. Quality review (70+ required)
7. Test generation (80% target)
8. Documentation

**Example:** `homeiq-microservice-creation.yaml`

### Pattern 2: Service Integration

**Steps:**
1. Analyze existing services
2. Design integration (Epic 31 patterns)
3. InfluxDB write implementation (direct)
4. data-api query implementation
5. Integration implementation
6. Quality review (70+ required)
7. Integration testing
8. Documentation

**Example:** `homeiq-service-integration.yaml`

### Pattern 3: Quality Audit

**Steps:**
1. Identify services to audit
2. Parallel quality reviews (multiple services)
3. Aggregate reviews
4. Generate tests for low-coverage services
5. Final report

**Example:** `homeiq-quality-audit.yaml`

---

## Creating a Custom Workflow

### Step 1: Identify the Pattern

Document the repeated sequence:
- What steps are involved?
- What are the dependencies between steps?
- What quality gates are needed?
- What HomeIQ-specific patterns apply?

### Step 2: Create Workflow YAML

Create a new file in `workflows/custom/`:
```yaml
# workflows/custom/homeiq-your-workflow.yaml

workflow:
  id: homeiq-your-workflow
  name: "Your Workflow Name"
  description: "Description of what this workflow does"
  version: "1.0.0"
  
  type: greenfield  # or brownfield
  auto_detect: true
  
  settings:
    quality_gates: true
    code_scoring: true
    context_tier_default: 2
  
  steps:
    # Define steps following HomeIQ patterns
```

### Step 3: Add HomeIQ-Specific Instructions

Include Epic 31 patterns in step instructions:
```yaml
- id: influxdb_integration
  agent: implementer
  action: write_code
  instructions: |
    Implement InfluxDB integration following Epic 31 architecture:
    - Direct InfluxDB writes (NO enrichment-pipeline)
    - Use InfluxDB Python client library
    - Write directly to InfluxDB (no HTTP POST to other services)
    - Follow existing patterns (see services/weather-api, services/sports-data)
```

### Step 4: Add Quality Gates

Ensure quality gates match HomeIQ standards:
```yaml
- id: review
  agent: reviewer
  scoring:
    enabled: true
    thresholds:
      overall_min: 70
      security_min: 7.0
      maintainability_min: 7.0
  gate:
    condition: "scoring.passed == true"
    on_pass: testing
    on_fail: implementation
```

### Step 5: Test the Workflow

Execute on a test instance:
```bash
python -m tapps_agents.cli orchestrator workflow workflows/custom/homeiq-your-workflow.yaml --prompt "Test description"
```

### Step 6: Refine and Document

- Adjust steps based on execution results
- Add comments explaining HomeIQ-specific decisions
- Document in this guide if pattern is useful for others

---

## Testing and Validation

### Testing Workflows

1. **Test on Small Instance**: Execute workflow on a simple example first
2. **Verify Artifacts**: Check that all `creates` artifacts are generated
3. **Check Quality Gates**: Ensure quality gates work correctly
4. **Validate HomeIQ Patterns**: Verify Epic 31 patterns are followed

### Validation Checklist

- [ ] Workflow executes without errors
- [ ] All steps complete successfully
- [ ] Quality gates enforce HomeIQ standards (70+ overall, 7.0+ security/maintainability)
- [ ] Epic 31 patterns are followed (direct InfluxDB writes, query via data-api)
- [ ] Docker patterns are correct (Python 3.12, health checks, port mapping)
- [ ] Documentation is generated
- [ ] Tests are generated (80% target coverage)

---

## Examples

### Example 1: Microservice Creation Workflow

See `workflows/custom/homeiq-microservice-creation.yaml` for complete example.

**Key Features:**
- Epic 31 architecture patterns (direct InfluxDB writes)
- Docker setup (Dockerfile, docker-compose.yml)
- Quality gates (70+ overall, 7.0+ security/maintainability)
- Test generation (80% target)
- HomeIQ-specific instructions at each step

### Example 2: Service Integration Workflow

See `workflows/custom/homeiq-service-integration.yaml` for complete example.

**Key Features:**
- Analysis of existing services
- Epic 31 integration patterns (direct writes, data-api queries)
- Integration testing
- Quality gates
- Documentation

### Example 3: Quality Audit Workflow

See `workflows/custom/homeiq-quality-audit.yaml` for complete example.

**Key Features:**
- Parallel execution (multiple service reviews)
- Aggregate reporting
- Test generation for low-coverage services
- Quality gap identification

---

## Best Practices

### 1. Follow Epic 31 Architecture

**Always:**
- ✅ Direct InfluxDB writes (no enrichment-pipeline)
- ✅ Query via data-api (no direct InfluxDB reads)
- ✅ Standalone services (no service-to-service HTTP dependencies)

**Never:**
- ❌ HTTP POST to enrichment-pipeline
- ❌ Service-to-service HTTP dependencies
- ❌ Direct InfluxDB queries from services

### 2. Enforce Quality Standards

**Always:**
- ✅ Quality gates with HomeIQ thresholds (70+ overall, 7.0+ security/maintainability)
- ✅ Loopback on failures (gate `on_fail` points to fix step)
- ✅ Test generation (80% target coverage)

### 3. Include HomeIQ-Specific Instructions

**Always:**
- ✅ Document Epic 31 patterns in step instructions
- ✅ Reference existing HomeIQ services as examples
- ✅ Include Docker patterns (Python 3.12, health checks)
- ✅ Document InfluxDB bucket/measurement names

### 4. Use Appropriate Context Tiers

- **Tier 1 (Minimal)**: Finalization, simple operations
- **Tier 2 (Moderate)**: Most operations (default)
- **Tier 3 (Full)**: Architecture design, complex implementations

### 5. Test Before Sharing

- Test workflow on real example
- Verify all steps execute correctly
- Check quality gates work
- Validate HomeIQ patterns are followed

---

## Related Documentation

- [CURSOR_TAPPS_AGENTS_INTEGRATION_STRATEGY.md](./CURSOR_TAPPS_AGENTS_INTEGRATION_STRATEGY.md) - Complete integration strategy
- [TAPPS_AGENTS_QUICK_REFERENCE.md](./TAPPS_AGENTS_QUICK_REFERENCE.md) - Quick reference
- [.cursor/rules/tapps-agents-workflow-selection.mdc](../.cursor/rules/tapps-agents-workflow-selection.mdc) - Workflow selection guide
- [.cursor/rules/epic-31-architecture.mdc](../.cursor/rules/epic-31-architecture.mdc) - Epic 31 architecture patterns
- `workflows/custom/` - HomeIQ custom workflows

---

**Version History:**
- **1.0.0** (January 2025) - Initial version for HomeIQ

