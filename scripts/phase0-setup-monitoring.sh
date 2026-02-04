#!/bin/bash
# Phase 0: Pre-Deployment Preparation - Build Monitoring Setup Script
# HomeIQ Rebuild and Deployment - Phase 0 Story 5
#
# Purpose: Set up comprehensive build monitoring and logging infrastructure
#
# Usage: ./scripts/phase0-setup-monitoring.sh [--start] [--stop]
#
# Options:
#   --start    Start monitoring services
#   --stop     Stop monitoring services
#
# Author: TappsCodingAgents - Implementer
# Date: 2026-02-04

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TIMESTAMP=$(date +%Y%m%d)
LOG_ROOT="${PROJECT_ROOT}/logs"
REBUILD_LOG="${LOG_ROOT}/rebuild_${TIMESTAMP}"
MONITORING_DIR="${PROJECT_ROOT}/monitoring"

# Action flags
ACTION="setup"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --start)
            ACTION="start"
            shift
            ;;
        --stop)
            ACTION="stop"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--start] [--stop]"
            exit 1
            ;;
    esac
done

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

log_section() {
    echo -e "\n${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}  $1"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}\n"
}

# Task 5.1: Configure BuildKit
configure_buildkit() {
    log_section "Task 5.1: Configuring BuildKit"

    # Export environment variables
    export DOCKER_BUILDKIT=1
    export BUILDKIT_PROGRESS=plain
    export COMPOSE_DOCKER_CLI_BUILD=1

    log_success "BuildKit environment variables set:"
    echo "   DOCKER_BUILDKIT=$DOCKER_BUILDKIT"
    echo "   BUILDKIT_PROGRESS=$BUILDKIT_PROGRESS"
    echo "   COMPOSE_DOCKER_CLI_BUILD=$COMPOSE_DOCKER_CLI_BUILD"
    echo ""

    # Create persistent configuration file
    local config_file="${PROJECT_ROOT}/.env.buildkit"
    cat > "$config_file" << 'EOF'
# BuildKit Configuration for HomeIQ Rebuild
# Source this file before running builds: source .env.buildkit

export DOCKER_BUILDKIT=1
export BUILDKIT_PROGRESS=plain
export COMPOSE_DOCKER_CLI_BUILD=1

echo "✓ BuildKit configured with detailed progress output"
EOF

    chmod +x "$config_file"
    log_success "BuildKit config saved: .env.buildkit"
    log_info "Source before builds: source .env.buildkit"

    # Verify BuildKit availability
    if docker buildx version &> /dev/null; then
        local buildx_version=$(docker buildx version 2>&1 | head -1)
        log_success "BuildKit available: $buildx_version"
    else
        log_warning "BuildKit not available (builds will use standard backend)"
    fi

    echo ""
}

