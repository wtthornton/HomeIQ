#!/bin/bash

################################################################################
# HA-Ingestor Deployment Wizard
# 
# Interactive deployment configuration wizard that guides users through
# setting up HA-Ingestor with their Home Assistant instance.
#
# Features:
# - Interactive deployment option selection
# - Automatic resource detection
# - Configuration file generation
# - Connection validation
# - Secure password generation
#
# Usage: ./scripts/deploy-wizard.sh
#
# Version: 1.0.0
# Created: October 2025
################################################################################

set -e  # Exit on error
set -o pipefail  # Exit on pipe failure

################################################################################
# Configuration
################################################################################

SCRIPT_VERSION="1.0.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONFIG_FILE="${PROJECT_ROOT}/.env"
VALIDATOR_SCRIPT="${SCRIPT_DIR}/validate-ha-connection.sh"

################################################################################
# Color Definitions
################################################################################

# Text colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Symbols
CHECKMARK="${GREEN}✅${NC}"
CROSS="${RED}❌${NC}"
WARNING="${YELLOW}⚠️${NC}"
INFO="${BLUE}ℹ️${NC}"
ARROW="${CYAN}➜${NC}"
ROCKET="${GREEN}🚀${NC}"
WIZARD="${MAGENTA}🧙${NC}"

################################################################################
# State Management
################################################################################

declare -A wizard_state

# Initialize state
wizard_state[deploy_type]=""
wizard_state[deploy_name]=""
wizard_state[ha_url]=""
wizard_state[ha_token]=""
wizard_state[os]=""
wizard_state[ram_gb]=0
wizard_state[disk_gb]=0
wizard_state[cpu_cores]=0
wizard_state[docker_version]=""
wizard_state[compose_version]=""
wizard_state[compose_command]="docker-compose"
wizard_state[config_generated]=false
wizard_state[validation_passed]=false

################################################################################
# Helper Functions - Output
################################################################################

