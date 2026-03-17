#!/bin/sh
# Zeek Docker healthcheck — process alive + log freshness
# No community Zeek Docker image implements a healthcheck (as of Mar 2026);
# this is a HomeIQ-original pattern for standalone-mode Zeek.

# Phase 1: Zeek process must be running
pgrep -x zeek > /dev/null 2>&1 || exit 1

# Phase 2: At least one log file must have been written within 10 minutes
# (2x the 5-min rotation interval configured in local.zeek for safety margin)
# During startup, no logs exist yet — the 120s start_period covers this window.
test -n "$(find /zeek/logs -name '*.log' -mmin -10 2>/dev/null)" || exit 1
