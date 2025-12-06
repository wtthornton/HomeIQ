# Setup Script for Code Quality Tools (PowerShell) - 2025 Edition
# Installs all necessary tools for code quality analysis
# Updated: December 2025 - Includes Ruff (10-100x faster than pylint), mypy, and modern patterns

$ErrorActionPreference = "Continue"

Write-Host "========================================" -ForegroundColor Blue
Write-Host "Code Quality Tools Setup (2025)" -ForegroundColor Blue
Write-Host "========================================`n" -ForegroundColor Blue

# ============================================
# Python Tools
# ============================================

Write-Host "[1/4] Installing Python quality tools...`n" -ForegroundColor Green

if (Get-Command pip -ErrorAction SilentlyContinue) {
    pip install -r requirements-quality.txt
    Write-Host "✓ Python tools installed`n" -ForegroundColor Green
} else {
    Write-Host "⚠ pip not found. Please install Python first.`n" -ForegroundColor Yellow
}

# ============================================
# Node.js Global Tools
# ============================================

Write-Host "[2/4] Installing Node.js global tools...`n" -ForegroundColor Green

if (Get-Command npm -ErrorAction SilentlyContinue) {
    # Install jscpd globally for cross-language duplication detection
    npm install -g jscpd
    Write-Host "✓ Node.js tools installed`n" -ForegroundColor Green
} else {
    Write-Host "⚠ npm not found. Please install Node.js first.`n" -ForegroundColor Yellow
}

# ============================================
# Frontend Dependencies
# ============================================

Write-Host "[3/4] Setting up frontend quality tools...`n" -ForegroundColor Green

# Setup health-dashboard (2025: Both TypeScript services)
if (Test-Path "services/health-dashboard") {
    Push-Location services/health-dashboard
    
    # Install jscpd as dev dependency (if not already installed)
    $jscpdInstalled = npm list jscpd 2>$null
    if (-not $jscpdInstalled) {
        npm install --save-dev jscpd
    }
    
    # Create reports directory
    New-Item -ItemType Directory -Force -Path reports | Out-Null
    
    Pop-Location
    Write-Host "[OK] health-dashboard tools ready" -ForegroundColor Green
} else {
    Write-Host "[SKIP] health-dashboard not found" -ForegroundColor Yellow
}

# Setup ai-automation-ui (2025 addition)
if (Test-Path "services/ai-automation-ui") {
    Push-Location services/ai-automation-ui
    
    # Install jscpd as dev dependency (if not already installed)
    $jscpdInstalled = npm list jscpd 2>$null
    if (-not $jscpdInstalled) {
        npm install --save-dev jscpd
    }
    
    Pop-Location
    Write-Host "[OK] ai-automation-ui tools ready`n" -ForegroundColor Green
} else {
    Write-Host "[SKIP] ai-automation-ui not found`n" -ForegroundColor Yellow
}

# ============================================
# Create Reports Directories
# ============================================

Write-Host "[4/4] Creating reports directories...`n" -ForegroundColor Green

New-Item -ItemType Directory -Force -Path reports/quality | Out-Null
New-Item -ItemType Directory -Force -Path reports/duplication | Out-Null
New-Item -ItemType Directory -Force -Path reports/coverage | Out-Null
New-Item -ItemType File -Force -Path reports/.gitkeep | Out-Null

Write-Host "✓ Directories created`n" -ForegroundColor Green

# ============================================
# Verify Installation
# ============================================

Write-Host "========================================" -ForegroundColor Blue
Write-Host "Verifying Installation" -ForegroundColor Blue
Write-Host "========================================`n" -ForegroundColor Blue

Write-Host "Checking Python tools (2025)..."
# Check Ruff (2025 standard - primary linter)
if (Get-Command python -ErrorAction SilentlyContinue) {
    $ruffCheck = python -m ruff --version 2>$null
    if ($ruffCheck) { Write-Host "  [OK] ruff (2025 standard)" -ForegroundColor Green } else { Write-Host "  [MISS] ruff - Install: pip install ruff" -ForegroundColor Yellow }
} else {
    Write-Host "  [SKIP] Python not found" -ForegroundColor Yellow
}
if (Get-Command radon -ErrorAction SilentlyContinue) { Write-Host "  [OK] radon" -ForegroundColor Green } else { Write-Host "  [MISS] radon" -ForegroundColor Yellow }
if (Get-Command mypy -ErrorAction SilentlyContinue) { Write-Host "  [OK] mypy (2025 standard)" -ForegroundColor Green } else { Write-Host "  [MISS] mypy - Install: pip install mypy" -ForegroundColor Yellow }
if (Get-Command pylint -ErrorAction SilentlyContinue) { Write-Host "  [OK] pylint (legacy)" -ForegroundColor Green } else { Write-Host "  [SKIP] pylint (optional - Ruff preferred)" -ForegroundColor Gray }
if (Get-Command prospector -ErrorAction SilentlyContinue) { Write-Host "  [OK] prospector" -ForegroundColor Green } else { Write-Host "  [SKIP] prospector (optional)" -ForegroundColor Gray }
if (Get-Command pip-audit -ErrorAction SilentlyContinue) { Write-Host "  [OK] pip-audit" -ForegroundColor Green } else { Write-Host "  [SKIP] pip-audit (optional)" -ForegroundColor Gray }

Write-Host "`nChecking Node.js tools..."
if (Get-Command jscpd -ErrorAction SilentlyContinue) { Write-Host "  [OK] jscpd" -ForegroundColor Green } else { Write-Host "  [MISS] jscpd - Install: npm install -g jscpd" -ForegroundColor Yellow }

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "Setup Complete!" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Green

Write-Host "Next steps:"
Write-Host "  1. Run quick check: .\scripts\quick-quality-check.ps1"
Write-Host "  2. Run full analysis: .\scripts\analyze-code-quality.ps1"
Write-Host "  3. Check databases: python scripts\check_database_quality.py --all"
Write-Host "  4. Optimize InfluxDB: python scripts\optimize_influxdb_shards.py"

Write-Host "`n[COMPLETE] Setup finished!" -ForegroundColor Green
Write-Host "`nWindows Usage Guide:" -ForegroundColor Blue
Write-Host "  Setup: .\scripts\setup-quality-tools.ps1" -ForegroundColor Cyan
Write-Host "  Quick: .\scripts\quick-quality-check.ps1" -ForegroundColor Cyan
Write-Host "  Full:  .\scripts\analyze-code-quality.ps1" -ForegroundColor Cyan
Write-Host "  DB:    python scripts\check_database_quality.py --all" -ForegroundColor Cyan
Write-Host "  Influx: python scripts\optimize_influxdb_shards.py" -ForegroundColor Cyan

