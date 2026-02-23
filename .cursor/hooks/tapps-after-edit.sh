#!/usr/bin/env bash
# TappsMCP afterFileEdit hook (fire-and-forget)
# Reminds the agent to check quality after file edits.
INPUT=$(cat)
PY="import sys,json; d=json.load(sys.stdin)"
PY="$PY; print(d.get('file','unknown'))"
FILE=$(echo "$INPUT" | python3 -c "$PY" 2>/dev/null)
echo "File edited: $FILE"
echo "Consider running tapps_quick_check to verify quality."
exit 0
