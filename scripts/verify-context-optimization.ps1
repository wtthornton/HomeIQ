# Context Optimization Verification Script
# Purpose: Verify all context window optimizations are in place

$ErrorActionPreference = "Continue"

Write-Host "=== Context Window Optimization Verification ===" -ForegroundColor Cyan
Write-Host ""

$allPassed = $true
$warnings = @()
$errors = @()

# Check 1: Root directory cleanup
Write-Host "1. Checking root directory cleanup..." -ForegroundColor Yellow
$rootMdFiles = Get-ChildItem -Path . -Filter "*.md" -File -Depth 0
$allowedRootFiles = @("README.md", "CHANGELOG.md", "CONTRIBUTING.md", "COMMIT_PLAN.md")
$rootCount = $rootMdFiles.Count
$unexpectedRootFiles = $rootMdFiles | Where-Object { $allowedRootFiles -notcontains $_.Name }

if ($rootCount -le 5 -and $unexpectedRootFiles.Count -eq 0) {
    Write-Host "   PASS: Root has $rootCount .md files (target: ≤5)" -ForegroundColor Green
} else {
    Write-Host "   FAIL: Root has $rootCount .md files, $($unexpectedRootFiles.Count) unexpected" -ForegroundColor Red
    $allPassed = $false
    $errors += "Root directory has unexpected files: $($unexpectedRootFiles.Name -join ', ')"
}

# Check 2: .cursorignore exists and includes archives
Write-Host "2. Checking .cursorignore file..." -ForegroundColor Yellow
if (Test-Path ".cursorignore") {
    $cursorIgnoreContent = Get-Content ".cursorignore" -Raw
    if ($cursorIgnoreContent -match "docs/archive" -and $cursorIgnoreContent -match "implementation/archive") {
        Write-Host "   PASS: .cursorignore exists and excludes archive directories" -ForegroundColor Green
    } else {
        Write-Host "   WARN: .cursorignore exists but may not exclude all archives" -ForegroundColor Yellow
        $warnings += ".cursorignore may need archive exclusions"
    }
} else {
    Write-Host "   FAIL: .cursorignore file not found" -ForegroundColor Red
    $allPassed = $false
    $errors += ".cursorignore file missing"
}

# Check 3: Simulation data excluded from context
Write-Host "3. Checking simulation data exclusions..." -ForegroundColor Yellow
if (Test-Path ".cursorignore") {
    $cursorIgnoreContent = Get-Content ".cursorignore" -Raw
    $simulationExclusions = @("simulation/data", "simulation/training_data", "simulation/results")
    $allExcluded = $simulationExclusions | ForEach-Object { $cursorIgnoreContent -match $_ }
    if ($allExcluded -notcontains $false) {
        Write-Host "   PASS: Simulation data directories excluded in .cursorignore" -ForegroundColor Green
    } else {
        Write-Host "   WARN: Some simulation data directories may not be excluded" -ForegroundColor Yellow
        $warnings += "Simulation data may need .cursorignore exclusions"
    }
} else {
    Write-Host "   WARN: .cursorignore not found" -ForegroundColor Yellow
    $warnings += ".cursorignore missing"
}

# Check 4: Agent file loading uses sharded files
Write-Host "4. Checking agent file loading configuration..." -ForegroundColor Yellow
if (Test-Path ".bmad-core/core-config.yaml") {
    $configContent = Get-Content ".bmad-core/core-config.yaml" -Raw
    
    # Check for agentLoadAlwaysFiles
    if ($configContent -match "agentLoadAlwaysFiles:") {
        # Check that files reference sharded locations (docs/architecture/ not docs/architecture.md)
        $shardedPattern = "docs/architecture/[^`"]+\.md"
        $monolithicPattern = "docs/architecture\.md|docs/prd\.md"
        
        if ($configContent -match $shardedPattern -and $configContent -notmatch $monolithicPattern) {
            Write-Host "   PASS: agentLoadAlwaysFiles uses sharded files" -ForegroundColor Green
        } else {
            Write-Host "   WARN: agentLoadAlwaysFiles may reference monolithic files" -ForegroundColor Yellow
            $warnings += "Check agentLoadAlwaysFiles for monolithic file references"
        }
    } else {
        Write-Host "   WARN: agentLoadAlwaysFiles not found in config" -ForegroundColor Yellow
        $warnings += "agentLoadAlwaysFiles configuration missing"
    }
} else {
    Write-Host "   FAIL: core-config.yaml not found" -ForegroundColor Red
    $allPassed = $false
    $errors += "core-config.yaml missing"
}

# Check 4: Architecture sharding
Write-Host "4. Checking architecture sharding..." -ForegroundColor Yellow
$architectureShards = Get-ChildItem -Path "docs/architecture" -Filter "*.md" -File -ErrorAction SilentlyContinue
$architectureIndex = Test-Path "docs/architecture/index.md"
$architectureMonolithic = Test-Path "docs/architecture.md"

