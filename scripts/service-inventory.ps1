# Service Inventory Script (PowerShell)
# Generates a comprehensive inventory of HomeIQ services for documentation verification

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

Write-Host "=== HomeIQ Service Inventory ===" -ForegroundColor Cyan
Write-Host "Generated: $(Get-Date)" -ForegroundColor Gray
Write-Host ""

# Count services defined in docker-compose.yml
Write-Host "📋 Services Defined in docker-compose.yml:" -ForegroundColor Yellow
Push-Location $ProjectRoot
try {
    $DefinedServices = docker compose config --services 2>$null | Sort-Object
    $DefinedCount = ($DefinedServices | Measure-Object -Line).Lines
    Write-Host "   Total: " -NoNewline
    Write-Host "$DefinedCount" -ForegroundColor Green -NoNewline
    Write-Host " services"
    Write-Host ""
    
    # List all defined services
    Write-Host "   Services list:" -ForegroundColor Gray
    $i = 1
    $DefinedServices | ForEach-Object {
        Write-Host "      $i. $_" -ForegroundColor Gray
        $i++
    }
    Write-Host ""
} finally {
    Pop-Location
}

# Count running containers
Write-Host "🚀 Currently Running Containers:" -ForegroundColor Yellow
$RunningContainers = docker ps --format "{{.Names}}" 2>$null
$RunningCount = ($RunningContainers | Measure-Object -Line).Lines
$HomeIqRunning = (docker ps --filter "name=homeiq" --format "{{.Names}}" 2>$null | Measure-Object -Line).Lines

Write-Host "   Total running: " -NoNewline
Write-Host "$RunningCount" -ForegroundColor Green -NoNewline
Write-Host " containers"
Write-Host "   HomeIQ services: " -NoNewline
Write-Host "$HomeIqRunning" -ForegroundColor Green -NoNewline
Write-Host " containers (with 'homeiq-' prefix)"
Write-Host ""

# Show container status
Write-Host "📊 Container Status:" -ForegroundColor Yellow
Write-Host ""
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.State}}" 2>$null | ForEach-Object { Write-Host "   $_" -ForegroundColor Gray }
Write-Host ""

# Health status summary
Write-Host "🏥 Health Status Summary:" -ForegroundColor Yellow
$Healthy = (docker ps --filter "health=healthy" --format "{{.Names}}" 2>$null | Measure-Object -Line).Lines
$Unhealthy = (docker ps --filter "health=unhealthy" --format "{{.Names}}" 2>$null | Measure-Object -Line).Lines
$NoHealthCheck = $RunningCount - $Healthy - $Unhealthy

Write-Host "   Healthy: " -NoNewline
Write-Host "$Healthy" -ForegroundColor Green

if ($Unhealthy -gt 0) {
    Write-Host "   Unhealthy: " -NoNewline
    Write-Host "$Unhealthy" -ForegroundColor Red
    Write-Host "   Unhealthy containers:" -ForegroundColor Red
    docker ps --filter "health=unhealthy" --format "      - {{.Names}}" 2>$null | ForEach-Object { Write-Host $_ -ForegroundColor Red }
}
Write-Host "   No health check: " -NoNewline
Write-Host "$NoHealthCheck" -ForegroundColor Yellow
Write-Host ""

# Check for containers without homeiq- prefix
Write-Host "⚠️  Container Naming Check:" -ForegroundColor Yellow
$NonStandard = $RunningContainers | Where-Object { $_ -notmatch "^homeiq-" -and $_ -ne "NAMES" }
$NonStandardCount = ($NonStandard | Measure-Object).Count

if ($NonStandardCount -gt 0) {
    Write-Host "   Containers without 'homeiq-' prefix: " -NoNewline
    Write-Host "$NonStandardCount" -ForegroundColor Yellow
    $NonStandard | ForEach-Object { Write-Host "      - $_" -ForegroundColor Yellow }
} else {
    Write-Host "   " -NoNewline
    Write-Host "✓ All containers use 'homeiq-' prefix" -ForegroundColor Green
}
Write-Host ""

# Profile-based services check
Write-Host "📌 Profile-Based Services:" -ForegroundColor Yellow
Push-Location $ProjectRoot
try {
    $ProfileServices = @()
    foreach ($service in $DefinedServices) {
        $serviceConfig = Select-String -Path "docker-compose.yml" -Pattern "^  $service`:" -Context 0, 10
        if ($serviceConfig -and $serviceConfig.Context.PostContext -match "profiles:") {
            $ProfileServices += $service
        }
    }
    
    if ($ProfileServices.Count -gt 0) {
        $ProfileServices | ForEach-Object { Write-Host "      - $_" -ForegroundColor Gray }
        Write-Host "   Note: These services require --profile production to run" -ForegroundColor Gray
    } else {
        Write-Host "   " -NoNewline
        Write-Host "✓ No profile-based services found" -ForegroundColor Green
    }
} finally {
    Pop-Location
}
Write-Host ""

# Summary
Write-Host "📈 Summary:" -ForegroundColor Yellow
Write-Host "   Defined: $DefinedCount services" -ForegroundColor Gray
Write-Host "   Running: $RunningCount containers" -ForegroundColor Gray
Write-Host "   Healthy: $Healthy containers" -ForegroundColor Gray

$Diff = $RunningCount - $DefinedCount
if ($Diff -ne 0) {
    if ($Diff -gt 0) {
        Write-Host "   " -NoNewline
        Write-Host "⚠ Difference: +$Diff containers (may include test services or external containers)" -ForegroundColor Yellow
    } else {
        Write-Host "   " -NoNewline
        Write-Host "⚠ Difference: $Diff containers (some services may be stopped)" -ForegroundColor Yellow
    }
} else {
    Write-Host "   " -NoNewline
    Write-Host "✓ All defined services are running" -ForegroundColor Green
}
Write-Host ""

Write-Host "=== End of Service Inventory ===" -ForegroundColor Cyan
