#!/bin/bash
# Phase 2: pytest-asyncio Batch Migration Orchestrator
# Story: PHASE2-002
# Author: Claude (Phase 2 Migration)
# Date: 2026-02-05

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DRY_RUN=${DRY_RUN:-false}
PHASE=${PHASE:-all}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
MIGRATION_SCRIPT="$SCRIPT_DIR/phase2-migrate-pytest-asyncio.py"

# Service groups by phase
declare -a PHASE_A_SERVICES=(
    "automation-miner"
    "blueprint-index"
    "ha-setup-service"
    "ha-simulator"
)

declare -a PHASE_B_SERVICES=(
    "ai-pattern-service"
    "ai-query-service"
    "ai-training-service"
    "device-intelligence-service"
    "ha-ai-agent-service"
    "openvino-service"
    "proactive-agent-service"
    "blueprint-suggestion-service"
)

declare -a PHASE_C_SERVICES=(
    "ai-core-service"
    "ml-service"
    "admin-api"
    "data-retention"
)

declare -a PHASE_D_SERVICES=(
    "data-api"
    "websocket-ingestion"
)

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

log_phase() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
    echo -e "${BLUE} $1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
    echo ""
}

# Migrate a single service
migrate_service() {
    local service=$1
    local dry_run_flag=""

    if [ "$DRY_RUN" = true ]; then
        dry_run_flag="--dry-run"
    fi

    log_info "Migrating: $service"

    if python "$MIGRATION_SCRIPT" "$service" $dry_run_flag; then
        log_success "$service migrated successfully"
        return 0
    else
        log_error "$service migration failed"
        return 1
    fi
}

# Migrate batch of services
migrate_batch() {
    local phase_name=$1
    shift
    local services=("$@")

    log_phase "$phase_name"

    local success_count=0
    local failure_count=0
    local failed_services=()

    for service in "${services[@]}"; do
        if migrate_service "$service"; then
            ((success_count++))
        else
            ((failure_count++))
            failed_services+=("$service")
        fi
        echo ""
    done

    # Summary
    echo -e "${BLUE}───────────────────────────────────────────────────${NC}"
    echo -e "${BLUE}$phase_name Summary:${NC}"
    echo -e "  ${GREEN}Success: $success_count${NC}"
    if [ $failure_count -gt 0 ]; then
        echo -e "  ${RED}Failed: $failure_count${NC}"
        echo -e "  ${RED}Failed services: ${failed_services[*]}${NC}"
    fi
    echo -e "${BLUE}───────────────────────────────────────────────────${NC}"
    echo ""

    # Return failure if any service failed
    if [ $failure_count -gt 0 ]; then
        return 1
    fi
    return 0
}

# Phase A: Low-Risk Test Group
run_phase_a() {
    log_info "Phase A: Low-Risk Test Group (4 services)"
    log_info "Purpose: Validate migration script on non-critical services"

    migrate_batch "Phase A: Low-Risk Test Group" "${PHASE_A_SERVICES[@]}"

    if [ $? -eq 0 ]; then
        log_success "Phase A completed successfully"
        return 0
    else
        log_error "Phase A had failures - manual review required"
        return 1
    fi
}

# Phase B: Medium-Risk Services
run_phase_b() {
    log_info "Phase B: Medium-Risk Services (8 services)"
    log_info "Purpose: Migrate medium-priority services"

    migrate_batch "Phase B: Medium-Risk Services" "${PHASE_B_SERVICES[@]}"

    if [ $? -eq 0 ]; then
        log_success "Phase B completed successfully"
        return 0
    else
        log_error "Phase B had failures - manual review required"
        return 1
    fi
}

# Phase C: High-Risk Services
run_phase_c() {
    log_info "Phase C: High-Risk Services (4 services)"
    log_info "Purpose: Migrate high-priority services"

    migrate_batch "Phase C: High-Risk Services" "${PHASE_C_SERVICES[@]}"

    if [ $? -eq 0 ]; then
        log_success "Phase C completed successfully"
        return 0
    else
        log_error "Phase C had failures - manual review required"
        return 1
    fi
}

