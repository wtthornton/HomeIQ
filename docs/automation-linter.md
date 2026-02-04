# HomeIQ Automation Linter Service

**Version:** 0.1.0
**Status:** MVP
**Port:** 8020
**Engine Version:** 0.1.0
**Ruleset Version:** 2026.02.1

---

## Overview

The Automation Linter service provides professional-grade lint and auto-fix capabilities for Home Assistant automation YAML. It helps you catch errors, enforce best practices, and maintain clean automation configurations before deploying to your Home Assistant instance.

### Key Features

- **15+ Lint Rules** covering syntax, schema, logic, reliability, and maintainability
- **Safe Auto-Fix** for common issues like missing descriptions and aliases
- **Real-time Validation** via REST API or web UI
- **Zero Configuration** - works out of the box with sensible defaults
- **Comprehensive Reporting** with clear explanations of why issues matter
- **Stable Rule IDs** for consistent tooling and CI/CD integration

### Use Cases

- **Pre-deployment Validation**: Catch errors before they break your Home Assistant
- **Code Review**: Automated checks for automation pull requests
- **Learning Tool**: Understand Home Assistant automation best practices
- **Refactoring Aid**: Safely improve existing automations
- **Team Consistency**: Enforce standards across multiple contributors

---

## Quick Start

### Running the Service

```bash
# Start with docker-compose
docker-compose up automation-linter

# Check health
curl http://localhost:8020/health
```

### Using the Web UI

1. Open http://localhost:8020 in your browser
2. Paste your automation YAML
3. Click **Lint** to check for issues
4. Click **Auto-Fix (Safe)** to apply safe corrections
5. Copy or download the fixed YAML

### Using the API

```bash
# Lint automation YAML
curl -X POST http://localhost:8020/lint \
  -H "Content-Type: application/json" \
  -d '{
    "yaml": "alias: Test\ntrigger:\n  - platform: state\n    entity_id: sensor.test\naction:\n  - service: light.turn_on\n    target:\n      entity_id: light.test"
  }'

# Auto-fix automation YAML
curl -X POST http://localhost:8020/fix \
  -H "Content-Type: application/json" \
  -d '{
    "yaml": "alias: Test\ntrigger:\n  - platform: state\n    entity_id: sensor.test\naction:\n  - service: light.turn_on",
    "fix_mode": "safe"
  }'
```

---

## API Reference

### Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check and version info |
| GET | `/rules` | List all lint rules |
| POST | `/lint` | Lint automation YAML |
| POST | `/fix` | Lint and auto-fix automation YAML |
| GET | `/` | Web UI or API info |
| GET | `/docs` | Interactive API documentation |

---

### POST /lint

Lint automation YAML and return findings without modifying the input.

**Request Body:**

```json
{
  "yaml": "string (required)",
  "options": {
    "strict": false
  }
}
```

**Parameters:**
- `yaml` (string, required): The automation YAML to lint
- `options.strict` (boolean, optional): If true, treat warnings as errors

**Response:** `200 OK`

```json
{
  "engine_version": "0.1.0",
  "ruleset_version": "2026.02.1",
  "automations_detected": 1,
  "findings": [
    {
      "rule_id": "MAINTAINABILITY001",
      "severity": "info",
      "message": "Automation is missing 'description' field",
      "why_it_matters": "Descriptions help document the purpose of automations for future maintenance",
      "path": "automations[0]",
      "suggested_fix": {
        "type": "auto",
        "summary": "Add description field"
      }
    }
  ],
  "summary": {
    "errors_count": 0,
    "warnings_count": 0,
    "info_count": 1
  }
}
```

**Error Responses:**
- `413 Payload Too Large`: YAML exceeds 500KB limit
- `500 Internal Server Error`: Linting failed (check logs)

**Example:**

```bash
curl -X POST http://localhost:8020/lint \
  -H "Content-Type: application/json" \
  -d @- <<'EOF'
{
  "yaml": "alias: Living Room Light\ntrigger:\n  - platform: sun\n    event: sunset\naction:\n  - service: light.turn_on\n    target:\n      entity_id: light.living_room"
}
EOF
```

---

### POST /fix

Lint and auto-fix automation YAML, returning both findings and corrected YAML.

**Request Body:**

```json
{
  "yaml": "string (required)",
  "fix_mode": "safe"
}
```

**Parameters:**
- `yaml` (string, required): The automation YAML to fix
- `fix_mode` (string, optional): Fix mode - "none" or "safe" (default: "safe")

**Response:** `200 OK`

```json
{
  "engine_version": "0.1.0",
  "ruleset_version": "2026.02.1",
  "automations_detected": 1,
  "findings": [...],
  "summary": {
    "errors_count": 0,
    "warnings_count": 0,
    "info_count": 2
  },
  "fixed_yaml": "alias: Living Room Light\ndescription: ''\nid: living_room_light\ntrigger:\n- platform: sun\n  event: sunset\naction:\n- service: light.turn_on\n  target:\n    entity_id: light.living_room\n",
  "applied_fixes": ["MAINTAINABILITY001", "MAINTAINABILITY002"],
  "diff_summary": "Applied 2 fixes"
}
```

