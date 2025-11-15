# MCP Code Execution Implementation Plan
## Simplified - No Feature Flags, LangChain Always On

**Status:** In Progress
**Started:** November 15, 2025
**Target Completion:** 7 weeks
**Approach:** LangChain + MCP Code Execution (always enabled)

---

## Executive Summary

Implementing Anthropic's MCP Code Execution pattern to achieve 90%+ token reduction for HomeIQ automation generation. Using LangChain as the orchestration layer (already in use) with MCP tools exposed as filesystem modules.

**Key Decisions:**
- ✅ No feature flags - Always on for single-home NUC deployment
- ✅ LangChain LCEL chains - Industry standard, already in use
- ✅ Simplified configuration - Minimal environment variables
- ✅ Docker rollback strategy - No need for percentage-based rollout

---

## Architecture Overview

```
User Request
    ↓
AI Automation Service (LangChain LCEL Chain)
    ↓ generates Python code
AI Code Executor Service (Secure Sandbox)
    ↓ executes code with MCP tool access
    ↓
    ├── import data → Data API (Port 8006)
    ├── import automation → AI Automation Service (Port 8024)
    └── import device → Device Intelligence Service (Port 8028)
    ↓
AI Code Executor (returns summary)
    ↓
AI Automation Service (LangChain interprets)
    ↓
YAML Automation (90% fewer tokens)
```

---

## Implementation Phases

### Phase 1: Foundation (Weeks 1-2)

**Week 1: Secure Python Sandbox**
- [ ] Create `services/ai-code-executor/` structure
- [ ] Implement `RestrictedPython` sandbox
- [ ] Resource limits (128MB RAM, 30s timeout, 50% CPU)
- [ ] Security validation (block dangerous patterns)
- [ ] Basic FastAPI service
- [ ] Security tests

**Week 2: MCP Filesystem**
- [ ] Implement MCP filesystem generator
- [ ] Auto-generate tool modules from schemas
- [ ] Progressive tool discovery
- [ ] Workspace isolation
- [ ] Test tool imports

**Deliverables:**
- Working sandbox service on port 8030
- MCP tool filesystem structure
- Security tests passing

---

### Phase 2: Integration (Weeks 3-4)

**Week 3: Real HomeIQ Services**
- [ ] Add `/mcp/tools/` endpoints to Data API
  - `query_device_history`
  - `get_devices`
  - `search_events`
- [ ] Add `/mcp/tools/` endpoints to AI Automation Service
  - `detect_patterns`
  - `generate_automation`
- [ ] Add `/mcp/tools/` endpoints to Device Intelligence Service
  - `get_device_capabilities`
- [ ] Update MCP filesystem generator with real URLs
- [ ] Integration tests with live services

**Week 4: LangChain Integration**
- [ ] Create `MCPCodeExecutionChain` (LCEL chain)
  - Code generation chain
  - Code execution via HTTP
  - Result interpretation chain
- [ ] Token tracking with `get_openai_callback()`
- [ ] Update AI Automation Service to use chain
- [ ] Token comparison tests (traditional vs MCP)
- [ ] Performance benchmarks

**Deliverables:**
- MCP endpoints in 3 services
- LangChain LCEL chains working end-to-end
- Token savings validated (>90%)

---

### Phase 3: Production Hardening (Weeks 5-6)

**Week 5: Security & Monitoring**
- [ ] Code security validator (pre-execution)
- [ ] Prometheus metrics
  - `code_executions_total{status}`
  - `code_execution_duration_seconds`
  - `code_execution_memory_mb`
  - `code_execution_token_savings`
- [ ] Metrics endpoint `/metrics`
- [ ] Emergency fallback (direct LLM if sandbox fails)
- [ ] Comprehensive security tests

**Week 6: Docker Integration**
- [ ] Dockerfile for ai-code-executor
- [ ] Update docker-compose.yml
- [ ] Resource limits (256MB, 0.5 CPU)
- [ ] Health checks
- [ ] Logging configuration
- [ ] Documentation (README, API docs)

**Deliverables:**
- Production-ready service
- Monitoring dashboards
- Complete documentation

---

### Phase 4: Deployment (Week 7)

**Week 7: NUC Deployment**
- [ ] Deploy to NUC via docker-compose
- [ ] Monitor for 48 hours
  - Success rate >95%
  - Memory <150MB
  - CPU <50%
  - Token savings >90%
- [ ] Optimize based on real usage
- [ ] Create runbook for operations

**Deliverables:**
- MCP Code Execution live on NUC
- Operational metrics validated
- Rollback procedures tested

---

## Resource Requirements (NUC)

| Component | RAM | CPU | Disk |
|-----------|-----|-----|------|
| ai-code-executor service | 128-256MB | 0.5 core | 50MB |
| Python runtime overhead | +50MB | +0.1 core | - |
| **Total Added** | ~200-300MB | ~0.6 core | 50MB |

**NUC Impact:** <2% of 16GB RAM, <10% of one CPU core

---

## Success Metrics

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Token Reduction | >90% | TBD | 🟡 Pending |
| Cost Savings | >87% | TBD | 🟡 Pending |
| Execution Latency (p95) | <500ms | TBD | 🟡 Pending |
| Memory Usage | <150MB | TBD | 🟡 Pending |
| CPU Usage | <50% | TBD | 🟡 Pending |
| Success Rate | >95% | TBD | 🟡 Pending |
| Security Blocks | <1% | TBD | 🟡 Pending |

---

## Configuration (Simplified)