print_header() {
    clear
    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║                                                            ║${NC}"
    echo -e "${BLUE}║  ${WIZARD}  ${WHITE}HA-Ingestor Deployment Wizard${BLUE}  v${SCRIPT_VERSION}            ║${NC}"
    echo -e "${BLUE}║                                                            ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_section() {
    local title=$1
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  $title${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

print_success() {
    echo -e "   ${CHECKMARK} $1"
}

print_error() {
    echo -e "   ${CROSS} $1"
}

print_warning() {
    echo -e "   ${WARNING} $1"
}

print_info() {
    echo -e "   ${INFO} $1"
}

print_step() {
    echo -e "   ${ARROW} $1"
}

################################################################################
# Helper Functions - Validation
################################################################################

validate_url() {
    local url=$1
    
    # Check if URL starts with http://, https://, ws://, or wss://
    if [[ $url =~ ^(http|https|ws|wss)://.*$ ]]; then
        return 0
    else
        return 1
    fi
}

validate_ip() {
    local ip=$1
    
    # Check if it's a valid IPv4 address
    if [[ $ip =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
        # Validate each octet is 0-255
        IFS='.' read -ra OCTETS <<< "$ip"
        for octet in "${OCTETS[@]}"; do
            if [ "$octet" -gt 255 ]; then
                return 1
            fi
        done
        return 0
    else
        return 1
    fi
}

validate_token() {
    local token=$1
    
    # Check token is not empty and has reasonable length
    if [ -z "$token" ]; then
        return 1
    fi
    
    if [ ${#token} -lt 50 ]; then
        print_warning "Token seems short (expected ~180 characters)"
        print_info "Make sure you're using a long-lived access token"
    fi
    
    return 0
}

################################################################################
# Helper Functions - Utilities
################################################################################

mask_token() {
    local token=$1
    local length=${#token}
    
    if [ $length -gt 20 ]; then
        echo "${token:0:10}...${token: -10}"
    else
        echo "***"
    fi
}

generate_secure_password() {
    local length=${1:-32}
    
    # Try openssl first
    if command -v openssl &> /dev/null; then
        openssl rand -hex $((length / 2)) 2>/dev/null
        return
    fi
    
    # Fallback to /dev/urandom
    if [ -r /dev/urandom ]; then
        head -c $((length / 2)) /dev/urandom | base64 | tr -d '/+=' | head -c $length
        return
    fi
    
    # Fallback to date-based (not cryptographically secure)
    echo "$(date +%s%N | sha256sum | head -c $length)"
}

press_any_key() {
    echo ""
    read -n 1 -s -r -p "Press any key to continue..."
    echo ""
}

################################################################################
# Error Handling
################################################################################

error_exit() {
    local message=$1
    echo ""
    print_error "$message"
    echo ""
    echo -e "${RED}Wizard failed. Please check the error and try again.${NC}"
    echo ""
    exit 1
}

cleanup() {
    # Cleanup function called on exit
    if [ $? -ne 0 ]; then
        echo ""
        print_info "Cleaning up..."
    fi
}

interrupt_handler() {
    echo ""
    echo ""
    print_warning "Wizard interrupted by user"
    echo ""
    echo "You can run the wizard again at any time:"
    echo "  ./scripts/deploy-wizard.sh"
    echo ""
    exit 130
}

# Set up traps
trap cleanup EXIT
trap interrupt_handler INT TERM

################################################################################
# Validation Functions
################################################################################

check_prerequisites() {
    print_section "Checking Prerequisites"
    
    local missing_deps=0
    
    # Check for required commands
    local required_commands=("docker" "curl" "awk" "sed")
    
    for cmd in "${required_commands[@]}"; do
        if command -v "$cmd" &> /dev/null; then
            print_success "$cmd found"
        else
            print_error "$cmd not found"
            ((missing_deps++))
        fi
    done
    
    if [ $missing_deps -gt 0 ]; then
        echo ""
        print_error "Missing required dependencies"
        echo ""
        echo "Please install the missing dependencies and try again."
        return 1
    fi
    
    echo ""
    print_success "All prerequisites met"
    return 0
}

################################################################################
# Main Functions - Will be implemented in subsequent tasks
################################################################################

################################################################################
# Task 1.2: Deployment Option Selection
################################################################################

select_deployment_option() {
    print_section "Deployment Configuration"
    
    echo "Where is your Home Assistant currently running?"
    echo ""
    echo -e "${CYAN}1) Same Machine (localhost)${NC}"
    echo "   ${CHECKMARK} Simplest setup, no network configuration"
    echo "   ${WARNING} Shares resources with Home Assistant"
    echo "   📌 Best for: Testing, development, abundant resources (8GB+ RAM)"
    echo ""
    echo -e "${CYAN}2) Separate Machine (Local Network)${NC}"
    echo "   ${CHECKMARK} Resource isolation, better performance"
    echo "   ${CHECKMARK} Independent scaling and fault tolerance"
    echo "   📌 Best for: Production, dedicated monitoring server"
    echo ""
    echo -e "${CYAN}3) Remote Access (Nabu Casa or Cloud)${NC}"
    echo "   ${CHECKMARK} Access from anywhere"
    echo "   ${WARNING} Requires Nabu Casa subscription or exposed HA instance"
    echo "   📌 Best for: Cloud infrastructure, remote monitoring"
    echo ""
    echo -e "${CYAN}4) Custom Configuration (Advanced)${NC}"
    echo "   ⚙️  Manual configuration for specific needs"
    echo ""
    
    while true; do
        read -p "Select deployment option (1-4): " deploy_choice
        
        case $deploy_choice in
            1)
                wizard_state[deploy_type]="same_machine"
                wizard_state[deploy_name]="Same Machine"
                print_success "Selected: Same Machine deployment"
                echo ""
                print_info "HA-Ingestor will run on the same machine as Home Assistant"
                print_info "Using localhost connection for minimal latency"
                return 0
                ;;
            2)
                wizard_state[deploy_type]="separate_network"
                wizard_state[deploy_name]="Separate Machine (Local Network)"
                print_success "Selected: Separate Machine deployment"
                echo ""
                print_info "HA-Ingestor will run on a separate machine"
                print_info "Ensure network connectivity between machines"
                return 0
                ;;
            3)
                wizard_state[deploy_type]="remote"
                wizard_state[deploy_name]="Remote Access"
                print_success "Selected: Remote deployment"
                echo ""
                print_info "HA-Ingestor will connect remotely to Home Assistant"
                print_info "Nabu Casa or properly secured remote access required"
                return 0
                ;;
            4)
                wizard_state[deploy_type]="custom"
                wizard_state[deploy_name]="Custom"
                print_success "Selected: Custom configuration"
                echo ""
                print_info "You'll configure all settings manually"
                return 0
                ;;
            *)
                print_error "Invalid choice. Please select 1-4."
                echo ""
                ;;
        esac
    done
}

################################################################################
# Task 1.3: Home Assistant Configuration
################################################################################

configure_home_assistant() {
    print_section "Home Assistant Configuration"
    
    local deploy_type=${wizard_state[deploy_type]}
    local default_url=""
    local url_prompt=""
    
    # Provide context-specific guidance based on deployment type
    case $deploy_type in
        same_machine)
            default_url="http://localhost:8123"
            url_prompt="Enter Home Assistant URL (or press Enter for localhost)"
            echo "📌 For same-machine deployment, typically use:"
            echo "   http://localhost:8123 or http://127.0.0.1:8123"
            echo ""
            ;;
        separate_network)
            url_prompt="Enter Home Assistant IP address or hostname"
            echo "📌 Enter the IP address of your Home Assistant server"
            echo "   Example: 192.168.1.100"
            echo ""
            
            while true; do
                read -p "Enter Home Assistant IP: " ha_ip
                
                if [ -z "$ha_ip" ]; then
                    print_error "IP address cannot be empty"
                    continue
                fi
                
                if validate_ip "$ha_ip"; then
                    default_url="http://${ha_ip}:8123"
                    print_success "IP address validated"
                    break
                else
                    print_warning "IP format may be invalid, but continuing..."
                    default_url="http://${ha_ip}:8123"
                    break
                fi
            done
            echo ""
            ;;
        remote)
            url_prompt="Enter Nabu Casa or remote URL"
            echo "📌 Enter your Nabu Casa or remote Home Assistant URL"
            echo "   Example: https://xxxxx.ui.nabu.casa"
            echo "   Use https:// for secure connections"
            echo ""
            ;;
        custom)
            url_prompt="Enter Home Assistant URL"
            echo "📌 Enter the complete URL to your Home Assistant instance"
            echo "   Include protocol: http:// https:// ws:// or wss://"
            echo ""
            ;;
    esac
    
    # Get URL
    while true; do
        read -p "$url_prompt [$default_url]: " ha_url
        ha_url=${ha_url:-$default_url}
        
        # Validate URL
        if validate_url "$ha_url"; then
            wizard_state[ha_url]=$ha_url
            print_success "URL accepted: $ha_url"
            break
        else
            print_error "Invalid URL format"
            print_info "URL must start with http://, https://, ws://, or wss://"
            echo ""
        fi
    done
    
    # Get access token
    echo ""
    print_info "You need a long-lived access token from Home Assistant"
    echo ""
    echo "To create one:"
    echo "  1. Open Home Assistant"
    echo "  2. Go to your Profile (click your name)"
    echo "  3. Scroll to 'Long-Lived Access Tokens'"
    echo "  4. Click 'Create Token'"
    echo "  5. Give it a name (e.g., 'HA-Ingestor')"
    echo "  6. Copy the token"
    echo ""
    
    while true; do
        read -sp "Enter Home Assistant access token: " ha_token
        echo ""
        
        if validate_token "$ha_token"; then
            wizard_state[ha_token]=$ha_token
            local masked=$(mask_token "$ha_token")
            print_success "Token saved: $masked (${#ha_token} characters)"
            break
        else
            print_error "Token cannot be empty"
            echo ""
        fi
    done
    
    # Offer to test connection
    echo ""
    read -p "Would you like to test the connection now? (Y/n): " test_now
    
    if [[ ! $test_now =~ ^[Nn]$ ]]; then
        test_connection_quick
    fi
}

