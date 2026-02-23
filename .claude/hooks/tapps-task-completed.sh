#!/usr/bin/env bash
# TappsMCP TaskCompleted hook
# Blocks task completion until quality gates pass.
INPUT=$(cat)
MSG="Before marking this task complete, run"
MSG="$MSG tapps_validate_changed to confirm quality."
echo "$MSG" >&2
exit 2
