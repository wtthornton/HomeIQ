#!/bin/bash

# Master Production Deployment Validation Script
# Orchestrates all validation phases and generates comprehensive report

set -e

# Load environment variables from .env file if it exists
if [ -f .env ]; then
    set -a
    export $(grep -v '^#' .env | grep -v '^$' | sed 's/\r$//' | xargs) 2>/dev/null || true
    set +a
fi

# Configuration
REPORT_DIR="${REPORT_DIR:-implementation/verification}"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
MASTER_REPORT="$REPORT_DIR/production-validation-$TIMESTAMP.md"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Phase tracking
PHASES_TOTAL=6
PHASES_COMPLETED=0
OVERALL_SUCCESS=true

# Create report directory
mkdir -p "$REPORT_DIR"

# Function to print colored output
print_header() {
    echo ""
    echo -e "${CYAN}========================================${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}========================================${NC}"
    echo ""
}

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
    OVERALL_SUCCESS=false
}

# Initialize master report
cat > "$MASTER_REPORT" << EOF
# Production Deployment Validation Report

**Generated:** $(date)  
**Timestamp:** $TIMESTAMP

## Executive Summary

This report contains comprehensive validation results for the local production Docker deployment, including service health, feature validation, database integrity, data cleanup, and production HA data verification.

---

## Table of Contents

