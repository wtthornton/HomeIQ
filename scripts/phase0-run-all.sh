#!/bin/bash
# Phase 0: Pre-Deployment Preparation - Master Orchestration Script
# HomeIQ Rebuild and Deployment
#
# Purpose: Execute all Phase 0 tasks in proper sequence
#
# Usage: ./scripts/phase0-run-all.sh [--auto-fix] [--skip-backup]
#
# Options:
#   --auto-fix       Auto-fix websocket health check issue
#   --skip-backup    Skip backup step (not recommended)
#
# Author: TappsCodingAgents - Simple Mode Orchestrator
# Date: 2026-02-04

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PHASE0_LOG="${PROJECT_ROOT}/logs/phase0_execution_${TIMESTAMP}.log"

# Flags
AUTO_FIX=false
SKIP_BACKUP=false

# Task tracking
TASKS_TOTAL=5
TASKS_COMPLETED=0
TASKS_FAILED=0

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --auto-fix)
            AUTO_FIX=true
            shift
            ;;
        --skip-backup)
            SKIP_BACKUP=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--auto-fix] [--skip-backup]"
            exit 1
            ;;
    esac
done

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$PHASE0_LOG"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$PHASE0_LOG"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$PHASE0_LOG"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$PHASE0_LOG"
}

log_section() {
    echo -e "\n${MAGENTA}╔══════════════════════════════════════════════════════════════════════════╗${NC}" | tee -a "$PHASE0_LOG"
    echo -e "${MAGENTA}║${NC}  $1" | tee -a "$PHASE0_LOG"
    echo -e "${MAGENTA}╚══════════════════════════════════════════════════════════════════════════╝${NC}\n" | tee -a "$PHASE0_LOG"
}

log_task() {
    local task_num=$1
    local task_name=$2
    echo -e "\n${CYAN}>>> Task $task_num/$TASKS_TOTAL: $task_name${NC}" | tee -a "$PHASE0_LOG"
}

# Setup Phase 0 logging
setup_logging() {
    mkdir -p "$(dirname "$PHASE0_LOG")"

    {
        echo "HomeIQ Phase 0: Pre-Deployment Preparation"
        echo "=========================================="
        echo "Started: $(date)"
        echo "Auto-fix: $AUTO_FIX"
        echo "Skip backup: $SKIP_BACKUP"
        echo ""
    } > "$PHASE0_LOG"

    log_info "Phase 0 execution log: $PHASE0_LOG"
}

# Task 1: Backup
run_backup() {
    if [ "$SKIP_BACKUP" = true ]; then
        log_warning "Skipping backup (--skip-backup flag)"
        return 0
    fi

    log_task 1 "Create Comprehensive System Backup"

    if bash "${SCRIPT_DIR}/phase0-backup.sh" 2>&1 | tee -a "$PHASE0_LOG"; then
        ((TASKS_COMPLETED++))
        log_success "Task 1 completed: Backup successful"
        return 0
    else
        ((TASKS_FAILED++))
        log_error "Task 1 failed: Backup failed"
        return 1
    fi
}

# Task 2: Diagnose WebSocket
run_websocket_diagnosis() {
    log_task 2 "Diagnose and Fix WebSocket Ingestion Service"

    local fix_flag=""
    if [ "$AUTO_FIX" = true ]; then
        fix_flag="--fix"
        log_info "Auto-fix enabled for websocket service"
    fi

    if bash "${SCRIPT_DIR}/phase0-diagnose-websocket.sh" $fix_flag 2>&1 | tee -a "$PHASE0_LOG"; then
        ((TASKS_COMPLETED++))
        log_success "Task 2 completed: WebSocket diagnosis successful"
        return 0
    else
        ((TASKS_FAILED++))
        log_error "Task 2 failed: WebSocket diagnosis failed"
        return 1
    fi
}

# Task 3: Python Version Audit
run_python_audit() {
    log_task 3 "Verify Python Versions Across All Services"

    if bash "${SCRIPT_DIR}/phase0-audit-python-versions.sh" --detailed 2>&1 | tee -a "$PHASE0_LOG"; then
        ((TASKS_COMPLETED++))
        log_success "Task 3 completed: Python version audit successful"
        return 0
    else
        ((TASKS_FAILED++))
        log_error "Task 3 failed: Python version audit failed"
        return 1
    fi
}

# Task 4: Infrastructure Validation
run_infrastructure_validation() {
    log_task 4 "Verify Infrastructure Requirements"

    if bash "${SCRIPT_DIR}/phase0-verify-infrastructure.sh" 2>&1 | tee -a "$PHASE0_LOG"; then
        ((TASKS_COMPLETED++))
        log_success "Task 4 completed: Infrastructure validation successful"
        return 0
    else
        ((TASKS_FAILED++))
        log_error "Task 4 failed: Infrastructure validation failed"
        log_warning "Check infrastructure report for remediation steps"
        return 1
    fi
}

# Task 5: Monitoring Setup
run_monitoring_setup() {
    log_task 5 "Set Up Build Monitoring and Logging"

    # Setup monitoring infrastructure
    if bash "${SCRIPT_DIR}/phase0-setup-monitoring.sh" 2>&1 | tee -a "$PHASE0_LOG"; then
        # Start monitoring services
        if bash "${SCRIPT_DIR}/phase0-setup-monitoring.sh" --start 2>&1 | tee -a "$PHASE0_LOG"; then
            ((TASKS_COMPLETED++))
            log_success "Task 5 completed: Monitoring setup successful"
            return 0
        else
            log_warning "Monitoring setup completed but failed to start services"
            ((TASKS_COMPLETED++))
            return 0
        fi
    else
        ((TASKS_FAILED++))
        log_error "Task 5 failed: Monitoring setup failed"
        return 1
    fi
}

