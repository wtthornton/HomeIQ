# First Quality Run Script (PowerShell)
# Guides you through your first code quality analysis

$ErrorActionPreference = "Continue"

# Initialize variables
$ruffIssues = 0
$remaining = 0
$mypyErrors = 0
$eslintWarnings = 0
$highComplexity = 0

Write-Host "========================================" -ForegroundColor Blue
Write-Host "First Code Quality Run" -ForegroundColor Blue
Write-Host "========================================`n" -ForegroundColor Blue

# Create reports directory
New-Item -ItemType Directory -Force -Path "reports/quality" | Out-Null

# ============================================
# Step 1: Quick Ruff Check
# ============================================

Write-Host "[Step 1/6] Quick Ruff Check...`n" -ForegroundColor Green

if (Get-Command python -ErrorAction SilentlyContinue) {
    try {
        python -m ruff --version | Out-Null
        Write-Host "Running Ruff linting..."
        python -m ruff check services/ 2>&1 | Out-File -FilePath "reports/quality/first-run-ruff.txt"
        
        $ruffIssues = (Select-String -Path "reports/quality/first-run-ruff.txt" -Pattern "^[A-Z][0-9]" -ErrorAction SilentlyContinue | Measure-Object).Count
        Write-Host "Found $ruffIssues linting issues" -ForegroundColor Yellow
        Write-Host "Report saved to: reports/quality/first-run-ruff.txt"
        Write-Host "✓ Step 1 complete`n" -ForegroundColor Green
    } catch {
        Write-Host "✗ Ruff not found. Install with: pip install ruff`n" -ForegroundColor Red
    }
} else {
    Write-Host "✗ Python not found`n" -ForegroundColor Red
}

# ============================================
# Step 2: Auto-Fix Safe Issues
# ============================================

Write-Host "[Step 2/6] Auto-Fixing Safe Issues...`n" -ForegroundColor Green

if (Get-Command python -ErrorAction SilentlyContinue) {
    try {
        python -m ruff --version | Out-Null
        Write-Host "Running Ruff auto-fix..."
        python -m ruff check --fix services/ 2>&1 | Select-Object -First 20
        
        Write-Host "Checking remaining issues..."
        python -m ruff check services/ 2>&1 | Out-File -FilePath "reports/quality/after-auto-fix.txt"
        $remaining = (Select-String -Path "reports/quality/after-auto-fix.txt" -Pattern "^[A-Z][0-9]" -ErrorAction SilentlyContinue | Measure-Object).Count
        Write-Host "Remaining issues: $remaining" -ForegroundColor Yellow
        Write-Host "✓ Step 2 complete`n" -ForegroundColor Green
    } catch {
        Write-Host "✗ Ruff not found`n" -ForegroundColor Red
    }
}

# ============================================
# Step 3: Type Checking
# ============================================

Write-Host "[Step 3/6] Type Checking with mypy...`n" -ForegroundColor Green

if (Get-Command python -ErrorAction SilentlyContinue) {
    try {
        python -m mypy --version | Out-Null
        Write-Host "Running mypy (this may take a few minutes)..."
        python -m mypy services/ 2>&1 | Out-File -FilePath "reports/quality/first-run-mypy.txt"
        
        $mypyErrors = (Select-String -Path "reports/quality/first-run-mypy.txt" -Pattern "error:" -ErrorAction SilentlyContinue | Measure-Object).Count
        Write-Host "Found $mypyErrors type errors" -ForegroundColor Yellow
        Write-Host "Report saved to: reports/quality/first-run-mypy.txt"
        Write-Host "✓ Step 3 complete`n" -ForegroundColor Green
    } catch {
        Write-Host "✗ mypy not found. Install with: pip install mypy`n" -ForegroundColor Red
    }
}

# ============================================
# Step 4: ESLint Check
# ============================================

Write-Host "[Step 4/6] ESLint Check...`n" -ForegroundColor Green

