#!/bin/bash
# Production Deployment Script
# HA Ingestor Production Deployment Automation

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENVIRONMENT="${ENVIRONMENT:-production}"
COMPOSE_FILE="docker-compose.yml"
ENV_FILE=".env"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Error handling
error_exit() {
    log_error "$1"
    exit 1
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        error_exit "Docker is not installed or not in PATH"
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        error_exit "Docker Compose is not installed or not in PATH"
    fi
    
    # Check if we're in the right directory
    if [[ ! -f "$PROJECT_ROOT/docker-compose.yml" ]]; then
        error_exit "Not in HA Ingestor project root directory"
    fi
    
    # Check if environment file exists
    if [[ ! -f "$PROJECT_ROOT/$ENV_FILE" ]]; then
        error_exit "Environment file not found: $ENV_FILE"
    fi
    
    log_success "Prerequisites check passed"
}

# Validate environment configuration
validate_configuration() {
    log_info "Validating environment configuration..."
    
    # Source environment variables
    set -a
    source "$PROJECT_ROOT/$ENV_FILE"
    set +a
    
    # Check required variables
    local required_vars=(
        "HOME_ASSISTANT_URL"
        "HOME_ASSISTANT_TOKEN"
        "INFLUXDB_PASSWORD"
        "INFLUXDB_TOKEN"
        "WEATHER_API_KEY"
        "JWT_SECRET_KEY"
        "ADMIN_PASSWORD"
    )
    
    local missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]] || [[ "${!var}" == *"your_"* ]] || [[ "${!var}" == *"here" ]]; then
            missing_vars+=("$var")
        fi
    done
    
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        log_error "Missing or invalid configuration variables:"
        for var in "${missing_vars[@]}"; do
            log_error "  - $var"
        done
        log_error "Please update $ENV_FILE with proper values"
        exit 1
    fi
    
    log_success "Configuration validation passed"
}

# Create necessary directories and volumes
setup_directories() {
    log_info "Setting up directories and volumes..."
    
    # Create log directories
    local log_dirs=(
        "$PROJECT_ROOT/logs/influxdb"
        "$PROJECT_ROOT/logs/websocket-ingestion"
        "$PROJECT_ROOT/logs/weather-api"
        "$PROJECT_ROOT/logs/admin-api"
        "$PROJECT_ROOT/logs/data-retention"
        "$PROJECT_ROOT/logs/dashboard"
        "$PROJECT_ROOT/backups"
    )
    
    for dir in "${log_dirs[@]}"; do
        mkdir -p "$dir"
        chmod 755 "$dir"
    done
    
    log_success "Directories setup completed"
}

# Pull latest images
pull_images() {
    log_info "Pulling latest images..."
    
    cd "$PROJECT_ROOT"
    
    # Use docker-compose or docker compose based on availability
    if command -v docker-compose &> /dev/null; then
        docker-compose --profile production pull
    else
        docker compose --profile production pull
    fi
    
    log_success "Images pulled successfully"
}

# Build custom images with parallel builds and caching
build_images() {
    log_info "Building custom images (using parallel builds and BuildKit cache)..."
    
    cd "$PROJECT_ROOT"
    
    # Enable BuildKit for better caching
    export DOCKER_BUILDKIT=1
    export COMPOSE_DOCKER_CLI_BUILD=1
    
    local build_start=$(date +%s)
    
    # Use docker-compose or docker compose based on availability
    # Remove --no-cache to enable BuildKit cache mounts
    if command -v docker-compose &> /dev/null; then
        docker-compose --profile production build --parallel
    else
        docker compose --profile production build --parallel
    fi
    
    local build_end=$(date +%s)
    local build_duration=$((build_end - build_start))
    local build_minutes=$((build_duration / 60))
    local build_seconds=$((build_duration % 60))
    
    log_success "Images built successfully in ${build_minutes}m ${build_seconds}s"
}

