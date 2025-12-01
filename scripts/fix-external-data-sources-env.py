#!/usr/bin/env python3
"""
Fix External Data Sources Environment Variables

This script checks the .env file and adds missing environment variables
required for external data sources (Carbon Intensity, Air Quality, 
Electricity Pricing, Calendar Service).
"""

import os
import re
from pathlib import Path

# Required environment variables for each service
REQUIRED_VARS = {
    'carbon-intensity': {
        'WATTTIME_USERNAME': 'your_watttime_username',
        'WATTTIME_PASSWORD': 'your_watttime_password',
        'GRID_REGION': 'CAISO_NORTH',  # Default value
    },
    'air-quality': {
        'WEATHER_API_KEY': 'your_openweathermap_api_key_here',
        'LATITUDE': '36.1699',  # Default: Las Vegas
        'LONGITUDE': '-115.1398',  # Default: Las Vegas
    },
    'electricity-pricing': {
        'PRICING_PROVIDER': 'awattar',  # Default value (no API key needed for awattar)
        'PRICING_API_KEY': '',  # Optional for awattar
    },
    'calendar': {
        'CALENDAR_ENTITIES': 'calendar.primary',  # Default value
        'CALENDAR_FETCH_INTERVAL': '900',  # Default: 15 minutes
    },
}

# Common variables that should exist
COMMON_VARS = {
    'INFLUXDB_TOKEN': 'homeiq-token',
    'INFLUXDB_ORG': 'homeiq',
    'INFLUXDB_BUCKET': 'home_assistant_events',
    'HOME_ASSISTANT_TOKEN': 'your_long_lived_access_token_here',
    'HA_HTTP_URL': 'http://192.168.1.86:8123',
    'HA_TOKEN': 'your_long_lived_access_token_here',
}


def read_env_file(env_path: Path) -> dict[str, str]:
    """Read existing .env file and return as dictionary"""
    env_vars = {}
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue
                # Parse KEY=VALUE
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    env_vars[key] = value
    return env_vars


def write_env_file(env_path: Path, env_vars: dict[str, str], comments: dict[str, str] = None):
    """Write environment variables to .env file with proper formatting"""
    if comments is None:
        comments = {}
    
    # Read existing file to preserve comments and structure
    existing_lines = []
    existing_keys = set()
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            existing_lines = f.readlines()
            for line in existing_lines:
                if '=' in line and not line.strip().startswith('#'):
                    key = line.split('=', 1)[0].strip()
                    existing_keys.add(key)
    
    # Prepare new content
    output_lines = []
    section_added = {}
    
    # Process existing lines and update values
    in_section = None
    for line in existing_lines:
        stripped = line.strip()
        
        # Detect section headers
        if stripped.startswith('#') and 'Carbon Intensity' in stripped:
            in_section = 'carbon-intensity'
        elif stripped.startswith('#') and 'Air Quality' in stripped:
            in_section = 'air-quality'
        elif stripped.startswith('#') and 'Electricity Pricing' in stripped:
            in_section = 'electricity-pricing'
        elif stripped.startswith('#') and 'Calendar Service' in stripped:
            in_section = 'calendar'
        elif stripped.startswith('#') and ('Weather API' in stripped or 'Home Assistant' in stripped):
            in_section = None
        
        # Update existing variables
        if '=' in line and not stripped.startswith('#'):
            key = line.split('=', 1)[0].strip()
            if key in env_vars:
                # Update the value
                value = env_vars[key]
                if ' ' in value or value == '':
                    output_lines.append(f"{key}={value}\n")
                else:
                    output_lines.append(f"{key}={value}\n")
                existing_keys.add(key)
                continue
        
        output_lines.append(line)
    
    # Add missing variables in appropriate sections
    sections = {
        'carbon-intensity': [
            '# =============================================================================',
            '# Carbon Intensity Configuration (WattTime API)',
            '# =============================================================================',
            '',
            '# Authentication Method (Choose ONE):',
            '',
            '# Method 1: Username/Password (RECOMMENDED - automatic token refresh)',
            '# Tokens are automatically refreshed every 25 minutes',
            '',
            '# Grid Region Configuration',
            '# US Regions: CAISO_NORTH, CAISO_SOUTH, ERCOT, PJM, NYISO, ISONE, MISO',
            '# International: Contact WattTime for available regions (paid plans)',
            '# Use WattTime region lookup API to find your specific region',
            '',
            '# Notes:',
            '# - Free tier: Limited to 1-2 US regions',
            '# - Paid tier: Global coverage (12+ countries)',
            '# - Register at: https://watttime.org',
        ],
        'air-quality': [
            '',
            '# Air Quality Configuration (uses WEATHER_API_KEY from above)',
            '# Air quality service now uses OpenWeather API instead of AirNow',
        ],
        'electricity-pricing': [
            '',
            '# Electricity Pricing Configuration',
        ],
        'calendar': [
            '',
            '# Calendar Service Configuration (Home Assistant Integration)',
            '# Create long-lived token: HA Profile → Security → Long-Lived Access Tokens',
            '# List calendars: Developer Tools → States → filter "calendar"',
        ],
    }
    
    # Add missing variables
    for service, vars_dict in REQUIRED_VARS.items():
        for key, default_value in vars_dict.items():
            if key not in existing_keys:
                # Add section header if not already added
                if service not in section_added:
                    if service in sections:
                        for comment_line in sections[service]:
                            output_lines.append(f"{comment_line}\n")
                    section_added[service] = True
                
                # Add the variable
                if default_value:
                    output_lines.append(f"{key}={default_value}\n")
                else:
                    output_lines.append(f"{key}=\n")
    
    # Add common variables if missing
    for key, default_value in COMMON_VARS.items():
        if key not in existing_keys:
            output_lines.append(f"{key}={default_value}\n")
    
    # Write the file
    with open(env_path, 'w', encoding='utf-8') as f:
        f.writelines(output_lines)


