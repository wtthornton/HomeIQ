#!/usr/bin/env bash
# TappsMCP PostToolUse hook (Edit/Write)
# Reminds the agent to run quality checks after file edits.
INPUT=$(cat)
PY="import sys,json; d=json.load(sys.stdin)"
PY="$PY; ti=d.get('tool_input',{})"
PY="$PY; print(ti.get('file_path',ti.get('path','')))"
FILE=$(echo "$INPUT" | python3 -c "$PY" 2>/dev/null)
if [ -n "$FILE" ] && echo "$FILE" | grep -qE '\.py$'; then
  echo "Python file edited: $FILE"
  echo "Consider running tapps_quick_check on it."
fi
exit 0
