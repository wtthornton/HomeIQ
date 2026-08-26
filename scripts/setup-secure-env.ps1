# Secure Environment Setup Script (PowerShell)
# This script helps you securely configure environment variables

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet('development', 'production', 'testing')]
    [string]$Environment = 'development'
)

# Color output functions
function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) {
        Write-Output $args
    }
    $host.UI.RawUI.ForegroundColor = $fc
}

function Write-Info { Write-ColorOutput Cyan $args }
function Write-Success { Write-ColorOutput Green $args }
function Write-Warning { Write-ColorOutput Yellow $args }
function Write-Error { Write-ColorOutput Red $args }

Write-Info "================================"
Write-Info "Secure Environment Setup"
Write-Info "================================"
Write-Output ""

# Function to prompt for input with validation
function Get-ConfigValue {
    param(
        [string]$Name,
        [string]$Description,
        [string]$Default = "",
        [bool]$IsSecret = $false
    )
    
    while ($true) {
        Write-Warning $Description
        
        if ($IsSecret) {
            $secureValue = Read-Host -AsSecureString "Enter $Name"
            $value = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto(
                [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureValue)
            )
        }
        else {
            if ($Default) {
                $value = Read-Host "Enter $Name [$Default]"
                if ([string]::IsNullOrWhiteSpace($value)) {
                    $value = $Default
                }
            }
            else {
                $value = Read-Host "Enter $Name"
            }
        }
        
        if (-not [string]::IsNullOrWhiteSpace($value)) {
            return $value
        }
        else {
            Write-Error "Value cannot be empty. Please try again."
        }
    }
}

# Function to generate secure random string
function New-SecureSecret {
    param([int]$Length = 32)
    
    $bytes = New-Object byte[] $Length
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    $rng.GetBytes($bytes)
    return [System.Convert]::ToBase64String($bytes).Substring(0, $Length)
}

# Determine environment file
$envFile = switch ($Environment) {
    'development' { '.env' }
    'production' { 'infrastructure\env.production' }
    'testing' { '.env.test' }
}

Write-Success "Setting up $Environment environment"
Write-Output ""

# Check if file exists
if (Test-Path $envFile) {
    Write-Warning "Warning: $envFile already exists"
    $overwrite = Read-Host "Do you want to overwrite it? (y/N)"
    if ($overwrite -ne 'y' -and $overwrite -ne 'Y') {
        Write-Output "Exiting without changes"
        exit 0
    }
    # Backup existing file
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    Copy-Item $envFile "$envFile.backup.$timestamp"
    Write-Success "Backed up existing file"
}

# Create directory if needed
$envDir = Split-Path $envFile -Parent
if ($envDir -and -not (Test-Path $envDir)) {
    New-Item -ItemType Directory -Path $envDir -Force | Out-Null
}

# Start building environment file
$content = @"
# $Environment Environment Configuration
# Generated on $(Get-Date)
# DO NOT commit this file to version control!

"@

# Home Assistant Configuration
Write-Info "Home Assistant Configuration"
Write-Info "================================"

$haUrl = Get-ConfigValue -Name "HOME_ASSISTANT_URL" `
    -Description "Home Assistant URL (e.g., http://homeassistant.local:8123)" `
    -Default "http://homeassistant.local:8123"

Write-Warning "To generate a Long-Lived Access Token:"
Write-Output "  1. Log into Home Assistant"
Write-Output "  2. Click your profile (bottom left)"
Write-Output "  3. Scroll to 'Long-Lived Access Tokens'"
Write-Output "  4. Click 'Create Token'"
Write-Output ""

$haToken = Get-ConfigValue -Name "HOME_ASSISTANT_TOKEN" `
    -Description "Home Assistant Long-Lived Access Token" `
    -IsSecret $true

$content += @"

# Home Assistant Configuration
HOME_ASSISTANT_URL=$haUrl
HOME_ASSISTANT_TOKEN=$haToken
"@

