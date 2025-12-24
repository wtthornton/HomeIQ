# Deployment Verification Checklist

## Pre-Deployment Verification

### Code Quality Checks
- [ ] All TypeScript types are properly defined and exported
- [ ] No missing imports or undefined references
- [ ] API endpoint definitions match between frontend and backend
- [ ] Environment variables are correctly configured
- [ ] All unit tests pass
- [ ] Integration tests pass

### Build Verification
- [ ] Frontend builds without errors
- [ ] Backend builds without errors
- [ ] Docker images build successfully
- [ ] All services start without errors

## Post-Deployment Verification

### Service Health Checks
- [ ] All Docker containers are running
- [ ] All services report healthy status
- [ ] No critical errors in service logs
- [ ] Database connections are working
- [ ] Inter-service communication is working

### API Endpoint Verification
- [ ] `/health` endpoint returns healthy status
- [ ] `/api/health` endpoint returns healthy status
- [ ] `/api/v1/health` endpoint returns dependency information
- [ ] `/api/v1/stats` endpoint returns statistics
- [ ] `/api/v1/alerts` endpoint returns alerts
- [ ] All endpoints return expected data structures

### Frontend Functionality Verification
- [ ] Dashboard loads without errors
- [ ] No JavaScript errors in browser console
- [ ] API calls are successful (check Network tab)
- [ ] Status calculation works correctly
- [ ] All dashboard components render properly
- [ ] Real-time updates are working

### Dashboard-Specific Checks
- [ ] System status shows correct health (not "DEGRADED PERFORMANCE")
- [ ] Core system components show healthy status
- [ ] Dependency health information is displayed
- [ ] Statistics are being fetched and displayed
- [ ] Alerts are being fetched and displayed
- [ ] Navigation between tabs works
- [ ] All dashboard features are functional

## Automated Verification Scripts

### Health Check Script
```bash
#!/bin/bash
# verify-deployment.sh

echo "Starting deployment verification..."

# Check service health
echo "Checking service health..."
curl -f http://localhost:8003/health || exit 1
curl -f http://localhost:8003/api/health || exit 1
curl -f http://localhost:8003/api/v1/health || exit 1
curl -f http://localhost:8003/api/v1/stats || exit 1

# Check dashboard
echo "Checking dashboard..."
curl -f http://localhost:3000 || exit 1

echo "Deployment verification completed successfully!"
```

### API Endpoint Test Script
```bash
#!/bin/bash
# test-api-endpoints.sh

echo "Testing API endpoints..."

# Test health endpoints
echo "Testing health endpoints..."
curl -s http://localhost:8003/health | jq '.status' | grep -q "healthy" || exit 1
curl -s http://localhost:8003/api/health | jq '.status' | grep -q "healthy" || exit 1
curl -s http://localhost:8003/api/v1/health | jq '.status' | grep -q "healthy" || exit 1

# Test stats endpoint
echo "Testing stats endpoint..."
curl -s http://localhost:8003/api/v1/stats | jq '.metrics' | grep -q "admin-api" || exit 1

# Test alerts endpoint
echo "Testing alerts endpoint..."
curl -s http://localhost:8003/api/v1/alerts | jq '.' || exit 1

echo "All API endpoints are working correctly!"
```

## Troubleshooting Guide

### Common Issues and Solutions

#### Dashboard Shows "DEGRADED PERFORMANCE"
1. Check if all API endpoints are accessible
2. Verify frontend is calling correct endpoints
3. Check browser console for JavaScript errors
4. Verify API response data structure matches frontend expectations

#### API Endpoints Return 404
1. Check if services are running
2. Verify endpoint URLs are correct
3. Check docker-compose configuration
4. Verify service routing

#### Frontend Build Errors
1. Check for missing type definitions
2. Verify all imports are correct
3. Check TypeScript configuration
4. Verify environment variables

#### Backend Health Check Failures
1. Check service logs for errors
2. Verify database connections
3. Check inter-service communication
4. Verify configuration files

## Monitoring and Alerting

### Key Metrics to Monitor
- Service health status
- API endpoint response times
- Frontend error rates
- Dashboard load times
- API call success rates

### Alert Conditions
- Any service reports unhealthy status
- API endpoints return 5xx errors
- Frontend shows JavaScript errors
- Dashboard fails to load
- API response times exceed thresholds

## Rollback Procedures

### Emergency Rollback
1. Stop all services
2. Revert to previous working version
3. Restart services
4. Verify functionality
5. Document rollback reason

### Gradual Rollback
1. Identify failing component
2. Revert specific component
3. Test functionality
4. Continue with other components if needed

## Post-Incident Review

### Documentation Updates
- [ ] Update deployment procedures
- [ ] Add new verification steps
- [ ] Update troubleshooting guides
- [ ] Document lessons learned

### Process Improvements
- [ ] Identify process gaps
- [ ] Implement new checks
- [ ] Update automation scripts
- [ ] Train team on new procedures
