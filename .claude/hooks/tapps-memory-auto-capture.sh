#!/usr/bin/env bash
# TappsMCP Stop hook - Auto-Capture (Epic 65.5)
# Extracts durable facts from context and saves via tapps_memory save_bulk.
# Runs tapps-mcp auto-capture with stdin; configurable max_facts, min_context.
INPUT=$(cat)
PYBIN=$(command -v python3 2>/dev/null || command -v python 2>/dev/null)
ACTIVE=$(echo "$INPUT" | "$PYBIN" -c   "import sys,json; d=json.load(sys.stdin); print(d.get('stop_hook_active','false'))"   2>/dev/null)
if [ "$ACTIVE" = "True" ] || [ "$ACTIVE" = "true" ]; then
  exit 0
fi
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
if command -v tapps-mcp >/dev/null 2>&1; then
  echo "$INPUT" | tapps-mcp auto-capture --project-root "$PROJECT_DIR" 2>/dev/null || true
elif [ -n "$PYBIN" ]; then
  echo "$INPUT" | "$PYBIN" -m tapps_mcp.cli auto-capture --project-root "$PROJECT_DIR" 2>/dev/null || true
fi
exit 0
