#!/bin/bash
# Phase 0: Pre-Deployment Preparation - Infrastructure Validation Script
# HomeIQ Rebuild and Deployment - Phase 0 Story 4
#
# Purpose: Verify infrastructure meets rebuild requirements
#
# Usage: ./scripts/phase0-verify-infrastructure.sh
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
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_DIR="${PROJECT_ROOT}/diagnostics/infrastructure"
REPORT_FILE="${REPORT_DIR}/infrastructure_validation_${TIMESTAMP}.md"

# Tracking
CHECKS_TOTAL=0
CHECKS_PASSED=0
CHECKS_FAILED=0
CHECKS_WARNING=0

# Requirements
REQ_DOCKER_VERSION="20.10"
REQ_COMPOSE_VERSION="2.0"
REQ_MEMORY_GB=16
REQ_DISK_GB=50
REQ_CPU_CORES=4
REQ_NODE_VERSION=18

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
    CHECKS_PASSED=$((CHECKS_PASSED + 1))
}

log_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
    CHECKS_WARNING=$((CHECKS_WARNING + 1))
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
    CHECKS_FAILED=$((CHECKS_FAILED + 1))
}

log_section() {
    echo -e "\n${CYAN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}  $1"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════╝${NC}\n"
}

# Setup report directory
setup_report_dir() {
    mkdir -p "$REPORT_DIR"
    log_info "Report directory: $REPORT_DIR"
}

# Task 4.1: Verify Docker environment
verify_docker_environment() {
    log_section "Task 4.1: Verifying Docker Environment"

    # Check if Docker is installed
    CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
    if command -v docker &> /dev/null; then
        DOCKER_VERSION=$(docker --version | grep -oP '\d+\.\d+\.\d+' | head -1)
        log_success "Docker installed: $DOCKER_VERSION"

        # Check version requirement
        CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
        if [ "$(printf '%s\n' "$REQ_DOCKER_VERSION" "$DOCKER_VERSION" | sort -V | head -n1)" = "$REQ_DOCKER_VERSION" ]; then
            log_success "Docker version meets requirement (≥$REQ_DOCKER_VERSION)"
        else
            log_error "Docker version $DOCKER_VERSION is below required $REQ_DOCKER_VERSION"
        fi
    else
        log_error "Docker is not installed or not in PATH"
    fi

    # Check Docker Compose
    CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
    if docker compose version &> /dev/null; then
        COMPOSE_VERSION=$(docker compose version --short 2>/dev/null | grep -oP '\d+\.\d+\.\d+' || echo "unknown")
        log_success "Docker Compose installed: $COMPOSE_VERSION"

        # Check version requirement
        CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
        if [[ "$COMPOSE_VERSION" != "unknown" ]]; then
            COMPOSE_MAJOR=$(echo "$COMPOSE_VERSION" | cut -d. -f1)
            if [ "$COMPOSE_MAJOR" -ge 2 ]; then
                log_success "Docker Compose version meets requirement (≥v$REQ_COMPOSE_VERSION)"
            else
                log_error "Docker Compose version $COMPOSE_VERSION is below required v$REQ_COMPOSE_VERSION"
            fi
        fi
    elif command -v docker-compose &> /dev/null; then
        log_warning "Using legacy docker-compose (recommend docker compose v2+)"
    else
        log_error "Docker Compose not installed"
    fi

    # Check BuildKit
    CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
    if command -v docker buildx version &> /dev/null; then
        BUILDKIT_VERSION=$(docker buildx version 2>/dev/null | grep -oP 'v\d+\.\d+\.\d+' || echo "unknown")
        log_success "BuildKit available: $BUILDKIT_VERSION"
    else
        log_warning "BuildKit not available (optional but recommended)"
    fi

    # Test BuildKit functionality
    CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
    export DOCKER_BUILDKIT=1
    if docker buildx ls &> /dev/null; then
        log_success "BuildKit functional"
    else
        log_warning "BuildKit test failed (may still work)"
    fi

    # Check Docker daemon
    CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
    if docker info &> /dev/null; then
        log_success "Docker daemon responsive"
    else
        log_error "Docker daemon not responding"
    fi

    echo ""
}

