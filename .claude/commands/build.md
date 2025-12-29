# Build Command (Simple Mode)

Complete feature development workflow with all quality gates. This is the most powerful command for building new features.

## Usage

```
@build "<description>"
```

Or with natural language:
```
Build a user authentication feature with JWT tokens
Create a REST API for managing products
Add user registration with email verification
```

## What It Does

Executes a complete 7-step workflow:

1. **Enhance Prompt** - Analyzes requirements and creates comprehensive specification
2. **Create User Stories** - Breaks down into user stories with acceptance criteria
3. **Design Architecture** - Creates system architecture and component design
4. **Design API/Models** - Designs API endpoints and data models
5. **Implement Code** - Generates code following all specifications
6. **Review Code** - Reviews code quality with scoring (loops if score < 70)
7. **Generate Tests** - Creates comprehensive test suite

## Examples

```
@build "Create a user authentication API with JWT tokens"
@build "Add CRUD operations for products with validation"
@build "Implement user registration with email verification"
```

## Features

- **Complete Workflow**: All steps from requirements to tests
- **Quality Gates**: Automatic quality checks with loopback
- **Documentation**: Creates workflow documentation at each step
- **Best Practices**: Follows SDLC best practices
- **Comprehensive**: Includes architecture, design, implementation, testing

## Output

- Enhanced requirements document
- User stories with acceptance criteria
- Architecture design document
- API/data model specifications
- Implemented code files
- Code review report
- Test suite with coverage

## Quality Gates

- Overall score must be ≥ 70 (loops back if below)
- Security score must be ≥ 7.0
- All tests must pass

## Integration

- **Cursor**: Use `@simple-mode *build "<desc>"` (Cursor Skill)
- **Claude Desktop**: Use `@build "<desc>"` (this command)
- **CLI**: Use `tapps-agents simple-mode full --prompt "<desc>" --auto`

## Documentation Created

All workflow documentation is saved to:
- `docs/workflows/simple-mode/step1-enhanced-prompt.md`
- `docs/workflows/simple-mode/step2-user-stories.md`
- `docs/workflows/simple-mode/step3-architecture.md`
- `docs/workflows/simple-mode/step4-design.md`
- `docs/workflows/simple-mode/step6-review.md`
- `docs/workflows/simple-mode/step7-testing.md`

