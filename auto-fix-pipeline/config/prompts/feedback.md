You just completed an automated bugfix run. Review how the TappsMCP tools performed
during this session and write structured feedback to {{feedback_file}}.

Run context:
- Date: {{run_timestamp}}
- Branch: {{branch}}
- Bugs fixed: {{bug_count}}
- Files changed: {{changed_files}}

Evaluate each TappsMCP tool you used (tapps_validate_changed, tapps_checklist, tapps_quick_check):

Write a markdown file at {{feedback_file}} with a header and entries using this format:

# TappsMCP Feedback - {{run_timestamp}}

### [CATEGORY] P[0-2]: One-line summary
- **Date**: {{run_timestamp}}
- **Run**: {{branch}}
- **Tool**: tool_name
- **Detail**: What happened, what was expected, what was actual
- **Recurrence**: 1

Categories: BUG, FALSE_POSITIVE, FALSE_NEGATIVE, UX, PERF, ENHANCEMENT, INTEGRATION

Also call {{tapps_prefix}}tapps_feedback for each tool you used (helpful=true/false with context).

If ALL tools worked perfectly with no issues, write a short note saying so -- keep the file for the audit trail.
Check {{feedback_dir}}/ for previous feedback files to look for recurring issues.
