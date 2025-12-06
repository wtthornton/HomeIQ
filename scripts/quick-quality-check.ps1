# Quick Quality Check - Fast analysis without full reports (2025 Edition)
# Use this for pre-commit checks or quick validation

$ErrorActionPreference = "Continue"

$ERRORS = 0
$WARNINGS = 0

Write-Host "Quick Quality Check" -ForegroundColor Green
Write-Host ""

# ============================================
# Python Complexity Check (2025: Ruff + Radon)
# ============================================

Write-Host "[1/5] Python Complexity..." -ForegroundColor Yellow

if (Get-Command radon -ErrorAction SilentlyContinue) {
    $complexOutput = radon cc services/*/src/ -n C -s 2>$null | Where-Object { $_ -ne "" }
    
    if ($complexOutput) {
        $complexCount = ($complexOutput | Measure-Object -Line).Lines
        Write-Host "  [X] Found $complexCount files with complexity > 10" -ForegroundColor Red
        $complexOutput | Select-Object -First 20
        $WARNINGS++
    } else {
        Write-Host "  [OK] All files have acceptable complexity" -ForegroundColor Green
    }
} else {
    Write-Host "  [SKIP] Radon not installed (skipping)" -ForegroundColor Yellow
}

# ============================================
# Python Linting (2025: Ruff)
# ============================================

Write-Host "`n[2/5] Python Linting (Ruff)..." -ForegroundColor Yellow

if (Get-Command python -ErrorAction SilentlyContinue) {
    $ruffOutput = python -m ruff check services/ 2>&1 | Out-String
    
    if ($ruffOutput -match "error|E\d+|F\d+") {
        Write-Host "  [X] Ruff errors found" -ForegroundColor Red
        ($ruffOutput | Select-String -Pattern "error|E\d+|F\d+" | Select-Object -First 10).Line
        $ERRORS++
    } elseif ($ruffOutput -match "warning|W\d+") {
        Write-Host "  [!] Ruff warnings found" -ForegroundColor Yellow
        $WARNINGS++
    } else {
        Write-Host "  [OK] No linting issues" -ForegroundColor Green
    }
} else {
    Write-Host "  [SKIP] Python/Ruff not found (skipping)" -ForegroundColor Yellow
}

# ============================================
# TypeScript Linting (2025: Both Services)
# ============================================

Write-Host "`n[3/5] TypeScript Linting..." -ForegroundColor Yellow

# Check health-dashboard
if (Test-Path "services/health-dashboard") {
    Push-Location services/health-dashboard
    
    if (Get-Command npm -ErrorAction SilentlyContinue) {
        $lintOutput = npm run lint 2>&1 | Out-String
        
        if ($lintOutput -match "error") {
            Write-Host "  [X] ESLint errors found (health-dashboard)" -ForegroundColor Red
            ($lintOutput | Select-String -Pattern "error" | Select-Object -First 10).Line
            $ERRORS++
        } elseif ($lintOutput -match "warning") {
            Write-Host "  [!] ESLint warnings found (health-dashboard)" -ForegroundColor Yellow
            $WARNINGS++
        } else {
            Write-Host "  [OK] No linting issues (health-dashboard)" -ForegroundColor Green
        }
    }
    
    Pop-Location
}

# Check ai-automation-ui (2025 addition)
if (Test-Path "services/ai-automation-ui") {
    Push-Location services/ai-automation-ui
    
    if (Get-Command npm -ErrorAction SilentlyContinue) {
        $lintOutput = npm run lint 2>&1 | Out-String
        
        if ($lintOutput -match "error") {
            Write-Host "  [X] ESLint errors found (ai-automation-ui)" -ForegroundColor Red
            ($lintOutput | Select-String -Pattern "error" | Select-Object -First 10).Line
            $ERRORS++
        } elseif ($lintOutput -match "warning") {
            Write-Host "  [!] ESLint warnings found (ai-automation-ui)" -ForegroundColor Yellow
            $WARNINGS++
        } else {
            Write-Host "  [OK] No linting issues (ai-automation-ui)" -ForegroundColor Green
        }
    }
    
    Pop-Location
}

# ============================================
# Type Checking (2025: Both Services)
# ============================================

Write-Host "`n[4/5] TypeScript Type Checking..." -ForegroundColor Yellow

# Check health-dashboard
if (Test-Path "services/health-dashboard") {
    Push-Location services/health-dashboard
    
    if (Get-Command npm -ErrorAction SilentlyContinue) {
        $typeOutput = npm run type-check 2>&1 | Out-String
        
        if ($typeOutput -match "error TS") {
            Write-Host "  [X] Type errors found (health-dashboard)" -ForegroundColor Red
            ($typeOutput | Select-String -Pattern "error TS" | Select-Object -First 10).Line
            $ERRORS++
        } else {
            Write-Host "  [OK] No type errors (health-dashboard)" -ForegroundColor Green
        }
    }
    
    Pop-Location
}

# Check ai-automation-ui (2025 addition)
if (Test-Path "services/ai-automation-ui") {
    Push-Location services/ai-automation-ui
    
    if (Get-Command npm -ErrorAction SilentlyContinue) {
        # Try type-check script, fallback to tsc
        if (Test-Path "package.json" -PathType Leaf) {
            $packageJson = Get-Content package.json | ConvertFrom-Json
            if ($packageJson.scripts.'type-check') {
                $typeOutput = npm run type-check 2>&1 | Out-String
            } else {
                $typeOutput = npx tsc --noEmit 2>&1 | Out-String
            }
        } else {
            $typeOutput = npx tsc --noEmit 2>&1 | Out-String
        }
        
        if ($typeOutput -match "error TS") {
            Write-Host "  [X] Type errors found (ai-automation-ui)" -ForegroundColor Red
            ($typeOutput | Select-String -Pattern "error TS" | Select-Object -First 10).Line
            $ERRORS++
        } else {
            Write-Host "  [OK] No type errors (ai-automation-ui)" -ForegroundColor Green
        }
    }
    
    Pop-Location
}

# ============================================
# Quick Duplication Check
# ============================================

Write-Host "`n[5/5] Quick Duplication Check..." -ForegroundColor Yellow

if (Get-Command jscpd -ErrorAction SilentlyContinue) {
    $dupOutput = jscpd services/data-api/src/ services/admin-api/src/ --threshold 5 --min-lines 10 --reporters console 2>$null | Out-String
    
    if ($dupOutput -match "duplicates") {
        Write-Host "  [!] Code duplication detected" -ForegroundColor Yellow
        $WARNINGS++
    } else {
        Write-Host "  [OK] No significant duplication" -ForegroundColor Green
    }
} else {
    Write-Host "  [SKIP] jscpd not installed (skipping)" -ForegroundColor Yellow
}

# ============================================
# Summary
# ============================================

Write-Host "`n========================================" -ForegroundColor Green

if ($ERRORS -eq 0 -and $WARNINGS -eq 0) {
    Write-Host "[PASS] All checks passed!" -ForegroundColor Green
    exit 0
} elseif ($ERRORS -eq 0) {
    Write-Host "[WARN] Passed with $WARNINGS warnings" -ForegroundColor Yellow
    exit 0
} else {
    Write-Host "[FAIL] Failed with $ERRORS errors and $WARNINGS warnings" -ForegroundColor Red
    Write-Host ""
    Write-Host "Run .\scripts\analyze-code-quality.ps1 for detailed report" -ForegroundColor Yellow
    exit 1
}

