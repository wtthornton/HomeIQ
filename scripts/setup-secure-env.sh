#!/bin/bash

# Secure Environment Setup Script
# This script helps you securely configure environment variables

set -e

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}Secure Environment Setup${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# Function to prompt for input with validation
prompt_for_value() {
    local var_name=$1
    local description=$2
    local default_value=$3
    local is_secret=${4:-false}
    local value=""
    
    while true; do
        echo -e "${YELLOW}$description${NC}"
        
        if [ "$is_secret" = true ]; then
            read -s -p "Enter $var_name: " value
            echo ""
        else
            if [ -n "$default_value" ]; then
                read -p "Enter $var_name [$default_value]: " value
                value=${value:-$default_value}
            else
                read -p "Enter $var_name: " value
            fi
        fi
        
        if [ -n "$value" ]; then
            break
        else
            echo -e "${RED}Value cannot be empty. Please try again.${NC}"
        fi
    done
    
    echo "$value"
}

# Function to generate secure random string
generate_secret() {
    openssl rand -hex 32 2>/dev/null || head -c 32 /dev/urandom | base64 | tr -d '/+=' | head -c 32
}

# Check if running in interactive mode
if [ ! -t 0 ]; then
    echo -e "${RED}Error: This script must be run in interactive mode${NC}"
    exit 1
fi

# Determine environment type
echo -e "${BLUE}What environment are you setting up?${NC}"
echo "1) Development (local)"
echo "2) Production"
echo "3) Testing"
read -p "Enter choice (1-3): " env_choice

case $env_choice in
    1)
        ENV_TYPE="development"
        ENV_FILE=".env"
        ;;
    2)
        ENV_TYPE="production"
        ENV_FILE="infrastructure/env.production"
        ;;
    3)
        ENV_TYPE="testing"
        ENV_FILE=".env.test"
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

echo -e "${GREEN}Setting up $ENV_TYPE environment${NC}"
echo ""

# Check if file exists
if [ -f "$ENV_FILE" ]; then
    echo -e "${YELLOW}Warning: $ENV_FILE already exists${NC}"
    read -p "Do you want to overwrite it? (y/N): " overwrite
    if [ "$overwrite" != "y" ] && [ "$overwrite" != "Y" ]; then
        echo "Exiting without changes"
        exit 0
    fi
    # Backup existing file
    cp "$ENV_FILE" "$ENV_FILE.backup.$(date +%Y%m%d_%H%M%S)"
    echo -e "${GREEN}Backed up existing file${NC}"
fi

# Create directory if needed
mkdir -p "$(dirname "$ENV_FILE")"

# Start building environment file
echo "# $ENV_TYPE Environment Configuration" > "$ENV_FILE"
echo "# Generated on $(date)" >> "$ENV_FILE"
echo "# DO NOT commit this file to version control!" >> "$ENV_FILE"
echo "" >> "$ENV_FILE"

# Home Assistant Configuration
echo -e "${BLUE}Home Assistant Configuration${NC}"
echo "================================" 

HA_URL=$(prompt_for_value "HOME_ASSISTANT_URL" \
    "Home Assistant URL (e.g., http://homeassistant.local:8123)" \
    "http://homeassistant.local:8123")

echo -e "${YELLOW}To generate a Long-Lived Access Token:${NC}"
echo "  1. Log into Home Assistant"
echo "  2. Click your profile (bottom left)"
echo "  3. Scroll to 'Long-Lived Access Tokens'"
echo "  4. Click 'Create Token'"
echo ""

HA_TOKEN=$(prompt_for_value "HOME_ASSISTANT_TOKEN" \
    "Home Assistant Long-Lived Access Token" \
    "" \
    true)

echo "" >> "$ENV_FILE"
echo "# Home Assistant Configuration" >> "$ENV_FILE"
echo "HOME_ASSISTANT_URL=$HA_URL" >> "$ENV_FILE"
echo "HOME_ASSISTANT_TOKEN=$HA_TOKEN" >> "$ENV_FILE"

