#!/bin/bash
# Build Performance Monitoring Script
# Tracks build times and resource usage for Docker builds

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_ROOT/logs/build-performance"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/build_${TIMESTAMP}.json"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Create log directory
mkdir -p "$LOG_DIR"

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Get system resources before build
get_system_resources() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        local cpu_usage=$(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1}')
        local mem_total=$(free -m | awk '/^Mem:/{print $2}')
        local mem_used=$(free -m | awk '/^Mem:/{print $3}')
        local mem_percent=$(awk "BEGIN {printf \"%.2f\", ($mem_used/$mem_total)*100}")
        local disk_usage=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
        
        echo "{\"cpu_percent\": $cpu_usage, \"mem_total_mb\": $mem_total, \"mem_used_mb\": $mem_used, \"mem_percent\": $mem_percent, \"disk_percent\": $disk_usage}"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        local cpu_usage=$(top -l 1 | awk '/CPU usage/ {print $3}' | sed 's/%//')
        local mem_total=$(sysctl -n hw.memsize | awk '{print $1/1024/1024}')
        local mem_used=$(vm_stat | awk '/Pages active/ {print $3}' | sed 's/\.//' | awk '{print $1*4096/1024/1024}')
        local mem_percent=$(awk "BEGIN {printf \"%.2f\", ($mem_used/$mem_total)*100}")
        local disk_usage=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
        
        echo "{\"cpu_percent\": $cpu_usage, \"mem_total_mb\": $mem_total, \"mem_used_mb\": $mem_used, \"mem_percent\": $mem_percent, \"disk_percent\": $disk_usage}"
    else
        # Windows (Git Bash/WSL)
        echo "{\"cpu_percent\": 0, \"mem_total_mb\": 0, \"mem_used_mb\": 0, \"mem_percent\": 0, \"disk_percent\": 0}"
    fi
}

# Get Docker stats
get_docker_stats() {
    local container_count=$(docker ps -q | wc -l)
    local image_count=$(docker images -q | wc -l)
    local volume_count=$(docker volume ls -q | wc -l)
    
    echo "{\"containers_running\": $container_count, \"images\": $image_count, \"volumes\": $volume_count}"
}

# Monitor build process
monitor_build() {
    local build_command="$1"
    local build_type="${2:-parallel}"
    
    log_info "Starting build performance monitoring..."
    log_info "Build type: $build_type"
    log_info "Command: $build_command"
    
    # Get initial system state
    local resources_before=$(get_system_resources)
    local docker_before=$(get_docker_stats)
    
    # Start build timer
    local build_start=$(date +%s.%N)
    
    # Run build command
    log_info "Executing build..."
    eval "$build_command"
    local build_exit_code=$?
    
    # End build timer
    local build_end=$(date +%s.%N)
    local build_duration=$(echo "$build_end - $build_start" | bc)
    
    # Get final system state
    local resources_after=$(get_system_resources)
    local docker_after=$(get_docker_stats)
    
    # Calculate build duration in minutes and seconds
    local build_minutes=$(echo "scale=0; $build_duration / 60" | bc)
    local build_seconds=$(echo "scale=2; $build_duration % 60" | bc)
    
    # Create JSON report
    local report=$(cat <<EOF
{
  "timestamp": "$TIMESTAMP",
  "build_type": "$build_type",
  "build_command": "$build_command",
  "build_duration_seconds": $build_duration,
  "build_duration_formatted": "${build_minutes}m ${build_seconds}s",
  "build_exit_code": $build_exit_code,
  "resources_before": $resources_before,
  "resources_after": $resources_after,
  "docker_before": $docker_before,
  "docker_after": $docker_after,
  "optimizations_enabled": {
    "DOCKER_BUILDKIT": "${DOCKER_BUILDKIT:-0}",
    "COMPOSE_DOCKER_CLI_BUILD": "${COMPOSE_DOCKER_CLI_BUILD:-0}",
    "parallel_build": "$([ "$build_type" == "parallel" ] && echo "true" || echo "false")"
  }
}
EOF
)
    
    # Save report
    echo "$report" > "$LOG_FILE"
    
    # Display summary
    echo ""
    log_success "Build Performance Report"
    echo "================================"
    echo "Build Duration: ${build_minutes}m ${build_seconds}s"
    echo "Build Type: $build_type"
    echo "Exit Code: $build_exit_code"
    echo "Log File: $LOG_FILE"
    echo ""
    
    if [[ $build_exit_code -eq 0 ]]; then
        log_success "Build completed successfully"
    else
        log_warning "Build completed with exit code $build_exit_code"
    fi
    
    return $build_exit_code
}

