# ensure-volumes.ps1 — Create Docker volumes shared across domain compose
# files if they don't exist. Idempotent: safe to run multiple times.
#
# Each of these is owned by one domain but mounted by others too. Every
# domain that shares one declares it `external: true` in its compose.yml
# (matching the homeiq-network pattern), so Compose never creates it
# itself -- it must exist before any domain starts, the same way
# ensure-network.ps1 pre-creates homeiq-network.
#
#   homeiq_logs        — owned by core-platform; also used by
#                         data-collectors and device-management.
#   ai_automation_data  — owned by ml-engine; also used by automation-core
#                         and pattern-analysis.

function Ensure-Volume {
    param([string]$VolumeName)
    $null = docker volume inspect $VolumeName 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Volume '$VolumeName' already exists."
    } else {
        docker volume create $VolumeName
        Write-Host "[CREATED] Volume '$VolumeName' created."
    }
}

$HomeiqLogsVolume = if ($env:HOMEIQ_LOGS_VOLUME) { $env:HOMEIQ_LOGS_VOLUME } else { "homeiq-core-platform_homeiq_logs" }
$AiAutomationDataVolume = if ($env:AI_AUTOMATION_DATA_VOLUME) { $env:AI_AUTOMATION_DATA_VOLUME } else { "homeiq-ml-engine_ai_automation_data" }

Ensure-Volume $HomeiqLogsVolume
Ensure-Volume $AiAutomationDataVolume
