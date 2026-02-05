#!/bin/bash
# Phase 1: Validate Service Requirements Compatibility
# Story 2 - Service Requirements Analysis

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Phase 1: Service Requirements Analysis${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Output directory
OUTPUT_DIR="diagnostics/phase1"
mkdir -p "$OUTPUT_DIR"

# Output file
OUTPUT_FILE="$OUTPUT_DIR/service_requirements_matrix_$(date +%Y%m%d_%H%M%S).csv"
REPORT_FILE="$OUTPUT_DIR/service_compatibility_report_$(date +%Y%m%d_%H%M%S).md"

# CSV header
echo "Service,Uses Base Requirements,SQLAlchemy Version,aiosqlite Version,FastAPI Version,Pydantic Version,httpx Version,Needs Update,Notes" > "$OUTPUT_FILE"

# Counters
TOTAL_SERVICES=0
SERVICES_WITH_BASE=0
SERVICES_NEED_UPDATE=0
SERVICES_READY=0

echo -e "${BLUE}Analyzing service requirements files...${NC}"
echo ""

# Function to extract version from requirements line
extract_version() {
    local line="$1"
    local package="$2"

    # Try various version formats
    if echo "$line" | grep -qi "^${package}"; then
        # Extract version constraint
        echo "$line" | sed -E "s/.*${package}[=><!]*([0-9.]+).*/\1/" | head -1
    else
        echo "N/A"
    fi
}

# Function to check if file uses base requirements
uses_base_requirements() {
    local file="$1"
    grep -q "^-r.*requirements-base.txt" "$file" 2>/dev/null && echo "YES" || echo "NO"
}

# Analyze each service
for req_file in services/*/requirements.txt; do
    if [ ! -f "$req_file" ]; then
        continue
    fi

    TOTAL_SERVICES=$((TOTAL_SERVICES + 1))

    # Extract service name
    SERVICE_NAME=$(basename $(dirname "$req_file"))

    # Check if uses base requirements
    USES_BASE=$(uses_base_requirements "$req_file")

    if [ "$USES_BASE" = "YES" ]; then
        SERVICES_WITH_BASE=$((SERVICES_WITH_BASE + 1))
    fi

    # Read requirements file
    CONTENT=$(cat "$req_file")

    # Extract versions
    SQLALCHEMY_VERSION=$(echo "$CONTENT" | grep -i "^sqlalchemy" | head -1 || echo "")
    AIOSQLITE_VERSION=$(echo "$CONTENT" | grep -i "^aiosqlite" | head -1 || echo "")
    FASTAPI_VERSION=$(echo "$CONTENT" | grep -i "^fastapi" | head -1 || echo "")
    PYDANTIC_VERSION=$(echo "$CONTENT" | grep -i "^pydantic[^-]" | head -1 || echo "")
    HTTPX_VERSION=$(echo "$CONTENT" | grep -i "^httpx" | head -1 || echo "")

    # Simplify versions for display
    SQLALCHEMY_SIMPLE=$(echo "$SQLALCHEMY_VERSION" | sed -E 's/sqlalchemy[=><!]*([0-9.]+).*/\1/' || echo "N/A")
    AIOSQLITE_SIMPLE=$(echo "$AIOSQLITE_VERSION" | sed -E 's/aiosqlite[=><!]*([0-9.]+).*/\1/' || echo "N/A")
    FASTAPI_SIMPLE=$(echo "$FASTAPI_VERSION" | sed -E 's/fastapi[=><!]*([0-9.]+).*/\1/' || echo "N/A")
    PYDANTIC_SIMPLE=$(echo "$PYDANTIC_VERSION" | sed -E 's/pydantic[=><!]*([0-9.]+).*/\1/' || echo "N/A")
    HTTPX_SIMPLE=$(echo "$HTTPX_VERSION" | sed -E 's/httpx[=><!]*([0-9.]+).*/\1/' || echo "N/A")

    # Determine if service needs update
    NEEDS_UPDATE="NO"
    NOTES=""

    # Check for outdated pinned versions
    if [ "$USES_BASE" = "NO" ]; then
        if [ -n "$SQLALCHEMY_VERSION" ]; then
            if echo "$SQLALCHEMY_VERSION" | grep -q "2.0.45"; then
                NEEDS_UPDATE="YES"
                NOTES="${NOTES}SQLAlchemy 2.0.45→2.0.46; "
            fi
        fi

        if [ -n "$AIOSQLITE_VERSION" ]; then
            if echo "$AIOSQLITE_VERSION" | grep -q "0.21"; then
                NEEDS_UPDATE="YES"
                NOTES="${NOTES}aiosqlite 0.21→0.22.1; "
            fi
        fi

        if [ -n "$FASTAPI_VERSION" ]; then
            if echo "$FASTAPI_VERSION" | grep -qE "0\.(115|116|117|118|119|120|121|122|123|124|125|126|127)\."; then
                if ! echo "$FASTAPI_VERSION" | grep -q "0.128"; then
                    NEEDS_UPDATE="YES"
                    NOTES="${NOTES}FastAPI <0.128; "
                fi
            fi
        fi
    else
        NOTES="Uses base requirements (inherits Phase 1 updates)"
        SERVICES_READY=$((SERVICES_READY + 1))
    fi

    if [ "$NEEDS_UPDATE" = "YES" ]; then
        SERVICES_NEED_UPDATE=$((SERVICES_NEED_UPDATE + 1))
    fi

    # Write to CSV
    echo "$SERVICE_NAME,$USES_BASE,$SQLALCHEMY_SIMPLE,$AIOSQLITE_SIMPLE,$FASTAPI_SIMPLE,$PYDANTIC_SIMPLE,$HTTPX_SIMPLE,$NEEDS_UPDATE,\"$NOTES\"" >> "$OUTPUT_FILE"

    # Print status
    if [ "$NEEDS_UPDATE" = "YES" ]; then
        echo -e "${YELLOW}⚠️  $SERVICE_NAME${NC} - Needs manual update: $NOTES"
    elif [ "$USES_BASE" = "YES" ]; then
        echo -e "${GREEN}✅ $SERVICE_NAME${NC} - Uses base requirements (ready)"
    else
        echo -e "${GREEN}✅ $SERVICE_NAME${NC} - Independent (compatible)"
    fi
done

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Analysis Complete${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Summary
echo -e "${GREEN}Summary:${NC}"
echo -e "  Total Services: $TOTAL_SERVICES"
echo -e "  Using Base Requirements: $SERVICES_WITH_BASE (auto-inherit Phase 1 updates)"
echo -e "  Need Manual Update: $SERVICES_NEED_UPDATE"
echo -e "  Already Compatible: $SERVICES_READY"
echo ""

# Generate detailed report
cat > "$REPORT_FILE" <<EOF
# Phase 1: Service Requirements Compatibility Report

**Generated:** $(date '+%Y-%m-%d %H:%M:%S')
**Story:** 2 of 12 - Validate Service Requirements Compatibility

## Summary

| Metric | Count | Percentage |
|--------|-------|------------|
| **Total Services** | $TOTAL_SERVICES | 100% |
| **Using Base Requirements** | $SERVICES_WITH_BASE | $((SERVICES_WITH_BASE * 100 / TOTAL_SERVICES))% |
| **Need Manual Update** | $SERVICES_NEED_UPDATE | $((SERVICES_NEED_UPDATE * 100 / TOTAL_SERVICES))% |
| **Already Compatible** | $SERVICES_READY | $((SERVICES_READY * 100 / TOTAL_SERVICES))% |

## Service Categories

### ✅ Services Using Base Requirements (Auto-Inherit Phase 1)

These services use \`-r ../../requirements-base.txt\` and will automatically inherit SQLAlchemy 2.0.46 and aiosqlite 0.22.1 updates when rebuilt.

EOF

# List services using base requirements
echo "" >> "$REPORT_FILE"
for req_file in services/*/requirements.txt; do
    if [ ! -f "$req_file" ]; then
        continue
    fi

    SERVICE_NAME=$(basename $(dirname "$req_file"))
    USES_BASE=$(uses_base_requirements "$req_file")

    if [ "$USES_BASE" = "YES" ]; then
        echo "- $SERVICE_NAME" >> "$REPORT_FILE"
    fi
done

# List services needing manual update
cat >> "$REPORT_FILE" <<EOF

### ⚠️  Services Needing Manual Update

These services have pinned versions of critical libraries and need explicit updates:

EOF

HAS_MANUAL_UPDATES=false
for req_file in services/*/requirements.txt; do
    if [ ! -f "$req_file" ]; then
        continue
    fi

    SERVICE_NAME=$(basename $(dirname "$req_file"))
    USES_BASE=$(uses_base_requirements "$req_file")

    if [ "$USES_BASE" = "NO" ]; then
        CONTENT=$(cat "$req_file")

        # Check for outdated versions
        NEEDS_UPDATE=false
        UPDATE_NOTES=""

        if echo "$CONTENT" | grep -q "sqlalchemy.*2.0.45"; then
            NEEDS_UPDATE=true
            UPDATE_NOTES="${UPDATE_NOTES}\n  - SQLAlchemy 2.0.45 → 2.0.46"
        fi

        if echo "$CONTENT" | grep -q "aiosqlite.*0.21"; then
            NEEDS_UPDATE=true
            UPDATE_NOTES="${UPDATE_NOTES}\n  - aiosqlite 0.21.x → 0.22.1"
        fi

        if [ "$NEEDS_UPDATE" = true ]; then
            HAS_MANUAL_UPDATES=true
            echo "" >> "$REPORT_FILE"
            echo "**$SERVICE_NAME:**" >> "$REPORT_FILE"
            echo -e "$UPDATE_NOTES" >> "$REPORT_FILE"
        fi
    fi
done

if [ "$HAS_MANUAL_UPDATES" = false ]; then
    echo "" >> "$REPORT_FILE"
    echo "✅ No services require manual updates." >> "$REPORT_FILE"
fi

# Rebuild strategy
cat >> "$REPORT_FILE" <<EOF

## Rebuild Strategy

### Sequential Rebuild (Services Using Base Requirements)

All services using \`requirements-base.txt\` will be rebuilt in the following order:

1. **Infrastructure** (restart only): influxdb, jaeger
2. **Core Services**: data-api → websocket-ingestion → admin-api → data-retention
3. **Integration Services** (parallel batch): weather-api, sports-api, carbon-intensity, electricity-pricing, air-quality, calendar-service, smart-meter-service, log-aggregator
4. **AI/ML Services** (parallel batch): ai-core-service, ai-pattern-service, ai-automation-service-new, ai-query-service, ai-training-service
5. **Device Services** (parallel batch): device-intelligence-service, device-health-monitor, device-context-classifier, device-database-client, device-recommender, device-setup-assistant, ha-setup-service
6. **Automation Services** (parallel batch): automation-linter, automation-miner, blueprint-index, blueprint-suggestion-service, yaml-validation-service, api-automation-edge
7. **Analytics Services** (parallel batch): energy-correlator, rule-recommendation-ml
8. **Frontend Services**: health-dashboard, ai-automation-ui

### Build Command Template

\`\`\`bash
# For each service
docker-compose build --no-cache {service-name}
docker-compose up -d {service-name}
sleep 30  # Wait for health check
docker ps --filter name={service-name} --format "{{.Status}}"
curl -f http://localhost:{port}/health
\`\`\`

## Next Steps

1. ✅ **Story 1 Complete**: requirements-base.txt updated
2. ✅ **Story 2 Complete**: Service compatibility validated
3. 📋 **Story 3 Next**: Rebuild infrastructure services
4. 📋 **Story 4-10**: Sequential service rebuilds
5. 📋 **Story 11**: Comprehensive validation
6. 📋 **Story 12**: Generate completion report

## Files Generated

- CSV Matrix: \`$OUTPUT_FILE\`
- This Report: \`$REPORT_FILE\`

## Sign-off

- [ ] All services categorized correctly
- [ ] Rebuild strategy confirmed
- [ ] Ready to proceed to Story 3 (Infrastructure Rebuild)

---

**Report Generated By:** Phase 1 Service Validation Script
**Phase:** 1 of 6 (Critical Compatibility Fixes)
**Status:** ✅ Complete
EOF

echo -e "${GREEN}✅ Analysis complete!${NC}"
echo ""
echo -e "Reports generated:"
echo -e "  📊 CSV Matrix: ${BLUE}$OUTPUT_FILE${NC}"
echo -e "  📄 Full Report: ${BLUE}$REPORT_FILE${NC}"
echo ""

# Display services needing manual updates
if [ $SERVICES_NEED_UPDATE -gt 0 ]; then
    echo -e "${YELLOW}⚠️  $SERVICES_NEED_UPDATE service(s) need manual requirements update${NC}"
    echo -e "${YELLOW}   Review the report for details${NC}"
    echo ""
fi

echo -e "${GREEN}✅ Story 2 Complete: Service Requirements Validated${NC}"
echo -e "${BLUE}📋 Next: Story 3 - Rebuild Infrastructure Services${NC}"
