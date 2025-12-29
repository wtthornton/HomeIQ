# Refactor Command

Refactor existing code to improve quality, maintainability, and performance.

## Usage

```
@refactor <file-path> "<instructions>"
```

Or with natural language:
```
Refactor src/api/auth.py to improve error handling
Refactor src/utils/helpers.py to reduce complexity
Improve the code structure in src/models/user.py
```

## What It Does

1. **Analyzes Code**: Examines current code structure and patterns
2. **Applies Refactoring**: Implements improvements based on instructions
3. **Maintains Functionality**: Ensures refactoring doesn't break existing behavior
4. **Improves Quality**: Enhances code quality, readability, and maintainability
5. **Updates Tests**: Updates tests if needed to match refactored code

## Examples

```
@refactor src/api/auth.py "Extract helper functions, improve error handling"
@refactor src/utils/helpers.py "Reduce cyclomatic complexity, add type hints"
@refactor src/models/user.py "Improve data validation, add docstrings"
```

## Common Refactoring Patterns

- **Extract Functions**: Break down complex functions
- **Improve Naming**: Use clearer variable and function names
- **Add Type Hints**: Improve type safety
- **Reduce Complexity**: Simplify complex logic
- **Improve Error Handling**: Add proper error handling
- **Add Documentation**: Improve docstrings and comments

## Output

- Refactored code file
- Quality improvement metrics
- Test updates (if needed)
- Refactoring summary

## Integration

- **Cursor**: Use `@implementer *refactor <file> "<instructions>"` (Cursor Skill)
- **Claude Desktop**: Use `@refactor <file> "<instructions>"` (this command)
- **CLI**: Use `tapps-agents implementer refactor <file> "<instructions>"`

