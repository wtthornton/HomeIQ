#!/bin/bash
# Stop all monitoring services

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Stopping monitoring services..."

# Stop using PIDs if available
if [ -f "monitor-health.pid" ]; then
    kill $(cat monitor-health.pid) 2>/dev/null && echo "✓ Health monitor stopped"
    rm monitor-health.pid
fi

if [ -f "monitor-resources.pid" ]; then
    kill $(cat monitor-resources.pid) 2>/dev/null && echo "✓ Resource monitor stopped"
    rm monitor-resources.pid
fi

# Fallback: kill by name
pkill -f "monitor-health.sh" 2>/dev/null
pkill -f "monitor-resources.sh" 2>/dev/null

echo "Monitoring services stopped"