def main():
    """Main function"""
    # Get project root (parent of scripts directory)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    env_path = project_root / '.env'
    
    print("🔍 Checking .env file for missing external data source variables...")
    print(f"   Location: {env_path}")
    print()
    
    # Read existing .env file
    existing_vars = read_env_file(env_path)
    
    # Check what's missing
    missing_vars = {}
    for service, vars_dict in REQUIRED_VARS.items():
        for key, default_value in vars_dict.items():
            if key not in existing_vars or existing_vars[key].strip() in ['', 'your_*', 'your_*_here']:
                if service not in missing_vars:
                    missing_vars[service] = {}
                missing_vars[service][key] = default_value
    
    # Check common variables
    missing_common = {}
    for key, default_value in COMMON_VARS.items():
        if key not in existing_vars or existing_vars[key].strip() in ['', 'your_*', 'your_*_here']:
            missing_common[key] = default_value
    
    if not missing_vars and not missing_common:
        print("✅ All required environment variables are present!")
        print()
        print("Note: Make sure to replace placeholder values with your actual API keys:")
        print("  - WATTTIME_USERNAME / WATTTIME_PASSWORD (for Carbon Intensity)")
        print("  - WEATHER_API_KEY (for Air Quality)")
        print("  - HOME_ASSISTANT_TOKEN / HA_TOKEN (for Calendar Service)")
        return
    
    print("⚠️  Missing or empty environment variables found:")
    print()
    
    if missing_vars:
        for service, vars_dict in missing_vars.items():
            print(f"  {service.upper().replace('-', ' ')}:")
            for key, default_value in vars_dict.items():
                status = "❌ MISSING" if key not in existing_vars else "⚠️  EMPTY"
                print(f"    {status}: {key}")
    
    if missing_common:
        print("  COMMON:")
        for key in missing_common:
            status = "❌ MISSING" if key not in existing_vars else "⚠️  EMPTY"
            print(f"    {status}: {key}")
    
    print()
    print("📝 Adding missing variables to .env file...")
    
    # Merge existing vars with defaults for missing ones
    all_vars = existing_vars.copy()
    for service, vars_dict in REQUIRED_VARS.items():
        for key, default_value in vars_dict.items():
            if key not in all_vars or not all_vars[key] or all_vars[key].strip() in ['', 'your_*', 'your_*_here']:
                all_vars[key] = default_value
    
    for key, default_value in COMMON_VARS.items():
        if key not in all_vars or not all_vars[key] or all_vars[key].strip() in ['', 'your_*', 'your_*_here']:
            all_vars[key] = default_value
    
    # Write updated .env file
    write_env_file(env_path, all_vars)
    
    print("✅ .env file updated!")
    print()
    print("📋 Next steps:")
    print("  1. Open .env file and replace placeholder values with your actual API keys:")
    print("     - WATTTIME_USERNAME / WATTTIME_PASSWORD: Get from https://watttime.org")
    print("     - WEATHER_API_KEY: Get from https://openweathermap.org/api")
    print("     - HOME_ASSISTANT_TOKEN / HA_TOKEN: Create in HA Profile → Security")
    print()
    print("  2. Restart the services:")
    print("     docker-compose restart carbon-intensity air-quality electricity-pricing")
    print()
    print("  3. Check service health:")
    print("     docker-compose ps")


if __name__ == '__main__':
    main()

