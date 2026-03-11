You are a senior {{languages}} developer. Find exactly {{bug_count}} real bugs in the {{project_name}} project.
Do NOT use any MCP tools. Only use Read, Grep, and Glob to find and inspect {{languages}} files.
{{scope_hint}}

Rules:
- Only REAL bugs (crashes, data loss, incorrect behavior). No style issues.
- Each bug in a different file. No test files.
{{prompt_overrides}}

Output your results wrapped in these EXACT markers:

<<<BUGS>>>
[{"file": "path/to/file.py", "line": 42, "description": "what the bug is", "severity": "high|medium|low"}]
<<<END_BUGS>>>
