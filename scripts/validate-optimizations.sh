#!/bin/bash
# Validation Script for Docker Optimizations
# Validates that all optimizations are properly configured

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

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

# Track validation results
PASSED=0
FAILED=0
WARNINGS=0

# Validate docker-compose.yml syntax
validate_compose_syntax() {
    log_info "Validating docker-compose.yml syntax..."
    
    cd "$PROJECT_ROOT"
    
    if docker compose config --quiet > /dev/null 2>&1; then
        log_success "docker-compose.yml syntax is valid"
        ((PASSED++))
        return 0
    else
        log_error "docker-compose.yml has syntax errors"
        ((FAILED++))
        return 1
    fi
}

# Validate CPU limits are set
validate_cpu_limits() {
    log_info "Validating CPU limits..."
    
    cd "$PROJECT_ROOT"
    
    local services_with_cpu=$(docker compose config | grep -c "cpus:" || echo "0")
    local services_with_deploy=$(docker compose config | grep -A 5 "deploy:" | grep -c "resources:" || echo "0")
    
    if [[ $services_with_cpu -gt 0 ]]; then
        log_success "Found $services_with_cpu CPU limit configurations"
        ((PASSED++))
    else
        log_error "No CPU limits found in docker-compose.yml"
        ((FAILED++))
        return 1
    fi
    
    # Check specific services
    local critical_services=("influxdb" "websocket-ingestion" "data-api" "admin-api")
    local missing_cpu=0
    
    for service in "${critical_services[@]}"; do
        if docker compose config | grep -A 10 "^  $service:" | grep -q "cpus:"; then
            log_success "$service has CPU limits"
        else
            log_warning "$service may be missing CPU limits"
            ((WARNINGS++))
            ((missing_cpu++))
        fi
    done
    
    if [[ $missing_cpu -eq 0 ]]; then
        ((PASSED++))
    fi
}

# Validate build cache configuration
validate_build_cache() {
    log_info "Validating build cache configuration..."
    
    cd "$PROJECT_ROOT"
    
    local cache_configs=$(grep -c "cache_from:" docker-compose.yml || echo "0")
    
    if [[ $cache_configs -gt 0 ]]; then
        log_success "Found $cache_configs services with cache_from configuration"
        ((PASSED++))
    else
        log_warning "No cache_from configurations found (optional optimization)"
        ((WARNINGS++))
    fi
}

# Validate deployment scripts
validate_deployment_scripts() {
    log_info "Validating deployment scripts..."
    
    local scripts=("scripts/deploy.sh" "scripts/rollback.sh")
    local all_valid=true
    
    for script in "${scripts[@]}"; do
        if [[ ! -f "$PROJECT_ROOT/$script" ]]; then
            log_error "$script not found"
            ((FAILED++))
            all_valid=false
        elif bash -n "$PROJECT_ROOT/$script" 2>/dev/null; then
            log_success "$script syntax is valid"
            ((PASSED++))
        else
            log_error "$script has syntax errors"
            ((FAILED++))
            all_valid=false
        fi
    done
    
    if [[ "$all_valid" == "true" ]]; then
        return 0
    else
        return 1
    fi
}

# Validate CI/CD workflows
validate_cicd_workflows() {
    log_info "Validating CI/CD workflows..."
    
    local workflows=(
        ".github/workflows/docker-build.yml"
        ".github/workflows/docker-test.yml"
        ".github/workflows/docker-security-scan.yml"
        ".github/workflows/docker-deploy.yml"
    )
    
    local all_exist=true
    
    for workflow in "${workflows[@]}"; do
        if [[ -f "$PROJECT_ROOT/$workflow" ]]; then
            log_success "$(basename $workflow) exists"
            ((PASSED++))
        else
            log_error "$workflow not found"
            ((FAILED++))
            all_exist=false
        fi
    done
    
    if [[ "$all_exist" == "true" ]]; then
        return 0
    else
        return 1
    fi
}

# Validate .dockerignore files
validate_dockerignore() {
    log_info "Validating .dockerignore files..."
    
    local services_with_dockerignore=0
    local services_checked=0
    
    # Check a sample of services
    local sample_services=(
        "services/data-api"
        "services/websocket-ingestion"
        "services/admin-api"
        "services/weather-api"
    )
    
    for service_dir in "${sample_services[@]}"; do
        ((services_checked++))
        if [[ -f "$PROJECT_ROOT/$service_dir/.dockerignore" ]]; then
            ((services_with_dockerignore++))
        fi
    done
    
    if [[ $services_with_dockerignore -gt 0 ]]; then
        log_success "Found .dockerignore files in $services_with_dockerignore/$services_checked sample services"
        ((PASSED++))
    else
        log_warning "No .dockerignore files found in sample services"
        ((WARNINGS++))
    fi
}

# Main validation function
main() {
    log_info "Starting Docker Optimization Validation"
    echo ""
    
    validate_compose_syntax
    validate_cpu_limits
    validate_build_cache
    validate_deployment_scripts
    validate_cicd_workflows
    validate_dockerignore
    
    echo ""
    log_info "Validation Summary:"
    echo "  ✅ Passed: $PASSED"
    echo "  ⚠️  Warnings: $WARNINGS"
    echo "  ❌ Failed: $FAILED"
    echo ""
    
    if [[ $FAILED -eq 0 ]]; then
        log_success "All critical validations passed!"
        return 0
    else
        log_error "Some validations failed. Please review the errors above."
        return 1
    fi
}

main "$@"

