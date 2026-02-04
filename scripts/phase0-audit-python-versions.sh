#!/bin/bash
# Phase 0: Pre-Deployment Preparation - Python Version Audit Script
# HomeIQ Rebuild and Deployment - Phase 0 Story 3
#
# Purpose: Check Python versions across all services and identify upgrade requirements
#
# Usage: ./scripts/phase0-audit-python-versions.sh [--detailed]
#
# Options:
#   --detailed    Include Dockerfile analysis and upgrade recommendations
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
AUDIT_DIR="${PROJECT_ROOT}/diagnostics/python-audit"
AUDIT_CSV="${AUDIT_DIR}/python_versions_audit_${TIMESTAMP}.csv"
DOCKERFILE_ANALYSIS="${AUDIT_DIR}/dockerfile_python_versions_${TIMESTAMP}.txt"
UPGRADE_PLAN="${AUDIT_DIR}/python_upgrade_plan_${TIMESTAMP}.md"

# Flags
DETAILED=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --detailed)
            DETAILED=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--detailed]"
            exit 1
            ;;
    esac
done

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

# Python services list
PYTHON_SERVICES=(
    # Core services
    "data-api"
    "websocket"
    "admin"
    "data-retention"

    # External integrations
    "weather-api"
    "sports-api"
    "carbon-intensity"
    "electricity-pricing"
    "air-quality"
    "calendar"
    "smart-meter"
    "log-aggregator"

    # AI/ML services
    "ai-core-service"
    "ai-pattern-service"
    "ai-automation-service-new"
    "ai-query-service"
    "ai-training-service"
    "ai-code-executor"
    "ha-ai-agent-service"
    "proactive-agent-service"
    "ml-service"
    "openvino-service"
    "rag-service"
    "openai-service"
    "ner-service"

    # Device management
    "device-intelligence"
    "device-health-monitor"
    "device-context-classifier"
    "device-database-client"
    "device-recommender"
    "device-setup-assistant"
    "setup-service"

    # Automation services
    "automation-linter"
    "automation-miner"
    "blueprint-index"
    "blueprint-suggestion"
    "yaml-validation-service"
    "api-automation-edge"

    # Analytics
    "energy-correlator"
    "rule-recommendation-ml"
)

# Setup audit directory
setup_audit_dir() {
    # Create audit directory FIRST (no log file dependency in this script)
    mkdir -p "$AUDIT_DIR"
    log_info "Setting up Python audit directory..."
    log_success "Audit directory created: $AUDIT_DIR"
}

