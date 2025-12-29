# Documentation Command

Generate documentation for code files, APIs, or entire projects.

## Usage

```
@docs <file-path>
```

Or with natural language:
```
Document the API in src/api/auth.py
Generate documentation for src/utils/helpers.py
Create API documentation for the authentication module
```

## What It Does

1. **Analyzes Code**: Examines code structure and functionality
2. **Generates Documentation**: Creates comprehensive documentation
3. **Includes Examples**: Adds code examples and usage patterns
4. **Formats Properly**: Uses appropriate documentation format (Markdown, etc.)

## Examples

```
@docs src/api/auth.py
@docs src/utils/helpers.py
@docs README.md --update
```

## Features

- **API Documentation**: Documents API endpoints and parameters
- **Function Documentation**: Documents functions and methods
- **Usage Examples**: Includes code examples
- **Type Information**: Documents types and parameters
- **Error Handling**: Documents error cases

## Output

- Documentation file (Markdown, etc.)
- API reference documentation
- Usage examples
- Type information

## Integration

- **Cursor**: Use `@documenter *document <file>` (Cursor Skill)
- **Claude Desktop**: Use `@docs <file>` (this command)
- **CLI**: Use `tapps-agents documenter document <file>`