# Task 4.2: Check system resources
check_system_resources() {
    log_section "Task 4.2: Checking System Resources"

    # Check available memory (Windows compatibility)
    CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
    if command -v free &> /dev/null; then
        # Linux
        TOTAL_MEM_KB=$(free -k | awk '/^Mem:/{print $2}')
        TOTAL_MEM_GB=$((TOTAL_MEM_KB / 1024 / 1024))
    elif command -v wmic &> /dev/null; then
        # Windows
        TOTAL_MEM_KB=$(wmic ComputerSystem get TotalPhysicalMemory /value 2>/dev/null | grep -oP '\d+' || echo "0")
        TOTAL_MEM_GB=$((TOTAL_MEM_KB / 1024 / 1024 / 1024))
    else
        TOTAL_MEM_GB=0
        log_warning "Could not detect total memory"
    fi

    if [ "$TOTAL_MEM_GB" -ge "$REQ_MEMORY_GB" ]; then
        log_success "Available memory: ${TOTAL_MEM_GB}GB (≥${REQ_MEMORY_GB}GB required)"
    elif [ "$TOTAL_MEM_GB" -gt 0 ]; then
        log_warning "Available memory: ${TOTAL_MEM_GB}GB (${REQ_MEMORY_GB}GB recommended)"
    fi

    # Check disk space
    CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
    if command -v df &> /dev/null; then
        AVAIL_DISK_GB=$(df -BG "$PROJECT_ROOT" | tail -1 | awk '{print $4}' | tr -d 'G')
        if [ "$AVAIL_DISK_GB" -ge "$REQ_DISK_GB" ]; then
            log_success "Available disk space: ${AVAIL_DISK_GB}GB (≥${REQ_DISK_GB}GB required)"
        else
            log_error "Available disk space: ${AVAIL_DISK_GB}GB (${REQ_DISK_GB}GB required)"
        fi
    else
        log_warning "Could not check disk space"
    fi

    # Check CPU cores
    CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
    if command -v nproc &> /dev/null; then
        CPU_CORES=$(nproc)
    elif command -v wmic &> /dev/null; then
        CPU_CORES=$(wmic cpu get NumberOfCores /value 2>/dev/null | grep -oP '\d+' | head -1 || echo "0")
    else
        CPU_CORES=0
        log_warning "Could not detect CPU cores"
    fi

    if [ "$CPU_CORES" -ge "$REQ_CPU_CORES" ]; then
        log_success "CPU cores: $CPU_CORES (≥${REQ_CPU_CORES} required)"
    elif [ "$CPU_CORES" -gt 0 ]; then
        log_warning "CPU cores: $CPU_CORES (${REQ_CPU_CORES} recommended)"
    fi

    # Check Docker resource usage
    CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
    if docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" \
        > "${REPORT_DIR}/docker_stats_${TIMESTAMP}.txt" 2>/dev/null; then
        log_success "Docker resource usage captured"
    else
        log_warning "Could not capture Docker stats"
    fi

    echo ""
}

