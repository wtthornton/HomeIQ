#Requires -Version 5.1
<#
.SYNOPSIS
    Audit and clean up Docker resources for a HomeIQ-only local environment.

.DESCRIPTION
    Removes stopped containers, orphan compose containers, dangling/unused images,
    unused networks, and optionally build cache and unused volumes.
    See implementation/DOCKER_CLEANUP_PLAN.md for the full plan.

.PARAMETER Audit
    Only show Docker disk usage and resource counts (no changes).

.PARAMETER Clean
    Run safe cleanup: container prune, image prune (dangling or all unused with -PruneAllImages),
    network prune, builder prune. Does NOT stop the running stack or remove volumes.

.PARAMETER PruneVolumes
    Also run 'docker volume prune'. Data in unused volumes will be permanently lost.
    Use only if you are sure no important data is in unused volumes.

.PARAMETER PruneAllImages
    Use 'docker image prune -a' to remove ALL unused images (not just dangling).
    Use if this host runs only HomeIQ.

.PARAMETER WhatIf
    Show what would be done without making changes.

.EXAMPLE
    .\scripts\cleanup-docker.ps1 -Audit

.EXAMPLE
    .\scripts\cleanup-docker.ps1 -Clean -WhatIf

.EXAMPLE
    .\scripts\cleanup-docker.ps1 -Clean

.EXAMPLE
    .\scripts\cleanup-docker.ps1 -Clean -PruneVolumes
#>

[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [switch] $Audit,
    [switch] $Clean,
    [switch] $PruneVolumes,
    [switch] $PruneAllImages
)

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot | Split-Path -Parent

function Write-Status { param($Message, $Color = "White") Write-Host $Message -ForegroundColor $Color }
function Invoke-Docker { param([string[]]$DockerArgs) & docker @DockerArgs }

# Ensure docker is available
try {
    Invoke-Docker version | Out-Null
} catch {
    Write-Status "Docker is not running or not in PATH." Red
    exit 1
}

if ($Audit) {
    Write-Status "`n=== Docker system disk usage ===" Cyan
    Invoke-Docker system, df
    Write-Status "`n=== Detailed disk usage ===" Cyan
    Invoke-Docker system, df, "-v"
    Write-Status "`n=== All containers ===" Cyan
    Invoke-Docker ps, "-a", "--format", "table {{.Names}}\t{{.Status}}\t{{.Image}}"
    Write-Status "`n=== All volumes ===" Cyan
    Invoke-Docker volume, ls
    Write-Status "`n=== All networks ===" Cyan
    Invoke-Docker network, ls
    exit 0
}

if (-not $Clean -and -not $PruneVolumes) {
    Write-Status "Use -Audit to only inspect, or -Clean to run safe cleanup. Use -WhatIf to preview." Yellow
    Write-Status "Examples:" Gray
    Write-Status "  .\scripts\cleanup-docker.ps1 -Audit" Gray
    Write-Status "  .\scripts\cleanup-docker.ps1 -Clean -WhatIf" Gray
    Write-Status "  .\scripts\cleanup-docker.ps1 -Clean" Gray
    exit 0
}

$actions = @()
if ($Clean) {
    $actions += "container prune"
    $actions += "image prune (dangling)"
    if ($PruneAllImages) { $actions += "image prune (all unused)" }
    $actions += "network prune"
    $actions += "builder prune"
}
if ($PruneVolumes) {
    $actions += "volume prune (DATA LOSS for unused volumes)"
}

Write-Status "`nPlanned actions: $($actions -join '; ')" Cyan
if ($PSCmdlet.ShouldProcess("Docker", "Cleanup: $($actions -join ', ')")) {
    if ($Clean) {
        Write-Status "`nContainer prune..." Gray
        Invoke-Docker container, prune, "-f"

        Write-Status "Image prune (dangling)..." Gray
        Invoke-Docker image, prune, "-f"
        if ($PruneAllImages) {
            Write-Status "Image prune (all unused)..." Gray
            Invoke-Docker image, prune, "-a", "-f"
        }

        Write-Status "Network prune..." Gray
        Invoke-Docker network, prune, "-f"

        Write-Status "Builder prune..." Gray
        Invoke-Docker builder, prune, "-f"
    }

    if ($PruneVolumes) {
        $confirm = Read-Host "Remove ALL unused volumes? Data will be lost. Type 'yes' to continue"
        if ($confirm -eq "yes") {
            Invoke-Docker volume, prune, "-f"
            Write-Status "Volume prune completed." Green
        } else {
            Write-Status "Volume prune skipped." Yellow
        }
    }

    Write-Status "`n=== Disk usage after cleanup ===" Cyan
    Invoke-Docker system, df
    Write-Status "`nDone. To remove compose orphans (stops stack): docker compose down --remove-orphans" Gray
} else {
    Write-Status "`nWhatIf: no changes made. Run without -WhatIf to perform cleanup." Yellow
}