# Deploy services with zero-downtime
deploy_services() {
    log_info "Deploying ALL services with zero-downtime strategy..."
    
    cd "$PROJECT_ROOT"
    
    # Use docker-compose to start ALL services with production profile
    # This ensures all services defined in docker-compose.yml are included
    log_info "Starting all services with production profile..."
    if command -v docker-compose &> /dev/null; then
        docker-compose --profile production up -d --build
    else
        docker compose --profile production up -d --build
    fi
    
    log_success "All services deployment initiated"
    
    # Wait for critical services to be healthy
    log_info "Waiting for critical services to be healthy..."
    local critical_services=(
        "influxdb"
        "data-api"
        "admin-api"
        "websocket-ingestion"
    )
    
    for service in "${critical_services[@]}"; do
        if wait_for_service_health "$service" 60; then
            log_success "$service is healthy"
        else
            log_warning "$service health check failed - continuing..."
        fi
    done
    
    log_success "Deployment completed"
}

# Wait for a specific service to be healthy
wait_for_service_health() {
    local service=$1
    local max_attempts=${2:-30}
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        cd "$PROJECT_ROOT"
        
        local health_status
        if command -v docker-compose &> /dev/null; then
            health_status=$(docker-compose ps -q "$service" 2>/dev/null | xargs docker inspect --format='{{.State.Health.Status}}' 2>/dev/null || echo "unknown")
        else
            health_status=$(docker compose ps -q "$service" 2>/dev/null | xargs docker inspect --format='{{.State.Health.Status}}' 2>/dev/null || echo "unknown")
        fi
        
        if [[ "$health_status" == "healthy" ]]; then
            return 0
        elif [[ "$health_status" == "running" ]]; then
            # Service is running but may not have health check - consider it ready
            log_info "$service is running (no health check defined)"
            return 0
        fi
        
        if [[ $attempt -lt $max_attempts ]]; then
            log_info "$service health status: $health_status (attempt $attempt/$max_attempts)"
            sleep 5
        fi
        
        ((attempt++))
    done
    
    return 1
}

# Wait for services to be healthy
wait_for_health() {
    log_info "Waiting for services to be healthy..."
    
    local services=(
        "influxdb"
        "websocket-ingestion"
        "admin-api"
        "data-retention"
        "health-dashboard"
    )
    
    local max_attempts=30
    local attempt=1
    
    for service in "${services[@]}"; do
        log_info "Checking health of $service..."
        
        while [[ $attempt -le $max_attempts ]]; do
            cd "$PROJECT_ROOT"
            
            local health_status
            if command -v docker-compose &> /dev/null; then
                health_status=$(docker-compose ps -q "$service" | xargs docker inspect --format='{{.State.Health.Status}}' 2>/dev/null || echo "unknown")
            else
                health_status=$(docker compose ps -q "$service" | xargs docker inspect --format='{{.State.Health.Status}}' 2>/dev/null || echo "unknown")
            fi
            
            if [[ "$health_status" == "healthy" ]]; then
                log_success "$service is healthy"
                break
            elif [[ $attempt -eq $max_attempts ]]; then
                log_warning "$service health check timed out (status: $health_status)"
            else
                log_info "$service health status: $health_status (attempt $attempt/$max_attempts)"
                sleep 10
            fi
            
            ((attempt++))
        done
        
        attempt=1
    done
}

# Run post-deployment tests
run_post_deployment_tests() {
    log_info "Running post-deployment tests..."
    
    # Test API key validation
    if [[ -f "$PROJECT_ROOT/tests/test_api_keys.py" ]]; then
        log_info "Running API key validation tests..."
        cd "$PROJECT_ROOT"
        python tests/test_api_keys.py --env-file "$ENV_FILE" --output json > deployment_test_results.json
        
        if [[ $? -eq 0 ]]; then
            log_success "API key validation tests passed"
        else
            log_warning "API key validation tests failed - check deployment_test_results.json"
        fi
    fi
    
    # Test service connectivity
    log_info "Testing service connectivity..."
    
    local endpoints=(
        "http://localhost:8086/health:InfluxDB"
        "http://localhost:8001/health:WebSocket Ingestion"
        "http://localhost:8006/health:Data API"
        "http://localhost:8003/api/v1/health:Admin API"
        "http://localhost:3000:Health Dashboard"
    )
    
    for endpoint in "${endpoints[@]}"; do
        local url="${endpoint%:*}"
        local service="${endpoint#*:}"
        
        if curl -f -s "$url" > /dev/null 2>&1; then
            log_success "$service is accessible"
        else
            log_warning "$service is not accessible at $url"
        fi
    done
    
    log_success "Post-deployment tests completed"
}

