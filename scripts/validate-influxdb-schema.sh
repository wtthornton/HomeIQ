#!/bin/bash

# InfluxDB Schema Validation Script
# Validates that the InfluxDB schema matches the expected hybrid architecture

set -e

# Configuration
INFLUXDB_URL="http://localhost:8086"
ORG_NAME="${INFLUXDB_ORG:-homeiq}"
BUCKET_NAME="${INFLUXDB_BUCKET:-home_assistant_events}"
ADMIN_TOKEN="${INFLUXDB_TOKEN:-homeiq-token}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Validation results
VALIDATION_PASSED=true

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓ PASS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[⚠ WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗ FAIL]${NC} $1"
    VALIDATION_PASSED=false
}

# Function to check if InfluxDB is accessible
check_influxdb_access() {
    print_status "Checking InfluxDB accessibility..."
    
    if ! curl -s -f "$INFLUXDB_URL/health" > /dev/null 2>&1; then
        print_error "InfluxDB is not accessible at $INFLUXDB_URL"
        return 1
    fi
    
    print_success "InfluxDB is accessible"
    return 0
}

# Function to validate organization
validate_organization() {
    print_status "Validating organization..."
    
    local org_exists
    org_exists=$(influx org list --host "$INFLUXDB_URL" --token "$ADMIN_TOKEN" --json | jq -r ".[] | select(.name == \"$ORG_NAME\") | .name")
    
    if [ "$org_exists" = "$ORG_NAME" ]; then
        print_success "Organization '$ORG_NAME' exists"
    else
        print_error "Organization '$ORG_NAME' not found"
    fi
}

# Function to validate bucket configuration
validate_bucket_configuration() {
    print_status "Validating bucket configuration..."
    
    # Check if main bucket exists
    local bucket_exists
    bucket_exists=$(influx bucket list --org "$ORG_NAME" --host "$INFLUXDB_URL" --token "$ADMIN_TOKEN" --json | jq -r ".[] | select(.name == \"$BUCKET_NAME\") | .name")
    
    if [ "$bucket_exists" = "$BUCKET_NAME" ]; then
        print_success "Main bucket '$BUCKET_NAME' exists"
        
        # Check retention policy (should be 365 days)
        local retention_seconds
        retention_seconds=$(influx bucket list --org "$ORG_NAME" --host "$INFLUXDB_URL" --token "$ADMIN_TOKEN" --json | jq -r ".[] | select(.name == \"$BUCKET_NAME\") | .retentionRules[0].everySeconds")
        
        local retention_days=$((retention_seconds / 86400))
        
        if [ "$retention_days" -eq 365 ]; then
            print_success "Retention policy is correct (365 days)"
        else
            print_error "Retention policy is incorrect (expected 365 days, found $retention_days days)"
        fi
    else
        print_error "Main bucket '$BUCKET_NAME' not found"
    fi
    
    # Check additional buckets
    validate_additional_buckets
}

# Function to validate additional buckets
validate_additional_buckets() {
    print_status "Validating additional buckets..."
    
    local expected_buckets=("sports_data" "weather_data" "system_metrics")
    local expected_retentions=(90 180 30)  # days
    
    for i in "${!expected_buckets[@]}"; do
        local bucket_name="${expected_buckets[$i]}"
        local expected_retention="${expected_retentions[$i]}"
        
        local bucket_exists
        bucket_exists=$(influx bucket list --org "$ORG_NAME" --host "$INFLUXDB_URL" --token "$ADMIN_TOKEN" --json | jq -r ".[] | select(.name == \"$bucket_name\") | .name")
        
        if [ "$bucket_exists" = "$bucket_name" ]; then
            print_success "Bucket '$bucket_name' exists"
            
            # Check retention policy
            local retention_seconds
            retention_seconds=$(influx bucket list --org "$ORG_NAME" --host "$INFLUXDB_URL" --token "$ADMIN_TOKEN" --json | jq -r ".[] | select(.name == \"$bucket_name\") | .retentionRules[0].everySeconds")
            
            local retention_days=$((retention_seconds / 86400))
            
            if [ "$retention_days" -eq "$expected_retention" ]; then
                print_success "Bucket '$bucket_name' retention policy is correct ($expected_retention days)"
            else
                print_error "Bucket '$bucket_name' retention policy is incorrect (expected $expected_retention days, found $retention_days days)"
            fi
        else
            print_warning "Bucket '$bucket_name' not found (may be created on demand)"
        fi
    done
}

