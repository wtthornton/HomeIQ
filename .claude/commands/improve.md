# Improve Command

Improve code quality, maintainability, and performance based on specific instructions.

## Usage

```
@improve <file-path> "<instructions>"
```

Or with natural language:
```
Improve error handling in src/api/auth.py
Optimize performance in src/utils/helpers.py
Enhance code quality in src/models/user.py
```

## What It Does

1. **Analyzes Code**: Examines current code quality
2. **Applies Improvements**: Implements improvements based on instructions
3. **Enhances Quality**: Improves maintainability, performance, readability
4. **Maintains Functionality**: Ensures improvements don't break existing behavior

## Examples

```
@improve src/api/auth.py "Add input validation, improve error handling"
@improve src/utils/helpers.py "Optimize performance, reduce memory usage"
@improve src/models/user.py "Add type hints, improve documentation"
```

## Common Improvements

- **Error Handling**: Add proper error handling and validation
- **Performance**: Optimize algorithms and reduce complexity
- **Readability**: Improve code structure and naming
- **Type Safety**: Add type hints and validation
- **Documentation**: Improve docstrings and comments
- **Testing**: Add missing test coverage

## Output

- Improved code file
- Quality improvement metrics
- Summary of changes

## Integration

- **Cursor**: Use `@improver *improve <file> "<instructions>"` (Cursor Skill)
- **Claude Desktop**: Use `@improve <file> "<instructions>"` (this command)
- **CLI**: Use `tapps-agents improver improve <file> "<instructions>"`

