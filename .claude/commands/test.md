# Test Command

Generate comprehensive tests for code files with coverage analysis.

## Usage

```
@test <file-path>
```

Or with natural language:
```
Generate tests for src/api/auth.py
Add test coverage for src/utils/helpers.py
Create tests for the authentication module
```

## What It Does

1. **Analyzes Code**: Understands the code structure and functionality
2. **Generates Tests**: Creates unit tests and integration tests
3. **Runs Tests**: Executes the test suite
4. **Reports Coverage**: Shows test coverage metrics
5. **Validates**: Ensures tests pass and cover critical paths

## Examples

```
@test src/api/auth.py
@test src/utils/helpers.py
@test tests/test_auth.py --integration
```

## Features

- **Unit Tests**: Tests individual functions and methods
- **Integration Tests**: Tests component interactions (optional)
- **Coverage Analysis**: Reports code coverage percentage
- **Test Patterns**: Follows project testing patterns (pytest, unittest, etc.)
- **Edge Cases**: Includes edge case and error handling tests

## Output

- Generated test files
- Test execution results
- Coverage report
- Test pass/fail status

## Integration

- **Cursor**: Use `@tester *test <file>` (Cursor Skill)
- **Claude Desktop**: Use `@test <file>` (this command)
- **CLI**: Use `tapps-agents tester test <file>`

