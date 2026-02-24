#!/usr/bin/env bash
# TappsMCP PostToolUse hook (Edit/Write)
# Reminds the agent to run quality checks after file edits.
# Use Python (python3 or python) so this works in Git Bash on Windows.
INPUT=$(cat)
PY='import sys,json
d=json.load(sys.stdin)
ti=d.get("tool_input",{})
p=ti.get("file_path",ti.get("path",""))
print(p if p and p.endswith(".py") else "")'
FILE=$(echo "$INPUT" | (command -v python3 >/dev/null 2>&1 && python3 -c "$PY" || python -c "$PY") 2>/dev/null)
if [ -n "$FILE" ]; then
  echo "Python file edited: $FILE"
  echo "Consider running tapps_quick_check on it."
fi
exit 0
