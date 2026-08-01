#!/bin/bash

# Environment Setup Script
# This script helps set up the environment configuration

set -e

echo "Setting up environment configuration..."

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp infrastructure/env.example .env
    echo "✅ Created .env file from template"
    echo "⚠️  Please edit .env file with your actual configuration values"
else
    echo "✅ .env file already exists"
fi

# Validate required environment variables
echo "Validating environment configuration..."

source .env

# Check required variables
required_vars=(
    "HOME_ASSISTANT_URL"
    "HOME_ASSISTANT_TOKEN"
    "INFLUXDB_USERNAME"
    "INFLUXDB_PASSWORD"
    "INFLUXDB_ORG"
    "INFLUXDB_BUCKET"
    "INFLUXDB_TOKEN"
)

missing_vars=()

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ] || [ "${!var}" = "your_long_lived_access_token_here" ] || [ "${!var}" = "admin123" ]; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -eq 0 ]; then
    echo "✅ All required environment variables are configured"
else
    echo "⚠️  The following environment variables need to be configured:"
    for var in "${missing_vars[@]}"; do
        echo "   - $var"
    done
    echo "Please edit the .env file with your actual values"
fi

echo "Environment setup complete!"
