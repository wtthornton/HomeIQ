# Code Score Command

Quick code quality scoring without detailed feedback. Faster than full review.

## Usage

```
@score <file-path>
```

Or with natural language:
```
Score src/api/auth.py
What's the quality score of src/utils/helpers.py?
```

## What It Does

Calculates objective quality metrics only (no LLM feedback):
- Complexity Score (0-10)
- Security Score (0-10)
- Maintainability Score (0-10)
- Test Coverage Score (0-100%)
- Performance Score (0-10)
- Overall Score (0-100)

## Examples

```
@score src/api/auth.py
@score src/utils/helpers.py
```

## Output Format

Quick score summary:
```
📊 Code Scores: src/api/auth.py

- Complexity: 7.2/10 ✅
- Security: 8.5/10 ✅
- Maintainability: 7.8/10 ✅
- Test Coverage: 85% ✅
- Performance: 7.0/10 ✅
- Overall: 76.5/100 ✅ PASS
```

## When to Use

- Quick quality checks before committing
- CI/CD quality gates
- Comparing code quality across files
- Fast feedback during development

## Integration

- **Claude Desktop**: Use `@score <file>` (this command)

