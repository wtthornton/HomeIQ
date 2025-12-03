# HomeIQ Project Cleanup Script
# Safely removes temporary files and test artifacts without affecting production code
# Run this AFTER .gitignore has been updated

Write-Host "HomeIQ Project Cleanup" -ForegroundColor Green
Write-Host "=========================" -ForegroundColor Green
Write-Host ""

$removedCount = 0
$errorCount = 0

# Phase 1: Remove Playwright MCP screenshots
if (Test-Path ".playwright-mcp") {
    $files = Get-ChildItem ".playwright-mcp" -Recurse -File -ErrorAction SilentlyContinue
    $count = $files.Count
    if ($count -gt 0) {
        Write-Host "[REMOVE] Removing .playwright-mcp/ ($count files)..." -ForegroundColor Yellow
        try {
            Remove-Item -Recurse -Force ".playwright-mcp" -ErrorAction Stop
            Write-Host "   [OK] Removed .playwright-mcp/ directory" -ForegroundColor Green
            $removedCount += $count
        } catch {
            Write-Host "   [ERROR] Error removing .playwright-mcp/: $_" -ForegroundColor Red
            $errorCount++
        }
    } else {
        Write-Host "[REMOVE] .playwright-mcp/ is empty, removing..." -ForegroundColor Yellow
        try {
            Remove-Item -Recurse -Force ".playwright-mcp" -ErrorAction Stop
            Write-Host "   [OK] Removed empty .playwright-mcp/ directory" -ForegroundColor Green
        } catch {
            Write-Host "   [ERROR] Error removing .playwright-mcp/: $_" -ForegroundColor Red
            $errorCount++
        }
    }
} else {
    Write-Host "[SKIP] .playwright-mcp/ not found (already removed)" -ForegroundColor Gray
}

# Phase 2: Remove root-level temporary files
$tempFiles = @(
    "test_results_before.txt",
    "test_results_after.txt",
    "homeiq-structure.txt",
    "homeiq-snapshot.txt",
    "homeiq-git-status.txt",
    "full_logs_approve_attempt.txt",
    "logs_before_click.txt",
    "deployment_test_results.json"
)

Write-Host ""
Write-Host "[REMOVE] Removing root-level temporary files..." -ForegroundColor Yellow

foreach ($file in $tempFiles) {
    if (Test-Path $file) {
        try {
            Remove-Item -Force $file -ErrorAction Stop
            Write-Host "   [OK] Removed: $file" -ForegroundColor Green
            $removedCount++
        } catch {
            Write-Host "   [ERROR] Error removing $file : $_" -ForegroundColor Red
            $errorCount++
        }
    }
}

# Phase 3: Remove 'nul' file (Windows reserved name, already in .gitignore)
if (Test-Path "nul") {
    Write-Host ""
    Write-Host "[REMOVE] Removing 'nul' file (Windows reserved name)..." -ForegroundColor Yellow
    try {
        Remove-Item -Force "nul" -ErrorAction Stop
        Write-Host "   [OK] Removed: nul" -ForegroundColor Green
        $removedCount++
    } catch {
        Write-Host "   [ERROR] Error removing nul: $_" -ForegroundColor Red
        Write-Host "   [INFO] This is a Windows reserved name - may need manual removal" -ForegroundColor Yellow
        $errorCount++
    }
}

# Phase 4: Clean empty directories (optional)
Write-Host ""
Write-Host "[CHECK] Checking empty directories..." -ForegroundColor Yellow

$emptyDirs = @(
    "coverage_html",
    "backups"
)

foreach ($dir in $emptyDirs) {
    if (Test-Path $dir) {
        $items = Get-ChildItem $dir -Force -ErrorAction SilentlyContinue
        if ($null -eq $items -or $items.Count -eq 0) {
            try {
                Remove-Item -Force $dir -ErrorAction Stop
                Write-Host "   [OK] Removed empty directory: $dir" -ForegroundColor Green
            } catch {
                Write-Host "   [ERROR] Error removing $dir : $_" -ForegroundColor Red
                $errorCount++
            }
        } else {
            Write-Host "   [SKIP] Skipping $dir (contains $($items.Count) items)" -ForegroundColor Gray
        }
    }
}

# Summary
Write-Host ""
Write-Host "=========================" -ForegroundColor Green
Write-Host "Cleanup Summary" -ForegroundColor Green
Write-Host "=========================" -ForegroundColor Green
Write-Host "Files/Directories Removed: $removedCount" -ForegroundColor Cyan
if ($errorCount -gt 0) {
    Write-Host "Errors Encountered: $errorCount" -ForegroundColor Yellow
}
Write-Host ""

if ($errorCount -eq 0) {
    Write-Host "[SUCCESS] Cleanup completed successfully!" -ForegroundColor Green
} else {
    Write-Host "[WARNING] Cleanup completed with some errors. Review above for details." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. Review changes: git status" -ForegroundColor White
Write-Host "2. Verify .gitignore and .cursorignore were updated" -ForegroundColor White
Write-Host "3. Commit .gitignore/.cursorignore updates first" -ForegroundColor White
Write-Host "4. Then commit file deletions (if files were tracked)" -ForegroundColor White
Write-Host ""

