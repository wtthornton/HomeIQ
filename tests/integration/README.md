# Integration Tests (Epic 53)

Integration tests that run against real services (Docker). See [Epic 53](../../stories/epic-53-ask-ai-integration-validation.md).

## Ask AI + HA validation

- **Test:** `test_ask_ai_ha_validation.py` — full Ask AI flow and HA automation validation
- **Schema:** `schemas/ask_ai_response_schema.md` — response shapes for query/suggestions/test/approve
- **Helper:** `helpers/ha_automation_validation.py` — list automations and check if an automation_id exists in deploy service or HA

### Prerequisites

- ai-automation-service running (Ask AI API), e.g. port 8024
- For HA validation: set **DEPLOY_SERVICE_URL** (e.g. `http://localhost:8036`) and/or **HA_URL** + **HA_TOKEN**

### Run

```bash
# From project root
pytest tests/integration/test_ask_ai_ha_validation.py -v

# With env (PowerShell)
$env:ASK_AI_API_URL = "http://localhost:8024/api/v1/ask-ai"
$env:DEPLOY_SERVICE_URL = "http://localhost:8036"
$env:HA_URL = "http://192.168.1.86:8123"
$env:HA_TOKEN = "your-long-lived-token"
pytest tests/integration/test_ask_ai_ha_validation.py -v
```

If root `tests/conftest.py` ignores the `integration` directory, run from inside the folder:

```bash
cd tests/integration
pytest test_ask_ai_ha_validation.py -v
```

### Env vars

| Variable | Description | Default |
|----------|-------------|---------|
| ASK_AI_API_URL | Ask AI base URL | http://localhost:8024/api/v1/ask-ai |
| DEPLOY_SERVICE_URL | Deploy service (list automations) | http://localhost:8036 |
| DEPLOY_AUTH_HEADER | Optional Bearer token for deploy | — |
| HA_URL | Home Assistant URL (direct) | — |
| HA_TOKEN | HA long-lived access token | — |

### CI (Epic 53.4)

Ask AI integration tests are **not** in the default CI run (they require OpenAI, HA, and Docker). Decision: **local/on-demand**. To run in CI, add an optional job with `ASK_AI_INTEGRATION_ENABLED=true` and secrets; see [Epic 53 Story 53.4](../../stories/epic-53-story-04-ci-integration-optional.md).