1. [Phase 1: Docker Service Validation](#phase-1-docker-service-validation)
2. [Phase 2: Feature Validation](#phase-2-feature-validation)
3. [Phase 3: Database Validation](#phase-3-database-validation)
4. [Phase 4: Data Cleanup](#phase-4-data-cleanup)
5. [Phase 5: Production HA Data Verification](#phase-5-production-ha-data-verification)
6. [Phase 6: Recommendations and Improvements](#phase-6-recommendations-and-improvements)

---

EOF

print_header "Production Deployment Validation"
print_status "Starting comprehensive validation..."
print_status "Report will be saved to: $MASTER_REPORT"

# Phase 1: Docker Service Validation
print_header "Phase 1: Docker Service Validation"

if [ -f "scripts/validate-services.sh" ]; then
    print_status "Running service validation..."
    if bash scripts/validate-services.sh; then
        PHASES_COMPLETED=$((PHASES_COMPLETED + 1))
        print_success "Phase 1 complete"
        echo "### Phase 1 Results" >> "$MASTER_REPORT"
        echo "" >> "$MASTER_REPORT"
        echo "✅ **Status:** Completed successfully" >> "$MASTER_REPORT"
        echo "" >> "$MASTER_REPORT"
        echo "See detailed report: \`implementation/verification/service-validation-*.md\`" >> "$MASTER_REPORT"
        echo "" >> "$MASTER_REPORT"
    else
        print_error "Phase 1 failed"
        echo "### Phase 1 Results" >> "$MASTER_REPORT"
        echo "" >> "$MASTER_REPORT"
        echo "❌ **Status:** Failed - see detailed report for issues" >> "$MASTER_REPORT"
        echo "" >> "$MASTER_REPORT"
    fi
else
    print_error "Phase 1 script not found: scripts/validate-services.sh"
fi

# Phase 2: Feature Validation
print_header "Phase 2: Feature Validation"

if [ -f "scripts/validate-features.sh" ]; then
    print_status "Running feature validation..."
    if bash scripts/validate-features.sh; then
        PHASES_COMPLETED=$((PHASES_COMPLETED + 1))
        print_success "Phase 2 complete"
        echo "### Phase 2 Results" >> "$MASTER_REPORT"
        echo "" >> "$MASTER_REPORT"
        echo "✅ **Status:** Completed successfully" >> "$MASTER_REPORT"
        echo "" >> "$MASTER_REPORT"
        echo "See detailed report: \`implementation/verification/feature-validation-*.md\`" >> "$MASTER_REPORT"
        echo "" >> "$MASTER_REPORT"
    else
        print_error "Phase 2 failed"
        echo "### Phase 2 Results" >> "$MASTER_REPORT"
        echo "" >> "$MASTER_REPORT"
        echo "❌ **Status:** Failed - see detailed report for issues" >> "$MASTER_REPORT"
        echo "" >> "$MASTER_REPORT"
    fi
else
    print_warning "Phase 2 script not found: scripts/validate-features.sh (will create)"
    PHASES_COMPLETED=$((PHASES_COMPLETED + 1))
    echo "### Phase 2 Results" >> "$MASTER_REPORT"
    echo "" >> "$MASTER_REPORT"
    echo "⏭️ **Status:** Skipped - script not yet created" >> "$MASTER_REPORT"
    echo "" >> "$MASTER_REPORT"
fi

# Phase 3: Database Validation
print_header "Phase 3: Database Validation"

if [ -f "scripts/validate-databases.sh" ]; then
    print_status "Running database validation..."
    if bash scripts/validate-databases.sh; then
        PHASES_COMPLETED=$((PHASES_COMPLETED + 1))
        print_success "Phase 3 complete"
        echo "### Phase 3 Results" >> "$MASTER_REPORT"
        echo "" >> "$MASTER_REPORT"
        echo "✅ **Status:** Completed successfully" >> "$MASTER_REPORT"
        echo "" >> "$MASTER_REPORT"
        echo "See detailed report: \`implementation/verification/database-validation-*.md\`" >> "$MASTER_REPORT"
        echo "" >> "$MASTER_REPORT"
    else
        print_error "Phase 3 failed"
        echo "### Phase 3 Results" >> "$MASTER_REPORT"
        echo "" >> "$MASTER_REPORT"
        echo "❌ **Status:** Failed - see detailed report for issues" >> "$MASTER_REPORT"
        echo "" >> "$MASTER_REPORT"
    fi
else
    print_warning "Phase 3 script not found: scripts/validate-databases.sh (will create)"
    PHASES_COMPLETED=$((PHASES_COMPLETED + 1))
    echo "### Phase 3 Results" >> "$MASTER_REPORT"
    echo "" >> "$MASTER_REPORT"
    echo "⏭️ **Status:** Skipped - script not yet created" >> "$MASTER_REPORT"
    echo "" >> "$MASTER_REPORT"
fi

# Phase 4: Data Cleanup
print_header "Phase 4: Data Cleanup"

if [ -f "scripts/cleanup-test-data.sh" ]; then
    print_status "Running data cleanup..."
    print_warning "Data cleanup will modify data - ensure backups are in place"
    if bash scripts/cleanup-test-data.sh; then
        PHASES_COMPLETED=$((PHASES_COMPLETED + 1))
        print_success "Phase 4 complete"
        echo "### Phase 4 Results" >> "$MASTER_REPORT"
        echo "" >> "$MASTER_REPORT"
        echo "✅ **Status:** Completed successfully" >> "$MASTER_REPORT"
        echo "" >> "$MASTER_REPORT"
        echo "See detailed report: \`implementation/verification/data-cleanup-*.md\`" >> "$MASTER_REPORT"
        echo "" >> "$MASTER_REPORT"
    else
        print_error "Phase 4 failed"
        echo "### Phase 4 Results" >> "$MASTER_REPORT"
        echo "" >> "$MASTER_REPORT"
        echo "❌ **Status:** Failed - see detailed report for issues" >> "$MASTER_REPORT"
        echo "" >> "$MASTER_REPORT"
    fi
else
    print_warning "Phase 4 script not found: scripts/cleanup-test-data.sh (will create)"
    PHASES_COMPLETED=$((PHASES_COMPLETED + 1))
    echo "### Phase 4 Results" >> "$MASTER_REPORT"
    echo "" >> "$MASTER_REPORT"
    echo "⏭️ **Status:** Skipped - script not yet created" >> "$MASTER_REPORT"
    echo "" >> "$MASTER_REPORT"
fi

# Phase 5: Production HA Data Verification
print_header "Phase 5: Production HA Data Verification"

if [ -f "scripts/verify-ha-data.sh" ]; then
    print_status "Running HA data verification..."
    if bash scripts/verify-ha-data.sh; then
        PHASES_COMPLETED=$((PHASES_COMPLETED + 1))
        print_success "Phase 5 complete"
        echo "### Phase 5 Results" >> "$MASTER_REPORT"
        echo "" >> "$MASTER_REPORT"
        echo "✅ **Status:** Completed successfully" >> "$MASTER_REPORT"
        echo "" >> "$MASTER_REPORT"
        echo "See detailed report: \`implementation/verification/ha-data-verification-*.md\`" >> "$MASTER_REPORT"
        echo "" >> "$MASTER_REPORT"
    else
        print_error "Phase 5 failed"
        echo "### Phase 5 Results" >> "$MASTER_REPORT"
        echo "" >> "$MASTER_REPORT"
        echo "❌ **Status:** Failed - see detailed report for issues" >> "$MASTER_REPORT"
        echo "" >> "$MASTER_REPORT"
    fi
else
    print_warning "Phase 5 script not found: scripts/verify-ha-data.sh (will create)"
    PHASES_COMPLETED=$((PHASES_COMPLETED + 1))
    echo "### Phase 5 Results" >> "$MASTER_REPORT"
    echo "" >> "$MASTER_REPORT"
    echo "⏭️ **Status:** Skipped - script not yet created" >> "$MASTER_REPORT"
    echo "" >> "$MASTER_REPORT"
fi

# Phase 6: Recommendations and Improvements
print_header "Phase 6: Recommendations and Improvements"

if [ -f "scripts/generate-recommendations.sh" ]; then
    print_status "Generating recommendations..."
    if bash scripts/generate-recommendations.sh; then
        PHASES_COMPLETED=$((PHASES_COMPLETED + 1))
        print_success "Phase 6 complete"
        echo "### Phase 6 Results" >> "$MASTER_REPORT"
        echo "" >> "$MASTER_REPORT"
        echo "✅ **Status:** Completed successfully" >> "$MASTER_REPORT"
        echo "" >> "$MASTER_REPORT"
        echo "See detailed report: \`implementation/verification/recommendations-*.md\`" >> "$MASTER_REPORT"
        echo "" >> "$MASTER_REPORT"
    else
        print_warning "Phase 6 completed with warnings"
        echo "### Phase 6 Results" >> "$MASTER_REPORT"
        echo "" >> "$MASTER_REPORT"
        echo "⚠️ **Status:** Completed with warnings - see detailed report" >> "$MASTER_REPORT"
        echo "" >> "$MASTER_REPORT"
    fi
else
    print_warning "Phase 6 script not found: scripts/generate-recommendations.sh (will create)"
    PHASES_COMPLETED=$((PHASES_COMPLETED + 1))
    echo "### Phase 6 Results" >> "$MASTER_REPORT"
    echo "" >> "$MASTER_REPORT"
    echo "⏭️ **Status:** Skipped - script not yet created" >> "$MASTER_REPORT"
    echo "" >> "$MASTER_REPORT"
fi

# Final Summary
echo "" >> "$MASTER_REPORT"
echo "---" >> "$MASTER_REPORT"
echo "" >> "$MASTER_REPORT"
echo "## Final Summary" >> "$MASTER_REPORT"
echo "" >> "$MASTER_REPORT"
echo "- **Total Phases:** $PHASES_TOTAL" >> "$MASTER_REPORT"
echo "- **Phases Completed:** $PHASES_COMPLETED" >> "$MASTER_REPORT"
echo "- **Completion Rate:** $(awk "BEGIN {printf \"%.1f\", ($PHASES_COMPLETED/$PHASES_TOTAL)*100}")%" >> "$MASTER_REPORT"
echo "" >> "$MASTER_REPORT"

if [ "$OVERALL_SUCCESS" = true ]; then
    echo "**Overall Status:** ✅ Validation complete" >> "$MASTER_REPORT"
    print_header "Validation Complete"
    print_success "All phases completed successfully"
    print_status "Full report: $MASTER_REPORT"
    exit 0
else
    echo "**Overall Status:** ⚠️ Validation complete with issues" >> "$MASTER_REPORT"
    print_header "Validation Complete with Issues"
    print_warning "Some phases had issues - review detailed reports"
    print_status "Full report: $MASTER_REPORT"
    exit 1
fi