# Check Python versions in containers
check_python_versions() {
    log_info "═══════════════════════════════════════════════════════"
    log_info "Task 3.1: Checking Python Versions in All Containers"
    log_info "═══════════════════════════════════════════════════════"
    echo ""

    # Create CSV header
    echo "Service,Container Name,Python Version,Major.Minor,Status,Priority,Base Image" > "$AUDIT_CSV"

    local total_services=0
    local checked_services=0
    local needs_upgrade=0
    local version_ok=0
    local not_found=0

    for service in "${PYTHON_SERVICES[@]}"; do
        total_services=$((total_services + 1))

        # Find container name
        local container_name="homeiq-${service}"

        echo -n "Checking ${service}... "

        # Check if container exists and is running
        if ! docker ps --format "{{.Names}}" | grep -q "^${container_name}$"; then
            log_warning "Container not running"
            echo "${service},${container_name},NOT_RUNNING,N/A,UNKNOWN,N/A,N/A" >> "$AUDIT_CSV"
            not_found=$((not_found + 1))
            continue
        fi

        # Get Python version
        local py_version=$(docker exec "$container_name" python --version 2>&1 || echo "N/A")

        if [ "$py_version" = "N/A" ] || [[ "$py_version" == *"not found"* ]]; then
            log_warning "Python not found"
            echo "${service},${container_name},NOT_FOUND,N/A,ERROR,HIGH,N/A" >> "$AUDIT_CSV"
            not_found=$((not_found + 1))
            continue
        fi

        checked_services=$((checked_services + 1))

        # Extract version number (e.g., "Python 3.12.1" -> "3.12")
        local version_num=$(echo "$py_version" | grep -oP 'Python \K[0-9]+\.[0-9]+' || echo "unknown")
        local major_minor=$(echo "$version_num" | cut -d. -f1,2)

        # Get base image
        local base_image=$(docker inspect "$container_name" --format='{{index .Config.Image}}' 2>/dev/null || echo "unknown")

        # Determine status and priority
        local status="OK"
        local priority="LOW"

        if [[ "$major_minor" =~ ^[0-9]+\.[0-9]+$ ]]; then
            local major=$(echo "$major_minor" | cut -d. -f1)
            local minor=$(echo "$major_minor" | cut -d. -f2)

            if [ "$major" -lt 3 ] || ([ "$major" -eq 3 ] && [ "$minor" -lt 10 ]); then
                status="NEEDS_UPGRADE"
                needs_upgrade=$((needs_upgrade + 1))

                # Assign priority based on service type
                if [[ "$service" == *"ai-"* ]] || [[ "$service" == *"ml-"* ]]; then
                    priority="HIGH"  # ML services need 3.10+ for Pandas 3.0
                elif [[ "$service" == "websocket" ]] || [[ "$service" == "data-api" ]]; then
                    priority="CRITICAL"  # Core services
                else
                    priority="MEDIUM"
                fi

                echo -e "${RED}✗${NC} ${py_version} (${status}, Priority: ${priority})"
            else
                version_ok=$((version_ok + 1))
                echo -e "${GREEN}✓${NC} ${py_version}"
            fi
        else
            log_warning "Could not parse version: $py_version"
            status="UNKNOWN"
            priority="MEDIUM"
        fi

        # Write to CSV
        echo "${service},${container_name},${py_version},${major_minor},${status},${priority},${base_image}" >> "$AUDIT_CSV"
    done

    echo ""
    log_success "Python version audit completed"
    log_info "Total services: $total_services"
    log_info "Checked: $checked_services"
    log_success "Version OK (3.10+): $version_ok"
    log_warning "Needs upgrade (<3.10): $needs_upgrade"
    log_error "Not found/running: $not_found"
    echo ""
}

# Analyze Dockerfiles
analyze_dockerfiles() {
    if [ "$DETAILED" = false ]; then
        return 0
    fi

    log_info "═══════════════════════════════════════════════════════"
    log_info "Task 3.2: Analyzing Dockerfiles for Base Images"
    log_info "═══════════════════════════════════════════════════════"
    echo ""

    cd "$PROJECT_ROOT"

    # Find all Dockerfiles
    log_info "Finding all Dockerfiles..."
    find services/ -name "Dockerfile" -o -name "Dockerfile.dev" | sort > "${AUDIT_DIR}/dockerfiles_list.txt"

    local dockerfile_count=$(wc -l < "${AUDIT_DIR}/dockerfiles_list.txt")
    log_info "Found $dockerfile_count Dockerfiles"
    echo ""

    # Analyze each Dockerfile
    {
        echo "Dockerfile Python Base Image Analysis"
        echo "======================================"
        echo "Generated: $(date)"
        echo ""
    } > "$DOCKERFILE_ANALYSIS"

    while IFS= read -r dockerfile; do
        {
            echo "=== $dockerfile ==="
            grep -E "^FROM python:" "$dockerfile" 2>/dev/null || echo "No Python base image found"
            echo ""
        } >> "$DOCKERFILE_ANALYSIS"
    done < "${AUDIT_DIR}/dockerfiles_list.txt"

    log_success "Dockerfile analysis completed: $(basename $DOCKERFILE_ANALYSIS)"
    echo ""
}

