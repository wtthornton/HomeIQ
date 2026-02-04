#!/bin/bash
# Phase 1: Real-time Rebuild Monitoring Dashboard
# Monitors batch rebuild progress with detailed metrics
#
# Usage: ./scripts/phase1-monitor-rebuild.sh [state-file]
#
# Author: TappsCodingAgents Framework with Context7 MCP
# Date: 2026-02-04

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
STATE_FILE="${1:-${PROJECT_ROOT}/.rebuild_state_phase1.json}"
LOG_DIR="${PROJECT_ROOT}/logs/phase1_builds"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m'

# Get latest log directory
get_latest_log_dir() {
    find "$LOG_DIR" -maxdepth 1 -type d | sort -r | head -2 | tail -1
}

# Count services by status
count_by_status() {
    local status=$1
    if [ -f "$STATE_FILE" ]; then
        grep -c "\"$status\"" "$STATE_FILE" 2>/dev/null || echo "0"
    else
        echo "0"
    fi
}

# Get service status
get_service_status() {
    local service=$1
    if [ -f "$STATE_FILE" ]; then
        grep "\"$service\"" "$STATE_FILE" | sed 's/.*: "\(.*\)".*/\1/' 2>/dev/null || echo "pending"
    else
        echo "pending"
    fi
}

# Display dashboard
display_dashboard() {
    clear

    local current_log_dir=$(get_latest_log_dir)
    local completed=$(count_by_status "completed")
    local failed=$(count_by_status "failed")
    local total=40
    local pending=$((total - completed - failed))
    local progress=$((completed * 100 / total))

    echo -e "${MAGENTA}╔══════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${MAGENTA}║${NC}  ${BOLD}HomeIQ Phase 1: Batch Rebuild Monitor${NC}"
    echo -e "${MAGENTA}║${NC}  $(date '+%Y-%m-%d %H:%M:%S')"
    echo -e "${MAGENTA}╚══════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    # Progress bar
    echo -e "${CYAN}Progress:${NC}"
    local bar_length=50
    local filled=$((progress * bar_length / 100))
    local empty=$((bar_length - filled))
    printf "  ["
    printf "%${filled}s" | tr ' ' '█'
    printf "%${empty}s" | tr ' ' '░'
    printf "] ${progress}%%\n"
    echo ""

    # Statistics
    echo -e "${CYAN}Status Summary:${NC}"
    echo -e "  ${GREEN}✅ Completed:${NC} $completed / $total"
    echo -e "  ${RED}❌ Failed:${NC}    $failed / $total"
    echo -e "  ${YELLOW}⏳ Pending:${NC}   $pending / $total"
    echo ""

    # Service breakdown by category
    echo -e "${CYAN}Services by Category:${NC}"
    echo ""

    display_category "Integration" "weather-api sports-api carbon-intensity-service electricity-pricing-service air-quality-service calendar-service smart-meter-service log-aggregator"
    display_category "AI/ML" "ai-core-service ai-pattern-service ai-automation-service-new ai-query-service ai-training-service ai-code-executor ha-ai-agent-service proactive-agent-service ml-service openvino-service rag-service nlp-fine-tuning rule-recommendation-ml"
    display_category "Device" "device-intelligence-service device-context-classifier device-database-client device-health-monitor device-recommender device-setup-assistant model-prep"
    display_category "Automation" "automation-linter automation-miner blueprint-index blueprint-suggestion-service yaml-validation-service api-automation-edge"
    display_category "Analytics" "energy-correlator energy-forecasting"
    display_category "Frontend" "health-dashboard ai-automation-ui"
    display_category "Other" "observability-dashboard ha-simulator"

    # Recent build activity
    echo ""
    echo -e "${CYAN}Recent Build Activity:${NC}"
    if [ -d "$current_log_dir" ]; then
        find "$current_log_dir" -name "*.log" -type f -mmin -5 | while read logfile; do
            local service=$(basename "$logfile" .log)
            local size=$(stat -f%z "$logfile" 2>/dev/null || stat -c%s "$logfile" 2>/dev/null || echo "0")
            local status=$(get_service_status "$service")

            case "$status" in
                completed)
                    echo -e "  ${GREEN}✓${NC} $service (${size} bytes)"
                    ;;
                failed)
                    echo -e "  ${RED}✗${NC} $service (${size} bytes)"
                    ;;
                *)
                    echo -e "  ${YELLOW}⋯${NC} $service (building...)"
                    ;;
            esac
        done | head -10
    else
        echo "  No build activity yet"
    fi

    # Docker container status
    echo ""
    echo -e "${CYAN}Docker Container Status:${NC}"
    docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "homeiq-weather-api|homeiq-ai-core|homeiq-device-intelligence|homeiq-automation-linter|homeiq-energy-correlator|homeiq-health-dashboard" | head -6

    # Resource usage
    echo ""
    echo -e "${CYAN}Resource Usage (Top 5):${NC}"
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" | grep "homeiq-" | head -6

    echo ""
    echo -e "${BLUE}Press Ctrl+C to exit | Refreshing every 5 seconds...${NC}"
}

# Display category status
display_category() {
    local category=$1
    shift
    local services=($@)

    local completed=0
    local failed=0
    local pending=0

    for service in "${services[@]}"; do
        local status=$(get_service_status "$service")
        case "$status" in
            completed) ((completed++)) ;;
            failed) ((failed++)) ;;
            *) ((pending++)) ;;
        esac
    done

    local total=${#services[@]}
    local progress=$((completed * 100 / total))

    printf "  %-15s [%2d/%2d] " "$category:" "$completed" "$total"

    if [ $failed -gt 0 ]; then
        echo -e "${RED}✗ $failed failed${NC}"
    elif [ $pending -gt 0 ]; then
        echo -e "${YELLOW}⋯ $pending pending${NC}"
    else
        echo -e "${GREEN}✅ complete${NC}"
    fi
}

# Main loop
main() {
    if [ ! -f "$STATE_FILE" ] && [ ! -d "$LOG_DIR" ]; then
        echo "Error: No rebuild in progress"
        echo "Start rebuild with: ./scripts/phase1-batch-rebuild.sh"
        exit 1
    fi

    trap 'echo ""; echo "Monitoring stopped"; exit 0' INT

    while true; do
        display_dashboard
        sleep 5
    done
}

main "$@"