**Fix Modes:**
- `none`: No fixes applied, only report findings
- `safe`: Apply safe, deterministic fixes (current MVP)
- `opinionated`: Apply additional best-practice rewrites (future)

**Example:**

```bash
curl -X POST http://localhost:8020/fix \
  -H "Content-Type: application/json" \
  -d '{
    "yaml": "alias: Test\ntrigger:\n  - platform: state\n    entity_id: sensor.test\naction:\n  - service: light.turn_on\n    target:\n      entity_id: light.test",
    "fix_mode": "safe"
  }'
```

---

### GET /rules

List all available lint rules with metadata.

**Response:** `200 OK`

```json
{
  "ruleset_version": "2026.02.1",
  "rules": [
    {
      "rule_id": "SCHEMA001",
      "name": "Missing Trigger",
      "severity": "error",
      "category": "schema",
      "enabled": true
    },
    {
      "rule_id": "MAINTAINABILITY001",
      "name": "Missing Description",
      "severity": "info",
      "category": "maintainability",
      "enabled": true
    }
  ]
}
```

**Example:**

```bash
curl http://localhost:8020/rules | jq '.rules[] | select(.severity == "error")'
```

---

### GET /health

Health check endpoint for monitoring and load balancers.

**Response:** `200 OK`

```json
{
  "status": "healthy",
  "engine_version": "0.1.0",
  "ruleset_version": "2026.02.1",
  "timestamp": 1738627200.123
}
```

**Example:**

```bash
# Simple health check
curl http://localhost:8020/health

# Check if service is ready
curl -f http://localhost:8020/health || echo "Service unhealthy"
```

---

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────┐
│          FastAPI Service (Port 8020)        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ REST API │  │  Web UI  │  │  Health  │  │
│  └─────┬────┘  └──────────┘  └──────────┘  │
└────────┼──────────────────────────────────┬─┘
         │                                   │
         ▼                                   │
┌────────────────────────────────────────────┤
│      Shared Lint Engine Module             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │  Parser  │→ │  Engine  │→ │ Renderer │ │
│  └──────────┘  └────┬─────┘  └──────────┘ │
│                     │                       │
│                     ▼                       │
│              ┌──────────────┐               │
│              │  15+ Rules   │               │
│              │  - Schema    │               │
│              │  - Logic     │               │
│              │  - Reliability│              │
│              └──────────────┘               │
└──────────────────────────────────────────────┘
```

### Shared Module (`shared/ha_automation_lint/`)

The lint engine is implemented as a reusable Python module:

```
ha_automation_lint/
├── __init__.py           # Public API
├── constants.py          # Version and configuration constants
├── models.py             # Internal Representation (IR) models
├── engine.py             # Main lint orchestrator
├── parsers/
│   └── yaml_parser.py    # YAML → IR converter
├── rules/
│   ├── base.py           # Rule base class
│   └── mvp_rules.py      # 15 MVP rules
├── fixers/
│   └── auto_fixer.py     # Auto-fix engine
└── renderers/
    └── yaml_renderer.py  # IR → YAML converter
```

**Key Design Principles:**
- **Stateless**: No global state, safe for concurrent use
- **Testable**: Pure functions, dependency injection
- **Extensible**: Easy to add new rules
- **Stable**: Rule IDs never change after publication

### Service Wrapper (`services/automation-linter/`)

FastAPI service that wraps the shared module:

```
automation-linter/
├── src/
│   └── main.py           # FastAPI application
├── ui/
│   └── index.html        # Web interface
├── requirements.txt      # Python dependencies
└── Dockerfile            # Container image
```

### Test Corpus (`simulation/automation-linter/`)

Regression test suite with realistic examples:

```
automation-linter/
├── README.md             # Corpus documentation
├── valid/                # Valid automations (0 errors)
├── invalid/              # Known-bad automations
├── edge/                 # Edge cases and warnings
└── expected/             # Expected findings (JSON)
```

---

## Development

### Local Development Setup

```bash
# Install dependencies
cd services/automation-linter
pip install -r requirements.txt

# Run service locally
uvicorn src.main:app --reload --port 8020

# Run tests
pytest tests/automation-linter/
```

### Running Tests

```bash
# Unit tests (fast)
pytest tests/automation-linter/unit/ -v

# Integration tests (requires service)
pytest tests/automation-linter/integration/ -v

# Regression tests (corpus validation)
pytest tests/automation-linter/regression/ -v

# All tests with coverage
pytest tests/automation-linter/ --cov=shared/ha_automation_lint --cov-report=html
```

### Adding New Rules

See [automation-linter-rules.md](./automation-linter-rules.md) for the complete rule catalog.

**Steps to add a new rule:**

1. **Define the rule class** in `shared/ha_automation_lint/rules/mvp_rules.py`:

```python
class MyNewRule(Rule):
    rule_id = "CATEGORY999"
    name = "My New Rule"
    severity = Severity.WARN
    category = RuleCategory.LOGIC

    def check(self, automation: AutomationIR) -> List[Finding]:
        # Implement check logic
        return []
