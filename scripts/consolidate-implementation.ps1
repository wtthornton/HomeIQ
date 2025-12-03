# Implementation Directory Consolidation Script
# Consolidates implementation directory from 2,070 files to <500 active files
# Archives completed/superseded files to implementation/archive/2025-q4/

param(
    [switch]$DryRun = $false,
    [switch]$Verbose = $false
)

Write-Host "Implementation Directory Consolidation" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green
Write-Host ""

$implementationPath = "implementation"
$archivePath = "implementation/archive/2025-q4"
$currentPath = "docs/current/implementation"

# Create archive directory if it doesn't exist
if (-not (Test-Path $archivePath)) {
    New-Item -ItemType Directory -Path $archivePath -Force | Out-Null
    Write-Host "[CREATE] Created archive directory: $archivePath" -ForegroundColor Yellow
}

# Create current docs directory if it doesn't exist
if (-not (Test-Path $currentPath)) {
    New-Item -ItemType Directory -Path $currentPath -Force | Out-Null
    Write-Host "[CREATE] Created current docs directory: $currentPath" -ForegroundColor Yellow
}

# Patterns for files to archive (completed/superseded)
$archivePatterns = @(
    "*_COMPLETE.md",
    "*_COMPLETE_SUMMARY.md",
    "*_STATUS.md",
    "*_FIX_SUMMARY.md",
    "*_FIXES_SUMMARY.md",
    "*_DEPLOYMENT_COMPLETE.md",
    "*_DEPLOYMENT_SUMMARY.md",
    "*_IMPLEMENTATION_COMPLETE.md",
    "*_IMPLEMENTATION_SUMMARY.md",
    "*_SESSION_SUMMARY.md",
    "*_SUMMARY.md",
    "EPIC_*_COMPLETE.md",
    "EPIC_*_SUMMARY.md",
    "*_FINAL_STATUS.md",
    "*_FINAL_SUMMARY.md"
)

# Patterns for files to move to docs/current/implementation (active reference)
$currentPatterns = @(
    "*_PLAN.md",
    "*_IMPLEMENTATION_PLAN.md",
    "*_DESIGN.md",
    "*_SPECIFICATION.md",
    "*_ARCHITECTURE.md"
)

# Patterns for files to keep in implementation/ (active work)
$keepPatterns = @(
    "*_IN_PROGRESS.md",
    "*_TODO.md",
    "*_NEXT_STEPS.md",
    "QUALITY_IMPROVEMENT_PROGRESS.md",
    "PRODUCTION_READINESS_ASSESSMENT.md"
)

$archivedCount = 0
$movedToCurrentCount = 0
$keptCount = 0
$errorCount = 0

# Get all markdown files in implementation (excluding archive and subdirectories that should stay)
$files = Get-ChildItem -Path $implementationPath -Recurse -Filter "*.md" -File | 
    Where-Object { 
        $_.FullName -notlike "*\archive\*" -and
        $_.FullName -notlike "*\analysis\*" -and
        $_.FullName -notlike "*\verification\*" -and
        $_.FullName -notlike "*\fixes\*" -and
        $_.FullName -notlike "*\screenshots\*" -and
        $_.FullName -notlike "*\production-readiness\*" -and
        $_.FullName -notlike "*\root-cleanup\*" -and
        $_.FullName -notlike "*\security\*"
    }

Write-Host "Found $($files.Count) markdown files to process" -ForegroundColor Cyan
Write-Host ""