# Function to validate schema structure by analyzing sample data
validate_schema_structure() {
    print_status "Validating schema structure..."
    
    # Try to get a sample record to analyze schema
    local sample_data
    sample_data=$(influx query \
        --org "$ORG_NAME" \
        --token "$ADMIN_TOKEN" \
        --host "$INFLUXDB_URL" \
        "from(bucket: \"$BUCKET_NAME\") |> range(start: -7d) |> limit(n:1) |> schema.fieldsAsCols()" 2>/dev/null || echo "")
    
    if [ -n "$sample_data" ] && [ "$sample_data" != "" ]; then
        print_success "Sample data found for schema analysis"
        
        # Validate required tags
        validate_required_tags "$sample_data"
        
        # Validate required fields
        validate_required_fields "$sample_data"
        
        # Validate Epic 23 enhancements
        validate_epic23_enhancements "$sample_data"
        
    else
        print_warning "No sample data found - cannot validate schema structure"
        print_status "Creating test data point for validation..."
        create_test_data_point
        validate_schema_structure  # Recursive call to validate after test data creation
    fi
}

# Function to validate required tags
validate_required_tags() {
    local sample_data="$1"
    
    print_status "Validating required tags..."
    
    local required_tags=("entity_id" "domain" "device_class" "area" "device_name")
    
    for tag in "${required_tags[@]}"; do
        if echo "$sample_data" | grep -q "\"$tag\""; then
            print_success "Required tag '$tag' found"
        else
            print_error "Required tag '$tag' not found"
        fi
    done
}

# Function to validate required fields
validate_required_fields() {
    local sample_data="$1"
    
    print_status "Validating required fields..."
    
    local required_fields=("state_value" "normalized_value" "unit_of_measurement")
    
    for field in "${required_fields[@]}"; do
        if echo "$sample_data" | grep -q "\"$field\""; then
            print_success "Required field '$field' found"
        else
            print_error "Required field '$field' not found"
        fi
    done
}

# Function to validate Epic 23 enhancements
validate_epic23_enhancements() {
    local sample_data="$1"
    
    print_status "Validating Epic 23 enhancements..."
    
    # Epic 23.1: Context tracking
    local context_fields=("context_id" "context_parent_id" "context_user_id")
    for field in "${context_fields[@]}"; do
        if echo "$sample_data" | grep -q "\"$field\""; then
            print_success "Epic 23.1 field '$field' found"
        else
            print_warning "Epic 23.1 field '$field' not found (may not be in sample data)"
        fi
    done
    
    # Epic 23.2: Device and area linkage
    local device_tags=("device_id" "area_id")
    for tag in "${device_tags[@]}"; do
        if echo "$sample_data" | grep -q "\"$tag\""; then
            print_success "Epic 23.2 tag '$tag' found"
        else
            print_warning "Epic 23.2 tag '$tag' not found (may not be in sample data)"
        fi
    done
    
    # Epic 23.4 entity_category is intentionally not checked: no collector
    # writes it (TAP-6156). Warning about a tag nothing produces trained
    # readers to ignore this section.
    
    # Epic 23.5: Device metadata
    local device_metadata_fields=("manufacturer" "model" "sw_version")
    for field in "${device_metadata_fields[@]}"; do
        if echo "$sample_data" | grep -q "\"$field\""; then
            print_success "Epic 23.5 field '$field' found"
        else
            print_warning "Epic 23.5 field '$field' not found (may not be in sample data)"
        fi
    done
}

# Function to create test data point for validation
create_test_data_point() {
    print_status "Creating test data point with full schema..."
    
    local test_data="home_assistant_events,entity_id=sensor.validation_test,domain=sensor,device_class=temperature,area=test_room,device_name=\"Validation Test Sensor\",device_id=test_001,area_id=room_001,entity_category=null,integration=test,weather_condition=clear,time_of_day=afternoon state_value=\"22.5\",previous_state=\"22.3\",normalized_value=22.5,unit_of_measurement=\"°C\",confidence=0.95,context_id=\"ctx_test\",context_parent_id=\"automation_test\",context_user_id=\"user_test\",duration_seconds=3600,energy_consumption=0.0,weather_temp=22.5,weather_humidity=45.0,weather_pressure=1013.25,manufacturer=\"Test Manufacturer\",model=\"Test Model\",sw_version=\"1.0.0\" $(date +%s%N)"
    
    echo "$test_data" | influx write \
        --bucket "$BUCKET_NAME" \
        --org "$ORG_NAME" \
        --token "$ADMIN_TOKEN" \
        --host "$INFLUXDB_URL" \
        --precision ns
    
    if [ $? -eq 0 ]; then
        print_success "Test data point created"
        sleep 2  # Wait for data to be available
    else
        print_error "Failed to create test data point"
    fi
}

