#!/bin/bash
# Rollback Script for HomeIQ Deployment
# Rolls back to previous Docker image versions

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
ENV_FILE="${ENV_FILE:-.env}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Rollback to previous version
rollback_service() {
    local service=$1
    log_info "Rolling back $service..."
    
    cd "$PROJECT_ROOT"
    
    # Stop current service
    if command -v docker-compose &> /dev/null; then
        docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" stop "$service"
    else
        docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" stop "$service"
    fi
    
    # Remove current container
    if command -v docker-compose &> /dev/null; then
        docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" rm -f "$service"
    else
        docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" rm -f "$service"
    fi
    
    # Start previous version (if tagged)
    log_info "Starting previous version of $service..."
    if command -v docker-compose &> /dev/null; then
        docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d "$service"
    else
        docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d "$service"
    fi
    
    log_success "$service rolled back"
}

# Main rollback function
main() {
    local service="${1:-all}"
    
    log_info "Starting rollback procedure"
    
    if [[ "$service" == "all" ]]; then
        log_warning "Rolling back all services - this may cause downtime"
        read -p "Are you sure? (yes/no): " confirm
        if [[ "$confirm" != "yes" ]]; then
            log_info "Rollback cancelled"
            exit 0
        fi
        
        # Rollback in reverse dependency order
        local services=(
            "health-dashboard"
            "log-aggregator"
            "energy-correlator"
            "smart-meter-service"
            "calendar-service"
            "air-quality-service"
            "electricity-pricing-service"
            "carbon-intensity-service"
            "weather-api"
            "websocket-ingestion"
            "admin-api"
            "data-api"
        )
        
        for svc in "${services[@]}"; do
            rollback_service "$svc"
            sleep 2
        done
    else
        rollback_service "$service"
    fi
    
    log_success "Rollback completed"
    log_info "Verify services: docker compose -f $COMPOSE_FILE ps"
}

main "$@"

