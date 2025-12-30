# Unified Git Cleanup Script Wrapper (PowerShell)
# Wraps the Python cleanup-git-unified.py script for easier use

param(
    [switch]$DryRun,
    [switch]$Fetch,
    [switch]$MergedRemote,
    [switch]$MergedLocal,
    [switch]$Worktrees,
    [switch]$Workflow,
    [switch]$All,
    [switch]$ForceLocal,
    [switch]$Summary,
    [switch]$Json,
    [string]$ProjectRoot = ""
)

$scriptPath = Join-Path $PSScriptRoot "cleanup-git-unified.py"

# Build command arguments
$args = @()

if ($DryRun) { $args += "--dry-run" }
if ($Fetch) { $args += "--fetch" }
if ($MergedRemote) { $args += "--merged-remote" }
if ($MergedLocal) { $args += "--merged-local" }
if ($Worktrees) { $args += "--worktrees" }
if ($Workflow) { $args += "--workflow" }
if ($All) { $args += "--all" }
if ($ForceLocal) { $args += "--force-local" }
if ($Summary) { $args += "--summary" }
if ($Json) { $args += "--json" }
if ($ProjectRoot) { $args += "--project-root"; $args += $ProjectRoot }

# Run Python script
Write-Host "=== Unified Git Cleanup Tool ===" -ForegroundColor Cyan
Write-Host ""

try {
    python $scriptPath @args
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Cleanup script exited with code $LASTEXITCODE" -ForegroundColor Red
        exit $LASTEXITCODE
    }
} catch {
    Write-Host "Error running cleanup script: $_" -ForegroundColor Red
    exit 1
}

