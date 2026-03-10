# Auto-Bugfix Scan Output Format

The auto-bugfix pipeline (`scripts/auto-bugfix.ps1`) expects the **scan** phase (Claude) to produce a machine-parseable bug list so the **fix** phase can target specific files and lines.

## Required format

The scan output must include a **single JSON array** of bug objects wrapped in exact markers:

```
<<<BUGS>>>
[{"file": "path/to/file.py", "line": 42, "description": "what the bug is", "severity": "high|medium|low"}]
<<<END_BUGS>>>
```

- **Markers:** `<<<BUGS>>>` and `<<<END_BUGS>>>` (three angle brackets each, no spaces).
- **Content:** A valid JSON array. Each element must have:
  - `file` (str): path relative to project root, e.g. `domains/core-platform/admin-api/src/main.py`
  - `line` (int): line number
  - `description` (str): short explanation of the bug
  - `severity` (str): one of `"high"`, `"medium"`, `"low"`

## Extraction and validation

1. The script extracts content between `<<<BUGS>>>` and `<<<END_BUGS>>>` via regex.
2. If that fails, it tries a fallback regex for a JSON array `[{ ... }]` in the raw output.
3. The extracted string is parsed as JSON; invalid JSON causes an error exit.
4. If no valid output is produced on the first attempt, the pipeline **retries once** with a “direct code review only” prompt (no MCP tools). **Max attempts: 2.**

## When scan fails

- After each failed attempt, raw output is written to `$env:TEMP\auto-bugfix-raw-attemptN.txt`.
- If both attempts fail, the script also copies the last attempt to `implementation/auto-bugfix-scan-failure-YYYYMMDD-HHmmss.txt` (if the directory exists) for inspection.
- The script exits with error code 1 and a message pointing to the saved file(s).

## References

- Scan prompts: `scripts/auto-bugfix.ps1` (inline `$findPrompt`, `$retryPrompt`)
- Prompt overrides: `docs/FIND_PROMPT_OVERRIDES.md`
