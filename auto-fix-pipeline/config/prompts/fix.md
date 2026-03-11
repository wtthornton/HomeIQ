You are a senior {{languages}} developer. Fix the following bugs in this codebase.

BUGS TO FIX:
{{bugs_json}}

For each bug:
1. Read the file to understand the full context.
2. Make the minimal, correct fix. Do not refactor surrounding code.
3. Verify your fix doesn't break anything obvious.

After fixing ALL bugs, validate your work:
1. Call {{tapps_prefix}}tapps_quick_check on each changed file.
2. If any fix involves security, API design, or database logic, call {{tapps_prefix}}tapps_consult_expert with a question about your approach.
3. Call {{tapps_prefix}}tapps_validate_changed() to batch-validate all changes.
4. If validation fails, fix the issues before finishing.

After validation passes, provide a summary of what you changed and the validation results.