# Display execution summary
display_summary() {
    log_section "Phase 0 Execution Summary"

    echo "" | tee -a "$PHASE0_LOG"
    echo "╔══════════════════════════════════════════════════════════════════════════╗" | tee -a "$PHASE0_LOG"
    echo "║                   PHASE 0: PRE-DEPLOYMENT PREPARATION                    ║" | tee -a "$PHASE0_LOG"
    echo "║                           EXECUTION SUMMARY                              ║" | tee -a "$PHASE0_LOG"
    echo "╚══════════════════════════════════════════════════════════════════════════╝" | tee -a "$PHASE0_LOG"
    echo "" | tee -a "$PHASE0_LOG"

    echo "📊 Results:" | tee -a "$PHASE0_LOG"
    echo "   Total tasks: $TASKS_TOTAL" | tee -a "$PHASE0_LOG"
    echo "   ✅ Completed: $TASKS_COMPLETED" | tee -a "$PHASE0_LOG"
    echo "   ❌ Failed: $TASKS_FAILED" | tee -a "$PHASE0_LOG"
    echo "" | tee -a "$PHASE0_LOG"

    if [ $TASKS_FAILED -eq 0 ]; then
        echo -e "${GREEN}✅ PHASE 0 COMPLETED SUCCESSFULLY${NC}" | tee -a "$PHASE0_LOG"
        echo "" | tee -a "$PHASE0_LOG"
        echo "📁 Generated Artifacts:" | tee -a "$PHASE0_LOG"
        echo "   - Backups: backups/phase0_*" | tee -a "$PHASE0_LOG"
        echo "   - WebSocket diagnostics: diagnostics/websocket-ingestion/" | tee -a "$PHASE0_LOG"
        echo "   - Python audit: diagnostics/python-audit/" | tee -a "$PHASE0_LOG"
        echo "   - Infrastructure report: diagnostics/infrastructure/" | tee -a "$PHASE0_LOG"
        echo "   - Build logs: logs/rebuild_$(date +%Y%m%d)/" | tee -a "$PHASE0_LOG"
        echo "   - Monitoring: monitoring/" | tee -a "$PHASE0_LOG"
        echo "" | tee -a "$PHASE0_LOG"
        echo "📖 Next Steps:" | tee -a "$PHASE0_LOG"
        echo "   ✅ Review all diagnostic reports" | tee -a "$PHASE0_LOG"
        echo "   ✅ Verify monitoring is operational: cd monitoring && ./build-dashboard.sh" | tee -a "$PHASE0_LOG"
        echo "   ⏳ Read Phase 1 plan: docs/planning/rebuild-deployment-plan.md" | tee -a "$PHASE0_LOG"
        echo "   ⏳ Begin Phase 1: Critical Compatibility Fixes (Week 1)" | tee -a "$PHASE0_LOG"
    else
        echo -e "${RED}❌ PHASE 0 FAILED - FIX ISSUES BEFORE PROCEEDING${NC}" | tee -a "$PHASE0_LOG"
        echo "" | tee -a "$PHASE0_LOG"
        echo "Failed Tasks:" | tee -a "$PHASE0_LOG"
        echo "   Review execution log for details: $PHASE0_LOG" | tee -a "$PHASE0_LOG"
        echo "" | tee -a "$PHASE0_LOG"
        echo "📖 Remediation:" | tee -a "$PHASE0_LOG"
        echo "   1. Review error messages in log file" | tee -a "$PHASE0_LOG"
        echo "   2. Fix identified issues" | tee -a "$PHASE0_LOG"
        echo "   3. Re-run Phase 0: $0" | tee -a "$PHASE0_LOG"
    fi

    echo "" | tee -a "$PHASE0_LOG"
    echo "📋 Full Execution Log:" | tee -a "$PHASE0_LOG"
    echo "   $PHASE0_LOG" | tee -a "$PHASE0_LOG"
    echo "" | tee -a "$PHASE0_LOG"
    echo "╚══════════════════════════════════════════════════════════════════════════╝" | tee -a "$PHASE0_LOG"
}

# Main execution
main() {
    clear
    echo ""
    echo "╔══════════════════════════════════════════════════════════════════════════╗"
    echo "║                                                                          ║"
    echo "║                    HomeIQ Rebuild and Deployment                         ║"
    echo "║              Phase 0: Pre-Deployment Preparation                         ║"
    echo "║                                                                          ║"
    echo "║  This script will execute all Phase 0 tasks in sequence:                ║"
    echo "║  1. Create comprehensive system backup                                  ║"
    echo "║  2. Diagnose and fix websocket-ingestion service                        ║"
    echo "║  3. Verify Python versions across all services                          ║"
    echo "║  4. Verify infrastructure requirements                                  ║"
    echo "║  5. Set up build monitoring and logging                                 ║"
    echo "║                                                                          ║"
    echo "╚══════════════════════════════════════════════════════════════════════════╝"
    echo ""

    setup_logging

    log_section "Starting Phase 0 Execution"

    # Execute tasks in sequence
    run_backup || true
    run_websocket_diagnosis || true
    run_python_audit || true
    run_infrastructure_validation || true
    run_monitoring_setup || true

    # Display summary
    display_summary

    # Exit with error if any tasks failed
    if [ $TASKS_FAILED -gt 0 ]; then
        exit 1
    fi

    log_success "Phase 0 Pre-Deployment Preparation completed successfully!"
    exit 0
}

# Run main function
main "$@"