test_connection_quick() {
    echo ""
    print_step "Testing connection to Home Assistant..."
    
    local ha_url=${wizard_state[ha_url]}
    local ha_token=${wizard_state[ha_token]}
    
    # Extract hostname for connectivity test
    local hostname=$(echo "$ha_url" | awk -F[/:] '{print $4}')
    
    # Quick HTTP test
    if command -v curl &> /dev/null; then
        local http_code=$(curl -s -o /dev/null -w "%{http_code}" \
            -H "Authorization: Bearer $ha_token" \
            --max-time 10 \
            "$ha_url/api/" 2>/dev/null || echo "000")
        
        if [ "$http_code" == "200" ]; then
            print_success "Connection successful!"
            print_success "Home Assistant is reachable and token is valid"
            wizard_state[validation_passed]=true
        elif [ "$http_code" == "000" ]; then
            print_warning "Could not connect to Home Assistant"
            print_info "This might be okay - we'll try again during full validation"
        elif [ "$http_code" == "401" ]; then
            print_warning "Authentication failed (HTTP 401)"
            print_info "Please verify your access token is correct"
        else
            print_warning "Unexpected response (HTTP $http_code)"
            print_info "Home Assistant might be reachable but not responding correctly"
        fi
    else
        print_warning "curl not available, skipping connection test"
    fi
    
    echo ""
}

