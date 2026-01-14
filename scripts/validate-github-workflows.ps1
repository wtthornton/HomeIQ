# Validate GitHub Actions Workflows
# Checks for common issues in workflow files

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$WorkflowsDir = Join-Path (Join-Path $ProjectRoot ".github") "workflows"

Write-Host "Validating GitHub Actions Workflows..." -ForegroundColor Cyan
Write-Host ""

$Errors = 0
$Warnings = 0

# Check if workflows directory exists
if (-not (Test-Path $WorkflowsDir)) {
    Write-Host "ERROR: Workflows directory not found: $WorkflowsDir" -ForegroundColor Red
    exit 1
}

# Check each workflow file
Get-ChildItem -Path $WorkflowsDir -Filter "*.yml" | ForEach-Object {
    $workflow = $_
    $filename = $workflow.Name
    Write-Host "Checking $filename..." -ForegroundColor Yellow
    
    # Check for basic YAML syntax using Python
    try {
        $yamlCheck = python -c "import yaml; yaml.safe_load(open('$($workflow.FullName)'))" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  [OK] Valid YAML syntax" -ForegroundColor Green
        } else {
            Write-Host "  [FAIL] Invalid YAML syntax" -ForegroundColor Red
            Write-Host "    $yamlCheck" -ForegroundColor Red
            $Errors++
        }
    } catch {
        Write-Host "  [WARN] Could not validate YAML (Python yaml module may not be installed)" -ForegroundColor Yellow
        $Warnings++
    }
    
    # Check for common issues
    $content = Get-Content $workflow.FullName -Raw
    
    if ($content -match "curl -f") {
        Write-Host "  [WARN] Uses 'curl -f' (may not be available in containers)" -ForegroundColor Yellow
        $Warnings++
    }
    
    if ($content -match "docker compose exec.*curl") {
        Write-Host "  [WARN] Uses curl in docker exec (may fail)" -ForegroundColor Yellow
        $Warnings++
    }
    
    # Check for missing script references
    $scriptMatches = [regex]::Matches($content, 'scripts/[^\s\n]+')
    foreach ($match in $scriptMatches) {
        $scriptPath = $match.Value.Trim()
        # Remove quotes and other characters that might be at the end
        $scriptPath = $scriptPath -replace '[`"''\s]+$', ''
        if ($scriptPath -match '^scripts/') {
            $fullPath = Join-Path $ProjectRoot $scriptPath
            if (-not (Test-Path $fullPath)) {
                Write-Host "  [WARN] Referenced script not found: $scriptPath" -ForegroundColor Yellow
                $Warnings++
            }
        }
    }
}

Get-ChildItem -Path $WorkflowsDir -Filter "*.yaml" | ForEach-Object {
    $workflow = $_
    $filename = $workflow.Name
    Write-Host "Checking $filename..." -ForegroundColor Yellow
    
    # Check for basic YAML syntax using Python
    try {
        $yamlCheck = python -c "import yaml; yaml.safe_load(open('$($workflow.FullName)'))" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  [OK] Valid YAML syntax" -ForegroundColor Green
        } else {
            Write-Host "  [FAIL] Invalid YAML syntax" -ForegroundColor Red
            Write-Host "    $yamlCheck" -ForegroundColor Red
            $Errors++
        }
    } catch {
        Write-Host "  [WARN] Could not validate YAML (Python yaml module may not be installed)" -ForegroundColor Yellow
        $Warnings++
    }
    
    # Check for common issues
    $content = Get-Content $workflow.FullName -Raw
    
    if ($content -match "curl -f") {
        Write-Host "  [WARN] Uses 'curl -f' (may not be available in containers)" -ForegroundColor Yellow
        $Warnings++
    }
    
    if ($content -match "docker compose exec.*curl") {
        Write-Host "  [WARN] Uses curl in docker exec (may fail)" -ForegroundColor Yellow
        $Warnings++
    }
    
    # Check for missing script references
    $scriptMatches = [regex]::Matches($content, 'scripts/[^\s\n]+')
    foreach ($match in $scriptMatches) {
        $scriptPath = $match.Value.Trim()
        $scriptPath = $scriptPath -replace '[`"''\s]+$', ''
        if ($scriptPath -match '^scripts/') {
            $fullPath = Join-Path $ProjectRoot $scriptPath
            if (-not (Test-Path $fullPath)) {
                Write-Host "  [WARN] Referenced script not found: $scriptPath" -ForegroundColor Yellow
                $Warnings++
            }
        }
    }
}

Write-Host ""
Write-Host "Summary:" -ForegroundColor Cyan
Write-Host "  Errors: $Errors" -ForegroundColor $(if ($Errors -gt 0) { "Red" } else { "Green" })
Write-Host "  Warnings: $Warnings" -ForegroundColor $(if ($Warnings -gt 0) { "Yellow" } else { "Green" })

if ($Errors -gt 0) {
    Write-Host ""
    Write-Host "Validation failed with $Errors error(s)" -ForegroundColor Red
    exit 1
} elseif ($Warnings -gt 0) {
    Write-Host ""
    Write-Host "Validation passed with $Warnings warning(s)" -ForegroundColor Yellow
    exit 0
} else {
    Write-Host ""
    Write-Host "All workflows validated successfully" -ForegroundColor Green
    exit 0
}
