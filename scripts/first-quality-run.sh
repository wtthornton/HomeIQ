#!/bin/bash
# First Quality Run Script
# Guides you through your first code quality analysis

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}First Code Quality Run${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Create reports directory
mkdir -p reports/quality

# ============================================
# Step 1: Quick Ruff Check
# ============================================

echo -e "${GREEN}[Step 1/6] Quick Ruff Check...${NC}\n"

if command -v python &> /dev/null && python -m ruff --version &> /dev/null; then
    echo "Running Ruff linting..."
    python -m ruff check services/ > reports/quality/first-run-ruff.txt 2>&1 || true
    
    RUFF_ISSUES=$(grep -c "^[A-Z][0-9]" reports/quality/first-run-ruff.txt 2>/dev/null || echo "0")
    echo -e "${YELLOW}Found $RUFF_ISSUES linting issues${NC}"
    echo "Report saved to: reports/quality/first-run-ruff.txt"
    echo -e "${GREEN}✓ Step 1 complete${NC}\n"
else
    echo -e "${RED}✗ Ruff not found. Install with: pip install ruff${NC}\n"
fi

# ============================================
# Step 2: Auto-Fix Safe Issues
# ============================================

echo -e "${GREEN}[Step 2/6] Auto-Fixing Safe Issues...${NC}\n"

if command -v python &> /dev/null && python -m ruff --version &> /dev/null; then
    echo "Running Ruff auto-fix..."
    python -m ruff check --fix services/ 2>&1 | head -20 || true
    
    echo "Checking remaining issues..."
    python -m ruff check services/ > reports/quality/after-auto-fix.txt 2>&1 || true
    REMAINING=$(grep -c "^[A-Z][0-9]" reports/quality/after-auto-fix.txt 2>/dev/null || echo "0")
    echo -e "${YELLOW}Remaining issues: $REMAINING${NC}"
    echo -e "${GREEN}✓ Step 2 complete${NC}\n"
else
    echo -e "${RED}✗ Ruff not found${NC}\n"
fi

# ============================================
# Step 3: Type Checking
# ============================================

echo -e "${GREEN}[Step 3/6] Type Checking with mypy...${NC}\n"

if command -v python &> /dev/null && python -m mypy --version &> /dev/null; then
    echo "Running mypy (this may take a few minutes)..."
    python -m mypy services/ > reports/quality/first-run-mypy.txt 2>&1 || true
    
    MYPY_ERRORS=$(grep -c "error:" reports/quality/first-run-mypy.txt 2>/dev/null || echo "0")
    echo -e "${YELLOW}Found $MYPY_ERRORS type errors${NC}"
    echo "Report saved to: reports/quality/first-run-mypy.txt"
    echo -e "${GREEN}✓ Step 3 complete${NC}\n"
else
    echo -e "${RED}✗ mypy not found. Install with: pip install mypy${NC}\n"
fi

# ============================================
# Step 4: ESLint Check
# ============================================

echo -e "${GREEN}[Step 4/6] ESLint Check...${NC}\n"

if [ -d "services/health-dashboard" ]; then
    cd services/health-dashboard
    
    if command -v npm &> /dev/null && npm run lint &> /dev/null 2>&1; then
        echo "Running ESLint..."
        npm run lint > ../../reports/quality/first-run-eslint.txt 2>&1 || true
        
        ESLINT_WARNINGS=$(grep -c "warning" ../../reports/quality/first-run-eslint.txt 2>/dev/null || echo "0")
        echo -e "${YELLOW}Found $ESLINT_WARNINGS warnings${NC}"
        echo "Report saved to: reports/quality/first-run-eslint.txt"
        echo -e "${GREEN}✓ Step 4 complete${NC}\n"
    else
        echo -e "${YELLOW}⚠ ESLint not configured or npm not found${NC}\n"
    fi
    
    cd ../..
else
    echo -e "${YELLOW}⚠ health-dashboard not found${NC}\n"
fi

# ============================================
# Step 5: Complexity Analysis
# ============================================

echo -e "${GREEN}[Step 5/6] Complexity Analysis...${NC}\n"

if command -v radon &> /dev/null; then
    echo "Running complexity analysis..."
    radon cc services/ -n C -s > reports/quality/first-run-complexity.txt 2>&1 || true
    
    HIGH_COMPLEXITY=$(grep -E " [CDEF] " reports/quality/first-run-complexity.txt 2>/dev/null | wc -l || echo "0")
    echo -e "${YELLOW}Found $HIGH_COMPLEXITY functions with high complexity${NC}"
    echo "Report saved to: reports/quality/first-run-complexity.txt"
    echo -e "${GREEN}✓ Step 5 complete${NC}\n"
else
    echo -e "${YELLOW}⚠ Radon not installed. Install with: pip install radon${NC}\n"
fi

# ============================================
# Step 6: Generate Summary
# ============================================

echo -e "${GREEN}[Step 6/6] Generating Summary...${NC}\n"

cat > reports/quality/FIRST_RUN_SUMMARY.md << EOF
# First Code Quality Run Summary

**Date:** $(date)

## Results Overview

### Ruff Linting
- Initial issues: $(grep -c "^[A-Z][0-9]" reports/quality/first-run-ruff.txt 2>/dev/null || echo "N/A")
- Remaining after auto-fix: $(grep -c "^[A-Z][0-9]" reports/quality/after-auto-fix.txt 2>/dev/null || echo "N/A")

### mypy Type Checking
- Total errors: $(grep -c "error:" reports/quality/first-run-mypy.txt 2>/dev/null || echo "N/A")

### ESLint
- Warnings: $(grep -c "warning" reports/quality/first-run-eslint.txt 2>/dev/null || echo "N/A")

### Complexity
- High complexity functions: $(grep -E " [CDEF] " reports/quality/first-run-complexity.txt 2>/dev/null | wc -l || echo "N/A")

## Reports Generated

- Ruff: \`reports/quality/first-run-ruff.txt\`
- After auto-fix: \`reports/quality/after-auto-fix.txt\`
- mypy: \`reports/quality/first-run-mypy.txt\`
- ESLint: \`reports/quality/first-run-eslint.txt\`
- Complexity: \`reports/quality/first-run-complexity.txt\`

## Next Steps

1. Review the reports above
2. Create an action plan (see \`docs/CODE_QUALITY_FIRST_RUN_PLAN.md\`)
3. Start with Priority 1: Quick wins (auto-fixes)
4. Gradually work through type errors and complexity issues

## Priority Actions

1. [ ] Review Ruff auto-fixes
2. [ ] Identify top 10 mypy errors to fix
3. [ ] List top 5 most complex functions
4. [ ] Create service-specific action plans
5. [ ] Set up weekly quality reviews

EOF

echo -e "${GREEN}✓ Summary generated: reports/quality/FIRST_RUN_SUMMARY.md${NC}\n"

# ============================================
# Final Summary
# ============================================

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}First Run Complete!${NC}"
echo -e "${BLUE}========================================${NC}\n"

echo "Reports generated in: ${YELLOW}reports/quality/${NC}"
echo "Summary: ${YELLOW}reports/quality/FIRST_RUN_SUMMARY.md${NC}\n"

echo "Next steps:"
echo "  1. Review: cat reports/quality/FIRST_RUN_SUMMARY.md"
echo "  2. See plan: cat docs/CODE_QUALITY_FIRST_RUN_PLAN.md"
echo "  3. Review Ruff: cat reports/quality/first-run-ruff.txt"
echo "  4. Review mypy: cat reports/quality/first-run-mypy.txt"

echo -e "\n${GREEN}Done!${NC}"

