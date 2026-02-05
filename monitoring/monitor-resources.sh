#!/bin/bash
# Resource Monitor - Track Docker resource usage
# Usage: ./monitor-resources.sh [interval_seconds]

INTERVAL=${1:-300}  # Default: 5 minutes
LOG_FILE="${PROJECT_ROOT:-..}/logs/current_rebuild/phase0/health/resource_monitor.log"

echo "Starting resource monitor (interval: ${INTERVAL}s, log: $LOG_FILE)"

while true; do
    {
        echo "=== $(date '+%Y-%m-%d %H:%M:%S') ==="
        docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"
        echo ""
    } | tee -a "$LOG_FILE"

    sleep "$INTERVAL"
done
