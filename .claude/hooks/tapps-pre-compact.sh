#!/usr/bin/env bash
# tapps-mcp-hook-version: 3.12.52
# tapps-mcp-hook-content-sha: 1d39aaf5
# TappsMCP PreCompact hook (TAP-2017)
# Indexes pre-compaction session state in brain for post-compact rehydration.
# Set TAPPS_MCP_COMPACTION_REHYDRATE=false to disable.
INPUT=$(cat)
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
BACKUP_DIR="$PROJECT_DIR/.tapps-mcp"
mkdir -p "$BACKUP_DIR"
# Keep disk backup as fallback for operators without brain configured.
echo "$INPUT" > "$BACKUP_DIR/pre-compact-context.json"
# Index in brain and write rehydration marker via tapps-mcp CLI.
if command -v tapps-mcp >/dev/null 2>&1; then
  echo "$INPUT" | tapps-mcp compact-index --project-root "$PROJECT_DIR" 2>/dev/null || true
elif command -v python3 >/dev/null 2>&1; then
  echo "$INPUT" | python3 -m tapps_mcp.cli compact-index --project-root "$PROJECT_DIR" 2>/dev/null || true
fi
echo "[TappsMCP] Pre-compact session indexed for rehydration."
exit 0