# Phase D: Critical Services (Sequential)
run_phase_d() {
    log_info "Phase D: Critical Services (2 services, SEQUENTIAL)"
    log_info "Purpose: Migrate critical path services with blue-green deployment"
    log_warning "These services require manual validation between migrations"

    log_phase "Phase D: Critical Services"

    local success_count=0
    local failure_count=0

    for service in "${PHASE_D_SERVICES[@]}"; do
        log_info "Migrating CRITICAL service: $service"

        if migrate_service "$service"; then
            ((success_count++))

            # Prompt for validation before next critical service
            if [ "$DRY_RUN" != true ] && [ "$service" != "${PHASE_D_SERVICES[-1]}" ]; then
                echo ""
                log_warning "CRITICAL service migrated: $service"
                log_warning "Please validate service health before continuing"
                read -p "Press Enter to continue to next critical service, or Ctrl+C to stop..."
                echo ""
            fi
        else
            ((failure_count++))
            log_error "CRITICAL service migration failed: $service"
            log_error "Stopping Phase D - manual intervention required"
            return 1
        fi
    done

    # Summary
    echo -e "${BLUE}───────────────────────────────────────────────────${NC}"
    echo -e "${BLUE}Phase D: Critical Services Summary:${NC}"
    echo -e "  ${GREEN}Success: $success_count${NC}"
    if [ $failure_count -gt 0 ]; then
        echo -e "  ${RED}Failed: $failure_count${NC}"
    fi
    echo -e "${BLUE}───────────────────────────────────────────────────${NC}"
    echo ""

    if [ $failure_count -eq 0 ]; then
        log_success "Phase D completed successfully"
        return 0
    else
        log_error "Phase D had failures"
        return 1
    fi
}

# Main execution
main() {
    log_phase "Phase 2: pytest-asyncio 1.3.0 Migration"

    if [ "$DRY_RUN" = true ]; then
        log_warning "DRY RUN MODE - No changes will be made"
    fi

    log_info "Phase: $PHASE"
    echo ""

    case "$PHASE" in
        a|A|phase-a|phase_a)
            run_phase_a
            ;;
        b|B|phase-b|phase_b)
            run_phase_b
            ;;
        c|C|phase-c|phase_c)
            run_phase_c
            ;;
        d|D|phase-d|phase_d)
            run_phase_d
            ;;
        all)
            log_info "Running all phases sequentially"
            echo ""

            if run_phase_a; then
                log_success "Phase A complete - continuing to Phase B"
                echo ""
            else
                log_error "Phase A failed - stopping"
                exit 1
            fi

            if run_phase_b; then
                log_success "Phase B complete - continuing to Phase C"
                echo ""
            else
                log_error "Phase B failed - stopping"
                exit 1
            fi

            if run_phase_c; then
                log_success "Phase C complete - continuing to Phase D"
                echo ""
            else
                log_error "Phase C failed - stopping"
                exit 1
            fi

            if run_phase_d; then
                log_success "Phase D complete - all phases finished"
                echo ""
            else
                log_error "Phase D failed"
                exit 1
            fi
            ;;
        *)
            log_error "Invalid phase: $PHASE"
            log_info "Valid phases: a, b, c, d, all"
            exit 1
            ;;
    esac

    log_phase "Migration Complete!"
    log_success "All requested phases completed successfully"

    if [ "$DRY_RUN" = true ]; then
        log_info "This was a dry run - no changes were made"
        log_info "Run without DRY_RUN=true to apply changes"
    fi
}

# Show help
show_help() {
    cat << EOF
Phase 2: pytest-asyncio 1.3.0 Batch Migration

Usage:
  $0 [options]

Options:
  -h, --help          Show this help message
  -d, --dry-run       Run in dry-run mode (no changes)
  -p, --phase PHASE   Run specific phase (a, b, c, d, or all)

Environment Variables:
  DRY_RUN=true        Enable dry-run mode
  PHASE=<phase>       Set phase (a, b, c, d, or all)

Phases:
  Phase A (4 services)  - Low-risk test group
  Phase B (8 services)  - Medium-risk services
  Phase C (4 services)  - High-risk services
  Phase D (2 services)  - Critical services (sequential)

Examples:
  # Dry run all phases
  $0 --dry-run

  # Run Phase A only
  $0 --phase a

  # Run all phases
  $0 --phase all

  # Using environment variables
  DRY_RUN=true PHASE=a $0

EOF
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -p|--phase)
            PHASE="$2"
            shift 2
            ;;
        *)
            log_error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Run main
main