################################################################################
# Task 1.4: System Resource Detection
################################################################################

detect_system_resources() {
    print_section "System Resource Detection"
    
    local warnings=0
    
    # Detect OS
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        wizard_state[os]="Linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        wizard_state[os]="macOS"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        wizard_state[os]="Windows (WSL/Cygwin)"
    else
        wizard_state[os]="Unknown"
    fi
    
    print_info "Operating System: ${wizard_state[os]}"
    
    # Check RAM (Linux)
    if [ -f /proc/meminfo ]; then
        local total_ram=$(awk '/MemTotal/ {printf "%.0f", $2/1024/1024}' /proc/meminfo)
        wizard_state[ram_gb]=$total_ram
        echo ""
        print_info "RAM: ${total_ram}GB"
        
        if [ "$total_ram" -lt 4 ]; then
            print_warning "Less than 4GB RAM detected"
            print_info "Consider using minimal service configuration"
            ((warnings++))
        elif [ "$total_ram" -lt 8 ]; then
            print_warning "Limited RAM (4-8GB)"
            print_info "Recommended: Use standard configuration, skip optional services"
            ((warnings++))
        else
            print_success "Sufficient RAM for full deployment"
        fi
    elif command -v sysctl &> /dev/null; then
        # macOS
        local total_ram=$(sysctl -n hw.memsize 2>/dev/null | awk '{printf "%.0f", $1/1024/1024/1024}')
        wizard_state[ram_gb]=$total_ram
        echo ""
        print_info "RAM: ${total_ram}GB"
        
        if [ "$total_ram" -lt 4 ]; then
            print_warning "Less than 4GB RAM detected"
            ((warnings++))
        elif [ "$total_ram" -ge 8 ]; then
            print_success "Sufficient RAM for full deployment"
        fi
    fi
    
    # Check disk space
    if command -v df &> /dev/null; then
        local available_disk=$(df -BG "$PROJECT_ROOT" 2>/dev/null | awk 'NR==2 {print $4}' | sed 's/G//' || echo "unknown")
        if [ "$available_disk" != "unknown" ]; then
            wizard_state[disk_gb]=$available_disk
            print_info "Available Disk Space: ${available_disk}GB"
            
            if [ "$available_disk" -lt 20 ]; then
                print_warning "Less than 20GB disk space available"
                print_info "Minimum: 20GB, Recommended: 50GB+"
                ((warnings++))
            else
                print_success "Sufficient disk space"
            fi
        fi
    fi
    
    # Check CPU
    local cpu_cores="unknown"
    if command -v nproc &> /dev/null; then
        cpu_cores=$(nproc)
    elif command -v sysctl &> /dev/null; then
        cpu_cores=$(sysctl -n hw.ncpu 2>/dev/null || echo "unknown")
    fi
    
    wizard_state[cpu_cores]=$cpu_cores
    print_info "CPU Cores: $cpu_cores"
    
    if [ "$cpu_cores" != "unknown" ] && [ "$cpu_cores" -lt 2 ]; then
        print_warning "Less than 2 CPU cores"
        ((warnings++))
    elif [ "$cpu_cores" != "unknown" ]; then
        print_success "Sufficient CPU cores"
    fi
    
    # Check Docker
    echo ""
    print_step "Checking Docker installation..."
    if command -v docker &> /dev/null; then
        local docker_version=$(docker --version | awk '{print $3}' | tr -d ',')
        wizard_state[docker_version]=$docker_version
        print_success "Docker installed: $docker_version"
    else
        print_error "Docker not found"
        echo ""
        echo "Docker is required. Please install Docker:"
        echo "  Linux: https://docs.docker.com/engine/install/"
        echo "  macOS: https://docs.docker.com/desktop/mac/install/"
        echo "  Windows: https://docs.docker.com/desktop/windows/install/"
        error_exit "Docker installation required"
    fi
    
    # Check Docker Compose
    if command -v docker-compose &> /dev/null; then
        local compose_version=$(docker-compose --version 2>/dev/null | awk '{print $3}' | tr -d ',' || echo "unknown")
        wizard_state[compose_version]=$compose_version
        wizard_state[compose_command]="docker-compose"
        print_success "Docker Compose installed: $compose_version"
    elif docker compose version &> /dev/null 2>&1; then
        local compose_version=$(docker compose version --short 2>/dev/null || echo "plugin")
        wizard_state[compose_version]=$compose_version
        wizard_state[compose_command]="docker compose"
        print_success "Docker Compose (plugin) installed: $compose_version"
    else
        print_error "Docker Compose not found"
        error_exit "Docker Compose installation required"
    fi
    
    # Summary
    echo ""
    if [ $warnings -eq 0 ]; then
        print_success "System meets all requirements!"
    else
        print_warning "$warnings warning(s) detected"
        echo ""
        echo "You can continue, but performance may be impacted."
        read -p "Continue anyway? (y/N): " continue_choice
        if [[ ! $continue_choice =~ ^[Yy]$ ]]; then
            error_exit "Deployment cancelled by user"
        fi
    fi
}

