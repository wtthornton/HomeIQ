# Setup script for home-assistant-datasets (PowerShell)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $ScriptDir)
$DatasetsDir = Join-Path (Join-Path $ProjectRoot "tests") "datasets"

Write-Host "Setting up home-assistant-datasets for testing..."
Write-Host "Project root: $ProjectRoot"
Write-Host "Datasets directory: $DatasetsDir"

# Check if datasets directory exists
$DatasetsPath = Join-Path $DatasetsDir "datasets"
if (Test-Path $DatasetsPath) {
    $TestFile = Join-Path (Join-Path $DatasetsPath "assist-mini") "home.yaml"
    if (Test-Path $TestFile) {
        Write-Host "✅ Datasets already exist at $DatasetsPath" -ForegroundColor Green
        exit 0
    }
}

# Create datasets directory
if (-not (Test-Path $DatasetsDir)) {
    New-Item -ItemType Directory -Path $DatasetsDir -Force | Out-Null
}

# Clone repository
Write-Host "Cloning home-assistant-datasets repository..."
$RepoDir = Join-Path $DatasetsDir "home-assistant-datasets"

if (Test-Path $RepoDir) {
    Write-Host "✅ Repository already cloned, updating..."
    Push-Location $RepoDir
    git pull
    Pop-Location
} else {
    Push-Location $DatasetsDir
    git clone https://github.com/allenporter/home-assistant-datasets.git
    Pop-Location
}

# Check if datasets directory exists in repo
$RepoDatasetsPath = Join-Path $RepoDir "datasets"
if (Test-Path $RepoDatasetsPath) {
    # Create junction/symlink (Windows)
    if (-not (Test-Path $DatasetsPath)) {
        Write-Host "Creating junction to datasets..."
        New-Item -ItemType Junction -Path $DatasetsPath -Target $RepoDatasetsPath -Force | Out-Null
    }
    Write-Host "✅ Datasets available at $DatasetsPath" -ForegroundColor Green
} else {
    Write-Host "❌ Error: datasets directory not found in repository" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "✅ Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Available datasets:"
Get-ChildItem $DatasetsPath -Directory | Select-Object -First 10 | ForEach-Object { Write-Host "  $($_.Name)" }
Write-Host ""
Write-Host "To use in tests, set DATASET_ROOT environment variable:"
Write-Host "  `$env:DATASET_ROOT = '$DatasetsPath'"