if ($architectureShards.Count -gt 10 -and $architectureIndex) {
    Write-Host "   PASS: Architecture is sharded ($($architectureShards.Count) files, index exists)" -ForegroundColor Green
} else {
    Write-Host "   WARN: Architecture sharding may be incomplete" -ForegroundColor Yellow
    $warnings += "Architecture sharding verification needed"
}

if ($architectureMonolithic) {
    Write-Host "   INFO: Monolithic docs/architecture.md exists (may be index only)" -ForegroundColor Cyan
}

# Check 5: PRD sharding
Write-Host "5. Checking PRD sharding..." -ForegroundColor Yellow
$prdShards = Get-ChildItem -Path "docs/prd" -Filter "*.md" -File -Recurse -ErrorAction SilentlyContinue
$prdIndex = (Test-Path "docs/prd/index.md") -or (Test-Path "docs/prd/epic-list.md")
$prdMonolithic = Test-Path "docs/prd.md"

if ($prdShards.Count -gt 10 -and $prdIndex) {
    Write-Host "   PASS: PRD is sharded ($($prdShards.Count) files, index exists)" -ForegroundColor Green
} else {
    Write-Host "   WARN: PRD sharding may be incomplete" -ForegroundColor Yellow
    $warnings += "PRD sharding verification needed"
}

if ($prdMonolithic) {
    Write-Host "   INFO: Monolithic docs/prd.md exists (may be index only)" -ForegroundColor Cyan
}

# Check 6: Archive directories exist
Write-Host "6. Checking archive directory structure..." -ForegroundColor Yellow
$docsArchiveExists = Test-Path "docs/archive"
$implArchiveExists = Test-Path "implementation/archive"

if ($docsArchiveExists -or $implArchiveExists) {
    Write-Host "   PASS: Archive directories exist" -ForegroundColor Green
    if ($docsArchiveExists) {
        $docsArchiveCount = (Get-ChildItem -Path "docs/archive" -Recurse -File -ErrorAction SilentlyContinue).Count
        Write-Host "      docs/archive: $docsArchiveCount files" -ForegroundColor Cyan
    }
    if ($implArchiveExists) {
        $implArchiveCount = (Get-ChildItem -Path "implementation/archive" -Recurse -File -ErrorAction SilentlyContinue).Count
        Write-Host "      implementation/archive: $implArchiveCount files" -ForegroundColor Cyan
    }
} else {
    Write-Host "   INFO: Archive directories don't exist yet (will be created when needed)" -ForegroundColor Cyan
}

# Check 7: File counts
Write-Host "7. Checking file counts..." -ForegroundColor Yellow
$implementationCount = (Get-ChildItem -Path "implementation" -Filter "*.md" -Recurse -File -ErrorAction SilentlyContinue | 
    Where-Object { $_.FullName -notmatch "\\archive\\" }).Count
$docsCount = (Get-ChildItem -Path "docs" -Filter "*.md" -Recurse -File -ErrorAction SilentlyContinue | 
    Where-Object { $_.FullName -notmatch "\\archive\\" }).Count

Write-Host "   INFO: implementation/: $implementationCount .md files" -ForegroundColor Cyan
Write-Host "   INFO: docs/: $docsCount .md files" -ForegroundColor Cyan

# Summary
Write-Host ""
Write-Host "=== Verification Summary ===" -ForegroundColor Cyan

if ($allPassed -and $warnings.Count -eq 0) {
    Write-Host "STATUS: All checks passed!" -ForegroundColor Green
} elseif ($allPassed) {
    Write-Host "STATUS: All critical checks passed, but $($warnings.Count) warning(s)" -ForegroundColor Yellow
} else {
    Write-Host "STATUS: $($errors.Count) error(s) found" -ForegroundColor Red
}

if ($warnings.Count -gt 0) {
    Write-Host ""
    Write-Host "Warnings:" -ForegroundColor Yellow
    foreach ($warning in $warnings) {
        Write-Host "  - $warning" -ForegroundColor Yellow
    }
}

if ($errors.Count -gt 0) {
    Write-Host ""
    Write-Host "Errors:" -ForegroundColor Red
    foreach ($error in $errors) {
        Write-Host "  - $error" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "File Organization:" -ForegroundColor Cyan
Write-Host "  Root .md files: $rootCount (target: ≤5)" -ForegroundColor $(if ($rootCount -le 5) { "Green" } else { "Yellow" })
Write-Host "  Implementation files: $implementationCount" -ForegroundColor Cyan
Write-Host "  Documentation files: $docsCount" -ForegroundColor Cyan

exit $(if ($allPassed) { 0 } else { 1 })

