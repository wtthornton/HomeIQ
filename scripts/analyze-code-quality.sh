#!/bin/bash
# Code Quality Analysis Script
# Analyzes Python and TypeScript code for complexity, duplication, and maintainability

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Create reports directory
mkdir -p reports/quality
mkdir -p reports/duplication
mkdir -p reports/coverage

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Code Quality Analysis Report${NC}"
echo -e "${BLUE}Generated: $(date)${NC}"
echo -e "${BLUE}========================================${NC}\n"

# ============================================
# PYTHON SERVICES ANALYSIS
# ============================================

echo -e "${GREEN}[1/6] Analyzing Python Code Complexity...${NC}\n"

# Check if radon is installed
if command -v radon &> /dev/null; then
    echo "Cyclomatic Complexity (average per module):"
    radon cc services/*/src/*.py services/*/src/**/*.py -a -s 2>/dev/null || echo "No Python files found or radon error"
    
    echo -e "\nMaintainability Index (A=85-100, B=65-84, C=50-64, D/F=0-49):"
    radon mi services/*/src/*.py services/*/src/**/*.py -s 2>/dev/null || echo "No Python files found or radon error"
    
    # Generate JSON report
    radon cc services/ -a --json > reports/quality/python-complexity.json 2>/dev/null || true
    radon mi services/ --json > reports/quality/python-maintainability.json 2>/dev/null || true
    
    echo -e "${GREEN}✓ Reports saved to reports/quality/${NC}\n"
else
    echo -e "${YELLOW}⚠ Radon not installed. Run: pip install -r requirements-quality.txt${NC}\n"
fi

# ============================================
# PYTHON LINTING
# ============================================

echo -e "${GREEN}[2/6] Running Python Linting (Pylint)...${NC}\n"

if command -v pylint &> /dev/null; then
    # Run pylint on key services (limit output)
    pylint services/data-api/src/ --output-format=text --reports=y > reports/quality/pylint-data-api.txt 2>&1 || true
    pylint services/admin-api/src/ --output-format=text --reports=y > reports/quality/pylint-admin-api.txt 2>&1 || true
    
    # Show summary
    echo "Pylint scores saved to reports/quality/pylint-*.txt"
    echo -e "${GREEN}✓ Linting complete${NC}\n"
else
    echo -e "${YELLOW}⚠ Pylint not installed. Run: pip install -r requirements-quality.txt${NC}\n"
fi

# ============================================
# TYPESCRIPT ANALYSIS
# ============================================

echo -e "${GREEN}[3/6] Analyzing TypeScript Code...${NC}\n"

cd services/health-dashboard

# Type checking
echo "Running TypeScript type checking..."
npm run type-check 2>&1 | tee ../../reports/quality/typescript-typecheck.txt || true

# ESLint with complexity rules
echo -e "\nRunning ESLint with complexity analysis..."
npm run lint -- --format json --output-file ../../reports/quality/eslint-report.json 2>/dev/null || true
npm run lint 2>&1 | tee ../../reports/quality/eslint-report.txt || true

cd ../..

echo -e "${GREEN}✓ TypeScript analysis complete${NC}\n"

# ============================================
# CODE DUPLICATION DETECTION
# ============================================

echo -e "${GREEN}[4/6] Detecting Code Duplication...${NC}\n"

if command -v jscpd &> /dev/null; then
    echo "Analyzing Python services..."
    jscpd services/data-api/src/ services/admin-api/src/ services/websocket-ingestion/src/ \
        --format python --threshold 3 --min-lines 5 \
        --output reports/duplication/python 2>/dev/null || echo "No duplicates found or jscpd error"
    
    echo -e "\nAnalyzing TypeScript/React code..."
    jscpd services/health-dashboard/src/ \
        --config services/health-dashboard/.jscpd.json 2>/dev/null || echo "No duplicates found or jscpd error"
    
    echo -e "${GREEN}✓ Duplication reports saved to reports/duplication/${NC}\n"
else
    echo -e "${YELLOW}⚠ jscpd not installed. Run: npm install -g jscpd${NC}\n"
fi

# ============================================
# DEPENDENCY ANALYSIS
# ============================================

