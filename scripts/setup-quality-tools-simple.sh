#!/bin/bash
# Simple Quality Tools Setup for NUC Deployment
# Installs essential, lightweight tools only

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Simple Quality Tools Setup (NUC-Optimized)${NC}"
echo -e "${BLUE}========================================${NC}\n"

# ============================================
# Python Tools
# ============================================

echo -e "${GREEN}[1/3] Installing Python quality tools...${NC}\n"

if command -v pip &> /dev/null; then
    echo "Installing Ruff (fast linter)..."
    pip install ruff > /dev/null 2>&1 || pip install ruff
    
    echo "Installing mypy (type checker)..."
    pip install mypy > /dev/null 2>&1 || pip install mypy
    
    echo -e "${GREEN}✓ Python tools installed${NC}\n"
else
    echo -e "${YELLOW}⚠ pip not found. Please install Python first.${NC}\n"
fi

# ============================================
# TypeScript/JavaScript Tools
# ============================================

echo -e "${GREEN}[2/3] Setting up TypeScript quality tools...${NC}\n"

if [ -d "services/health-dashboard" ]; then
    cd services/health-dashboard
    
    if command -v npm &> /dev/null; then
        echo "Installing ESLint complexity plugin..."
        npm install --save-dev eslint-plugin-complexity 2>&1 | grep -v "npm WARN" || true
        
        echo -e "${GREEN}✓ TypeScript tools ready${NC}\n"
    else
        echo -e "${YELLOW}⚠ npm not found. Skipping TypeScript tools.${NC}\n"
    fi
    
    cd ../..
else
    echo -e "${YELLOW}⚠ health-dashboard not found${NC}\n"
fi

# ============================================
# Verify Installation
# ============================================

echo -e "${GREEN}[3/3] Verifying installation...${NC}\n"

echo "Checking Python tools..."
command -v ruff && echo "  ✓ ruff" || echo "  ✗ ruff (not installed)"
command -v mypy && echo "  ✓ mypy" || echo "  ✗ mypy (not installed)"

echo -e "\nChecking TypeScript tools..."
if [ -d "services/health-dashboard" ]; then
    cd services/health-dashboard
    npm list eslint-plugin-complexity > /dev/null 2>&1 && echo "  ✓ eslint-plugin-complexity" || echo "  ✗ eslint-plugin-complexity (not installed)"
    cd ../..
fi

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}\n"

echo "Next steps:"
echo "  1. Run quick check: ruff check services/"
echo "  2. Run type check: mypy services/"
echo "  3. Run full analysis: ./scripts/analyze-code-quality.sh"
echo "  4. View guide: cat docs/CODE_QUALITY_SIMPLE_PLAN.md"

echo -e "\n${BLUE}Done!${NC}"