```

2. **Add to registry** in `get_all_rules()`:

```python
def get_all_rules() -> List[Rule]:
    return [
        # ... existing rules ...
        MyNewRule(),
    ]
```

3. **Add test cases** in `simulation/automation-linter/`:
   - Valid example (should not trigger)
   - Invalid example (should trigger)

4. **Update documentation** in `docs/automation-linter-rules.md`

5. **Increment RULESET_VERSION** in `shared/ha_automation_lint/constants.py`

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `MAX_YAML_SIZE_BYTES` | `500000` | Maximum request size (500KB) |
| `PROCESSING_TIMEOUT_SECONDS` | `30` | Processing timeout |

**Example:**

```yaml
# docker-compose.yml
automation-linter:
  environment:
    - LOG_LEVEL=DEBUG
    - MAX_YAML_SIZE_BYTES=1000000
```

### Docker Deployment

**Resource Limits:**
- Memory: 256M limit, 128M reservation
- CPU: 0.5 limit, 0.25 reservation

**Health Check:**
- Interval: 30s
- Timeout: 10s
- Retries: 3
- Start period: 10s

**Volumes (Development):**
```yaml
volumes:
  - ./services/automation-linter/src:/app/src           # Live reload
  - ./services/automation-linter/ui:/app/ui             # UI updates
  - ./shared/ha_automation_lint:/app/shared/ha_automation_lint  # Engine updates
```

---

## Limitations (MVP)

### Current Limitations

1. **Auto-Fix Scope**:
   - Only "safe" mode implemented
   - Limited to adding missing fields (description, alias)
   - No opinionated refactoring (planned for Phase 1)

2. **No Persistent Storage**:
   - Stateless service
   - No lint run history
   - No user accounts (planned for Phase 2)

3. **No Authentication**:
   - Open API (suitable for internal use)
   - No rate limiting beyond request size
   - Auth planned for hosted version (Phase 3)

4. **Performance**:
   - Single automation: <100ms
   - 100 automations: <3s
   - No streaming for large files

### Known Issues

- **Templates**: Complex Jinja2 templates in entity IDs may trigger false positives
- **Packages**: Package format (multiple keys) not fully supported
- **Custom Components**: Rules assume core HA platforms only

---

## Roadmap

### Phase 1: Hardening (Q2 2026)

**Goal:** Production-ready with expanded rule set

- [ ] Expand to 40-60 rules based on real-world usage
- [ ] Improved auto-fix with JSONPath patching
- [ ] Advanced reporting (group by automation, category)
- [ ] Performance optimization for large YAML files
- [ ] Rule severity override configuration
- [ ] YAML diff preview for fixes
- [ ] Telemetry for rule effectiveness

### Phase 2: "Prove Paid" (Q3 2026)

**Goal:** Validate paid service model within HomeIQ

- [ ] User identity (email + magic link)
- [ ] Usage limits (runs/day, fix downloads)
- [ ] Purchase tracking (one-time unlock: $1 "supporter")
- [ ] Run history storage (opt-in)
- [ ] User dashboard
- [ ] Payment integration (Stripe)

### Phase 3: Standalone Service (Q4 2026)

**Goal:** Carve out to independent hosted service

- [ ] Extract shared module to independent package
- [ ] Standalone deployment configuration
- [ ] Domain + TLS setup
- [ ] Advanced rate limiting (per-user + per-IP)
- [ ] Billing provider integration
- [ ] User account management
- [ ] Terms/privacy pages
- [ ] Marketing site and documentation

---

## Troubleshooting

### Service Won't Start

```bash
# Check logs
docker-compose logs automation-linter

# Verify port is available
netstat -an | grep 8020

# Test shared module import
docker-compose exec automation-linter python -c "from ha_automation_lint import LintEngine; print('OK')"
```

### Health Check Failing

```bash
# Manual health check
curl -v http://localhost:8020/health

# Check from inside container
docker-compose exec automation-linter curl localhost:8020/health
```

### Lint Returns Unexpected Results

```bash
# Check ruleset version
curl http://localhost:8020/health | jq '.ruleset_version'

# List enabled rules
curl http://localhost:8020/rules | jq '.rules[] | select(.enabled == true) | .rule_id'

# Test specific YAML
curl -X POST http://localhost:8020/lint \
  -H "Content-Type: application/json" \
  -d @simulation/automation-linter/valid/simple-light.yaml
```

---

## Support

### Documentation

- **Rules Catalog**: [automation-linter-rules.md](./automation-linter-rules.md)
- **Implementation Plan**: [implementation/automation-linter-implementation-plan.md](./implementation/automation-linter-implementation-plan.md)
- **Test Corpus**: [simulation/automation-linter/README.md](../simulation/automation-linter/README.md)

### Getting Help

- **GitHub Issues**: https://github.com/wtthornton/HomeIQ/issues
- **API Documentation**: http://localhost:8020/docs (when service is running)

---

## License

Part of the HomeIQ project. See [LICENSE](../LICENSE) for details.

---

**Last Updated:** 2026-02-03
**Maintainer:** HomeIQ Team
**Version:** 0.1.0 MVP
