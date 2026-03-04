# domain.ps1 — Per-domain Docker Compose helper for HomeIQ.
# Usage: .\scripts\domain.ps1 <command> <domain> [service]
#
# Commands:
#   start    Start a domain's services
#   stop     Stop a domain's services
#   restart  Restart a domain's services
#   status   Show running containers for a domain
#   logs     Tail service logs (optional: specific service name)
#   build    Build domain images
#   list     Print valid domain names

param(
    [Parameter(Position=0)]
    [string]$Command,

    [Parameter(Position=1)]
    [string]$Domain,

    [Parameter(Position=2)]
    [string]$Service
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

$ValidDomains = @(
    "core-platform"
    "data-collectors"
    "ml-engine"
    "automation-core"
    "blueprints"
    "energy-analytics"
    "device-management"
    "pattern-analysis"
    "frontends"
)

function Show-Usage {
    Write-Host "Usage: .\scripts\domain.ps1 <command> <domain> [service]"
    Write-Host ""
    Write-Host "Commands:"
    Write-Host "  start    Start a domain's services"
    Write-Host "  stop     Stop a domain's services"
    Write-Host "  restart  Restart a domain's services"
    Write-Host "  status   Show running containers for a domain"
    Write-Host "  logs     Tail service logs (optional: specific service name)"
    Write-Host "  build    Build domain images"
    Write-Host "  list     Print valid domain names"
    Write-Host ""
    Write-Host "Valid domains:"
    foreach ($d in $ValidDomains) {
        Write-Host "  $d"
    }
    exit 1
}

function Test-Domain {
    param([string]$DomainName)
    if ($ValidDomains -contains $DomainName) {
        return $true
    }
    Write-Host "[ERROR] Invalid domain: $DomainName" -ForegroundColor Red
    Write-Host ""
    Write-Host "Valid domains:"
    foreach ($d in $ValidDomains) {
        Write-Host "  $d"
    }
    exit 1
}

if (-not $Command) {
    Show-Usage
}

# Handle list command (no domain required)
if ($Command -eq "list") {
    foreach ($d in $ValidDomains) {
        Write-Host $d
    }
    exit 0
}

# All other commands require a domain
if (-not $Domain) {
    Show-Usage
}

Test-Domain -DomainName $Domain

$ComposeFile = Join-Path $ProjectRoot "domains" $Domain "compose.yml"

if (-not (Test-Path $ComposeFile)) {
    Write-Host "[ERROR] Compose file not found: $ComposeFile" -ForegroundColor Red
    exit 1
}

switch ($Command) {
    "start" {
        Write-Host "[START] Starting $Domain..." -ForegroundColor Green
        & "$ScriptDir\ensure-network.ps1"
        docker compose -f $ComposeFile up -d
        Write-Host "[OK] $Domain started." -ForegroundColor Green
    }
    "stop" {
        Write-Host "[STOP] Stopping $Domain..." -ForegroundColor Yellow
        docker compose -f $ComposeFile down
        Write-Host "[OK] $Domain stopped." -ForegroundColor Green
    }
    "restart" {
        Write-Host "[RESTART] Restarting $Domain..." -ForegroundColor Yellow
        & "$ScriptDir\ensure-network.ps1"
        docker compose -f $ComposeFile restart
        Write-Host "[OK] $Domain restarted." -ForegroundColor Green
    }
    "status" {
        docker compose -f $ComposeFile ps
    }
    "logs" {
        if ($Service) {
            docker compose -f $ComposeFile logs -f $Service
        } else {
            docker compose -f $ComposeFile logs -f
        }
    }
    "build" {
        Write-Host "[BUILD] Building $Domain images..." -ForegroundColor Green
        docker compose -f $ComposeFile build
        Write-Host "[OK] $Domain images built." -ForegroundColor Green
    }
    default {
        Write-Host "[ERROR] Unknown command: $Command" -ForegroundColor Red
        Show-Usage
    }
}