# Nabu Casa (Optional)
Write-Output ""
$useNabuCasa = Read-Host "Do you want to configure Nabu Casa fallback? (y/N)"
if ($useNabuCasa -eq 'y' -or $useNabuCasa -eq 'Y') {
    Write-Output ""
    $nabuCasaUrl = Get-ConfigValue -Name "NABU_CASA_URL" `
        -Description "Nabu Casa URL (e.g., https://xxxxx.ui.nabu.casa)"
    
    $nabuCasaToken = Get-ConfigValue -Name "NABU_CASA_TOKEN" `
        -Description "Nabu Casa Token (can be same as HA token)" `
        -IsSecret $true
    
    $content += @"

# Nabu Casa Fallback Configuration
NABU_CASA_URL=$nabuCasaUrl
NABU_CASA_TOKEN=$nabuCasaToken
"@
}

# InfluxDB Configuration
Write-Output ""
Write-Info "InfluxDB Configuration"
Write-Info "================================"

if ($Environment -eq 'production') {
    Write-Warning "Using secure random passwords for production"
    $influxPassword = New-SecureSecret
    $influxToken = New-SecureSecret
    Write-Success "Generated secure InfluxDB credentials"
}
else {
    $influxPassword = "admin123"
    $influxToken = "homeiq-token"
    Write-Success "Using default development credentials"
}

$influxUsername = Get-ConfigValue -Name "INFLUXDB_USERNAME" `
    -Description "InfluxDB Username" `
    -Default "admin"

$content += @"

# InfluxDB Configuration
INFLUXDB_URL=http://influxdb:8086
INFLUXDB_USERNAME=$influxUsername
INFLUXDB_PASSWORD=$influxPassword
INFLUXDB_ORG=homeiq
INFLUXDB_BUCKET=home_assistant_events
INFLUXDB_TOKEN=$influxToken
"@

# Weather API Configuration
Write-Output ""
Write-Info "Weather API Configuration"
Write-Info "================================"

$useWeatherApi = Read-Host "Do you want to enable Weather API integration? (y/N)"
if ($useWeatherApi -eq 'y' -or $useWeatherApi -eq 'Y') {
    Write-Output ""
    Write-Warning "Get a free API key from: https://openweathermap.org/api"
    
    $weatherApiKey = Get-ConfigValue -Name "WEATHER_API_KEY" `
        -Description "OpenWeatherMap API Key" `
        -IsSecret $true
    
    $content += @"

# Weather API Configuration
WEATHER_API_KEY=$weatherApiKey
WEATHER_API_URL=https://api.openweathermap.org/data/2.5
ENABLE_WEATHER_API=true
"@
}
else {
    $content += @"

# Weather API Configuration (Disabled)
ENABLE_WEATHER_API=false
"@
}

# Authentication Configuration
Write-Output ""
Write-Info "Authentication Configuration"
Write-Info "================================"

if ($Environment -eq 'production') {
    Write-Warning "Generating secure JWT secret"
    $jwtSecret = New-SecureSecret -Length 64
    
    $adminPassword = Get-ConfigValue -Name "ADMIN_PASSWORD" `
        -Description "Admin API Password" `
        -IsSecret $true
    
    $enableAuth = "true"
}
else {
    $jwtSecret = "super-secret-jwt-key"
    $adminPassword = "adminpass"
    $enableAuth = "false"
    Write-Success "Using default development credentials"
}

$content += @"

# Authentication Configuration
ADMIN_API_JWT_SECRET=$jwtSecret
ADMIN_API_JWT_ALGORITHM=HS256
ADMIN_API_JWT_TTL=30
ADMIN_PASSWORD=$adminPassword
ENABLE_AUTH=$enableAuth
"@

# Logging Configuration
$logLevel = if ($Environment -eq 'production') { 'INFO' } else { 'DEBUG' }

$content += @"

# Logging Configuration
LOG_LEVEL=$logLevel
LOG_FILE_PATH=/app/logs
"@

# Timezone Configuration
$timezone = Get-ConfigValue -Name "TZ" `
    -Description "Timezone (e.g., America/Los_Angeles, Europe/London)" `
    -Default "America/Los_Angeles"

$content += @"

# Timezone Configuration
TZ=$timezone
"@

# Service Ports
$content += @"

# Service Ports
ADMIN_API_PORT=8000
WEBSOCKET_INGESTION_PORT=8000
WEATHER_API_PORT=8001
INFLUXDB_PORT=8086
HEALTH_DASHBOARD_PORT=3000
"@

# Data Retention Configuration
$content += @"

# Data Retention Configuration
CLEANUP_INTERVAL_HOURS=24
MONITORING_INTERVAL_MINUTES=5
COMPRESSION_INTERVAL_HOURS=24
BACKUP_INTERVAL_HOURS=24
BACKUP_DIR=/backups
"@

# Write the file
$content | Out-File -FilePath $envFile -Encoding UTF8

Write-Output ""
Write-Success "================================"
Write-Success "✅ Environment configuration created successfully!"
Write-Success "================================"
Write-Output ""
Write-Info "File location: $envFile"
Write-Output ""

if ($Environment -eq 'production') {
    Write-Warning "⚠️  IMPORTANT SECURITY REMINDERS:"
    Write-Output "1. This file contains sensitive credentials"
    Write-Output "2. Never commit this file to version control"
    Write-Output "3. Store a backup in a secure location (password manager, vault)"
    Write-Output "4. Rotate credentials regularly"
    Write-Output "5. Use different credentials for each environment"
    Write-Output ""
    Write-Warning "Generated credentials have been saved. Please store them securely:"
    Write-Output "  - InfluxDB Password: [hidden]"
    Write-Output "  - InfluxDB Token: [hidden]"
    Write-Output "  - JWT Secret: [hidden]"
}

Write-Output ""
Write-Info "Next steps:"
Write-Output "1. Review the configuration: Get-Content $envFile"
Write-Output "2. Test the configuration:"

if ($Environment -eq 'production') {
    Write-Output "   .\scripts\start-prod.sh"
}
else {
    Write-Output "   .\scripts\start-dev.sh"
}

Write-Output "3. Check service health: .\scripts\test-services.sh"
Write-Output ""
Write-Success "Setup complete!"