# Nabu Casa (Optional)
echo ""
read -p "Do you want to configure Nabu Casa fallback? (y/N): " use_nabu_casa
if [ "$use_nabu_casa" = "y" ] || [ "$use_nabu_casa" = "Y" ]; then
    echo ""
    NABU_CASA_URL=$(prompt_for_value "NABU_CASA_URL" \
        "Nabu Casa URL (e.g., https://xxxxx.ui.nabu.casa)" \
        "")
    
    NABU_CASA_TOKEN=$(prompt_for_value "NABU_CASA_TOKEN" \
        "Nabu Casa Token (can be same as HA token)" \
        "" \
        true)
    
    echo "" >> "$ENV_FILE"
    echo "# Nabu Casa Fallback Configuration" >> "$ENV_FILE"
    echo "NABU_CASA_URL=$NABU_CASA_URL" >> "$ENV_FILE"
    echo "NABU_CASA_TOKEN=$NABU_CASA_TOKEN" >> "$ENV_FILE"
fi

# InfluxDB Configuration
echo ""
echo -e "${BLUE}InfluxDB Configuration${NC}"
echo "================================"

if [ "$ENV_TYPE" = "production" ]; then
    echo -e "${YELLOW}Using secure random passwords for production${NC}"
    INFLUXDB_PASSWORD=$(generate_secret)
    INFLUXDB_TOKEN=$(generate_secret)
    echo -e "${GREEN}Generated secure InfluxDB credentials${NC}"
else
    INFLUXDB_PASSWORD="admin123"
    INFLUXDB_TOKEN="homeiq-token"
    echo -e "${GREEN}Using default development credentials${NC}"
fi

INFLUXDB_USERNAME=$(prompt_for_value "INFLUXDB_USERNAME" \
    "InfluxDB Username" \
    "admin")

echo "" >> "$ENV_FILE"
echo "# InfluxDB Configuration" >> "$ENV_FILE"
echo "INFLUXDB_URL=http://influxdb:8086" >> "$ENV_FILE"
echo "INFLUXDB_USERNAME=$INFLUXDB_USERNAME" >> "$ENV_FILE"
echo "INFLUXDB_PASSWORD=$INFLUXDB_PASSWORD" >> "$ENV_FILE"
echo "INFLUXDB_ORG=homeiq" >> "$ENV_FILE"
echo "INFLUXDB_BUCKET=home_assistant_events" >> "$ENV_FILE"
echo "INFLUXDB_TOKEN=$INFLUXDB_TOKEN" >> "$ENV_FILE"

# Weather API Configuration
echo ""
echo -e "${BLUE}Weather API Configuration${NC}"
echo "================================"

read -p "Do you want to enable Weather API integration? (y/N): " use_weather_api
if [ "$use_weather_api" = "y" ] || [ "$use_weather_api" = "Y" ]; then
    echo ""
    echo -e "${YELLOW}Get a free API key from: https://openweathermap.org/api${NC}"
    
    WEATHER_API_KEY=$(prompt_for_value "WEATHER_API_KEY" \
        "OpenWeatherMap API Key" \
        "" \
        true)
    
    echo "" >> "$ENV_FILE"
    echo "# Weather API Configuration" >> "$ENV_FILE"
    echo "WEATHER_API_KEY=$WEATHER_API_KEY" >> "$ENV_FILE"
    echo "WEATHER_API_URL=https://api.openweathermap.org/data/2.5" >> "$ENV_FILE"
    echo "ENABLE_WEATHER_API=true" >> "$ENV_FILE"
else
    echo "" >> "$ENV_FILE"
    echo "# Weather API Configuration (Disabled)" >> "$ENV_FILE"
    echo "ENABLE_WEATHER_API=false" >> "$ENV_FILE"
fi

# Authentication Configuration
echo ""
echo -e "${BLUE}Authentication Configuration${NC}"
echo "================================"

if [ "$ENV_TYPE" = "production" ]; then
    echo -e "${YELLOW}Generating secure JWT secret${NC}"
    JWT_SECRET=$(generate_secret)
    
    ADMIN_PASSWORD=$(prompt_for_value "ADMIN_PASSWORD" \
        "Admin API Password" \
        "" \
        true)
    
    ENABLE_AUTH="true"
