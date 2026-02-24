#!/bin/bash
# Setup Script for Code Quality Tools
# Installs all necessary tools for code quality analysis

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Code Quality Tools Setup${NC}"
echo -e "${BLUE}========================================${NC}\n"

# ============================================
# Python Tools
# ============================================

echo -e "${GREEN}[1/4] Installing Python quality tools...${NC}\n"

if command -v pip &> /dev/null; then
    pip install -r requirements-quality.txt
    echo -e "${GREEN}✓ Python tools installed${NC}\n"
else
    echo -e "${YELLOW}⚠ pip not found. Please install Python first.${NC}\n"
fi

# ============================================
# Node.js Global Tools
# ============================================

echo -e "${GREEN}[2/4] Installing Node.js global tools...${NC}\n"

if command -v npm &> /dev/null; then
    # Install jscpd globally for cross-language duplication detection
    npm install -g jscpd
    echo -e "${GREEN}✓ Node.js tools installed${NC}\n"
else
    echo -e "${YELLOW}⚠ npm not found. Please install Node.js first.${NC}\n"
fi

# ============================================
# Frontend Dependencies
# ============================================

echo -e "${GREEN}[3/4] Setting up frontend quality tools...${NC}\n"

if [ -d "domains/core-platform/health-dashboard" ]; then
    cd domains/core-platform/health-dashboard
    
    # Install jscpd as dev dependency (if not already installed)
    if ! npm list jscpd &> /dev/null; then
        npm install --save-dev jscpd
    fi
    
    # Create reports directory
    mkdir -p reports
    
    cd ../../..
    echo -e "${GREEN}✓ Frontend tools ready${NC}\n"
else
    echo -e "${YELLOW}⚠ health-dashboard not found${NC}\n"
fi

# ============================================
# Create Reports Directories
# ============================================

echo -e "${GREEN}[4/4] Creating reports directories...${NC}\n"

mkdir -p reports/quality
mkdir -p reports/duplication
mkdir -p reports/coverage
touch reports/.gitkeep

echo -e "${GREEN}✓ Directories created${NC}\n"

# ============================================
# Verify Installation
# ============================================

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Verifying Installation${NC}"
echo -e "${BLUE}========================================${NC}\n"

echo "Checking Python tools..."
command -v radon && echo "  ✓ radon" || echo "  ✗ radon"
command -v pylint && echo "  ✓ pylint" || echo "  ✗ pylint"
command -v prospector && echo "  ✓ prospector" || echo "  ✗ prospector"
command -v mypy && echo "  ✓ mypy" || echo "  ✗ mypy"
command -v pip-audit && echo "  ✓ pip-audit" || echo "  ✗ pip-audit"

echo -e "\nChecking Node.js tools..."
command -v jscpd && echo "  ✓ jscpd" || echo "  ✗ jscpd"

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}Setup Complete!${NC}"
echo -e "${GREEN}========================================${NC}\n"

echo "Next steps:"
echo "  1. Run full analysis: ./scripts/analyze-code-quality.sh"
echo "  2. Run quick check: ./scripts/quick-quality-check.sh"
echo "  3. View guide: cat README-QUALITY-ANALYSIS.md"

echo -e "\n${BLUE}Done!${NC}"

