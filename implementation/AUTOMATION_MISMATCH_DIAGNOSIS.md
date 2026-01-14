# Automation Mismatch Diagnosis

**Date:** January 16, 2026  
**Issue:** HA AutomateAI shows 0 deployed automations, but Home Assistant has 2 automations

## Root Cause

The "Deployed Automations" page in HA AutomateAI (`localhost:3001/deployed`) shows "No Deployed Automations Yet" because the `ai-automation-service-new` service cannot successfully connect to Home Assistant to fetch the automation list.

## Technical Details

### How It Should Work

1. **UI Request:** `Deployed.tsx` calls `api.listDeployedAutomations()`
2. **API Endpoint:** `/api/deploy/automations` (deployment_router.py)
3. **Service Method:** `DeploymentService.list_deployed_automations()`
4. **HA Client:** `HomeAssistantClient.list_automations()`
5. **Home Assistant API:** `GET http://192.168.1.86:8123/api/config/automation/config`

### Why It's Failing

The `list_automations()` method in `ha_client.py` has two failure modes:

```python
async def list_automations(self) -> list[dict[str, Any]]:
    if not self.ha_url or not self.access_token:
        return []  # ❌ Returns empty if not configured
    
    try:
        response = await self.client.get(url)
        # ...
    except httpx.HTTPError as e:
        logger.error(f"Failed to list automations: {e}")
        return []  # ❌ Returns empty on any error
```

**Possible causes:**
1. **Missing Token:** `HOME_ASSISTANT_TOKEN` not set in `.env` file
2. **Connection Failure:** Network issue or Home Assistant unreachable from container
3. **Authentication Failure:** Invalid or expired token
4. **API Endpoint Issue:** Wrong endpoint format or Home Assistant version incompatibility

## Configuration Check

### Docker Compose Configuration

```yaml
ai-automation-service-new:
  environment:
    - HA_URL=${HOME_ASSISTANT_URL:-http://192.168.1.86:8123}
    - HA_TOKEN=${HOME_ASSISTANT_TOKEN:-}  # ⚠️ Empty if not set
```

### Expected Environment Variables

The service expects these in `.env`:
```bash
HOME_ASSISTANT_URL=http://192.168.1.86:8123
HOME_ASSISTANT_TOKEN=your-long-lived-access-token-here
```

## Diagnosis Steps

### 1. Check Service Logs

```powershell
docker logs ai-automation-service-new --tail 50
```

Look for:
- `"Home Assistant URL or token not configured"` (missing config)
- `"Failed to list automations"` (connection/API error)
- `"Home Assistant client initialized with url=..."` (config loaded)

### 2. Test API Endpoint Directly

```powershell
# Test if service can reach Home Assistant
$token = "YOUR_HA_TOKEN"
$response = Invoke-RestMethod -Uri "http://192.168.1.86:8123/api/config/automation/config" -Headers @{Authorization="Bearer $token"}
$response | ConvertTo-Json
```

### 3. Check Environment Variables in Container

```powershell
docker exec ai-automation-service-new env | Select-String "HA_"
```

Should show:
```
HA_URL=http://192.168.1.86:8123
HA_TOKEN=eyJ0eXAiOiJKV1QiLCJhbGc...
```

### 4. Test Service Health Endpoint

```powershell
Invoke-RestMethod -Uri "http://localhost:8036/health"
```

## Solutions

### Solution 1: Add Home Assistant Token to .env

1. Get a long-lived access token from Home Assistant:
   - Go to `http://192.168.1.86:8123/profile`
   - Scroll to "Long-Lived Access Tokens"
   - Create a new token
   - Copy the token

2. Add to `.env` file:
   ```bash
   HOME_ASSISTANT_URL=http://192.168.1.86:8123
   HOME_ASSISTANT_TOKEN=eyJ0eXAiOiJKV1QiLCJhbGc...
   ```

3. Restart service:
   ```powershell
   docker-compose restart ai-automation-service-new
   ```

### Solution 2: Fix Environment Variable Mapping

The docker-compose uses `HA_URL` and `HA_TOKEN`, but the service config expects `ha_url` and `ha_token`. Pydantic should handle this, but verify:

**Option A:** Update docker-compose to match config expectations:
```yaml
environment:
  - ha_url=${HOME_ASSISTANT_URL:-http://192.168.1.86:8123}
  - ha_token=${HOME_ASSISTANT_TOKEN:-}
```

**Option B:** Update config.py to explicitly read from environment:
```python
ha_url: str | None = Field(default=None, env="HA_URL")
ha_token: str | None = Field(default=None, env="HA_TOKEN")
```

### Solution 3: Improve Error Handling

Update `ha_client.py` to provide better error messages:

```python
async def list_automations(self) -> list[dict[str, Any]]:
    if not self.ha_url or not self.access_token:
        logger.warning("Home Assistant not configured - cannot list automations")
        return []
    
    url = f"{self.ha_url}/api/config/automation/config"
    
    try:
        response = await self.client.get(url)
        response.raise_for_status()
        data = response.json()
        logger.info(f"Successfully fetched {len(data)} automations from Home Assistant")
        return data if isinstance(data, list) else []
    except httpx.HTTPStatusError as e:
        logger.error(f"Home Assistant API error: {e.response.status_code} - {e.response.text}")
        return []
    except httpx.HTTPError as e:
        logger.error(f"Failed to connect to Home Assistant: {e}")
        return []
```

## Expected Behavior After Fix

Once configured correctly:
1. **Deployed page** should show all 2 automations from Home Assistant
2. **Automations list** should include:
   - "Office motion lights on, off after 5 minutes no motion"
   - "Turn on Office Lights on Presence"
3. **Status** should show "enabled" for both
4. **Last triggered** should show actual timestamps

## Notes

- The automations in Home Assistant were created **directly in Home Assistant** (not through HA AutomateAI)
- HA AutomateAI's "Deployed" page should show **ALL** automations from Home Assistant, not just ones deployed through HA AutomateAI
- This is a **read-only view** - it doesn't track which automations were created by HA AutomateAI vs. manually

## Related Files

- `services/ai-automation-service-new/src/clients/ha_client.py` - HA API client
- `services/ai-automation-service-new/src/services/deployment_service.py` - Deployment service
- `services/ai-automation-service-new/src/api/deployment_router.py` - API endpoints
- `services/ai-automation-ui/src/pages/Deployed.tsx` - UI component
- `docker-compose.yml` - Service configuration