echo -e "${GREEN}[5/6] Analyzing Dependencies...${NC}\n"

# Python dependencies
if command -v pipdeptree &> /dev/null; then
    echo "Python dependency tree:"
    pipdeptree --warn silence > reports/quality/python-dependencies.txt 2>/dev/null || true
    echo -e "${GREEN}✓ Saved to reports/quality/python-dependencies.txt${NC}"
fi

# Security audit
if command -v pip-audit &> /dev/null; then
    echo -e "\nRunning security audit..."
    pip-audit --desc --format json > reports/quality/security-audit.json 2>/dev/null || true
    echo -e "${GREEN}✓ Security audit saved${NC}"
fi

echo ""

# ============================================
# GENERATE SUMMARY REPORT
# ============================================

echo -e "${GREEN}[6/6] Generating Summary Report...${NC}\n"

cat > reports/quality/SUMMARY.md << 'EOF'
# Code Quality Analysis Summary

Generated: $(date)

## Complexity Metrics

### Python Services
- **Complexity Reports**: `python-complexity.json`
- **Maintainability Index**: `python-maintainability.json`
- **Linting Reports**: `pylint-*.txt`

**Target Thresholds:**
- Cyclomatic Complexity: < 15 (warn), < 20 (error)
- Maintainability Index: > 65 (B grade or better)
- Pylint Score: > 8.0 / 10.0

### TypeScript/React
- **Type Check**: `typescript-typecheck.txt`
- **ESLint Report**: `eslint-report.json` / `eslint-report.txt`

**Target Thresholds:**
- Complexity: < 15
- Max Lines per Function: < 100
- Max Nesting Depth: < 4

## Duplication Analysis

Reports in `../duplication/` directory.

**Target Threshold:** < 3% duplication

## Dependency Health

- **Dependency Tree**: `python-dependencies.txt`
- **Security Audit**: `security-audit.json`

## Files Analyzed

### Python Services
- data-api
- admin-api
- websocket-ingestion
- enrichment-pipeline
- ai-automation-service
- (+ 15 other microservices)

### TypeScript Services
- health-dashboard (React + TypeScript)

## How to Read Reports

### Radon Complexity Scores
- **A (1-5)**: Low risk, simple code
- **B (6-10)**: Moderate complexity
- **C (11-20)**: Complex, consider refactoring
- **D (21-50)**: High risk, refactor recommended
- **F (51+)**: Very high risk, urgent refactoring needed

### Maintainability Index
- **A (85-100)**: Highly maintainable
- **B (65-84)**: Moderately maintainable
- **C (50-64)**: Difficult to maintain
- **D/F (0-49)**: Legacy code, high technical debt

### Pylint Scores
- **10/10**: Perfect (rare!)
- **8-10**: Good quality
- **6-8**: Acceptable, some issues
- **< 6**: Needs improvement

## Next Steps

1. Review high-complexity functions (C, D, F ratings)
2. Address code duplication > 5%
3. Fix security vulnerabilities (if any)
4. Improve low maintainability index scores
5. Add tests for complex functions

## Tools Used

- **radon**: Complexity and maintainability
- **pylint**: Python linting
- **ESLint**: TypeScript linting
- **jscpd**: Duplication detection
- **TypeScript**: Type checking
- **pip-audit**: Security scanning

EOF

echo -e "${GREEN}✓ Summary report created: reports/quality/SUMMARY.md${NC}\n"

# ============================================
# FINAL SUMMARY
# ============================================

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Analysis Complete!${NC}"
echo -e "${BLUE}========================================${NC}\n"

echo -e "Reports generated in: ${YELLOW}reports/quality/${NC}"
echo -e "Duplication reports in: ${YELLOW}reports/duplication/${NC}\n"

echo "Next steps:"
echo "  1. Review: cat reports/quality/SUMMARY.md"
echo "  2. Check complexity: cat reports/quality/python-complexity.json"
echo "  3. View duplication: open reports/duplication/html/index.html"
echo "  4. Check ESLint: cat reports/quality/eslint-report.txt"

echo -e "\n${GREEN}Done!${NC}"