################################################################################
# Task 1.5: Configuration Generation
################################################################################

generate_configuration() {
    print_section "Configuration Generation"
    
    local env_file="$PROJECT_ROOT/.env"
    local backup_file=""
    
    # Backup existing config
    if [ -f "$env_file" ]; then
        backup_file="${env_file}.backup.$(date +%Y%m%d_%H%M%S)"
        cp "$env_file" "$backup_file"
        print_info "Backed up existing config to: $(basename $backup_file)"
    fi
    
    print_step "Generating secure passwords..."
    
    # Generate secure passwords
    local influx_password=$(generate_secure_password 32)
    local influx_token=$(generate_secure_password 64)
    local admin_password=$(generate_secure_password 24)
    local jwt_secret=$(generate_secure_password 64)
    
    print_success "Secure passwords generated"
    
    print_step "Creating configuration file..."
    
    # Create configuration file
    cat > "$env_file" << EOF
# ============================================================================
# HA-Ingestor Configuration
# Generated by Deployment Wizard v${SCRIPT_VERSION} on $(date)
# Deployment Type: ${wizard_state[deploy_name]}
# ============================================================================

# Home Assistant Configuration
HOME_ASSISTANT_URL=${wizard_state[ha_url]}
HOME_ASSISTANT_TOKEN=${wizard_state[ha_token]}

# InfluxDB Configuration
INFLUXDB_URL=http://influxdb:8086
INFLUXDB_USERNAME=admin
INFLUXDB_PASSWORD=$influx_password
INFLUXDB_ORG=homeiq
INFLUXDB_BUCKET=home_assistant_events
INFLUXDB_TOKEN=$influx_token

# API Configuration
API_HOST=0.0.0.0
ADMIN_API_PORT=8003
WEBSOCKET_INGESTION_PORT=8001
DATA_RETENTION_PORT=8080
HEALTH_DASHBOARD_PORT=3000

# Authentication
ENABLE_AUTH=true
ADMIN_PASSWORD=$admin_password
JWT_SECRET_KEY=$jwt_secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE_PATH=/app/logs
LOG_FORMAT=json
LOG_OUTPUT=both

# Data Retention
CLEANUP_INTERVAL_HOURS=24
MONITORING_INTERVAL_MINUTES=5
COMPRESSION_INTERVAL_HOURS=24
BACKUP_INTERVAL_HOURS=24
BACKUP_DIR=/backups

# Weather API (Optional - uncomment and add key if desired)
# WEATHER_API_KEY=your_openweathermap_key_here
# WEATHER_API_URL=https://api.openweathermap.org/data/2.5
# WEATHER_DEFAULT_LOCATION=Las Vegas,NV,US
# WEATHER_ENRICHMENT_ENABLED=true
# WEATHER_CACHE_MINUTES=15
# WEATHER_RATE_LIMIT_PER_MINUTE=50
# WEATHER_RATE_LIMIT_PER_DAY=900
# WEATHER_REQUEST_TIMEOUT=10

# External Data Services (Optional)
# WATTTIME_API_TOKEN=
# GRID_REGION=CAISO_NORTH
# PRICING_PROVIDER=awattar
# PRICING_API_KEY=
# AIRNOW_API_KEY=
# LATITUDE=36.1699
# LONGITUDE=-115.1398
# GOOGLE_CLIENT_ID=
# GOOGLE_CLIENT_SECRET=
# GOOGLE_REFRESH_TOKEN=
# METER_TYPE=generic
# METER_API_TOKEN=
# METER_DEVICE_ID=

EOF

    # Set secure permissions (Linux/Mac only)
    if [[ "$OSTYPE" != "msys" ]] && [[ "$OSTYPE" != "cygwin" ]]; then
        chmod 600 "$env_file" 2>/dev/null || true
    fi
    
    print_success "Configuration saved to: .env"
    print_info "File permissions: 600 (owner read/write only)"
    
    # Save credentials for user
    local creds_file="$PROJECT_ROOT/CREDENTIALS.txt"
    cat > "$creds_file" << EOF
═══════════════════════════════════════════════════════════
HA-Ingestor Credentials
Generated: $(date)
═══════════════════════════════════════════════════════════

🌐 Admin Dashboard
   URL: http://localhost:3000
   Username: admin
   Password: $admin_password

📊 InfluxDB
   URL: http://localhost:8086
   Username: admin
   Password: $influx_password
   Token: $influx_token
   Organization: homeiq
   Bucket: home_assistant_events

⚠️  IMPORTANT: Save these credentials securely and delete this file!

═══════════════════════════════════════════════════════════
EOF
    
    if [[ "$OSTYPE" != "msys" ]] && [[ "$OSTYPE" != "cygwin" ]]; then
        chmod 600 "$creds_file" 2>/dev/null || true
    fi
    
    echo ""
    print_success "Credentials saved to: CREDENTIALS.txt"
    print_warning "SAVE THESE CREDENTIALS AND DELETE CREDENTIALS.txt FOR SECURITY!"
    
    wizard_state[config_generated]=true
}

