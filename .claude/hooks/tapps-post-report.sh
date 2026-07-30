#!/usr/bin/env bash
# tapps-mcp-hook-version: 3.12.52
# tapps-mcp-hook-content-sha: dd5a53bb
# TappsMCP PostToolUse hook (tapps_report)
# Reads the report sidecar progress file and echoes a summary.
INPUT=$(cat)
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
PROGRESS="$PROJECT_DIR/.tapps-mcp/.report-progress.json"
if [ -f "$PROGRESS" ]; then
  PYBIN=$(command -v python3 2>/dev/null || command -v python 2>/dev/null)
  SUMMARY=$("$PYBIN" -c "
import json,sys
try:
    d=json.load(open('$PROGRESS'))
    status=d.get('status','unknown')
    if status=='completed':
        total=d.get('total',0)
        results=d.get('results',[])
        if results:
            avg=sum(r.get('score',0) for r in results)/len(results)
            print(f'[TappsMCP] Report: {total} files scored, avg {avg:.1f}/100')
        else:
            print(f'[TappsMCP] Report: {total} files scored')
    elif status=='error':
        print(f'[TappsMCP] Report error: {d.get("error","unknown")}')
    elif status=='running':
        done=d.get('completed',0)
        total=d.get('total',0)
        print(f'[TappsMCP] Report in progress: {done}/{total} files')
except Exception:
    pass
" 2>/dev/null)
  [ -n "$SUMMARY" ] && echo "$SUMMARY"
fi
exit 0
