<#
.SYNOPSIS
    Backup ML models before library upgrades

.DESCRIPTION
    Creates timestamped backups of all trained ML models (.pkl, .joblib) 
    to prevent data loss during numpy/pandas/scikit-learn upgrades.
    
    Models may need regeneration after upgrading to scikit-learn 1.8+
    due to pickle incompatibilities between versions.

.EXAMPLE
    .\scripts\backup-ml-models.ps1
    
.EXAMPLE
    .\scripts\backup-ml-models.ps1 -RestoreLatest

.NOTES
    Epic: backend-completion
    Story: ML Library Upgrades (Phase 3)
    Author: HomeIQ CI
    Date: 2026-03-06
#>

param(
    [switch]$RestoreLatest,
    [string]$BackupDir = "backups/ml-models"
)

$ErrorActionPreference = "Stop"
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupPath = Join-Path $PSScriptRoot "..\$BackupDir\$timestamp"

$modelPaths = @(
    "domains/ml-engine/device-intelligence-service/models",
    "domains/ml-engine/ai-training-service/models",
    "domains/ml-engine/device-intelligence-service/data/models"
)

function Write-Status {
    param([string]$Message, [string]$Color = "Cyan")
    Write-Host "[$((Get-Date).ToString('HH:mm:ss'))] $Message" -ForegroundColor $Color
}

if ($RestoreLatest) {
    $latestBackup = Get-ChildItem "$PSScriptRoot\..\$BackupDir" -Directory | 
                    Sort-Object Name -Descending | 
                    Select-Object -First 1
    
    if (-not $latestBackup) {
        Write-Status "No backups found in $BackupDir" "Red"
        exit 1
    }
    
    Write-Status "Restoring from backup: $($latestBackup.Name)" "Yellow"
    
    foreach ($modelPath in $modelPaths) {
        $sourcePath = Join-Path $latestBackup.FullName $modelPath
        $destPath = Join-Path $PSScriptRoot "..\$modelPath"
        
        if (Test-Path $sourcePath) {
            Write-Status "  Restoring: $modelPath"
            Copy-Item -Path "$sourcePath\*" -Destination $destPath -Recurse -Force
        }
    }
    
    Write-Status "Restore complete!" "Green"
    exit 0
}

Write-Status "ML Model Backup Script"
Write-Status "======================"
Write-Status "Backup location: $backupPath"

New-Item -ItemType Directory -Force -Path $backupPath | Out-Null

$totalFiles = 0
$totalSize = 0

foreach ($modelPath in $modelPaths) {
    $fullPath = Join-Path $PSScriptRoot "..\$modelPath"
    
    if (Test-Path $fullPath) {
        $destDir = Join-Path $backupPath $modelPath
        New-Item -ItemType Directory -Force -Path $destDir | Out-Null
        
        $files = Get-ChildItem -Path $fullPath -Recurse -File -Include "*.pkl", "*.joblib", "*.json"
        
        foreach ($file in $files) {
            $relativePath = $file.FullName.Substring($fullPath.Length + 1)
            $destFile = Join-Path $destDir $relativePath
            $destFileDir = Split-Path $destFile -Parent
            
            if (-not (Test-Path $destFileDir)) {
                New-Item -ItemType Directory -Force -Path $destFileDir | Out-Null
            }
            
            Copy-Item -Path $file.FullName -Destination $destFile
            $totalFiles++
            $totalSize += $file.Length
            Write-Status "  Backed up: $($file.Name) ($([math]::Round($file.Length / 1KB, 1)) KB)" "Gray"
        }
    } else {
        Write-Status "  Skipping (not found): $modelPath" "Yellow"
    }
}

Write-Status "======================"
Write-Status "Backup Summary:" "Green"
Write-Status "  Files: $totalFiles"
Write-Status "  Size: $([math]::Round($totalSize / 1MB, 2)) MB"
Write-Status "  Location: $backupPath"
Write-Status ""
Write-Status "To restore, run: .\scripts\backup-ml-models.ps1 -RestoreLatest" "Cyan"
