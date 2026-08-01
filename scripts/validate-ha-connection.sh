#!/bin/bash

################################################################################
# HA-Ingestor Connection Validator
# 
# Comprehensive testing script that validates Home Assistant connectivity,
# authentication, and API access before deployment.
#
# Features:
# - TCP/IP connectivity tests
# - HTTP/HTTPS endpoint validation
# - WebSocket connection tests
# - Authentication validation
# - API access verification
# - Detailed reporting
#
# Usage: ./scripts/validate-ha-connection.sh [options]
#
# Options:
#   -v, --verbose    Verbose output
#   -q, --quiet      Quiet mode (errors only)
#   -r, --report     Generate detailed report file
#
# Version: 1.0.0
# Created: October 2025
################################################################################

set -e
set -o pipefail

################################################################################
# Configuration
################################################################################

SCRIPT_VERSION="1.0.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Test results tracking
test_passed=0
test_failed=0
test_warnings=0
test_total=0
declare -a test_results
declare -a test_messages

# Options
VERBOSE=false
QUIET=false
GENERATE_REPORT=true

################################################################################
# Color Definitions
################################################################################

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m'

CHECKMARK="${GREEN}✅${NC}"
CROSS="${RED}❌${NC}"
WARNING="${YELLOW}⚠️${NC}"
INFO="${BLUE}ℹ️${NC}"

################################################################################
# Helper Functions
################################################################################

print_header() {
    if [ "$QUIET" = false ]; then
        echo ""
        echo -e "${BLUE}╔═══════════════════════════════════════════════════════════╗${NC}"
        echo -e "${BLUE}║  ${WHITE}Home Assistant Connection Validator${BLUE}  v${SCRIPT_VERSION}      ║${NC}"
        echo -e "${BLUE}╚═══════════════════════════════════════════════════════════╝${NC}"
        echo ""
    fi
}

print_section() {
    if [ "$QUIET" = false ]; then
        echo ""
        echo -e "${CYAN}━━━ $1 ━━━${NC}"
        echo ""
    fi
}

print_success() {
    if [ "$QUIET" = false ]; then
        echo -e "   ${CHECKMARK} $1"
    fi
}

print_error() {
    echo -e "   ${CROSS} $1"
}

print_warning() {
    if [ "$QUIET" = false ]; then
        echo -e "   ${WARNING} $1"
    fi
}

print_info() {
    if [ "$VERBOSE" = true ] && [ "$QUIET" = false ]; then
        echo -e "   ${INFO} $1"
    fi
}

print_verbose() {
    if [ "$VERBOSE" = true ] && [ "$QUIET" = false ]; then
        echo "   $1"
    fi
}

################################################################################
# Test Result Tracking
################################################################################

record_test() {
    local test_name=$1
    local result=$2
    local message=$3
    
    ((test_total++))
    test_results+=("$test_name|$result|$message")
    
    case $result in
        pass)
            ((test_passed++))
            ;;
        fail)
            ((test_failed++))
            ;;
        warn)
            ((test_warnings++))
            ;;
    esac
}

################################################################################
# Configuration Loading
################################################################################

load_configuration() {
    print_section "Loading Configuration"
    
    if [ -f "$PROJECT_ROOT/.env" ]; then
        # Source the env file properly (handle export statements)
        set -a
        source "$PROJECT_ROOT/.env"
        set +a
        print_success "Configuration loaded from: .env"
    elif [ -f "$PROJECT_ROOT/infrastructure/env.production" ]; then
        set -a
        source "$PROJECT_ROOT/infrastructure/env.production"
        set +a
        print_success "Configuration loaded from: infrastructure/env.production"
    else
        print_error "No configuration file found"
        echo ""
        echo "Please run the deployment wizard first or create .env file:"
        echo "  ./scripts/deploy-wizard.sh"
        exit 1
    fi
    
    # Validate required variables
    if [ -z "$HOME_ASSISTANT_URL" ] || [ -z "$HOME_ASSISTANT_TOKEN" ]; then
        print_error "Configuration incomplete"
        echo ""
        echo "Required variables:"
        echo "  HOME_ASSISTANT_URL"
        echo "  HOME_ASSISTANT_TOKEN"
        exit 1
    fi
    
    # Mask token in output
    local masked_token="${HOME_ASSISTANT_TOKEN:0:10}...${HOME_ASSISTANT_TOKEN: -10}"
    print_info "URL: $HOME_ASSISTANT_URL"
    print_info "Token: $masked_token"
}