foreach ($file in $files) {
    $fileName = $file.Name
    $relativePath = $file.FullName.Replace((Get-Location).Path + "\", "")
    
    $action = "KEEP"
    $destination = $null
    
    # Check if file matches archive patterns
    $shouldArchive = $false
    foreach ($pattern in $archivePatterns) {
        if ($fileName -like $pattern) {
            $shouldArchive = $true
            $action = "ARCHIVE"
            $destination = Join-Path $archivePath $fileName
            break
        }
    }
    
    # Check if file matches current patterns (if not archiving)
    if (-not $shouldArchive) {
        foreach ($pattern in $currentPatterns) {
            if ($fileName -like $pattern) {
                $action = "MOVE_TO_CURRENT"
                $destination = Join-Path $currentPath $fileName
                break
            }
        }
    }
    
    # Check if file matches keep patterns (override)
    foreach ($pattern in $keepPatterns) {
        if ($fileName -like $pattern) {
            $action = "KEEP"
            $destination = $null
            break
        }
    }
    
    # Execute action
    if ($DryRun) {
        Write-Host "[$action] $relativePath" -ForegroundColor $(if ($action -eq "ARCHIVE") { "Yellow" } elseif ($action -eq "MOVE_TO_CURRENT") { "Cyan" } else { "Gray" })
        if ($destination) {
            Write-Host "      -> $destination" -ForegroundColor DarkGray
        }
    } else {
        try {
            switch ($action) {
                "ARCHIVE" {
                    # Handle duplicate names in archive
                    $archiveFile = $destination
                    $counter = 1
                    while (Test-Path $archiveFile) {
                        $baseName = [System.IO.Path]::GetFileNameWithoutExtension($fileName)
                        $extension = [System.IO.Path]::GetExtension($fileName)
                        $archiveFile = Join-Path $archivePath "$baseName-$counter$extension"
                        $counter++
                    }
                    
                    Move-Item -Path $file.FullName -Destination $archiveFile -Force
                    Write-Host "[ARCHIVE] $fileName -> archive/2025-q4/" -ForegroundColor Yellow
                    $archivedCount++
                }
                "MOVE_TO_CURRENT" {
                    # Handle duplicate names
                    $currentFile = $destination
                    $counter = 1
                    while (Test-Path $currentFile) {
                        $baseName = [System.IO.Path]::GetFileNameWithoutExtension($fileName)
                        $extension = [System.IO.Path]::GetExtension($fileName)
                        $currentFile = Join-Path $currentPath "$baseName-$counter$extension"
                        $counter++
                    }
                    
                    Move-Item -Path $file.FullName -Destination $currentFile -Force
                    Write-Host "[MOVE] $fileName -> docs/current/implementation/" -ForegroundColor Cyan
                    $movedToCurrentCount++
                }
                "KEEP" {
                    if ($Verbose) {
                        Write-Host "[KEEP] $fileName" -ForegroundColor Gray
                    }
                    $keptCount++
                }
            }
        } catch {
            Write-Host "[ERROR] Failed to process $fileName : $_" -ForegroundColor Red
            $errorCount++
        }
    }
}

Write-Host ""
Write-Host "=====================================" -ForegroundColor Green
Write-Host "Consolidation Summary" -ForegroundColor Green
Write-Host "=====================================" -ForegroundColor Green

if ($DryRun) {
    Write-Host "DRY RUN - No files were moved" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To execute, run:" -ForegroundColor Cyan
    Write-Host "  .\scripts\consolidate-implementation.ps1" -ForegroundColor White
} else {
    Write-Host "Files Archived: $archivedCount" -ForegroundColor Yellow
    Write-Host "Files Moved to Current: $movedToCurrentCount" -ForegroundColor Cyan
    Write-Host "Files Kept: $keptCount" -ForegroundColor Green
    if ($errorCount -gt 0) {
        Write-Host "Errors: $errorCount" -ForegroundColor Red
    }
    
    # Count remaining files
    $remainingFiles = (Get-ChildItem -Path $implementationPath -Recurse -Filter "*.md" -File | 
        Where-Object { 
            $_.FullName -notlike "*\archive\*" -and
            $_.FullName -notlike "*\analysis\*" -and
            $_.FullName -notlike "*\verification\*"
        }).Count
    
    Write-Host ""
    Write-Host "Remaining Files in implementation/: $remainingFiles" -ForegroundColor Cyan
    Write-Host "Target: <500 files" -ForegroundColor Cyan
    
    if ($remainingFiles -lt 500) {
        Write-Host "[SUCCESS] Target achieved!" -ForegroundColor Green
    } else {
        Write-Host "[INFO] Additional cleanup may be needed" -ForegroundColor Yellow
    }
}

Write-Host ""

