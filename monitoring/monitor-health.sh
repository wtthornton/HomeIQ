#!/bin/bash
# Health Monitor - Continuously monitor service health
# Usage: ./monitor-health.sh [interval_seconds]

INTERVAL=${1:-300}  # Default: 5 minutes
LOG_FILE="${PROJECT_ROOT:-..}/logs/current_rebuild/phase0/health/health_monitor.log"

echo "Starting health monitor (interval: ${INTERVAL}s, log: $LOG_FILE)"

while true; do
    {
        echo "=== $(date '+%Y-%m-%d %H:%M:%S') ==="
        docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "homeiq|NAMES"
        echo ""
    } | tee -a "$LOG_FILE"

    sleep "$INTERVAL"
done
