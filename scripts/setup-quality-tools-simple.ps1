# Simple Quality Tools Setup for NUC Deployment (PowerShell)
# Installs essential, lightweight tools only

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Blue
Write-Host "Simple Quality Tools Setup (NUC-Optimized)" -ForegroundColor Blue
Write-Host "========================================`n" -ForegroundColor Blue

# ============================================
# Python Tools
# ============================================

Write-Host "[1/3] Installing Python quality tools...`n" -ForegroundColor Green

if (Get-Command pip -ErrorAction SilentlyContinue) {
    Write-Host "Installing Ruff (fast linter)..."
    pip install ruff 2>&1 | Out-Null
    
    Write-Host "Installing mypy (type checker)..."
    pip install mypy 2>&1 | Out-Null
    
    Write-Host "✓ Python tools installed`n" -ForegroundColor Green
} else {
    Write-Host "⚠ pip not found. Please install Python first.`n" -ForegroundColor Yellow
}

# ============================================
# TypeScript/JavaScript Tools
# ============================================

Write-Host "[2/3] Setting up TypeScript quality tools...`n" -ForegroundColor Green

if (Test-Path "services/health-dashboard") {
    Push-Location "services/health-dashboard"
    
    if (Get-Command npm -ErrorAction SilentlyContinue) {
        Write-Host "Installing ESLint complexity plugin..."
        npm install --save-dev eslint-plugin-complexity 2>&1 | Out-Null
        
        Write-Host "✓ TypeScript tools ready`n" -ForegroundColor Green
    } else {
        Write-Host "⚠ npm not found. Skipping TypeScript tools.`n" -ForegroundColor Yellow
    }
    
    Pop-Location
} else {
    Write-Host "⚠ health-dashboard not found`n" -ForegroundColor Yellow
}

# ============================================
# Verify Installation
# ============================================

Write-Host "[3/3] Verifying installation...`n" -ForegroundColor Green

Write-Host "Checking Python tools..."
if (Get-Command ruff -ErrorAction SilentlyContinue) {
    Write-Host "  ✓ ruff" -ForegroundColor Green
} else {
    Write-Host "  ✗ ruff (not installed)" -ForegroundColor Red
}

if (Get-Command mypy -ErrorAction SilentlyContinue) {
    Write-Host "  ✓ mypy" -ForegroundColor Green
} else {
    Write-Host "  ✗ mypy (not installed)" -ForegroundColor Red
}

Write-Host "`nChecking TypeScript tools..."
if (Test-Path "services/health-dashboard") {
    Push-Location "services/health-dashboard"
    $complexityInstalled = npm list eslint-plugin-complexity 2>&1 | Select-String -Pattern "eslint-plugin-complexity"
    if ($complexityInstalled) {
        Write-Host "  ✓ eslint-plugin-complexity" -ForegroundColor Green
    } else {
        Write-Host "  ✗ eslint-plugin-complexity (not installed)" -ForegroundColor Red
    }
    Pop-Location
}

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Green

Write-Host "Next steps:"
Write-Host "  1. Run quick check: ruff check services/"
Write-Host "  2. Run type check: mypy services/"
Write-Host "  3. Run full analysis: .\scripts\analyze-code-quality.sh"
Write-Host "  4. View guide: Get-Content docs\CODE_QUALITY_SIMPLE_PLAN.md"

Write-Host "`nDone!" -ForegroundColor Blue