# Task 4.3: Verify Node.js versions
verify_nodejs_versions() {
    log_section "Task 4.3: Verifying Node.js Versions"

    # Check health-dashboard
    CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
    if docker ps --format "{{.Names}}" | grep -q "homeiq-dashboard"; then
        NODE_VERSION_HEALTH=$(docker exec homeiq-dashboard node --version 2>/dev/null | grep -oP '\d+' | head -1 || echo "0")
        if [ "$NODE_VERSION_HEALTH" -ge "$REQ_NODE_VERSION" ]; then
            log_success "health-dashboard: Node.js v${NODE_VERSION_HEALTH}.x (≥v${REQ_NODE_VERSION} required)"
        elif [ "$NODE_VERSION_HEALTH" -gt 0 ]; then
            log_warning "health-dashboard: Node.js v${NODE_VERSION_HEALTH}.x (v${REQ_NODE_VERSION}+ recommended for Vite 6)"
        else
            log_warning "health-dashboard: Could not determine Node.js version"
        fi
    else
        log_warning "health-dashboard container not running"
    fi

    # Check ai-automation-ui
    CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
    if docker ps --format "{{.Names}}" | grep -q "ai-automation-ui"; then
        NODE_VERSION_AI=$(docker exec ai-automation-ui node --version 2>/dev/null | grep -oP '\d+' | head -1 || echo "0")
        if [ "$NODE_VERSION_AI" -ge "$REQ_NODE_VERSION" ]; then
            log_success "ai-automation-ui: Node.js v${NODE_VERSION_AI}.x (≥v${REQ_NODE_VERSION} required)"
        elif [ "$NODE_VERSION_AI" -gt 0 ]; then
            log_warning "ai-automation-ui: Node.js v${NODE_VERSION_AI}.x (v${REQ_NODE_VERSION}+ recommended for Vite 6)"
        else
            log_warning "ai-automation-ui: Could not determine Node.js version"
        fi
    else
        log_warning "ai-automation-ui container not running"
    fi

    # Create Node.js version audit CSV
    cat > "${REPORT_DIR}/nodejs_versions_${TIMESTAMP}.csv" << EOF
Service,Container,Node Version,Required,Status
health-dashboard,homeiq-dashboard,${NODE_VERSION_HEALTH}.x,${REQ_NODE_VERSION}.x+,$([ "$NODE_VERSION_HEALTH" -ge "$REQ_NODE_VERSION" ] && echo "OK" || echo "UPGRADE_RECOMMENDED")
ai-automation-ui,ai-automation-ui,${NODE_VERSION_AI}.x,${REQ_NODE_VERSION}.x+,$([ "$NODE_VERSION_AI" -ge "$REQ_NODE_VERSION" ] && echo "OK" || echo "UPGRADE_RECOMMENDED")
EOF

    log_info "Node.js audit saved: nodejs_versions_${TIMESTAMP}.csv"
    echo ""
}

