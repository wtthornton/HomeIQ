# Quality Check

Quick quality check for HomeIQ code before committing.

## Instructions

### Quick Score (Fast, No LLM)
```bash
python -m tapps_agents.cli reviewer score {{file_path}}
```

### Full Review (With LLM Feedback)
```
@simple-mode *review {{file_path}}
```

### Lint Check
```bash
python -m tapps_agents.cli reviewer lint {{file_path}}
```

### Type Check
```bash
python -m tapps_agents.cli reviewer type-check {{file_path}}
```

## Quality Thresholds

| Metric | Standard | Critical Services |
|--------|----------|-------------------|
| Overall Score | ≥ 70 | ≥ 80 |
| Security | ≥ 7.0/10 | ≥ 8.0/10 |
| Maintainability | ≥ 7.0/10 | ≥ 8.0/10 |
| Test Coverage | ≥ 80% | ≥ 90% |

**Critical Services:** websocket-ingestion, data-api, health-dashboard

## Parameters

- `file_path`: Path to file or directory to check