################################################################################
# Main Wizard Flow
################################################################################

run_wizard() {
    print_header
    
    echo -e "${WHITE}Welcome to the HA-Ingestor Deployment Wizard!${NC}"
    echo ""
    echo "This wizard will help you:"
    echo "  • Choose the right deployment option"
    echo "  • Configure Home Assistant connection"
    echo "  • Detect system resources"
    echo "  • Generate configuration files"
    echo "  • Validate your setup"
    echo ""
    echo "Let's get started!"
    echo ""
    
    press_any_key
    
    # Check prerequisites
    if ! check_prerequisites; then
        error_exit "Prerequisites not met"
    fi
    
    press_any_key
    
    # Step 1: Select deployment option
    select_deployment_option
    
    # Step 2: Configure Home Assistant
    configure_home_assistant
    
    # Step 3: Detect system resources
    detect_system_resources
    
    # Step 4: Generate configuration
    generate_configuration
    
    # Step 5: Summary and next steps
    show_summary
}

show_summary() {
    print_section "Setup Complete!"
    
    echo -e "${GREEN}${ROCKET} Congratulations! Your HA-Ingestor is configured.${NC}"
    echo ""
    echo -e "${WHITE}Next Steps:${NC}"
    echo ""
    echo "1. Review your configuration:"
    echo "   cat .env"
    echo ""
    echo "2. Start the services:"
    echo "   docker-compose up -d"
    echo ""
    echo "3. Monitor the logs:"
    echo "   docker-compose logs -f"
    echo ""
    echo "4. Access the dashboard:"
    echo "   http://localhost:3000"
    echo ""
    echo -e "${CYAN}For help and documentation:${NC}"
    echo "  • User Guide: docs/USER_MANUAL.md"
    echo "  • Troubleshooting: docs/TROUBLESHOOTING_GUIDE.md"
    echo "  • API Docs: docs/API_DOCUMENTATION.md"
    echo ""
    echo -e "${GREEN}Happy monitoring! ${WIZARD}${NC}"
    echo ""
}

################################################################################
# Script Entry Point
################################################################################

main() {
    # Change to project root
    cd "$PROJECT_ROOT" || error_exit "Cannot access project directory"
    
    # Run the wizard
    run_wizard
    
    exit 0
}

# Run main function
main "$@"