# Create upgrade matrix and plan
create_upgrade_plan() {
    if [ "$DETAILED" = false ]; then
        return 0
    fi

    log_info "═══════════════════════════════════════════════════════"
    log_info "Task 3.3 & 3.4: Creating Upgrade Plan"
    log_info "═══════════════════════════════════════════════════════"
    echo ""

    # Count services by status
    local critical_count=$(grep -c ",CRITICAL," "$AUDIT_CSV" 2>/dev/null || echo "0")
    local high_count=$(grep -c ",HIGH," "$AUDIT_CSV" 2>/dev/null || echo "0")
    local medium_count=$(grep -c ",MEDIUM," "$AUDIT_CSV" 2>/dev/null || echo "0")
    local upgrade_count=$(grep -c "NEEDS_UPGRADE" "$AUDIT_CSV" 2>/dev/null || echo "0")

    # Create comprehensive upgrade plan
    cat > "$UPGRADE_PLAN" << EOF
# Python Version Upgrade Plan

**Generated:** $(date)
**Audit File:** $(basename $AUDIT_CSV)
**Total Services Audited:** $(tail -n +2 "$AUDIT_CSV" | wc -l)
**Services Needing Upgrade:** $upgrade_count

---

## Executive Summary

This plan outlines the Python version upgrade requirements for HomeIQ services.

### Upgrade Priority Breakdown

| Priority | Count | Action Required |
|----------|-------|-----------------|
| CRITICAL | $critical_count | Upgrade before Phase 1 |
| HIGH | $high_count | Upgrade in Phase 1 |
| MEDIUM | $medium_count | Upgrade in Phase 2 |
| LOW | N/A | No upgrade needed |

---

## Services Requiring Upgrade

### Critical Priority (Core Services)

$(awk -F, '$5 == "NEEDS_UPGRADE" && $6 == "CRITICAL" {print "- **" $1 "**: " $3 " → Python 3.10+"}' "$AUDIT_CSV")

**Rationale:** These are core services critical to HomeIQ operation.

---

### High Priority (ML/AI Services)

$(awk -F, '$5 == "NEEDS_UPGRADE" && $6 == "HIGH" {print "- **" $1 "**: " $3 " → Python 3.10+"}' "$AUDIT_CSV")

**Rationale:** ML services require Python 3.10+ for:
- NumPy 2.x compatibility
- Pandas 3.0 support
- Modern scikit-learn features

---

### Medium Priority (Other Services)

$(awk -F, '$5 == "NEEDS_UPGRADE" && $6 == "MEDIUM" {print "- **" $1 "**: " $3 " → Python 3.10+"}' "$AUDIT_CSV")

**Rationale:** Standard services, can be upgraded alongside library updates.

---

## Upgrade Strategy

### Phase 1: Critical & High Priority (Week 1)

**Services:** $(awk -F, '($5 == "NEEDS_UPGRADE") && ($6 == "CRITICAL" || $6 == "HIGH") {printf "%s ", $1}' "$AUDIT_CSV")

**Steps:**
1. Update Dockerfiles: \`FROM python:3.12-slim\` (or 3.10-slim minimum)
2. Test locally with \`docker-compose build --no-cache <service>\`
3. Run unit tests: \`docker exec <container> pytest\`
4. Deploy to staging
5. Validate functionality
6. Deploy to production

**Estimated Effort:** 1-2 days

---

### Phase 2: Medium Priority (Week 2)

**Services:** $(awk -F, '$5 == "NEEDS_UPGRADE" && $6 == "MEDIUM" {printf "%s ", $1}' "$AUDIT_CSV")

**Steps:**
1. Group services by dependency
2. Update Dockerfiles in batches
3. Test each batch independently
4. Deploy incrementally

**Estimated Effort:** 2-3 days

---

## Dockerfile Update Template

### Before
\`\`\`dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
\`\`\`

### After
\`\`\`dockerfile
FROM python:3.12-slim  # or 3.10-slim minimum
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
\`\`\`

---

## Testing Requirements

### Unit Tests
- Run full test suite for each service
- Verify no breaking changes
- Check for deprecated Python features

### Integration Tests
- Test service-to-service communication
- Validate API contracts
- Check database connections

### Smoke Tests
- Verify service starts correctly
- Health check passes
- Basic functionality works

---

## Rollout Sequence

1. **Day 1:** Core services (data-api, websocket-ingestion, admin-api)
2. **Day 2:** ML services (ml-service, ai-pattern-service, etc.)
3. **Day 3:** Device services
4. **Day 4:** Automation services
5. **Day 5:** Remaining services

---

## Risk Mitigation

### Backup Strategy
- Tag current images before rebuild
- Keep previous Docker images for 7 days
- Document rollback procedure

### Validation Checklist
- [ ] Service builds successfully
- [ ] Container starts without errors
- [ ] Health check passes
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] No new errors in logs

---

## Compatibility Notes

### Python 3.10+ Features Used
- Structural pattern matching (match/case)
- Parenthesized context managers
- Better error messages
- Performance improvements

### Breaking Changes from Python 3.9
- None expected for most services
- Some typing improvements may require updates
- Deprecated warnings may appear

---

## Next Steps

1. Review this upgrade plan
2. Prioritize services based on business impact
3. Update Dockerfiles for Critical/High priority services
4. Test in local development environment
5. Create PR with Dockerfile updates
6. Deploy to staging
7. Validate and deploy to production

---

## Audit Data

Full audit results: \`$(basename $AUDIT_CSV)\`

EOF

    log_success "Upgrade plan created: $(basename $UPGRADE_PLAN)"
    echo ""
}

# Display summary
display_summary() {
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "  Python Version Audit Summary"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""

    # Display CSV in table format
    log_info "Python Version Matrix:"
    echo ""
    column -t -s, "$AUDIT_CSV" | head -20
    echo ""

    if [ $(tail -n +2 "$AUDIT_CSV" | wc -l) -gt 19 ]; then
        log_info "... (showing first 19 services, see full CSV for complete list)"
        echo ""
    fi

    # Statistics
    local total=$(tail -n +2 "$AUDIT_CSV" | wc -l)
    local needs_upgrade=$(grep -c "NEEDS_UPGRADE" "$AUDIT_CSV" 2>/dev/null || echo "0")
    local version_ok=$(grep -c ",OK," "$AUDIT_CSV" 2>/dev/null || echo "0")

    log_info "📊 Statistics:"
    echo "   Total services audited: $total"
    echo "   ✅ Python 3.10+: $version_ok"
    echo "   ⚠️  Needs upgrade: $needs_upgrade"
    echo ""

    log_info "📁 Output Files:"
    echo "   - Audit CSV: $AUDIT_CSV"

    if [ "$DETAILED" = true ]; then
        echo "   - Dockerfile Analysis: $DOCKERFILE_ANALYSIS"
        echo "   - Upgrade Plan: $UPGRADE_PLAN"
    fi
    echo ""

    log_info "📖 Next Steps:"
    if [ "$needs_upgrade" -gt 0 ]; then
        echo "   1. Review services needing upgrade"
        if [ "$DETAILED" = true ]; then
            echo "   2. Read upgrade plan: cat $UPGRADE_PLAN"
            echo "   3. Update Dockerfiles for critical services first"
        else
            echo "   2. Run with --detailed for upgrade recommendations"
            echo "   3. Update Dockerfiles as needed"
        fi
    else
        echo "   ✅ All services are on Python 3.10+"
        echo "   → Proceed to Phase 0 Story 4 (Infrastructure validation)"
    fi
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
}

# Main execution
main() {
    echo ""
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║  Python Version Audit                                        ║"
    echo "║  Phase 0 - Story 3: Verify Python Versions                  ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo ""

    setup_audit_dir
    check_python_versions
    analyze_dockerfiles
    create_upgrade_plan
    display_summary

    log_success "Python version audit completed successfully"
}

# Run main function
main "$@"