if (Test-Path "services/health-dashboard") {
    Push-Location "services/health-dashboard"
    
    if (Get-Command npm -ErrorAction SilentlyContinue) {
        try {
            npm run lint 2>&1 | Out-File -FilePath "../../reports/quality/first-run-eslint.txt"
            $eslintWarnings = (Select-String -Path "../../reports/quality/first-run-eslint.txt" -Pattern "warning" -ErrorAction SilentlyContinue | Measure-Object).Count
            Write-Host "Found $eslintWarnings warnings" -ForegroundColor Yellow
            Write-Host "Report saved to: reports/quality/first-run-eslint.txt"
            Write-Host "✓ Step 4 complete`n" -ForegroundColor Green
        } catch {
            Write-Host "⚠ ESLint not configured`n" -ForegroundColor Yellow
        }
    }
    
    Pop-Location
} else {
    Write-Host "⚠ health-dashboard not found`n" -ForegroundColor Yellow
}

# ============================================
# Step 5: Complexity Analysis
# ============================================

Write-Host "[Step 5/6] Complexity Analysis...`n" -ForegroundColor Green

if (Get-Command radon -ErrorAction SilentlyContinue) {
    Write-Host "Running complexity analysis..."
    radon cc services/ -n C -s 2>&1 | Out-File -FilePath "reports/quality/first-run-complexity.txt"
    
    $highComplexity = (Select-String -Path "reports/quality/first-run-complexity.txt" -Pattern " [CDEF] " -ErrorAction SilentlyContinue | Measure-Object).Count
    Write-Host "Found $highComplexity functions with high complexity" -ForegroundColor Yellow
    Write-Host "Report saved to: reports/quality/first-run-complexity.txt"
    Write-Host "✓ Step 5 complete`n" -ForegroundColor Green
} else {
    Write-Host "⚠ Radon not installed. Install with: pip install radon`n" -ForegroundColor Yellow
}

# ============================================
# Step 6: Generate Summary
# ============================================

Write-Host "[Step 6/6] Generating Summary...`n" -ForegroundColor Green

$dateStr = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$summaryLines = @(
    "# First Code Quality Run Summary",
    "",
    "**Date:** $dateStr",
    "",
    "## Results Overview",
    "",
    "### Ruff Linting",
    "- Initial issues: $ruffIssues",
    "- Remaining after auto-fix: $remaining",
    "",
    "### mypy Type Checking",
    "- Total errors: $mypyErrors",
    "",
    "### ESLint",
    "- Warnings: $eslintWarnings",
    "",
    "### Complexity",
    "- High complexity functions: $highComplexity",
    "",
    "## Reports Generated",
    "",
    "- Ruff: ``reports/quality/first-run-ruff.txt``",
    "- After auto-fix: ``reports/quality/after-auto-fix.txt``",
    "- mypy: ``reports/quality/first-run-mypy.txt``",
    "- ESLint: ``reports/quality/first-run-eslint.txt``",
    "- Complexity: ``reports/quality/first-run-complexity.txt``",
    "",
    "## Next Steps",
    "",
    "1. Review the reports above",
    "2. Create an action plan (see ``docs/CODE_QUALITY_FIRST_RUN_PLAN.md``)",
    "3. Start with Priority 1: Quick wins (auto-fixes)",
    "4. Gradually work through type errors and complexity issues",
    "",
    "## Priority Actions",
    "",
    "1. [ ] Review Ruff auto-fixes",
    "2. [ ] Identify top 10 mypy errors to fix",
    "3. [ ] List top 5 most complex functions",
    "4. [ ] Create service-specific action plans",
    "5. [ ] Set up weekly quality reviews"
)

$summaryLines -join "`n" | Out-File -FilePath "reports/quality/FIRST_RUN_SUMMARY.md" -Encoding UTF8

Write-Host "✓ Summary generated: reports/quality/FIRST_RUN_SUMMARY.md`n" -ForegroundColor Green

# ============================================
# Final Summary
# ============================================

Write-Host "========================================" -ForegroundColor Blue
Write-Host "First Run Complete!" -ForegroundColor Blue
Write-Host "========================================`n" -ForegroundColor Blue

Write-Host "Reports generated in: reports/quality/"
Write-Host "Summary: reports/quality/FIRST_RUN_SUMMARY.md`n"

Write-Host "Next steps:"
Write-Host "  1. Review: Get-Content reports/quality/FIRST_RUN_SUMMARY.md"
Write-Host "  2. See plan: Get-Content docs/CODE_QUALITY_FIRST_RUN_PLAN.md"
Write-Host "  3. Review Ruff: Get-Content reports/quality/first-run-ruff.txt"
Write-Host "  4. Review mypy: Get-Content reports/quality/first-run-mypy.txt"

Write-Host "`nDone!" -ForegroundColor Green

