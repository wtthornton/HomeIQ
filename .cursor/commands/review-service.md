# Review Service

Review a HomeIQ microservice for code quality, architecture compliance, and Epic 31 patterns.

## Instructions

1. Use TappsCodingAgents to review the service:
   ```
   @simple-mode *review {{service_path}}
   ```

2. Check for Epic 31 compliance:
   - ✅ Direct InfluxDB writes (no enrichment-pipeline)
   - ✅ Standalone service pattern
   - ✅ Health endpoint at `/health`
   - ✅ Proper logging with correlation IDs

3. Verify quality thresholds:
   - Overall score ≥ 70 (≥ 80 for critical services)
   - Security score ≥ 7.0/10
   - Maintainability ≥ 7.0/10

4. Report findings and suggest improvements.

## Parameters

- `service_path`: Path to the service main.py file (e.g., `services/data-api/src/main.py`)
