# run-multirepo.ps1 — Multi-repo mode for the auto-fix pipeline (Phase 4).
# Reads repos.yaml and runs the pipeline once per repo with -ProjectRootOverride and -ConfigPath.
#
# Usage (from meta-repo root):
#   .\auto-fix-pipeline\runner\run-multirepo.ps1 -ReposPath "auto-fix-pipeline/config/example/repos-example.yaml"
#   .\auto-fix-pipeline\runner\run-multirepo.ps1 -ReposPath "repos.yaml" -Bugs 3
#
# Requires: scripts/auto-bugfix.ps1 in meta-repo (or -ScriptPath). Each repo gets -ProjectRootOverride.

param(
    [Parameter(Mandatory = $true)]
    [string]$ReposPath,
    [string]$MetaRoot = "",
    [string]$ScriptPath = "",
    [int]$Bugs = 5,
    [string]$Branch = "",
    [string]$TargetDir = "",
    [string]$Base = "master",
    [switch]$Chain,
    [switch]$NoDashboard,
    [switch]$NoRotate,
    [string]$TargetUnit = "",
    [switch]$Worktree
)

$ErrorActionPreference = "Stop"

# Meta-repo root: where repos.yaml paths are relative to
if (-not $MetaRoot) {
    $RunnerDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $AutoFixDir = Split-Path -Parent $RunnerDir
    $MetaRoot = Split-Path -Parent $AutoFixDir
}
$MetaRoot = (Resolve-Path -Path $MetaRoot -ErrorAction Stop).Path
Set-Location $MetaRoot

# Resolve repos file
$reposFile = if ([System.IO.Path]::IsPathRooted($ReposPath)) { $ReposPath } else { Join-Path $MetaRoot $ReposPath }
if (-not (Test-Path $reposFile)) {
    Write-Error "Repos file not found: $reposFile"
    exit 1
}

# Parse repos.yaml
$reposJson = python -c "import yaml,json,sys; f=open(sys.argv[1],encoding='utf-8'); d=yaml.safe_load(f); f.close(); print(json.dumps(d or {}))" $reposFile 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "Failed to parse repos YAML: $reposFile"
    exit 1
}
$reposDoc = $reposJson | ConvertFrom-Json
if (-not $reposDoc.repos -or $reposDoc.repos.Count -eq 0) {
    Write-Error "repos.yaml must contain a non-empty 'repos' array."
    exit 1
}

$defaultConfig = $reposDoc.default_config
$scriptExe = if ($ScriptPath) { (Resolve-Path $ScriptPath -ErrorAction Stop).Path } else { Join-Path $MetaRoot "scripts/auto-bugfix.ps1" }
if (-not (Test-Path $scriptExe)) {
    Write-Error "Script not found: $scriptExe. Set -ScriptPath or ensure scripts/auto-bugfix.ps1 exists in meta-repo."
    exit 1
}

$totalRepos = $reposDoc.repos.Count
$failed = 0
$idx = 0
foreach ($repo in $reposDoc.repos) {
    $idx++
    $repoPath = $repo.path
    if (-not $repoPath) {
        Write-Host "[$idx/$totalRepos] Skipping repo with empty path." -ForegroundColor Yellow
        continue
    }
    $repoAbs = if ([System.IO.Path]::IsPathRooted($repoPath)) { $repoPath } else { (Join-Path $MetaRoot $repoPath) }
    if (-not (Test-Path $repoAbs)) {
        Write-Host "[$idx/$totalRepos] Repo path not found: $repoAbs" -ForegroundColor Yellow
        $failed++
        continue
    }
    $repoName = if ($repo.name) { $repo.name } else { $repoPath }
    $configPath = if ($repo.config_path) { $repo.config_path } else { $defaultConfig }
    if (-not $configPath) {
        Write-Host "[$idx/$totalRepos] No config for repo: $repoName" -ForegroundColor Yellow
        $failed++
        continue
    }
    $configAbs = if ([System.IO.Path]::IsPathRooted($configPath)) { $configPath } else { Join-Path $MetaRoot $configPath }
    if (-not (Test-Path $configAbs)) {
        Write-Host "[$idx/$totalRepos] Config not found for $repoName : $configAbs" -ForegroundColor Yellow
        $failed++
        continue
    }

    Write-Host ""
    Write-Host "[$idx/$totalRepos] Running pipeline: $repoName" -ForegroundColor Cyan
    Write-Host "  ProjectRoot: $repoAbs" -ForegroundColor Gray
    Write-Host "  Config: $configPath" -ForegroundColor Gray

    $scriptArgs = @{
        ProjectRootOverride = $repoAbs
        ConfigPath          = $configAbs
        Bugs                = $Bugs
        Base                = $Base
    }
    if ($Branch) { $scriptArgs.Branch = $Branch }
    if ($TargetDir) { $scriptArgs.TargetDir = $TargetDir }
    if ($Chain) { $scriptArgs.Chain = $true }
    if ($NoDashboard) { $scriptArgs.NoDashboard = $true }
    if ($NoRotate) { $scriptArgs.NoRotate = $true }
    if ($TargetUnit) { $scriptArgs.TargetUnit = $TargetUnit }
    if ($Worktree) { $scriptArgs.Worktree = $true }

    & $scriptExe @scriptArgs
    if ($LASTEXITCODE -ne 0) { $failed++ }
}

Write-Host ""
if ($failed -eq 0) {
    Write-Host "Multi-repo run complete: all $totalRepos repo(s) finished." -ForegroundColor Green
    exit 0
} else {
    Write-Host "Multi-repo run finished with $failed failure(s) out of $totalRepos repo(s)." -ForegroundColor Yellow
    exit 1
}