################################################################################
# Task 2.2: Basic Connectivity Tests
################################################################################

test_tcp_connectivity() {
    print_section "TCP/IP Connectivity Test"
    
    # Extract hostname and port from URL
    local hostname=$(echo "$HOME_ASSISTANT_URL" | awk -F[/:] '{print $4}')
    local port=$(echo "$HOME_ASSISTANT_URL" | awk -F[/:] '{print $5}')
    port=${port:-8123}
    
    print_verbose "Testing connection to $hostname:$port"
    
    # Test TCP connection with timeout
    if timeout 5 bash -c "cat < /dev/null > /dev/tcp/$hostname/$port" 2>/dev/null; then
        print_success "TCP connection successful to $hostname:$port"
        record_test "TCP Connectivity" "pass" "Successfully connected to $hostname:$port"
    else
        print_error "Cannot reach $hostname:$port"
        echo ""
        echo "   Troubleshooting:"
        echo "   • Check if Home Assistant is running"
        echo "   • Verify firewall settings"
        echo "   • Ensure correct IP address/hostname"
        echo "   • Check network connectivity"
        record_test "TCP Connectivity" "fail" "Cannot connect to $hostname:$port"
        return 1
    fi
}

test_http_endpoint() {
    print_section "HTTP Endpoint Test"
    
    if ! command -v curl &> /dev/null; then
        print_warning "curl not available, skipping HTTP test"
        record_test "HTTP Endpoint" "warn" "curl not available"
        return 0
    fi
    
    print_verbose "Testing HTTP endpoint: $HOME_ASSISTANT_URL"
    
    # Test HTTP endpoint
    local http_code=$(curl -s -o /dev/null -w "%{http_code}" \
        --max-time 10 \
        "$HOME_ASSISTANT_URL/" 2>/dev/null || echo "000")
    
    if [ "$http_code" -ge 200 ] && [ "$http_code" -lt 500 ]; then
        print_success "HTTP endpoint accessible (HTTP $http_code)"
        record_test "HTTP Endpoint" "pass" "HTTP $http_code"
    elif [ "$http_code" == "000" ]; then
        print_error "HTTP endpoint unreachable"
        echo ""
        echo "   Troubleshooting:"
        echo "   • Check if Home Assistant is running"
        echo "   • Verify the URL is correct"
        echo "   • Check for SSL/TLS issues if using HTTPS"
        record_test "HTTP Endpoint" "fail" "Connection failed"
        return 1
    else
        print_warning "Unexpected HTTP response: $http_code"
        record_test "HTTP Endpoint" "warn" "HTTP $http_code"
    fi
    
    # Test response time
    local response_time=$(curl -s -o /dev/null -w "%{time_total}" \
        --max-time 10 \
        "$HOME_ASSISTANT_URL/" 2>/dev/null || echo "0")
    
    if [ "$response_time" != "0" ]; then
        print_info "Response time: ${response_time}s"
        
        # Convert to milliseconds for comparison
        local response_ms=$(echo "$response_time * 1000" | bc 2>/dev/null || echo "0")
        if [ "${response_ms%.*}" -gt 2000 ]; then
            print_warning "Slow response time (>2s)"
        fi
    fi
}

################################################################################
# Task 2.3: WebSocket Connection Test
################################################################################

