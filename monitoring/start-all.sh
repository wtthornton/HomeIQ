#!/bin/bash
# Start all monitoring services in background

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Starting all monitoring services..."

# Start health monitor
nohup ./monitor-health.sh 300 > /dev/null 2>&1 &
echo "✓ Health monitor started (PID: $!)"

# Start resource monitor
nohup ./monitor-resources.sh 300 > /dev/null 2>&1 &
echo "✓ Resource monitor started (PID: $!)"

# Schedule error aggregation (every hour via cron or manual)
echo "✓ Error aggregator ready (run ./aggregate-errors.sh manually)"

# Save PIDs
pgrep -f "monitor-health.sh" > monitor-health.pid
pgrep -f "monitor-resources.sh" > monitor-resources.pid

echo ""
echo "Monitoring services started!"
echo "View logs: cd ../logs/current_rebuild/phase0/health"
echo "Dashboard: ./build-dashboard.sh"
echo "Stop: ./stop-all.sh"