# Generate infrastructure report
generate_report() {
    log_section "Generating Infrastructure Validation Report"

    cat > "$REPORT_FILE" << EOF
# Infrastructure Validation Report

**Generated:** $(date)
**Project:** HomeIQ Rebuild and Deployment - Phase 0
**Report ID:** infra-validation-${TIMESTAMP}

---

## Summary

**Total Checks:** $CHECKS_TOTAL
**Passed:** ✅ $CHECKS_PASSED
**Warnings:** ⚠️  $CHECKS_WARNING
**Failed:** ❌ $CHECKS_FAILED

**Overall Status:** $(if [ $CHECKS_FAILED -eq 0 ]; then echo "✅ READY FOR REBUILD"; else echo "❌ BLOCKERS DETECTED"; fi)

---

## Docker Environment

### Docker

- **Version:** $(docker --version 2>/dev/null || echo "Not installed")
- **Required:** ≥ $REQ_DOCKER_VERSION
- **Status:** $(docker --version &>/dev/null && echo "✅ Installed" || echo "❌ Not found")

### Docker Compose

- **Version:** $(docker compose version --short 2>/dev/null || echo "Not installed")
- **Required:** ≥ v$REQ_COMPOSE_VERSION
- **Status:** $(docker compose version &>/dev/null && echo "✅ Installed" || echo "❌ Not found")

### BuildKit

- **Version:** $(docker buildx version 2>/dev/null | grep -oP 'v\d+\.\d+\.\d+' || echo "Not available")
- **Status:** $(docker buildx version &>/dev/null && echo "✅ Available" || echo "⚠️  Not available")

### Docker Daemon

- **Status:** $(docker info &>/dev/null && echo "✅ Responsive" || echo "❌ Not responding")

---

## System Resources

### Memory

- **Total:** ${TOTAL_MEM_GB}GB
- **Required:** ≥ ${REQ_MEMORY_GB}GB
- **Status:** $([ "$TOTAL_MEM_GB" -ge "$REQ_MEMORY_GB" ] && echo "✅ Sufficient" || echo "⚠️  Below recommendation")

### Disk Space

- **Available:** ${AVAIL_DISK_GB:-Unknown}GB
- **Required:** ≥ ${REQ_DISK_GB}GB
- **Status:** $([ "${AVAIL_DISK_GB:-0}" -ge "$REQ_DISK_GB" ] && echo "✅ Sufficient" || echo "❌ Insufficient")

### CPU Cores

- **Available:** ${CPU_CORES}
- **Required:** ≥ ${REQ_CPU_CORES}
- **Status:** $([ "$CPU_CORES" -ge "$REQ_CPU_CORES" ] && echo "✅ Sufficient" || echo "⚠️  Below recommendation")

---

## Node.js Environment

### Frontend Services

| Service | Container | Version | Required | Status |
|---------|-----------|---------|----------|--------|
| health-dashboard | homeiq-dashboard | v${NODE_VERSION_HEALTH}.x | v${REQ_NODE_VERSION}.x+ | $([ "$NODE_VERSION_HEALTH" -ge "$REQ_NODE_VERSION" ] && echo "✅ OK" || echo "⚠️  Upgrade recommended") |
| ai-automation-ui | ai-automation-ui | v${NODE_VERSION_AI}.x | v${REQ_NODE_VERSION}.x+ | $([ "$NODE_VERSION_AI" -ge "$REQ_NODE_VERSION" ] && echo "✅ OK" || echo "⚠️  Upgrade recommended") |

**Note:** Node.js 18+ required for Vite 6, Node.js 20.19+ recommended for Vite 7

---

## Infrastructure Blockers

$(if [ $CHECKS_FAILED -eq 0 ]; then
    echo "✅ **No blockers detected**"
    echo ""
    echo "Infrastructure meets all requirements for rebuild."
else
    echo "❌ **Blockers detected:**"
    echo ""
    if [ "$TOTAL_MEM_GB" -lt "$REQ_MEMORY_GB" ]; then
        echo "- Insufficient memory: ${TOTAL_MEM_GB}GB < ${REQ_MEMORY_GB}GB required"
    fi
    if [ "${AVAIL_DISK_GB:-0}" -lt "$REQ_DISK_GB" ]; then
        echo "- Insufficient disk space: ${AVAIL_DISK_GB}GB < ${REQ_DISK_GB}GB required"
    fi
    if ! docker --version &>/dev/null; then
        echo "- Docker not installed"
    fi
    if ! docker compose version &>/dev/null && ! command -v docker-compose &>/dev/null; then
        echo "- Docker Compose not installed"
    fi
fi)

---

## Warnings

$(if [ $CHECKS_WARNING -eq 0 ]; then
    echo "✅ **No warnings**"
else
    echo "⚠️  **Warnings detected:**"
    echo ""
    if [ "$CPU_CORES" -lt "$REQ_CPU_CORES" ]; then
        echo "- CPU cores below recommendation: $CPU_CORES < $REQ_CPU_CORES"
        echo "  Impact: Slower builds, may affect parallel compilation"
    fi
    if [ "$NODE_VERSION_HEALTH" -lt "$REQ_NODE_VERSION" ] || [ "$NODE_VERSION_AI" -lt "$REQ_NODE_VERSION" ]; then
        echo "- Node.js version below recommendation"
        echo "  Impact: May not support latest Vite features"
    fi
    if ! docker buildx version &>/dev/null; then
        echo "- BuildKit not available"
        echo "  Impact: Slower builds, no cache mounts"
    fi
fi)

---

## Remediation Plan

$(if [ $CHECKS_FAILED -gt 0 ]; then
    echo "### Critical Issues (Must Fix)"
    echo ""
    if ! docker --version &>/dev/null; then
        echo "1. **Install Docker**"
        echo "   - Windows: Download Docker Desktop from docker.com"
        echo "   - Linux: Follow official installation guide"
    fi
    if ! docker compose version &>/dev/null; then
        echo "2. **Install Docker Compose v2+**"
        echo "   - Included with Docker Desktop"
        echo "   - Linux: \`sudo apt-get install docker-compose-plugin\`"
    fi
    if [ "${AVAIL_DISK_GB:-0}" -lt "$REQ_DISK_GB" ]; then
        echo "3. **Free up disk space**"
        echo "   - Remove unused Docker images: \`docker image prune -a\`"
        echo "   - Clean up Docker volumes: \`docker volume prune\`"
        echo "   - Clean system temporary files"
    fi
    echo ""
fi)

$(if [ $CHECKS_WARNING -gt 0 ]; then
    echo "### Recommended Improvements"
    echo ""
    if [ "$CPU_CORES" -lt "$REQ_CPU_CORES" ]; then
        echo "1. **Increase CPU allocation**"
        echo "   - Docker Desktop: Settings → Resources → CPUs"
        echo "   - Recommended: $REQ_CPU_CORES+ cores"
    fi
    if [ "$NODE_VERSION_HEALTH" -lt "$REQ_NODE_VERSION" ] || [ "$NODE_VERSION_AI" -lt "$REQ_NODE_VERSION" ]; then
        echo "2. **Upgrade Node.js in frontend containers**"
        echo "   - Update Dockerfiles to use Node 20+ base image"
        echo "   - Rebuild containers: \`docker-compose build health-dashboard ai-automation-ui\`"
    fi
    if ! docker buildx version &>/dev/null; then
        echo "3. **Enable BuildKit**"
        echo "   - Set environment: \`export DOCKER_BUILDKIT=1\`"
        echo "   - Add to ~/.bashrc for persistence"
    fi
    echo ""
fi)

---

## Next Steps

$(if [ $CHECKS_FAILED -eq 0 ]; then
    echo "✅ **Infrastructure validated and ready for rebuild**"
    echo ""
    echo "1. ✅ Proceed to Phase 0 Story 5 (Build monitoring setup)"
    echo "2. ⏳ Begin Phase 1: Critical Compatibility Fixes"
else
    echo "❌ **Fix blockers before proceeding**"
    echo ""
    echo "1. ⏳ Address critical issues listed above"
    echo "2. ⏳ Re-run this validation: \`./scripts/phase0-verify-infrastructure.sh\`"
    echo "3. ⏳ Once passed, proceed to Story 5"
fi)

---

## Diagnostic Files

- Docker stats: \`docker_stats_${TIMESTAMP}.txt\`
- Node.js audit: \`nodejs_versions_${TIMESTAMP}.csv\`
- Full report: \`$(basename $REPORT_FILE)\`

---

**Report Location:** \`$REPORT_FILE\`
EOF

    log_success "Infrastructure report generated: $(basename $REPORT_FILE)"
}

# Display summary
display_summary() {
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "  Infrastructure Validation Summary"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    echo "📊 Results:"
    echo "   Total checks: $CHECKS_TOTAL"
    echo "   ✅ Passed: $CHECKS_PASSED"
    echo "   ⚠️  Warnings: $CHECKS_WARNING"
    echo "   ❌ Failed: $CHECKS_FAILED"
    echo ""

    if [ $CHECKS_FAILED -eq 0 ]; then
        echo -e "${GREEN}✅ INFRASTRUCTURE READY FOR REBUILD${NC}"
    else
        echo -e "${RED}❌ BLOCKERS DETECTED - FIX BEFORE PROCEEDING${NC}"
    fi
    echo ""

    echo "📁 Report Files:"
    echo "   - Full report: $(basename $REPORT_FILE)"
    echo "   - Location: $REPORT_DIR"
    echo ""

    echo "📖 Next Steps:"
    if [ $CHECKS_FAILED -eq 0 ]; then
        echo "   1. Review report: cat $REPORT_FILE"
        echo "   2. Proceed to Phase 0 Story 5 (Build monitoring)"
    else
        echo "   1. Review report: cat $REPORT_FILE"
        echo "   2. Fix critical issues listed in report"
        echo "   3. Re-run validation: $0"
    fi
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
}

# Main execution
main() {
    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║  Infrastructure Validation                                   ║"
    echo "║  Phase 0 - Story 4: Verify Infrastructure Requirements      ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""

    setup_report_dir
    verify_docker_environment
    check_system_resources
    verify_nodejs_versions
    generate_report
    display_summary

    # Exit with error if any checks failed
    if [ $CHECKS_FAILED -gt 0 ]; then
        exit 1
    fi

    log_success "Infrastructure validation completed successfully"
}

# Run main function
main "$@"