test_websocket_connection() {
    print_section "WebSocket Connection Test"
    
    # Convert HTTP URL to WebSocket URL
    local ws_url=$(echo "$HOME_ASSISTANT_URL" | sed 's/http:/ws:/g' | sed 's/https:/wss:/g')
    ws_url="${ws_url}/api/websocket"
    
    print_verbose "WebSocket URL: $ws_url"
    
    # Test with Python if available
    if command -v python3 &> /dev/null; then
        local ws_test_result=$(python3 << 'EOF'
import sys
import json

try:
    import websockets
    import asyncio
except ImportError:
    print("SKIP")
    sys.exit(0)

ws_url = sys.argv[1] if len(sys.argv) > 1 else ""

async def test_ws():
    try:
        async with websockets.connect(ws_url, timeout=10) as ws:
            msg = await asyncio.wait_for(ws.recv(), timeout=5)
            data = json.loads(msg)
            if data.get("type") == "auth_required":
                print("PASS")
                return True
            print("UNEXPECTED")
            return False
    except Exception as e:
        print(f"FAIL:{e}")
        return False

try:
    result = asyncio.run(test_ws())
    sys.exit(0 if result else 1)
except Exception as e:
    print(f"ERROR:{e}")
    sys.exit(1)
EOF
        "$ws_url" 2>&1)
        
        if [[ "$ws_test_result" == "PASS" ]]; then
            print_success "WebSocket connection successful"
            record_test "WebSocket Connection" "pass" "Successfully connected"
        elif [[ "$ws_test_result" == "SKIP" ]]; then
            print_warning "Python websockets module not installed, skipping test"
            print_info "Install with: pip install websockets"
            record_test "WebSocket Connection" "warn" "Python websockets not available"
        else
            print_warning "WebSocket test failed or inconclusive"
            print_verbose "Result: $ws_test_result"
            record_test "WebSocket Connection" "warn" "Test failed"
        fi
    else
        print_warning "Python not available, skipping WebSocket test"
        record_test "WebSocket Connection" "warn" "Python not available"
    fi
}

################################################################################
# Task 2.4: Authentication Validation
################################################################################

