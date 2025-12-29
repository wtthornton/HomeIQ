# Claude Desktop Commands

This directory contains Claude Desktop commands that work alongside Cursor Skills. These commands provide the same functionality in both Claude Desktop and Cursor IDE.

## Quick Start

Use commands in Claude Desktop by typing `@command-name`:

```
@review src/api/auth.py
@build "Create a user authentication feature"
@test src/api/auth.py
```

## Available Commands

### Core Development Commands

| Command | Description | Cursor Equivalent |
|---------|-------------|-------------------|
| `@review` | Full code review with scoring | `@reviewer *review` |
| `@score` | Quick quality scoring | `@reviewer *score` |
| `@implement` | Generate code from description | `@implementer *implement` |
| `@test` | Generate and run tests | `@tester *test` |
| `@debug` | Debug errors and find root cause | `@debugger *debug` |
| `@refactor` | Refactor code with instructions | `@implementer *refactor` |
| `@improve` | Improve code quality | `@improver *improve` |
| `@lint` | Run code linting | `@reviewer *lint` |

### Planning & Design Commands

| Command | Description | Cursor Equivalent |
|---------|-------------|-------------------|
| `@plan` | Create development plan | `@planner *plan` |
| `@design` | Design system architecture | `@architect *design` |
| `@docs` | Generate documentation | `@documenter *document` |

### Quality & Security Commands

| Command | Description | Cursor Equivalent |
|---------|-------------|-------------------|
| `@security-scan` | Scan for vulnerabilities | `@reviewer *security-scan` |
| `@library-docs` | Get library documentation | `@reviewer *docs` |

### Workflow Commands (Simple Mode)

| Command | Description | Cursor Equivalent |
|---------|-------------|-------------------|
| `@build` | Complete feature workflow | `@simple-mode *build` |
| `@fix` | Fix bugs with debugging | `@simple-mode *fix` |

## Usage Examples

### Code Review
```
@review src/api/auth.py
@score src/utils/helpers.py
@lint src/ --fix
```

### Code Generation
```
@implement "Create a user authentication API" src/api/auth.py
@refactor src/api/auth.py "Improve error handling"
@improve src/utils/helpers.py "Add type hints"
```

### Testing
```
@test src/api/auth.py
@test src/utils/helpers.py --integration
```

### Debugging
```
@debug "Null pointer error on line 42" --file src/api/auth.py
@fix src/api/auth.py "Fix authentication token validation"
```

### Planning & Design
```
@plan "Create a user authentication feature"
@design "REST API for product management"
@docs src/api/auth.py
```

### Complete Workflows
```
@build "Create a user authentication API with JWT tokens"
@fix src/api/auth.py "Fix the null pointer error"
```

### Library Documentation
```
@library-docs fastapi
@library-docs fastapi routing
@library-docs pytest fixtures
```

## Integration with Cursor Skills

These commands are designed to work alongside Cursor Skills:

- **Claude Desktop**: Use `@command-name` (these commands)
- **Cursor IDE**: Use `@agent-name *command` (Cursor Skills)
- **CLI**: Use `tapps-agents <agent> <command>` (terminal)

All three interfaces provide the same functionality, so you can use whichever is most convenient for your workflow.

## Command Details

See individual command files for detailed usage:
- `review.md` - Code review with scoring
- `score.md` - Quick quality scoring
- `implement.md` - Code generation
- `test.md` - Test generation
- `debug.md` - Error debugging
- `build.md` - Complete feature workflow
- `fix.md` - Bug fixing workflow
- `refactor.md` - Code refactoring
- `improve.md` - Code improvement
- `lint.md` - Code linting
- `plan.md` - Development planning
- `design.md` - System design
- `docs.md` - Documentation generation
- `security-scan.md` - Security scanning
- `library-docs.md` - Library documentation

## Best Practices

1. **Use `@build` for new features** - Complete workflow with all quality gates
2. **Use `@review` before committing** - Ensure code quality
3. **Use `@test` after implementation** - Verify functionality
4. **Use `@fix` for bugs** - Systematic debugging workflow
5. **Use `@library-docs` for API reference** - Get up-to-date library docs

## Configuration

Commands use the same configuration as Cursor Skills:
- `.tapps-agents/config.yaml` - Project configuration
- `.tapps-agents/kb/context7-cache` - Library documentation cache

## Troubleshooting

If a command doesn't work:
1. Check that TappsCodingAgents is installed: `pip list | grep tapps-agents`
2. Verify configuration: Check `.tapps-agents/config.yaml`
3. Check command syntax: See individual command files
4. Try CLI equivalent: `tapps-agents <agent> <command>`

## Related Documentation

- **Cursor Skills**: See `.claude/skills/` for Cursor Skills
- **CLI Reference**: See `docs/TAPPS_AGENTS_COMMAND_REFERENCE.md`
- **Quick Reference**: See `.cursor/rules/quick-reference.mdc`

