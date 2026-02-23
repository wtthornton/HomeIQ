# TappsMCP Coverage Metrics Research and Fixes

**Date:** 2026-02-23  
**Status:** Implemented workarounds; TappsMCP fix needed  
**Related:** TappsMCP dashboard, coverage metrics

---

## Summary

The TappsMCP dashboard shows **Coverage Metrics** all as 0 (files_scored, files_gated, files_scanned, docs_lookup_calls, checklist_calls) despite tool_metrics clearly showing tool usage (tapps_score_file: 36, tapps_quality_gate: 10, tapps_security_scan: 5, etc.). Research identified the root cause and implemented project-side mitigations. **TappsMCP maintainers need to fix path normalization on Windows** for coverage metrics to work.

---

## Findings

### Evidence

- **tool_calls JSONL** (` .tapps-mcp/metrics/tool_calls_*.jsonl`) contains valid records with `file_path` populated:
  - `tapps_score_file` with `file_path: "C:\\cursor\\HomeIQ\\services\\weather-api\\src\\main.py"`
  - `tapps_quality_gate` with `file_path` set
  - `tapps_security_scan` with `file_path` set
- **coverage_metrics** returns: `files_scored: 0`, `files_gated: 0`, `files_scanned: 0`, `core_tools_used: []`, `core_tools_unused: ["tapps_checklist", "tapps_quality_gate", "tapps_score_file", "tapps_security_scan"]`

### Root Cause

Coverage metrics aggregation filters tool calls by "path under project root." On Windows, path comparison likely fails due to:

- Case sensitivity (`C:\` vs `c:\`)
- Backslash vs forward slash normalization
- Project root not matching logged paths when dashboard aggregates

---

## Implemented Fixes (HomeIQ)

### 1. TAPPS pipeline rule update

**File:** `.cursor/rules/tapps-pipeline.md`

Added guidance to use **relative paths** when calling `tapps_score_file`, `tapps_quality_gate`, `tapps_security_scan`:

- Convert absolute paths (e.g. `C:\cursor\HomeIQ\domains\...`) to relative (e.g. `domains/data-collectors/weather-api/src/main.py`) before calling
- Relative paths may allow the server to record coverage metrics correctly

### 2. tapps_feedback submitted

Submitted `tapps_feedback` to TappsMCP for `tapps_dashboard` with `helpful: false` and detailed context about the coverage metrics issue, including the Windows path hypothesis.

---

## TappsMCP Fix Needed

**If you contribute to or maintain TappsMCP**, please consider the following fix.

### Draft Issue for TappsMCP

**Title:** Coverage metrics (files_scored, files_gated, files_scanned) always 0 on Windows despite valid tool_calls

**Description:**

The `tapps_dashboard` coverage_metrics section returns zeros for files_scored, files_gated, files_scanned, docs_lookup_calls, and checklist_calls even when tool_calls JSONL contains valid records with non-null `file_path`.

**Environment:**
- OS: Windows 10/11
- Paths in tool_calls: `C:\cursor\HomeIQ\services\weather-api\src\main.py` (absolute Windows paths)
- TAPPS_MCP_PROJECT_ROOT: `C:\cursor\HomeIQ` (or `${workspaceFolder}`)

**Observed:**
- tool_metrics shows tapps_score_file: 36, tapps_quality_gate: 10, tapps_security_scan: 5
- coverage_metrics shows files_scored: 0, files_gated: 0, files_scanned: 0
- core_tools_used: [], core_tools_unused: [all core tools]

**Hypothesis:**
The coverage aggregation filters tool calls by "file_path under project root." On Windows, path comparison may fail due to:
- Case differences (C:\ vs c:\)
- Backslash handling
- Missing or inconsistent path normalization

**Suggested fix:**
Normalize `file_path` before comparison when aggregating coverage metrics:
- Use `pathlib.Path` or `os.path.normpath` with case-insensitive handling on Windows
- Resolve both project root and file_path to the same format before checking containment
- Consider storing normalized (e.g. relative) paths in the metrics pipeline to avoid per-report normalization issues

---

## References

- AGENTS.md: File path guidance (relative paths preferred)
- .tapps-mcp/metrics/tool_calls_*.jsonl: Raw tool call logs
- TappsMCP dashboard JSON output: coverage_metrics structure