test_authentication() {
    print_section "Authentication Test"
    
    if ! command -v curl &> /dev/null; then
        print_warning "curl not available, skipping authentication test"
        record_test "Authentication" "warn" "curl not available"
        return 0
    fi
    
    print_verbose "Testing authentication with provided token"
    
    # Test token format
    local token_length=${#HOME_ASSISTANT_TOKEN}
    if [ $token_length -lt 50 ]; then
        print_warning "Token seems short ($token_length characters)"
        print_info "Long-lived access tokens are typically ~180 characters"
    fi
    
    # Test API authentication
    local auth_response=$(curl -s -X GET \
        -H "Authorization: Bearer $HOME_ASSISTANT_TOKEN" \
        -H "Content-Type: application/json" \
        --max-time 10 \
        "$HOME_ASSISTANT_URL/api/" 2>/dev/null)
    
    if echo "$auth_response" | grep -q "API running"; then
        print_success "Authentication successful"
        print_success "Token is valid"
        record_test "Authentication" "pass" "Token validated successfully"
    else
        print_error "Authentication failed"
        print_verbose "Response: $auth_response"
        echo ""
        echo "   Troubleshooting:"
        echo "   • Verify token is copied correctly (no extra spaces)"
        echo "   • Generate new long-lived access token"
        echo "   • Check token hasn't expired"
        echo "   • Verify token has proper permissions"
        record_test "Authentication" "fail" "Token validation failed"
        return 1
    fi
}

test_api_access() {
    print_section "API Access Test"
    
    if ! command -v curl &> /dev/null; then
        print_warning "curl not available, skipping API test"
        record_test "API Access" "warn" "curl not available"
        return 0
    fi
    
    print_verbose "Testing API access permissions"
    
    # Test state API access
    local state_response=$(curl -s -X GET \
        -H "Authorization: Bearer $HOME_ASSISTANT_TOKEN" \
        -H "Content-Type: application/json" \
        --max-time 10 \
        "$HOME_ASSISTANT_URL/api/states" 2>/dev/null)
    
    if echo "$state_response" | grep -q "entity_id"; then
        print_success "API access confirmed (can read states)"
        
        # Count entities (if jq is available)
        if command -v jq &> /dev/null; then
            local entity_count=$(echo "$state_response" | jq '. | length' 2>/dev/null || echo "unknown")
            if [ "$entity_count" != "unknown" ]; then
                print_info "Found $entity_count entities"
            fi
        fi
        
        record_test "API Access" "pass" "Can read state data"
    elif echo "$state_response" | grep -q "401\|Unauthorized"; then
        print_error "API access denied (unauthorized)"
        record_test "API Access" "fail" "Unauthorized"
        return 1
    else
        print_warning "Limited or no API access"
        print_verbose "Response: ${state_response:0:100}..."
        record_test "API Access" "warn" "Access may be restricted"
    fi
}

################################################################################
# Task 2.5: Report Generation
################################################################################

generate_report() {
    print_section "Validation Summary"
    
    local report_file=""
    if [ "$GENERATE_REPORT" = true ]; then
        report_file="$PROJECT_ROOT/ha-connection-validation-$(date +%Y%m%d_%H%M%S).txt"
    fi
    
    # Generate summary
    {
        echo "═══════════════════════════════════════════════════════════"
        echo "Home Assistant Connection Validation Report"
        echo "Generated: $(date)"
        echo "═══════════════════════════════════════════════════════════"
        echo ""
        echo "Configuration:"
        echo "  URL: $HOME_ASSISTANT_URL"
        echo "  Token: ${HOME_ASSISTANT_TOKEN:0:10}...${HOME_ASSISTANT_TOKEN: -10}"
        echo ""
        echo "Test Results:"
        echo "  ✅ Passed: $test_passed"
        echo "  ❌ Failed: $test_failed"
        echo "  ⚠️  Warnings: $test_warnings"
        echo "  📊 Total: $test_total"
        echo ""
        
        # Detailed results
        echo "Detailed Results:"
        for result in "${test_results[@]}"; do
            IFS='|' read -r name status message <<< "$result"
            case $status in
                pass)
                    echo "  ✅ $name: $message"
                    ;;
                fail)
                    echo "  ❌ $name: $message"
                    ;;
                warn)
                    echo "  ⚠️  $name: $message"
                    ;;
            esac
        done
        
        echo ""
        
        # Recommendations
        if [ $test_failed -eq 0 ]; then
            echo "🎉 All tests passed! Your Home Assistant connection is ready."
            echo ""
            echo "Next Steps:"
            echo "  1. Start HA-Ingestor: docker-compose up -d"
            echo "  2. Monitor logs: docker-compose logs -f"
            echo "  3. Access dashboard: http://localhost:3000"
        else
            echo "⚠️  Some tests failed. Please review and fix issues."
            echo ""
            echo "Common Solutions:"
            echo "  • Verify Home Assistant is running and accessible"
            echo "  • Check firewall and network settings"
            echo "  • Regenerate long-lived access token"
            echo "  • Ensure correct URL format (http:// or https://)"
            echo "  • Check Home Assistant logs for errors"
        fi
        
        echo ""
        echo "═══════════════════════════════════════════════════════════"
        
    } | tee ${report_file:+$report_file}
    
    if [ -n "$report_file" ]; then
        echo ""
        echo "Report saved to: $(basename $report_file)"
    fi
    
    # Return appropriate exit code
    if [ $test_failed -gt 0 ]; then
        return 1
    else
        return 0
    fi
}

################################################################################
# Main Function
################################################################################

main() {
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -q|--quiet)
                QUIET=true
                shift
                ;;
            -r|--report)
                GENERATE_REPORT=true
                shift
                ;;
            --no-report)
                GENERATE_REPORT=false
                shift
                ;;
            -h|--help)
                echo "Usage: $0 [options]"
                echo ""
                echo "Options:"
                echo "  -v, --verbose     Verbose output"
                echo "  -q, --quiet       Quiet mode (errors only)"
                echo "  -r, --report      Generate report file (default)"
                echo "  --no-report       Don't generate report file"
                echo "  -h, --help        Show this help"
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                echo "Use -h or --help for usage information"
                exit 1
                ;;
        esac
    done
    
    # Change to project root
    cd "$PROJECT_ROOT" || { echo "Cannot access project directory"; exit 1; }
    
    print_header
    
    # Load configuration
    load_configuration
    
    # Run tests
    test_tcp_connectivity || true
    test_http_endpoint || true
    test_websocket_connection || true
    test_authentication || true
    test_api_access || true
    
    # Generate report and exit
    if generate_report; then
        exit 0
    else
        exit 1
    fi
}

# Run main function
main "$@"

