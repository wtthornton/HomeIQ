# UI Automation Display Debug

**Issue:** UI shows "No Deployed Automations Yet" even though API returns 2 automations

## Verification Results

✅ **Backend API Working:**
- Direct API call: `http://localhost:8036/api/deploy/automations` → Returns 2 automations
- Through nginx: `http://localhost:3001/api/deploy/automations` → Returns 2 automations
- Response format: `{"automations": [...]}` ✅ Correct

✅ **Frontend Code:**
- `Deployed.tsx` line 38: `const result = await api.listDeployedAutomations();`
- Line 40: `setAutomations(result.automations || result.data || []);`
- Code looks correct

## Possible Causes

1. **Browser Cache** - Most likely
   - Old JavaScript bundle cached
   - Solution: Hard refresh (Ctrl+Shift+R or Ctrl+F5)

2. **API Authentication**
   - Frontend requires `VITE_API_KEY` environment variable
   - Check browser console for authentication errors

3. **CORS Issues**
   - Check browser console for CORS errors

4. **Response Parsing**
   - Check if response is being parsed correctly
   - Check browser Network tab for actual response

## Debugging Steps

### Step 1: Check Browser Console
1. Open browser DevTools (F12)
2. Go to Console tab
3. Look for errors when clicking "Refresh List"
4. Check for:
   - `Failed to load deployed automations`
   - `VITE_API_KEY environment variable is not set`
   - CORS errors
   - Network errors

### Step 2: Check Network Tab
1. Open browser DevTools (F12)
2. Go to Network tab
3. Click "Refresh List" button
4. Find the request to `/api/deploy/automations`
5. Check:
   - Request URL (should be `http://localhost:3001/api/deploy/automations`)
   - Response status (should be 200)
   - Response body (should contain `{"automations": [...]}`)
   - Request headers (check for `X-HomeIQ-API-Key`)

### Step 3: Hard Refresh
1. Press `Ctrl+Shift+R` (Windows/Linux) or `Cmd+Shift+R` (Mac)
2. Or press `Ctrl+F5`
3. This clears browser cache and reloads JavaScript

### Step 4: Check Service Logs
```powershell
docker logs ai-automation-service-new --tail 50 | Select-String -Pattern "deploy/automations|Found.*automation"
```

## Quick Fixes

### Fix 1: Hard Refresh Browser
**Most likely solution:**
- Press `Ctrl+Shift+R` or `Ctrl+F5` in the browser
- This forces a reload of all JavaScript files

### Fix 2: Clear Browser Cache
1. Open browser DevTools (F12)
2. Right-click the refresh button
3. Select "Empty Cache and Hard Reload"

### Fix 3: Check API Key
If the frontend requires an API key:
1. Check browser console for `VITE_API_KEY` errors
2. If needed, set environment variable in `.env`:
   ```bash
   VITE_API_KEY=your-api-key-here
   ```
3. Rebuild UI if needed:
   ```powershell
   docker-compose build ai-automation-ui
   docker-compose up -d ai-automation-ui
   ```

### Fix 4: Rebuild UI (if code changed)
If frontend code was modified:
```powershell
docker-compose build ai-automation-ui
docker-compose up -d ai-automation-ui
```

## Expected Behavior

After fix:
1. Navigate to `http://localhost:3001/deployed`
2. Click "Refresh List"
3. Should see 2 automations:
   - "Office motion lights on, off after 5 minutes no motion"
   - "Turn on Office Lights on Presence"

## Next Steps

1. **Try hard refresh first** (Ctrl+Shift+R)
2. **Check browser console** for errors
3. **Check Network tab** to see actual API response
4. **Report findings** if issue persists
