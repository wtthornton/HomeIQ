#!/usr/bin/env bash
# TappsMCP TaskCompleted hook
# Reminds to run quality checks but does NOT block.
INPUT=$(cat)
MSG="Reminder: run tapps_validate_changed to confirm quality."
echo "$MSG" >&2
exit 0
