# Implement Command

Generate code from natural language description following project patterns and best practices.

## Usage

```
@implement "<description>" <file-path>
```

Or with natural language:
```
Implement a user authentication API with JWT tokens in src/api/auth.py
Create a REST endpoint for products in src/api/products.py
```

## What It Does

1. **Analyzes Requirements**: Understands the description and requirements
2. **Follows Project Patterns**: Uses existing code patterns and conventions
3. **Generates Code**: Creates implementation following best practices
4. **Includes Documentation**: Adds docstrings and comments
5. **Auto-Review**: Optionally reviews generated code for quality

## Examples

```
@implement "Create a user authentication API with JWT tokens" src/api/auth.py
@implement "Add CRUD operations for products" src/api/products.py
@implement "Create a utility function to validate email addresses" src/utils/validation.py
```

## Features

- **Context-Aware**: Understands project structure and dependencies
- **Pattern Matching**: Follows existing code patterns
- **Type Hints**: Includes proper type annotations
- **Error Handling**: Includes appropriate error handling
- **Documentation**: Adds docstrings and comments

## Output

- Generated code file
- Quality score (if auto-review enabled)
- Documentation and comments
- Integration with existing codebase

## Integration

- **Cursor**: Use `@implementer *implement "<desc>" <file>` (Cursor Skill)
- **Claude Desktop**: Use `@implement "<desc>" <file>` (this command)
- **CLI**: Use `tapps-agents implementer implement "<desc>" <file>`

