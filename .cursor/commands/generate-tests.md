# Generate Tests

Generate comprehensive tests for HomeIQ code.

## Instructions

### Using Simple Mode (Recommended)
```
@simple-mode *test {{file_path}}
```

### Using CLI
```bash
# Generate and run tests
python -m tapps_agents.cli tester test {{file_path}}

# Generate with integration tests
python -m tapps_agents.cli tester test {{file_path}} --integration

# Generate without running
python -m tapps_agents.cli tester generate-tests {{file_path}}
```

## Test Standards

- Target coverage: ≥ 80%
- Use pytest for Python services
- Use Vitest for React components
- Use Playwright for E2E tests

## Running Tests

### Python Services
```bash
cd services/{{service_name}}
pytest tests/ -v --cov=src
```

### React (health-dashboard)
```bash
cd services/health-dashboard
npm run test
npm run test:e2e
```

## Parameters

- `file_path`: Path to file to generate tests for
