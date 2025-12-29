# Design Command

Create system architecture and component design for a feature or system.

## Usage

```
@design "<description>"
```

Or with natural language:
```
Design the architecture for a user authentication system
Create a system design for a REST API
Design the component structure for user management
```

## What It Does

1. **Analyzes Requirements**: Understands system requirements
2. **Designs Architecture**: Creates high-level system architecture
3. **Defines Components**: Identifies and designs components
4. **Maps Data Flow**: Shows how data flows through the system
5. **Considers Performance**: Includes performance considerations

## Examples

```
@design "User authentication system with JWT tokens"
@design "REST API for product management"
@design "Microservice architecture for user management"
```

## Output

- System architecture diagram (text/ASCII)
- Component descriptions
- Data flow diagrams
- Technology stack recommendations
- Performance considerations
- Scalability recommendations

## Format

```
## System Architecture

### Components
- Authentication Service
- User Management Service
- Token Service

### Data Flow
1. User → Authentication Service → Token Service
2. Token Service → User Management Service

### Technology Stack
- FastAPI for API
- PostgreSQL for database
- Redis for caching
```

## Integration

- **Cursor**: Use `@architect *design "<desc>"` (Cursor Skill)
- **Claude Desktop**: Use `@design "<desc>"` (this command)
- **CLI**: Use `tapps-agents architect design "<desc>"`

