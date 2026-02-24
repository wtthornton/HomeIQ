#!/bin/bash
# Quick Quality Check - Fast analysis without full reports
# Use this for pre-commit checks or quick validation

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}Quick Quality Check${NC}\n"

ERRORS=0
WARNINGS=0

# ============================================
# Python Complexity Check
# ============================================

echo -e "${YELLOW}[1/4] Python Complexity...${NC}"

if command -v radon &> /dev/null; then
    # Check for high complexity (> 15)
    COMPLEX_FILES=$(radon cc domains/*/*/src/ -n C -s 2>/dev/null | grep -v "^$" | wc -l)

    if [ "$COMPLEX_FILES" -gt 0 ]; then
        echo -e "${RED}  ✗ Found $COMPLEX_FILES files with complexity > 10${NC}"
        radon cc domains/*/*/src/ -n C -s 2>/dev/null | head -20
        WARNINGS=$((WARNINGS + 1))
    else
        echo -e "${GREEN}  ✓ All files have acceptable complexity${NC}"
    fi
else
    echo -e "${YELLOW}  ⊘ Radon not installed (skipping)${NC}"
fi

# ============================================
# TypeScript Linting
# ============================================

echo -e "\n${YELLOW}[2/4] TypeScript Linting...${NC}"

cd domains/core-platform/health-dashboard
LINT_OUTPUT=$(npm run lint 2>&1 || true)

if echo "$LINT_OUTPUT" | grep -q "error"; then
    echo -e "${RED}  ✗ ESLint errors found${NC}"
    echo "$LINT_OUTPUT" | grep "error" | head -10
    ERRORS=$((ERRORS + 1))
elif echo "$LINT_OUTPUT" | grep -q "warning"; then
    echo -e "${YELLOW}  ! ESLint warnings found${NC}"
    WARNINGS=$((WARNINGS + 1))
else
    echo -e "${GREEN}  ✓ No linting issues${NC}"
fi

cd ../../..

# ============================================
# Type Checking
# ============================================

echo -e "\n${YELLOW}[3/4] TypeScript Type Checking...${NC}"

cd domains/core-platform/health-dashboard
TYPE_OUTPUT=$(npm run type-check 2>&1 || true)

if echo "$TYPE_OUTPUT" | grep -q "error TS"; then
    echo -e "${RED}  ✗ Type errors found${NC}"
    echo "$TYPE_OUTPUT" | grep "error TS" | head -10
    ERRORS=$((ERRORS + 1))
else
    echo -e "${GREEN}  ✓ No type errors${NC}"
fi

cd ../../..

# ============================================
# Quick Duplication Check
# ============================================

echo -e "\n${YELLOW}[4/4] Quick Duplication Check...${NC}"

if command -v jscpd &> /dev/null; then
    # Check just the main services for duplication
    DUP_OUTPUT=$(jscpd domains/core-platform/data-api/src/ domains/core-platform/admin-api/src/ \
        --threshold 5 --min-lines 10 --reporters console 2>/dev/null || true)
    
    if echo "$DUP_OUTPUT" | grep -q "duplicates"; then
        echo -e "${YELLOW}  ! Code duplication detected${NC}"
        WARNINGS=$((WARNINGS + 1))
    else
        echo -e "${GREEN}  ✓ No significant duplication${NC}"
    fi
else
    echo -e "${YELLOW}  ⊘ jscpd not installed (skipping)${NC}"
fi

# ============================================
# Summary
# ============================================

echo -e "\n${GREEN}========================================${NC}"

if [ "$ERRORS" -eq 0 ] && [ "$WARNINGS" -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed!${NC}"
    exit 0
elif [ "$ERRORS" -eq 0 ]; then
    echo -e "${YELLOW}⚠ Passed with $WARNINGS warnings${NC}"
    exit 0
else
    echo -e "${RED}✗ Failed with $ERRORS errors and $WARNINGS warnings${NC}"
    echo -e "\nRun ${YELLOW}./scripts/analyze-code-quality.sh${NC} for detailed report"
    exit 1
fi