# Generate comparison report
generate_comparison() {
    log_info "Generating comparison report..."
    
    local latest_log=$(ls -t "$LOG_DIR"/build_*.json 2>/dev/null | head -1)
    local previous_log=$(ls -t "$LOG_DIR"/build_*.json 2>/dev/null | head -2 | tail -1)
    
    if [[ -z "$latest_log" ]]; then
        log_warning "No build logs found for comparison"
        return
    fi
    
    if [[ -z "$previous_log" ]]; then
        log_info "Only one build log found - no comparison available"
        return
    fi
    
    log_info "Comparing:"
    log_info "  Latest: $(basename "$latest_log")"
    log_info "  Previous: $(basename "$previous_log")"
    
    # Extract durations using jq if available, otherwise use grep/sed
    if command -v jq &> /dev/null; then
        local latest_duration=$(jq -r '.build_duration_seconds' "$latest_log")
        local previous_duration=$(jq -r '.build_duration_seconds' "$previous_log")
        local improvement=$(echo "scale=2; (($previous_duration - $latest_duration) / $previous_duration) * 100" | bc)
        
        echo ""
        log_success "Build Time Comparison"
        echo "========================"
        echo "Previous: $(jq -r '.build_duration_formatted' "$previous_log")"
        echo "Latest:   $(jq -r '.build_duration_formatted' "$latest_log")"
        echo "Change:   ${improvement}%"
        echo ""
    else
        log_warning "jq not available - install for detailed comparison"
    fi
}

# Main function
main() {
    local command="${1:-build}"
    
    case "$command" in
        "build")
            # Enable BuildKit
            export DOCKER_BUILDKIT=1
            export COMPOSE_DOCKER_CLI_BUILD=1
            
            # Default to parallel build
            local build_type="${BUILD_TYPE:-parallel}"
            local build_cmd="docker compose build --parallel"
            
            if [[ "$build_type" == "sequential" ]]; then
                build_cmd="docker compose build"
            fi
            
            monitor_build "$build_cmd" "$build_type"
            ;;
        "compare")
            generate_comparison
            ;;
        "list")
            log_info "Build performance logs:"
            ls -lh "$LOG_DIR"/build_*.json 2>/dev/null | awk '{print $9, $5}'
            ;;
        "latest")
            local latest_log=$(ls -t "$LOG_DIR"/build_*.json 2>/dev/null | head -1)
            if [[ -n "$latest_log" ]]; then
                if command -v jq &> /dev/null; then
                    jq '.' "$latest_log"
                else
                    cat "$latest_log"
                fi
            else
                log_warning "No build logs found"
            fi
            ;;
        "help"|"-h"|"--help")
            echo "Build Performance Monitoring Script"
            echo ""
            echo "Usage: $0 [command]"
            echo ""
            echo "Commands:"
            echo "  build     Monitor a build (default)"
            echo "  compare   Compare latest build with previous"
            echo "  list      List all build logs"
            echo "  latest    Show latest build report"
            echo "  help      Show this help message"
            echo ""
            echo "Environment Variables:"
            echo "  BUILD_TYPE      Build type: parallel (default) or sequential"
            echo "  DOCKER_BUILDKIT Enable BuildKit (default: 1)"
            echo ""
            ;;
        *)
            log_warning "Unknown command: $command"
            echo "Use '$0 help' for usage information"
            exit 1
            ;;
    esac
}

main "$@"

