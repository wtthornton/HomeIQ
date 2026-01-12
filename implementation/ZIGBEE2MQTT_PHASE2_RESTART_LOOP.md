# Zigbee2MQTT Devices Fix - Phase 2 Restart Loop Issue

**Date:** 2026-01-12  
**Phase:** 2 - Fix device-intelligence-service  
**Status:** ⚠️ Container in Restart Loop

## Issue

After deleting the database file and restarting the container, the `device-intelligence-service` container entered a restart loop. The container status shows "Restarting (3)" indicating it's crashing on startup.

## Actions Taken

1. ✅ Deleted database file as root: `docker exec -u root homeiq-device-intelligence rm -f ./data/device_intelligence.db`
2. ✅ Restarted container: `docker restart homeiq-device-intelligence`
3. ❌ Container entered restart loop: Status shows "Restarting (3)"

## Possible Causes

1. **Database directory missing**: The `./data/` directory might not exist
2. **Permissions issue**: Directory might not have correct permissions for appuser
3. **Startup error**: Service might be failing to initialize database
4. **Configuration issue**: Missing environment variables or configuration

## Next Steps

1. Check container logs to identify the startup error
2. Verify data directory exists and has correct permissions
3. Check if database initialization is failing
4. May need to recreate the data directory with correct permissions

## Investigation Required

- Check service logs for error messages
- Verify data directory structure in container
- Check database initialization code for issues
- Verify service can create database directory if missing
