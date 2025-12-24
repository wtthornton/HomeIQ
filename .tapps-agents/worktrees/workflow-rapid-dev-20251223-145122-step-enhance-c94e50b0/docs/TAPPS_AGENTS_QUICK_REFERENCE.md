# TappsCodingAgents Quick Reference for HomeIQ

**Quick decision guide for Cursor AI** - Choose the right execution tier instantly.

---

## Quick Decision Tree

```
┌─────────────────────────────────────────────────┐
│           User Request                          │
└─────────────────────────────────────────────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
    Single File?          Standard Feature?
        │                       │
    YES │                   YES │
        ↓                       ↓
  Simple Mode            Simple Mode
  *review, *test         *build, *fix
  *fix                      
        │
        │
    Single-Step?
        │
    YES │
        ↓
  Direct Agent
  enhancer, debugger
        │
        │
  Pattern 3+ times?
  OR HomeIQ-specific?
        │
    YES │
        ↓
  Custom Workflow
  homeiq-*.yaml
```

---

## Decision Matrix

| What You Need | Execution Tier | Command |
|---------------|---------------|---------|
| **Review code** | Simple Mode | `@simple-mode *review {file}` |
| **Fix bug** | Simple Mode | `@simple-mode *fix {file} "{description}"` |
| **Create feature** | Simple Mode | `@simple-mode *build "{description}"` |
| **Generate tests** | Simple Mode | `@simple-mode *test {file}` |
| **Enhance prompt** | Direct Agent | `python -m tapps_agents.cli enhancer enhance-quick "{prompt}"` |
| **Analyze error** | Direct Agent | `python -m tapps_agents.cli debugger analyze-error "{error}" --file {file}` |
| **Create microservice** | Custom Workflow | `python -m tapps_agents.cli orchestrator workflow workflows/custom/homeiq-microservice-creation.yaml --prompt "{description}"` |
| **Integrate service** | Custom Workflow | `python -m tapps_agents.cli orchestrator workflow workflows/custom/homeiq-service-integration.yaml --prompt "{description}"` |
| **Quality audit** | Custom Workflow | `python -m tapps_agents.cli orchestrator workflow workflows/custom/homeiq-quality-audit.yaml` |

---

## Simple Mode Commands

```bash
# Build new feature
@simple-mode *build "Create new InfluxDB query endpoint"

# Review code quality
@simple-mode *review services/websocket-ingestion/src/main.py

# Fix bug
@simple-mode *fix services/data-api/src/main.py "Fix connection timeout"

# Generate tests
@simple-mode *test services/data-api/src/main.py

# Full SDLC workflow
@simple-mode *full "Build complete REST API"
```

**Use Simple Mode for:** Single files, standard features, bug fixes, test generation

---

## Direct Agent Commands

```bash
# Quick prompt enhancement
python -m tapps_agents.cli enhancer enhance-quick "Add device health monitoring"

# Full enhancement
python -m tapps_agents.cli enhancer enhance "Create new InfluxDB query endpoint"

# Error analysis
python -m tapps_agents.cli debugger analyze-error "Connection timeout" --file services/data-api/src/main.py

# Code review
python -m tapps_agents.cli reviewer review services/websocket-ingestion/src/main.py

# Test generation
python -m tapps_agents.cli tester test services/ai-automation-service/src/main.py
```

**Use Direct Agents for:** Single-step operations, specific agent capabilities

---

## Custom Workflows

```bash
# Create new microservice
python -m tapps_agents.cli orchestrator workflow workflows/custom/homeiq-microservice-creation.yaml --prompt "Create weather-api service"

# Integrate service
python -m tapps_agents.cli orchestrator workflow workflows/custom/homeiq-service-integration.yaml --prompt "Integrate external API"

# Quality audit
python -m tapps_agents.cli orchestrator workflow workflows/custom/homeiq-quality-audit.yaml
```

**Use Custom Workflows for:** HomeIQ-specific patterns, multi-service operations, repeatable patterns

---

## HomeIQ Quality Standards

| Metric | Minimum | Target |
|--------|---------|--------|
| **Overall Score** | 70+ | 80+ (critical services) |
| **Security** | 7.0+ | 9.0+ |
| **Maintainability** | 7.0+ | 8.0+ |
| **Test Coverage** | 80% | 80%+ |

