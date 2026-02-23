#!/usr/bin/env bash
# TappsMCP Stop hook
# Blocks session stop until tapps_validate_changed has been called.
# IMPORTANT: Must check stop_hook_active to prevent infinite loops.
INPUT=$(cat)
PY="import sys,json; d=json.load(sys.stdin)"
PY="$PY; print(d.get('stop_hook_active','false'))"
ACTIVE=$(echo "$INPUT" | python3 -c "$PY" 2>/dev/null)
if [ "$ACTIVE" = "True" ] || [ "$ACTIVE" = "true" ]; then
  exit 0
fi
echo "Run tapps_validate_changed before ending the session." >&2
exit 2
