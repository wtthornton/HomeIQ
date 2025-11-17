# Discovery Status and Next Steps

**Date:** November 17, 2025  
**Status:** ⚠️ Discovery Running, Awaiting Completion

## Current Status

### Discovery Process
- ✅ **WebSocket Service**: Restarted successfully
- ✅ **Bulk Upsert Requests**: Observed in data-api logs
  - `POST /internal/devices/bulk_upsert HTTP/1.1" 200 OK`
  - `POST /internal/entities/bulk_upsert HTTP/1.1" 200 OK`
- ⚠️ **WebSocket Concurrency Error**: Discovery may have encountered issues due to concurrent WebSocket calls

### What Should Happen

When discovery completes successfully, you should see logs like:
```
🔌 DISCOVERING ENTITIES (message_id: XXXX)
✅ Discovered X entities
✅ Stored X entities to SQLite
✅ STORAGE COMPLETE
```

## Verification Steps

### 1. Check Discovery Logs
```bash
docker logs homeiq-websocket | grep -i "DISCOVERING\|DISCOVERED\|Stored\|COMPLETE"
```

### 2. Verify Database Population
After discovery completes, check if friendly names are populated:
```sql
SELECT entity_id, name, name_by_user, original_name, friendly_name 
FROM entities 
WHERE entity_id LIKE 'light.hue%'
LIMIT 10;
```

Expected results should show:
- `friendly_name`: "LR Back Left Ceiling", "LR Back Right Ceiling", etc.
- `name`: Entity Registry name
- `name_by_user`: User-customized name (if set)
- `original_name`: Original name before customization

### 3. Test AI Automation Service
After friendly names are populated, test the AI automation service:
- Create a new automation query
- Verify that device names show as "LR Back Left Ceiling" instead of "Hue Color Downlight 15"

## Troubleshooting

### If Discovery Didn't Complete

1. **Check WebSocket Connection**:
   ```bash
   docker logs homeiq-websocket | grep -i "connection\|websocket\|connected"
   ```

2. **Manual Discovery Trigger**:
   ```bash
   curl -X POST http://localhost:8001/api/v1/discovery/trigger
   ```
   Note: May encounter WebSocket concurrency errors if WebSocket is already in use

3. **Wait for Automatic Discovery**:
   - Discovery runs automatically when WebSocket connects
   - Also runs when device/entity registry events are received
   - Cache expires after 30 minutes, triggering refresh

### If Friendly Names Are Still NULL

1. **Check bulk_upsert_entities Code**:
   - Verify it extracts `name`, `name_by_user`, `original_name` from Entity Registry
   - Verify it computes `friendly_name` correctly (priority: `name_by_user` > `name` > `original_name`)

2. **Check Entity Registry Data**:
   - Verify Home Assistant Entity Registry contains the expected name fields
   - Check if entities have `name_by_user` set in HA

3. **Re-run Discovery**:
   - Restart websocket-ingestion service
   - Or wait for automatic discovery on next connection

## Expected Timeline

- **Immediate**: Discovery should run within 1-2 minutes of WebSocket connection
- **After Discovery**: Friendly names should be available in database
- **AI Service**: Will use friendly names on next query (may need to clear cache)

## Next Actions

1. ✅ Restart websocket-ingestion (completed)
2. ⏳ Wait for discovery to complete (in progress)
3. ⏳ Verify friendly names in database (pending)
4. ⏳ Test AI automation service (pending)

---

**Status:** Monitoring discovery completion