else
    JWT_SECRET="super-secret-jwt-key"
    ADMIN_PASSWORD="adminpass"
    ENABLE_AUTH="false"
    echo -e "${GREEN}Using default development credentials${NC}"
fi

echo "" >> "$ENV_FILE"
echo "# Authentication Configuration" >> "$ENV_FILE"
echo "ADMIN_API_JWT_SECRET=$JWT_SECRET" >> "$ENV_FILE"
echo "ADMIN_API_JWT_ALGORITHM=HS256" >> "$ENV_FILE"
echo "ADMIN_API_JWT_TTL=30" >> "$ENV_FILE"
echo "ADMIN_PASSWORD=$ADMIN_PASSWORD" >> "$ENV_FILE"
echo "ENABLE_AUTH=$ENABLE_AUTH" >> "$ENV_FILE"

# Logging Configuration
echo "" >> "$ENV_FILE"
echo "# Logging Configuration" >> "$ENV_FILE"

if [ "$ENV_TYPE" = "production" ]; then
    echo "LOG_LEVEL=INFO" >> "$ENV_FILE"
else
    echo "LOG_LEVEL=DEBUG" >> "$ENV_FILE"
fi

echo "LOG_FILE_PATH=/app/logs" >> "$ENV_FILE"

# Timezone Configuration
TZ=$(prompt_for_value "TZ" \
    "Timezone (e.g., America/Los_Angeles, Europe/London)" \
    "America/Los_Angeles")

echo "" >> "$ENV_FILE"
echo "# Timezone Configuration" >> "$ENV_FILE"
echo "TZ=$TZ" >> "$ENV_FILE"

# Service Ports
echo "" >> "$ENV_FILE"
echo "# Service Ports" >> "$ENV_FILE"
echo "ADMIN_API_PORT=8000" >> "$ENV_FILE"
echo "WEBSOCKET_INGESTION_PORT=8000" >> "$ENV_FILE"
echo "WEATHER_API_PORT=8001" >> "$ENV_FILE"
echo "INFLUXDB_PORT=8086" >> "$ENV_FILE"
echo "HEALTH_DASHBOARD_PORT=3000" >> "$ENV_FILE"

# Data Retention Configuration
echo "" >> "$ENV_FILE"
echo "# Data Retention Configuration" >> "$ENV_FILE"
echo "CLEANUP_INTERVAL_HOURS=24" >> "$ENV_FILE"
echo "MONITORING_INTERVAL_MINUTES=5" >> "$ENV_FILE"
echo "COMPRESSION_INTERVAL_HOURS=24" >> "$ENV_FILE"
echo "BACKUP_INTERVAL_HOURS=24" >> "$ENV_FILE"
echo "BACKUP_DIR=/backups" >> "$ENV_FILE"

# Set secure file permissions
chmod 600 "$ENV_FILE"

echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}✅ Environment configuration created successfully!${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo -e "${BLUE}File location:${NC} $ENV_FILE"
echo -e "${BLUE}File permissions:${NC} 600 (read/write for owner only)"
echo ""

if [ "$ENV_TYPE" = "production" ]; then
    echo -e "${YELLOW}⚠️  IMPORTANT SECURITY REMINDERS:${NC}"
    echo "1. This file contains sensitive credentials"
    echo "2. Never commit this file to version control"
    echo "3. Store a backup in a secure location (password manager, vault)"
    echo "4. Rotate credentials regularly"
    echo "5. Use different credentials for each environment"
    echo ""
    echo -e "${YELLOW}Generated credentials have been saved. Please store them securely:${NC}"
    echo "  - InfluxDB Password: [hidden]"
    echo "  - InfluxDB Token: [hidden]"
    echo "  - JWT Secret: [hidden]"
fi

echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "1. Review the configuration: cat $ENV_FILE"
echo "2. Test the configuration:"

if [ "$ENV_TYPE" = "production" ]; then
    echo "   ./scripts/start-prod.sh"
else
    echo "   ./scripts/start-dev.sh"
fi

echo "3. Check service health: ./scripts/test-services.sh"
echo ""
echo -e "${GREEN}Setup complete!${NC}"

