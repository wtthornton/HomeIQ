#!/bin/bash
#
# Automated Rollback Script
# Rolls back to a previous deployment on health check failures
#
# Usage:
#   ./scripts/deployment/rollback.sh --deployment-id <id>
#   ./scripts/deployment/rollback.sh --previous
#   ./scripts/deployment/rollback.sh --tag <tag>
#

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

DEPLOYMENT_ID=""
ROLLBACK_TO_PREVIOUS=false
ROLLBACK_TAG=""
VERIFY_AFTER_ROLLBACK=true

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --deployment-id)
            DEPLOYMENT_ID="$2"
            shift 2
            ;;
        --previous)
            ROLLBACK_TO_PREVIOUS=true
            shift
            ;;
        --tag)
            ROLLBACK_TAG="$2"
            shift 2
            ;;
        --no-verify)
            VERIFY_AFTER_ROLLBACK=false
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--deployment-id <id>] [--previous] [--tag <tag>] [--no-verify]"
            exit 1
            ;;
    esac
done

# Get previous deployment ID
get_previous_deployment() {
    if command -v python &> /dev/null; then
        python scripts/deployment/track-deployment.py --list | \
            grep -A 5 "Status: success" | \
            head -n 1 | \
            grep -oP "ID: \K[^\s]+" || echo ""
    else
        echo ""
    fi
}

# Rollback to previous deployment
rollback_to_previous() {
    echo -e "${YELLOW}🔄 Rolling back to previous deployment...${NC}"
    
    local previous_id=$(get_previous_deployment)
    if [[ -z "$previous_id" ]]; then
        echo -e "${RED}❌ No previous successful deployment found${NC}"
        echo -e "${YELLOW}⚠️ Stopping all services as fallback${NC}"
        docker compose down
        exit 1
    fi
    
    echo -e "${GREEN}✅ Found previous deployment: $previous_id${NC}"
    rollback_to_tag "$previous_id"
}

# Rollback to specific tag
rollback_to_tag() {
    local tag=$1
    echo -e "${YELLOW}🔄 Rolling back to tag: $tag${NC}"
    
    # Stop current services
    echo "Stopping current services..."
    docker compose down || true
    
    # Pull previous images if tagged
    if [[ -n "$tag" ]]; then
        echo "Pulling previous images..."
        docker compose config --services | while read service; do
            local image_name="homeiq-${service}:${tag}"
            if docker image inspect "$image_name" &> /dev/null; then
                echo "  Found image: $image_name"
                docker tag "$image_name" "homeiq-${service}:latest" || true
            else
                echo -e "${YELLOW}⚠️ Image $image_name not found, using latest${NC}"
            fi
        done
    fi
    
    # Start services with previous configuration
    echo "Starting services with previous configuration..."
    docker compose up -d
    
    # Wait for services to start
    echo "Waiting for services to stabilize..."
    sleep 30
    
    # Verify rollback
    if [[ "$VERIFY_AFTER_ROLLBACK" == "true" ]]; then
        verify_rollback
    fi
}

# Verify rollback success
verify_rollback() {
    echo -e "${YELLOW}🔍 Verifying rollback...${NC}"
    
    if [[ -f "scripts/deployment/health-check.sh" ]]; then
        if bash scripts/deployment/health-check.sh --critical-only; then
            echo -e "${GREEN}✅ Rollback verification passed${NC}"
            
            # Track rollback
            if command -v python &> /dev/null && [[ -n "$DEPLOYMENT_ID" ]]; then
                python scripts/deployment/track-deployment.py \
                    --deployment-id "${DEPLOYMENT_ID}-rollback" \
                    --status "success" \
                    --commit "rollback" \
                    --branch "rollback" \
                    --notes "Rollback from ${DEPLOYMENT_ID}"
            fi
        else
            echo -e "${RED}❌ Rollback verification failed${NC}"
            echo -e "${YELLOW}⚠️ Manual intervention required${NC}"
            exit 1
        fi
    else
        echo -e "${YELLOW}⚠️ Health check script not found, skipping verification${NC}"
        docker compose ps
    fi
}

# Main execution
main() {
    echo "=========================================="
    echo "HomeIQ Deployment Rollback"
    echo "=========================================="
    echo ""
    
    if [[ "$ROLLBACK_TO_PREVIOUS" == "true" ]]; then
        rollback_to_previous
    elif [[ -n "$ROLLBACK_TAG" ]]; then
        rollback_to_tag "$ROLLBACK_TAG"
    elif [[ -n "$DEPLOYMENT_ID" ]]; then
        # Rollback to specific deployment
        rollback_to_tag "$DEPLOYMENT_ID"
    else
        echo -e "${RED}❌ No rollback target specified${NC}"
        echo "Usage: $0 [--deployment-id <id>] [--previous] [--tag <tag>]"
        exit 1
    fi
    
    echo ""
    echo -e "${GREEN}✅ Rollback completed successfully${NC}"
    echo "=========================================="
}

# Run main function
main "$@"