**Current Status:**
- ✅ data-api: 80.1/100
- ❌ websocket-ingestion: 62.4/100 (0% test coverage)
- ❌ ai-automation-service: 57.7/100 (0% test coverage)

---

## Epic 31 Architecture (MUST FOLLOW)

**✅ DO:**
- Direct InfluxDB writes
- Query via data-api
- Standalone services

**❌ DON'T:**
- Use enrichment-pipeline (deprecated)
- Create service-to-service HTTP dependencies
- Direct InfluxDB reads from services

**Pattern:**
```
Service → InfluxDB (direct write)
         ↓
      data-api (query)
         ↓
    Dashboard/Client
```

---

## Common Patterns

### Pattern 1: Create Microservice
**Use:** `homeiq-microservice-creation.yaml`
**When:** Creating new microservice with Docker, InfluxDB integration

### Pattern 2: Integrate Service
**Use:** `homeiq-service-integration.yaml`
**When:** Integrating external API or service with HomeIQ infrastructure

### Pattern 3: Quality Audit
**Use:** `homeiq-quality-audit.yaml`
**When:** Reviewing quality across multiple services

### Pattern 4: Single File Review
**Use:** Simple Mode `*review`
**When:** Reviewing code quality for one file/service

### Pattern 5: Bug Fix
**Use:** Simple Mode `*fix`
**When:** Fixing bugs in existing code

---

## File Locations

```
workflows/
├── presets/              # Framework workflows
│   ├── full-sdlc.yaml
│   ├── rapid-dev.yaml
│   └── quick-fix.yaml
│
└── custom/               # HomeIQ-specific workflows
    ├── homeiq-microservice-creation.yaml
    ├── homeiq-service-integration.yaml
    └── homeiq-quality-audit.yaml

docs/
├── CURSOR_TAPPS_AGENTS_INTEGRATION_STRATEGY.md  # Complete strategy
├── HOMEIQ_CUSTOM_WORKFLOWS_GUIDE.md              # Workflow creation
├── TAPPS_AGENTS_QUICK_REFERENCE.md               # This file
└── TAPPS_AGENTS_USAGE_GUIDE.md                   # Usage guide

.cursor/rules/
├── simple-mode.mdc                              # Simple Mode guide
├── tapps-agents-workflow-selection.mdc          # Workflow selection
└── epic-31-architecture.mdc                     # Architecture patterns
```

---

## Quick Examples

### Example 1: Review Service
```bash
@simple-mode *review services/websocket-ingestion/src/main.py
```

### Example 2: Create Microservice
```bash
python -m tapps_agents.cli orchestrator workflow workflows/custom/homeiq-microservice-creation.yaml --prompt "Create weather-api service"
```

### Example 3: Fix Bug
```bash
@simple-mode *fix services/data-api/src/main.py "Fix connection timeout"
```

### Example 4: Quality Audit
```bash
python -m tapps_agents.cli orchestrator workflow workflows/custom/homeiq-quality-audit.yaml
```

---

## Related Documentation

- **Complete Strategy:** [CURSOR_TAPPS_AGENTS_INTEGRATION_STRATEGY.md](./CURSOR_TAPPS_AGENTS_INTEGRATION_STRATEGY.md)
- **Workflow Creation:** [HOMEIQ_CUSTOM_WORKFLOWS_GUIDE.md](./HOMEIQ_CUSTOM_WORKFLOWS_GUIDE.md)
- **Usage Guide:** [TAPPS_AGENTS_USAGE_GUIDE.md](./TAPPS_AGENTS_USAGE_GUIDE.md)
- **Workflow Selection Rule:** [.cursor/rules/tapps-agents-workflow-selection.mdc](../.cursor/rules/tapps-agents-workflow-selection.mdc)
- **Simple Mode Rule:** [.cursor/rules/simple-mode.mdc](../.cursor/rules/simple-mode.mdc)
- **Epic 31 Architecture:** [.cursor/rules/epic-31-architecture.mdc](../.cursor/rules/epic-31-architecture.mdc)

---

**Last Updated:** January 2025

