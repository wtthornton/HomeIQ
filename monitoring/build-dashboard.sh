#!/bin/bash
# Build Progress Dashboard - Real-time status
# Usage: ./build-dashboard.sh

clear

while true; do
    clear
    echo "╔══════════════════════════════════════════════════════════════════╗"
    echo "║          HomeIQ Rebuild - Live Dashboard                        ║"
    echo "║          $(date '+%Y-%m-%d %H:%M:%S')                                    ║"
    echo "╚══════════════════════════════════════════════════════════════════╝"
    echo ""

    echo "━━━ Service Health ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    docker ps --format "table {{.Names}}\t{{.Status}}" | head -15
    echo ""

    echo "━━━ Resource Usage ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" | head -10
    echo ""

    echo "━━━ Recent Errors ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    if [ -d "${PROJECT_ROOT:-..}/logs/current_rebuild/phase0/errors" ]; then
        find "${PROJECT_ROOT:-..}/logs/current_rebuild/phase0/errors" -name "*.log" -type f -mmin -60 | \
            xargs tail -5 2>/dev/null || echo "No recent errors"
    else
        echo "Error logs not initialized"
    fi
    echo ""

    echo "Press Ctrl+C to exit | Refreshing every 10 seconds..."
    sleep 10
done
