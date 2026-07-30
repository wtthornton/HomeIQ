#!/usr/bin/env bash
# tapps-mcp-hook-version: 3.12.52
# tapps-mcp-hook-content-sha: 2ccfc888
# TappsMCP SessionStart hook (compact)
# Re-injects TappsMCP context after context compaction.
INPUT=$(cat)
echo "[TappsMCP] Context was compacted — re-injecting TappsMCP awareness."
# Compaction can drop the original session_start result from context. Re-prompt
# so the agent re-establishes it; the session-start gate (if enabled) already
# has its per-session sentinel from the initial run, so no gate re-trip occurs.
echo "If tapps_session_start context was lost in compaction, call tapps_session_start() again."
echo "Remember: use tapps_quick_check after editing Python files."
echo "Run tapps_validate_changed before declaring work complete."
PROJECT="${TAPPS_PROJECT_ROOT:-${CLAUDE_PROJECT_DIR:-.}}"
if command -v tapps-mcp >/dev/null 2>&1; then
  USAGE_HINT=$(tapps-mcp usage-gaps-hint --project-root "$PROJECT" 2>/dev/null || true)
  if [ -n "$USAGE_HINT" ]; then
    echo "TappsMCP prior-session reminder: $USAGE_HINT"
  fi
fi
exit 0
