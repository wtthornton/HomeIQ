# Scheduled Model Training Script (PowerShell)
# 
# This script can be used with Task Scheduler on Windows to automatically
# retrain ML models on a schedule.
#
# Usage:
#   Create a scheduled task that runs this script weekly
#   Example: Run every Sunday at 2 AM

param(
    [int]$DaysBack = 180,
    [switch]$Force = $true
)

# Configuration
$ServiceDir = Split-Path -Parent $PSScriptRoot
$LogFile = Join-Path $ServiceDir "training.log"
$ScriptPath = Join-Path $ServiceDir "scripts\train_models.py"

# Change to service directory
Set-Location $ServiceDir

# Log start
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content -Path $LogFile -Value "========================================"
Add-Content -Path $LogFile -Value "Scheduled Model Training Started"
Add-Content -Path $LogFile -Value "Date: $timestamp"
Add-Content -Path $LogFile -Value "Days Back: $DaysBack"
Add-Content -Path $LogFile -Value "========================================"

# Build command
$cmd = "python `"$ScriptPath`" --days-back $DaysBack"
if ($Force) {
    $cmd += " --force"
}
$cmd += " --verbose"

# Run training script
try {
    Invoke-Expression $cmd | Tee-Object -FilePath $LogFile -Append
    $exitCode = 0
    Add-Content -Path $LogFile -Value "Training completed successfully"
} catch {
    $exitCode = 1
    Add-Content -Path $LogFile -Value "Training failed: $_"
}

# Log completion
Add-Content -Path $LogFile -Value "========================================"
Add-Content -Path $LogFile -Value ""

exit $exitCode