# Function to validate data flow
validate_data_flow() {
    print_status "Validating data flow..."
    
    # Check if services can write to InfluxDB
    local test_measurement="data_flow_test"
    local test_data="${test_measurement} test_field=\"validation_success\" $(date +%s%N)"
    
    echo "$test_data" | influx write \
        --bucket "$BUCKET_NAME" \
        --org "$ORG_NAME" \
        --token "$ADMIN_TOKEN" \
        --host "$INFLUXDB_URL" \
        --precision ns
    
    if [ $? -eq 0 ]; then
        print_success "Data writing test passed"
        
        # Clean up test data
        influx delete \
            --bucket "$BUCKET_NAME" \
            --org "$ORG_NAME" \
            --token "$ADMIN_TOKEN" \
            --host "$INFLUXDB_URL" \
            --start "$(date -u -d '1 minute ago' '+%Y-%m-%dT%H:%M:%SZ')" \
            --stop "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" \
            --predicate "_measurement=\"$test_measurement\""
        
        print_success "Test data cleaned up"
    else
        print_error "Data writing test failed"
    fi
}

# Function to validate query performance
validate_query_performance() {
    print_status "Validating query performance..."
    
    # Test basic query performance
    local start_time=$(date +%s%N)
    
    influx query \
        --org "$ORG_NAME" \
        --token "$ADMIN_TOKEN" \
        --host "$INFLUXDB_URL" \
        "from(bucket: \"$BUCKET_NAME\") |> range(start: -1d) |> limit(n:100)" > /dev/null 2>&1
    
    local end_time=$(date +%s%N)
    local duration_ms=$(( (end_time - start_time) / 1000000 ))
    
    if [ $duration_ms -lt 1000 ]; then
        print_success "Query performance is good (${duration_ms}ms)"
    elif [ $duration_ms -lt 5000 ]; then
        print_warning "Query performance is acceptable (${duration_ms}ms)"
    else
        print_error "Query performance is poor (${duration_ms}ms)"
    fi
}

# Function to display validation summary
display_validation_summary() {
    echo ""
    echo "=========================================="
    echo "          VALIDATION SUMMARY"
    echo "=========================================="
    
    if [ "$VALIDATION_PASSED" = true ]; then
        echo -e "${GREEN}✅ ALL VALIDATIONS PASSED${NC}"
        echo ""
        echo "InfluxDB schema is correctly configured for hybrid architecture."
        echo "The system is ready for production use."
    else
        echo -e "${RED}❌ VALIDATION FAILED${NC}"
        echo ""
        echo "Some validations failed. Please review the errors above and:"
        echo "1. Fix any configuration issues"
        echo "2. Run the reset script: ./scripts/reset-influxdb-schema.sh"
        echo "3. Re-run this validation script"
        echo ""
        exit 1
    fi
}

# Function to clean up test data
cleanup_test_data() {
    print_status "Cleaning up test data..."
    
    # Delete validation test data
    influx delete \
        --bucket "$BUCKET_NAME" \
        --org "$ORG_NAME" \
        --token "$ADMIN_TOKEN" \
        --host "$INFLUXDB_URL" \
        --start "$(date -u -d '1 hour ago' '+%Y-%m-%dT%H:%M:%SZ')" \
        --stop "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" \
        --predicate 'entity_id="sensor.validation_test"' 2>/dev/null || true
    
    print_success "Test data cleaned up"
}

# Main execution
main() {
    echo "🔍 InfluxDB Schema Validation Script"
    echo "===================================="
    echo ""
    
    # Run all validations
    check_influxdb_access || exit 1
    validate_organization
    validate_bucket_configuration
    validate_schema_structure
    validate_data_flow
    validate_query_performance
    
    # Clean up test data
    cleanup_test_data
    
    # Display summary
    display_validation_summary
}

# Run main function
main "$@"
