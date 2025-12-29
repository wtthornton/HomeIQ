# Plan Command

Create development plan with user stories, acceptance criteria, and estimates.

## Usage

```
@plan "<description>"
```

Or with natural language:
```
Plan a user authentication feature
Create a plan for a REST API for products
Plan the implementation of user registration
```

## What It Does

1. **Analyzes Requirements**: Understands the feature description
2. **Creates User Stories**: Breaks down into user stories
3. **Defines Acceptance Criteria**: Adds acceptance criteria for each story
4. **Estimates Effort**: Provides story point estimates
5. **Identifies Dependencies**: Maps dependencies between stories

## Examples

```
@plan "Create a user authentication API with JWT tokens"
@plan "Add CRUD operations for products"
@plan "Implement user registration with email verification"
```

## Output

- User stories with IDs
- Acceptance criteria for each story
- Story point estimates
- Dependency mapping
- Priority recommendations

## Format

```
## User Story 1: User Registration

**Description**: As a user, I want to register with email and password

**Acceptance Criteria**:
- User can register with valid email and password
- Email validation is performed
- Password meets security requirements
- User receives confirmation email

**Story Points**: 5
**Priority**: High
**Dependencies**: None
```

## Integration

- **Cursor**: Use `@planner *plan "<desc>"` (Cursor Skill)
- **Claude Desktop**: Use `@plan "<desc>"` (this command)
- **CLI**: Use `tapps-agents planner plan "<desc>"`

