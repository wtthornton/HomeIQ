# Library Documentation Command

Get up-to-date library documentation from Context7 knowledge base.

## Usage

```
@library-docs <library-name> [topic]
```

Or with natural language:
```
Show me FastAPI routing documentation
Get pytest fixtures documentation
Look up SQLAlchemy query documentation
```

## What It Does

1. **Searches Cache**: Checks Context7 KB cache first (fast, <0.15s)
2. **Fetches Documentation**: Gets library documentation from Context7 API
3. **Filters by Topic**: Optionally filters by specific topic
4. **Provides Examples**: Includes code examples and usage patterns

## Examples

```
@library-docs fastapi
@library-docs fastapi routing
@library-docs pytest fixtures
@library-docs sqlalchemy queries
```

## Features

- **KB-First Caching**: Uses cached documentation when available (90%+ hit rate)
- **Up-to-Date**: Fetches latest documentation from Context7
- **Topic Filtering**: Can filter by specific topics
- **Code Examples**: Includes practical code examples
- **Cross-References**: Links to related libraries

## Output

- Library documentation
- Code examples
- API reference
- Best practices
- Related libraries

## Integration

- **Cursor**: Use `@reviewer *docs <library> [topic]` (Cursor Skill)
- **Claude Desktop**: Use `@library-docs <library> [topic]` (this command)
- **CLI**: Use `tapps-agents reviewer docs <library> [topic]`

## Context7 Setup

Requires Context7 API key in `.tapps-agents/config.yaml`:
```yaml
context7:
  enabled: true
  api_key: "your-api-key"
```

