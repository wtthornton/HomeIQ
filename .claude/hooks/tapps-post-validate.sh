#!/usr/bin/env bash
# tapps-mcp-hook-version: 3.12.52
# tapps-mcp-hook-content-sha: cca39db6
# TappsMCP PostToolUse hook (tapps_validate_changed)
# Reads the sidecar progress file and echoes a summary to the transcript.
# This provides a second delivery path for validation results.
INPUT=$(cat)
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
PROGRESS="$PROJECT_DIR/.tapps-mcp/.validation-progress.json"
if [ -f "$PROGRESS" ]; then
  PYBIN=$(command -v python3 2>/dev/null || command -v python 2>/dev/null)
  SUMMARY=$("$PYBIN" -c "
import json,sys
try:
    d=json.load(open('$PROGRESS'))
    status=d.get('status','unknown')
    if status=='completed':
        total=d.get('total',0)
        passed=sum(1 for r in d.get('results',[]) if r.get('gate_passed'))
        failed=total-passed
        ms=d.get('elapsed_ms',0)
        sec=ms/1000.0
        gp='ALL PASSED' if d.get('all_gates_passed') else f'{failed} FAILED'
        print(f'[TappsMCP] Validation: {total} files, {gp} ({sec:.1f}s)')
    elif status=='error':
        print(f'[TappsMCP] Validation error: {d.get("error","unknown")}')
    elif status=='running':
        done=d.get('completed',0)
        total=d.get('total',0)
        print(f'[TappsMCP] Validation in progress: {done}/{total} files')
except Exception:
    pass
" 2>/dev/null)
  if [ -n "$SUMMARY" ]; then
    echo "$SUMMARY"
  fi
fi
exit 0
