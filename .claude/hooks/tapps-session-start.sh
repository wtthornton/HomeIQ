#!/usr/bin/env bash
# TappsMCP SessionStart hook (startup/resume)
# Injects TappsMCP pipeline context into the session.
INPUT=$(cat)
echo "[TappsMCP] Session started — TappsMCP quality pipeline is active."
echo "Available tools: tapps_quick_check, tapps_score_file, tapps_quality_gate,"
echo "tapps_validate_changed, tapps_security_scan, tapps_consult_expert."
echo "Run tapps_session_start to initialize the session context."
exit 0