```bash
# infrastructure/.env - MINIMAL CONFIG

# Home Assistant
HA_HTTP_URL=http://192.168.1.86:8123
HA_TOKEN=your_long_lived_token

# OpenAI
OPENAI_API_KEY=sk-your-key-here

# MCP Code Executor (optional, has defaults)
MCP_CODE_EXECUTOR_URL=http://ai-code-executor:8030  # default
EXECUTION_TIMEOUT=30  # default
MAX_MEMORY_MB=128  # default
MAX_CPU_PERCENT=50.0  # default

# NO FEATURE FLAGS - Everything always on
```

---

## Rollback Strategy

### Quick Rollback (If Issues Arise)

```bash
# Option 1: Stop code executor (fallback to direct LLM)
docker compose stop ai-code-executor
docker compose restart ai-automation-service

# Option 2: Full service rollback
docker compose down ai-code-executor ai-automation-service
docker compose up -d ai-automation-service

# Option 3: Emergency code-level fallback (already built-in)
# MCPCodeExecutionChain has try/catch fallback to direct LLM
```

### Investigate & Fix

```bash
# Check logs
docker compose logs ai-code-executor --tail=100

# Check metrics
curl http://localhost:8030/metrics

# Check health
curl http://localhost:8030/health

# Test execution
curl -X POST http://localhost:8030/execute \
  -H "Content-Type: application/json" \
  -d '{"code": "print(\"test\")\n\"test\""}'
```

---

## File Structure

```
HomeIQ/
├── services/
│   ├── ai-code-executor/              # NEW SERVICE
│   │   ├── src/
│   │   │   ├── __init__.py
│   │   │   ├── main.py                # FastAPI app
│   │   │   ├── config.py              # Settings
│   │   │   ├── executor/
│   │   │   │   ├── sandbox.py         # Secure sandbox
│   │   │   │   └── mcp_sandbox.py     # MCP-enhanced sandbox
│   │   │   ├── mcp/
│   │   │   │   ├── filesystem_generator.py
│   │   │   │   └── homeiq_tools.py    # Tool definitions
│   │   │   ├── security/
│   │   │   │   └── code_validator.py  # Pre-execution validation
│   │   │   └── monitoring/
│   │   │       └── metrics.py         # Prometheus metrics
│   │   ├── tests/
│   │   │   ├── test_sandbox.py
│   │   │   ├── test_mcp_integration.py
│   │   │   └── test_security.py
│   │   ├── requirements.txt
│   │   ├── Dockerfile
│   │   └── README.md
│   │
│   ├── ai-automation-service/         # UPDATED
│   │   ├── src/
│   │   │   ├── langchain_integration/
│   │   │   │   ├── mcp_chains.py      # NEW: LangChain LCEL chains
│   │   │   │   └── mcp_agent.py       # NEW: Optional agent mode
│   │   │   ├── api/
│   │   │   │   ├── mcp_router.py      # NEW: MCP tool endpoints
│   │   │   │   └── nl_generation_router.py  # UPDATED: Use LangChain
│   │   │   └── config.py              # UPDATED: Remove feature flags
│   │
│   ├── data-api/                      # UPDATED
│   │   ├── src/
│   │   │   └── api/
│   │   │       └── mcp_router.py      # NEW: MCP tool endpoints
│   │
│   └── device-intelligence-service/   # UPDATED
│       ├── src/
│       │   └── api/
│       │       └── mcp_router.py      # NEW: MCP tool endpoints
│
├── docker-compose.yml                 # UPDATED: Add ai-code-executor
├── docs/
│   └── implementation/
│       └── MCP_CODE_EXECUTION_PLAN.md # This file
└── infrastructure/
    └── .env                           # UPDATED: Simplified config
```

---

## Dependencies

### New Dependencies (ai-code-executor)

```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0
RestrictedPython==6.2
psutil==5.9.6
aiofiles==23.2.1
httpx==0.25.2
prometheus-client==0.19.0
```

### Updated Dependencies (ai-automation-service)

```txt
# Already has LangChain, just ensure versions:
langchain==0.1.0
langchain-openai==0.0.2
langchain-community==0.0.10
```

---

## Testing Strategy

### Unit Tests
- Sandbox security (block dangerous code)
- Resource limits (timeout, memory, CPU)
- Code validator (pre-execution checks)
- MCP filesystem generation

### Integration Tests
- End-to-end with real services
- LangChain chain execution
- Token usage measurement
- Error handling & fallbacks

### Performance Tests
- 100 executions (measure p50, p95, p99)
- Memory profiling
- CPU usage monitoring
- Token savings validation

### Security Tests
- Attempt file access (should block)
- Attempt network access (should block)
- Attempt infinite loop (should timeout)
- Attempt memory bomb (should limit)

---

## Documentation Deliverables

- [ ] This implementation plan
- [ ] ai-code-executor README.md
- [ ] API documentation (OpenAPI/Swagger)
- [ ] Architecture diagrams
- [ ] Token comparison analysis
- [ ] Troubleshooting guide
- [ ] Operational runbook

---

## Timeline

| Phase | Weeks | Status |
|-------|-------|--------|
| Phase 1: Foundation | 1-2 | 🟡 In Progress |
| Phase 2: Integration | 3-4 | ⏳ Pending |
| Phase 3: Production | 5-6 | ⏳ Pending |
| Phase 4: Deployment | 7 | ⏳ Pending |

**Total:** 7 weeks

---

## Next Steps

1. ✅ Create this plan document
2. 🔄 Create ai-code-executor service structure
3. ⏳ Implement secure sandbox
4. ⏳ Implement MCP filesystem
5. ⏳ Create LangChain chains
6. ⏳ Add MCP endpoints to services
7. ⏳ Deploy to NUC

---

**Last Updated:** November 15, 2025
**Version:** 1.0 (Simplified - No Feature Flags)
