#!/usr/bin/env bash
# TappsMCP stop hook (Cursor)
# Uses followup_message to prompt validation before session ends.
# Note: Cursor does not support exit-2 blocking on the stop event.
INPUT=$(cat)
MSG="Before ending: please run tapps_validate_changed"
MSG="$MSG to confirm all changed files pass quality gates."
echo "{"followup_message": "$MSG"}"
exit 0