# Show deployment status
show_status() {
    log_info "Deployment Status:"
    
    cd "$PROJECT_ROOT"
    
    if command -v docker-compose &> /dev/null; then
        docker-compose --profile production ps
    else
        docker compose --profile production ps
    fi
    
    echo ""
    log_info "Service URLs:"
    echo "  - InfluxDB: http://localhost:8086"
    echo "  - WebSocket Ingestion: http://localhost:8001"
    echo "  - Admin API: http://localhost:8003"
    echo "  - Data Retention: http://localhost:8080"
    echo "  - Health Dashboard: http://localhost:3000"
    
    echo ""
    log_info "Logs can be viewed with:"
    echo "  - All services: docker-compose -f $COMPOSE_FILE logs -f"
    echo "  - Specific service: docker-compose -f $COMPOSE_FILE logs -f <service-name>"
}

# Main deployment function
main() {
    log_info "Starting HA Ingestor Production Deployment"
    log_info "Environment: $ENVIRONMENT"
    log_info "Compose file: $COMPOSE_FILE"
    log_info "Environment file: $ENV_FILE"
    
    check_prerequisites
    validate_configuration
    setup_directories
    pull_images
    build_images
    deploy_services
    # Health checks are now done during deployment (zero-downtime)
    run_post_deployment_tests
    show_status
    
    log_success "Production deployment completed successfully!"
    
    echo ""
    log_info "Next steps:"
    echo "  1. Verify all services are running: docker-compose -f $COMPOSE_FILE ps"
    echo "  2. Check logs: docker-compose -f $COMPOSE_FILE logs -f"
    echo "  3. Access the health dashboard: http://localhost:3000"
    echo "  4. Test API endpoints: http://localhost:8003/api/v1/health"
}

# Handle script arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "validate")
        check_prerequisites
        validate_configuration
        log_success "Configuration validation completed"
        ;;
    "status")
        show_status
        ;;
    "logs")
        cd "$PROJECT_ROOT"
        if command -v docker-compose &> /dev/null; then
            docker-compose --profile production logs -f
        else
            docker compose --profile production logs -f
        fi
        ;;
    "stop")
        cd "$PROJECT_ROOT"
        log_info "Stopping all services..."
        # Stop all services including those with profiles
        if command -v docker-compose &> /dev/null; then
            docker-compose --profile production --profile test down --remove-orphans --timeout 30 2>/dev/null || true
            docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" down --remove-orphans --timeout 30 2>/dev/null || true
        else
            docker compose --profile production --profile test down --remove-orphans --timeout 30 2>/dev/null || true
            docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" down --remove-orphans --timeout 30 2>/dev/null || true
        fi
        # Stop any remaining containers
        running_containers=$(docker ps -q)
        if [[ -n "$running_containers" ]]; then
            log_info "Stopping remaining containers..."
            docker stop $running_containers --time 0 2>/dev/null || true
        fi
        log_success "All services stopped"
        ;;
    "restart")
        cd "$PROJECT_ROOT"
        log_info "Restarting all services..."
        if command -v docker-compose &> /dev/null; then
            docker-compose --profile production restart
        else
            docker compose --profile production restart
        fi
        log_success "All services restarted"
        ;;
    "help"|"-h"|"--help")
        echo "HA Ingestor Production Deployment Script"
        echo ""
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  deploy    Deploy all services (default)"
        echo "  validate  Validate configuration only"
        echo "  status    Show deployment status"
        echo "  logs      Show service logs"
        echo "  stop      Stop all services"
        echo "  restart   Restart all services"
        echo "  help      Show this help message"
        ;;
    *)
        log_error "Unknown command: $1"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac
