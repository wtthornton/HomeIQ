# Archive Old Implementation Files Script
# Purpose: Identify and archive old implementation notes by quarter

param(
    [switch]$DryRun = $false,
    [switch]$Verbose = $false,
    [int]$MonthsOld = 6
)

$ErrorActionPreference = "Stop"

# Calculate cutoff date
$cutoffDate = (Get-Date).AddMonths(-$MonthsOld)

Write-Host "=== Archive Old Implementation Files ===" -ForegroundColor Cyan
Write-Host "Cutoff date: $cutoffDate (files older than $MonthsOld months)" -ForegroundColor Yellow
Write-Host ""

# Define archive structure by quarter
function Get-ArchivePath {
    param([DateTime]$fileDate)
    
    $year = $fileDate.Year
    $quarter = [Math]::Floor(($fileDate.Month - 1) / 3) + 1
    
    return "implementation/archive/$year-q$quarter"
}

# Get all markdown files in implementation (excluding archive and subdirectories like analysis/)
$implementationFiles = Get-ChildItem -Path "implementation" -Filter "*.md" -File -Recurse | 
    Where-Object { 
        $_.FullName -notmatch "\\archive\\" -and
        $_.FullName -notmatch "\\analysis\\" -and
        $_.FullName -notmatch "\\verification\\"
    }

$archivedCount = 0
$skippedCount = 0
$errors = @()

foreach ($file in $implementationFiles) {
    $fileDate = $file.LastWriteTime
    
    # Skip if file is newer than cutoff
    if ($fileDate -gt $cutoffDate) {
        if ($Verbose) {
            Write-Host "SKIP: $($file.Name) (recent: $fileDate)" -ForegroundColor Gray
        }
        $skippedCount++
        continue
    }
    
    # Determine archive path
    $archivePath = Get-ArchivePath -fileDate $fileDate
    
    # Ensure archive directory exists
    if (-not (Test-Path $archivePath)) {
        if (-not $DryRun) {
            New-Item -ItemType Directory -Path $archivePath -Force | Out-Null
        }
        Write-Host "CREATE: $archivePath" -ForegroundColor Green
    }
    
    # Calculate relative path from implementation/ to preserve structure
    $relativePath = $file.FullName.Replace((Resolve-Path "implementation").Path + "\", "")
    $targetPath = Join-Path $archivePath $relativePath
    $targetDir = Split-Path $targetPath -Parent
    
    # Ensure target directory exists
    if (-not (Test-Path $targetDir)) {
        if (-not $DryRun) {
            New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
        }
    }
    
    # Check if target already exists
    if (Test-Path $targetPath) {
        Write-Host "WARN: Target exists: $targetPath" -ForegroundColor Yellow
        Write-Host "      Skipping move of $($file.Name)" -ForegroundColor Yellow
        $skippedCount++
        continue
    }
    
    if ($DryRun) {
        Write-Host "DRY-RUN: Would archive $($file.Name) ($fileDate) → $targetPath" -ForegroundColor Cyan
    } else {
        try {
            Move-Item -Path $file.FullName -Destination $targetPath -Force
            Write-Host "ARCHIVE: $($file.Name) ($fileDate) → $targetPath" -ForegroundColor Green
            $archivedCount++
        } catch {
            Write-Host "ERROR: Failed to archive $($file.Name) - $_" -ForegroundColor Red
            $errors += "$($file.Name) : $_"
        }
    }
}

Write-Host ""
Write-Host "=== Summary ===" -ForegroundColor Cyan
Write-Host "Files archived: $archivedCount" -ForegroundColor Green
Write-Host "Files skipped: $skippedCount" -ForegroundColor Yellow

if ($errors.Count -gt 0) {
    Write-Host "Errors: $($errors.Count)" -ForegroundColor Red
    foreach ($error in $errors) {
        Write-Host "  - $error" -ForegroundColor Red
    }
}

if ($DryRun) {
    Write-Host ""
    Write-Host "This was a DRY RUN. No files were actually moved." -ForegroundColor Yellow
    Write-Host "Run without -DryRun to perform the actual archiving." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Example: .\scripts\archive-old-implementation-files.ps1 -MonthsOld 6" -ForegroundColor Cyan
}