# Task 5.2: Create log directory structure
create_log_structure() {
    log_section "Task 5.2: Creating Build Log Directory Structure"

    # Create main rebuild log directory
    mkdir -p "$REBUILD_LOG"
    log_success "Rebuild log directory: $REBUILD_LOG"

    # Create phase subdirectories
    local phases=("phase0" "phase1" "phase2" "phase3" "phase4" "deployment")
    for phase in "${phases[@]}"; do
        mkdir -p "$REBUILD_LOG/$phase"/{build,test,health,errors}
        log_success "Created $phase subdirectories"
    done

    # Create symlink to current rebuild
    ln -sf "rebuild_${TIMESTAMP}" "${LOG_ROOT}/current_rebuild" 2>/dev/null || \
        log_warning "Could not create symlink (may already exist)"

    # Create log rotation config
    cat > "${REBUILD_LOG}/README.md" << EOF
# HomeIQ Rebuild Logs - $(date +%Y-%m-%d)

## Directory Structure

\`\`\`
rebuild_${TIMESTAMP}/
├── phase0/          # Pre-deployment preparation
│   ├── build/       # Build output logs
│   ├── test/        # Test execution logs
│   ├── health/      # Health check logs
│   └── errors/      # Error aggregation logs
├── phase1/          # Critical compatibility fixes
├── phase2/          # Standard library updates
├── phase3/          # ML/AI library upgrades
├── phase4/          # Frontend updates
└── deployment/      # Final deployment logs
\`\`\`

## Log Retention

- **Active Rebuild:** Kept indefinitely
- **Old Rebuilds:** Cleaned after 30 days
- **Critical Errors:** Archived separately

## Monitoring

- Health Monitor: \`monitoring/monitor-health.sh\`
- Resource Monitor: \`monitoring/monitor-resources.sh\`
- Error Aggregator: \`monitoring/aggregate-errors.sh\`

## Access

View current logs:
\`\`\`bash
cd logs/current_rebuild
tail -f phase0/health/health_monitor.log
\`\`\`
EOF

    log_success "Log structure created and documented"
    echo ""
}

# Task 5.3: Create monitoring scripts
create_monitoring_scripts() {
    log_section "Task 5.3: Creating Monitoring Scripts"

    mkdir -p "$MONITORING_DIR"

    # Script 1: Health Monitor
    log_info "Creating health monitoring script..."
    cat > "${MONITORING_DIR}/monitor-health.sh" << 'EOF'
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
EOF
    chmod +x "${MONITORING_DIR}/monitor-health.sh"
    log_success "Health monitor created: monitor-health.sh"

    # Script 2: Resource Monitor
    log_info "Creating resource monitoring script..."
    cat > "${MONITORING_DIR}/monitor-resources.sh" << 'EOF'
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
EOF
    chmod +x "${MONITORING_DIR}/monitor-resources.sh"
    log_success "Resource monitor created: monitor-resources.sh"

    # Script 3: Error Aggregator
    log_info "Creating error aggregation script..."
    cat > "${MONITORING_DIR}/aggregate-errors.sh" << 'EOF'
#!/bin/bash
# Error Aggregator - Collect errors from all containers
# Usage: ./aggregate-errors.sh

ERROR_LOG="${PROJECT_ROOT:-..}/logs/current_rebuild/phase0/errors/all_errors_$(date +%Y%m%d_%H%M%S).log"

echo "Aggregating errors from all containers..."
echo "Output: $ERROR_LOG"

{
    echo "=== Error Aggregation - $(date) ==="
    echo ""

    for container in $(docker ps --filter name=homeiq --format "{{.Names}}"); do
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "Container: $container"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

        # Get errors from last hour
        docker logs "$container" --since 1h 2>&1 | \
            grep -i -E "error|exception|failed|critical|traceback" | \
            tail -20 || echo "No recent errors"

        echo ""
    done

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "Aggregation completed: $(date)"
} | tee "$ERROR_LOG"

echo ""
echo "Error log saved: $ERROR_LOG"
EOF
    chmod +x "${MONITORING_DIR}/aggregate-errors.sh"
    log_success "Error aggregator created: aggregate-errors.sh"

    # Script 4: Build Progress Dashboard
    log_info "Creating build progress dashboard..."
    cat > "${MONITORING_DIR}/build-dashboard.sh" << 'EOF'
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
EOF
    chmod +x "${MONITORING_DIR}/build-dashboard.sh"
    log_success "Build dashboard created: build-dashboard.sh"

    # Create monitoring control script
    log_info "Creating monitoring control script..."
    cat > "${MONITORING_DIR}/start-all.sh" << 'EOF'
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
EOF
    chmod +x "${MONITORING_DIR}/start-all.sh"

    # Create stop script
    cat > "${MONITORING_DIR}/stop-all.sh" << 'EOF'
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
EOF
    chmod +x "${MONITORING_DIR}/stop-all.sh"

    log_success "Monitoring control scripts created"
    echo ""
}

# Start monitoring services
start_monitoring() {
    log_section "Starting Monitoring Services"

    cd "$MONITORING_DIR"
    ./start-all.sh

    log_success "Monitoring services started"
    log_info "View logs: cd $REBUILD_LOG/phase0/health"
    log_info "Dashboard: cd $MONITORING_DIR && ./build-dashboard.sh"
    echo ""
}

# Stop monitoring services
stop_monitoring() {
    log_section "Stopping Monitoring Services"

    if [ -d "$MONITORING_DIR" ]; then
        cd "$MONITORING_DIR"
        ./stop-all.sh
        log_success "Monitoring services stopped"
    else
        log_warning "Monitoring directory not found"
    fi

    echo ""
}

# Validate monitoring setup
validate_monitoring() {
    log_section "Task 5.4: Validating Monitoring Setup"

    local validation_failed=false

    # Check BuildKit config
    if [ -f "${PROJECT_ROOT}/.env.buildkit" ]; then
        log_success "BuildKit configuration file exists"
    else
        log_error "BuildKit configuration missing"
        validation_failed=true
    fi

    # Check log directories
    if [ -d "$REBUILD_LOG" ]; then
        log_success "Rebuild log directory exists"

        local phase_count=$(find "$REBUILD_LOG" -maxdepth 1 -type d | wc -l)
        log_info "Found $((phase_count - 1)) phase directories"
    else
        log_error "Rebuild log directory missing"
        validation_failed=true
    fi

    # Check monitoring scripts
    local required_scripts=(
        "monitor-health.sh"
        "monitor-resources.sh"
        "aggregate-errors.sh"
        "build-dashboard.sh"
        "start-all.sh"
        "stop-all.sh"
    )

    for script in "${required_scripts[@]}"; do
        if [ -x "${MONITORING_DIR}/$script" ]; then
            log_success "Script executable: $script"
        else
            log_error "Script missing or not executable: $script"
            validation_failed=true
        fi
    done

    # Check if monitoring is running (only if started)
    if pgrep -f "monitor-health.sh" > /dev/null; then
        log_success "Health monitor running"
    else
        log_info "Health monitor not running (start with --start)"
    fi

    if pgrep -f "monitor-resources.sh" > /dev/null; then
        log_success "Resource monitor running"
    else
        log_info "Resource monitor not running (start with --start)"
    fi

    if [ "$validation_failed" = true ]; then
        log_error "Validation failed"
        return 1
    else
        log_success "Monitoring setup validated"
        return 0
    fi

    echo ""
}

# Display summary
display_summary() {
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "  Build Monitoring Setup Summary"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""

    if [ "$ACTION" = "setup" ] || [ "$ACTION" = "start" ]; then
        log_info "📁 Directories Created:"
        echo "   - Rebuild logs: $REBUILD_LOG"
        echo "   - Monitoring scripts: $MONITORING_DIR"
        echo ""

        log_info "🔧 BuildKit Configuration:"
        echo "   - Config file: .env.buildkit"
        echo "   - Source before builds: source .env.buildkit"
        echo ""

        log_info "📊 Monitoring Scripts:"
        echo "   - Health: monitoring/monitor-health.sh"
        echo "   - Resources: monitoring/monitor-resources.sh"
        echo "   - Errors: monitoring/aggregate-errors.sh"
        echo "   - Dashboard: monitoring/build-dashboard.sh"
        echo ""

        log_info "🎛️  Control:"
        echo "   - Start all: cd monitoring && ./start-all.sh"
        echo "   - Stop all: cd monitoring && ./stop-all.sh"
        echo "   - Dashboard: cd monitoring && ./build-dashboard.sh"
        echo ""

        if [ "$ACTION" = "start" ]; then
            log_info "✅ Status:"
            echo "   - Monitoring services: RUNNING"
            echo "   - Health logs: $REBUILD_LOG/phase0/health"
        fi
    elif [ "$ACTION" = "stop" ]; then
        log_info "✅ Status:"
        echo "   - Monitoring services: STOPPED"
    fi

    echo ""
    log_info "📖 Next Steps:"
    if [ "$ACTION" = "setup" ]; then
        echo "   1. Start monitoring: $0 --start"
        echo "   2. View dashboard: cd monitoring && ./build-dashboard.sh"
        echo "   3. Proceed to Phase 1 rebuild"
    elif [ "$ACTION" = "start" ]; then
        echo "   ✅ Monitoring operational"
        echo "   1. View dashboard: cd monitoring && ./build-dashboard.sh"
        echo "   2. Check logs: cd logs/current_rebuild/phase0/health"
        echo "   3. Proceed to Phase 1 rebuild"
    elif [ "$ACTION" = "stop" ]; then
        echo "   ✅ Monitoring stopped"
        echo "   1. Review logs: cd logs/current_rebuild"
    fi
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
}

# Main execution
main() {
    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║  Build Monitoring Setup                                      ║"
    echo "║  Phase 0 - Story 5: Set Up Build Monitoring                 ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""

    case "$ACTION" in
        setup)
            configure_buildkit
            create_log_structure
            create_monitoring_scripts
            validate_monitoring
            ;;
        start)
            if [ ! -d "$MONITORING_DIR" ]; then
                log_error "Monitoring not set up. Run without --start first."
                exit 1
            fi
            start_monitoring
            ;;
        stop)
            stop_monitoring
            ;;
    esac

    display_summary

    log_success "Build monitoring setup completed successfully"
}

# Run main function
main "$@"
