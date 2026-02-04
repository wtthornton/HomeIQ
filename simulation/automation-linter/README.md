# Automation Linter Test Corpus

This directory contains test YAML files for regression testing the HomeIQ Automation Linter.

## Purpose

The test corpus ensures that:
- Valid automations pass without errors
- Invalid automations are correctly identified
- Edge cases are handled appropriately
- Rule stability is maintained across versions

## Structure

### `valid/` - Valid Automations
Contains properly formatted Home Assistant automations that should not trigger any errors. These may trigger info or warning messages for best practices, but should have 0 errors.

Examples include:
- Simple automations (lights, switches)
- Multi-trigger automations
- Automations with conditions
- Complex action sequences (choose, repeat, etc.)
- Automations with variables and templates

### `invalid/` - Invalid Automations
Contains automations with known errors that must be detected by the linter. Each file demonstrates a specific error condition.

Examples include:
- Missing required keys (trigger, action)
- Invalid formats (service names, entity IDs)
- Schema violations
- Duplicate IDs

### `edge/` - Edge Cases
Contains automations that demonstrate edge cases or potential issues that should trigger warnings or info messages.

Examples include:
- Performance concerns (high-frequency triggers)
- Logic issues (delay with single mode)
- Maintainability issues (missing descriptions)

### `expected/` - Expected Results
Contains JSON files with expected findings for each test case. Used for regression testing.

## Naming Convention

Files should be named descriptively:
- `{description}.yaml` - The test automation
- `{description}.json` - Expected findings (in `expected/` directory)

Examples:
- `valid/simple-light.yaml`
- `invalid/missing-trigger.yaml`
- `edge/delay-single-mode.yaml`

## Adding New Test Cases

1. Create the YAML file in the appropriate directory
2. Run the linter to generate findings:
   ```bash
   curl -X POST http://localhost:8020/lint \
     -H "Content-Type: application/json" \
     -d @test.json
   ```
3. Save expected findings to `expected/{filename}.json`
4. Add the test case to regression tests

## Running Tests

### Manual Testing
```bash
# Test a single file
curl -X POST http://localhost:8020/lint \
  -H "Content-Type: application/json" \
  -d '{"yaml": "$(cat valid/simple-light.yaml)"}'

# Test with auto-fix
curl -X POST http://localhost:8020/fix \
  -H "Content-Type: application/json" \
  -d '{"yaml": "$(cat invalid/missing-description.yaml)", "fix_mode": "safe"}'
```

### Automated Testing
```bash
# Run regression tests
pytest tests/automation-linter/regression/

# Run all tests
pytest tests/automation-linter/
```

## Test Coverage

The corpus covers all MVP rules:

**Schema Rules (SCHEMA001-005):**
- ✅ Missing trigger
- ✅ Missing action
- ✅ Unknown top-level keys
- ✅ Duplicate IDs
- ✅ Invalid service format

**Syntax Rules (SYNTAX001):**
- ✅ Trigger missing platform

**Logic Rules (LOGIC001-005):**
- ✅ Delay with single mode
- ✅ High-frequency trigger without debounce
- ✅ Choose without default
- ✅ Empty trigger list
- ✅ Empty action list

**Reliability Rules (RELIABILITY001-002):**
- ✅ Service missing target
- ✅ Invalid entity_id format

**Maintainability Rules (MAINTAINABILITY001-002):**
- ✅ Missing description
- ✅ Missing alias

## Maintenance

- Update test cases when rules are added or modified
- Maintain expected findings when ruleset version changes
- Keep examples realistic and based on actual Home Assistant patterns
- Document any special test conditions or requirements
