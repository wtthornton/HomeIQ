# Container Rebuild Checklist

**Date:** November 18, 2025  
**Status:** Ready for Rebuild

## Code Changes Summary

### ✅ Frontend (ai-automation-ui)

**File:** `services/ai-automation-ui/src/components/ask-ai/DebugPanel.tsx`  
**Last Modified:** 11/18/2025 11:22:55 AM  
**Changes:**
- Added "🔄 Execution Flow" tab to Debug Panel
- Implemented Timeline and Flow Diagram views
- Added flow step visualization from user prompt to HA response
- Added expandable step details with request/response information

**File:** `services/ai-automation-ui/src/pages/AskAI.tsx`  
**Last Modified:** Recent  
**Changes:**
- Added `originalQuery`, `extractedEntities`, and `approveResponse` props to DebugPanel
- Implemented logic to store `approve_response` in suggestion object
- Added extraction of original query from message history

### ✅ Backend (ai-automation-service)

**File:** `services/ai-automation-service/src/api/ask_ai_router.py`  
**Last Modified:** 11/18/2025 10:53:10 AM  
**Changes:**
- Fixed SQLite foreign key constraint error
- Added minimal query record creation before clarification session
- Implemented query record update logic for existing records
- Added proper transaction handling with flush() and rollback()

## Rebuild Instructions

### Prerequisites

1. **Start Docker Desktop** (if not already running)
2. **Verify code changes are saved** (all files show recent modification times)

### Rebuild Process

**Option 1: Use the rebuild script (Recommended)**
```powershell
.\scripts\rebuild-ai-automation-containers.ps1
```

**Option 2: Manual rebuild**
```powershell
# Rebuild both services
docker compose build ai-automation-service ai-automation-ui

# Restart containers
docker compose up -d ai-automation-service ai-automation-ui
```

**Option 3: Rebuild and restart in one command**
```powershell
docker compose up -d --build ai-automation-service ai-automation-ui
```

### Verification Steps

1. **Check container status:**
   ```powershell
   docker compose ps ai-automation-service ai-automation-ui
   ```
   Both containers should show "Up" status.

2. **Check container logs:**
   ```powershell
   docker compose logs -f ai-automation-service ai-automation-ui
   ```
   Look for successful startup messages and no errors.

3. **Verify UI changes:**
   - Clear browser cache (Ctrl+Shift+Delete or Ctrl+F5)
   - Navigate to http://localhost:3001/ask-ai
   - Submit a query to generate suggestions
   - Open Debug Panel on a suggestion
   - Verify "🔄 Execution Flow" tab is visible

4. **Verify backend fix:**
   - Submit a query that would trigger clarification
   - Verify no foreign key constraint errors in logs
   - Check that suggestions are generated successfully

## Expected Results

### Frontend
- ✅ Debug Panel shows "🔄 Execution Flow" tab
- ✅ Execution Flow tab displays Timeline and Flow Diagram views
- ✅ Flow steps show complete sequence from user prompt to HA response
- ✅ Steps are expandable with detailed request/response information

### Backend
- ✅ No SQLite foreign key constraint errors
- ✅ Clarification sessions are created successfully
- ✅ Query records are properly saved and updated
- ✅ Suggestions are generated without errors

## Troubleshooting

### If containers fail to build:
1. Check Docker Desktop is running
2. Check for syntax errors in modified files
3. Review build logs: `docker compose build ai-automation-service ai-automation-ui`

### If containers fail to start:
1. Check logs: `docker compose logs ai-automation-service ai-automation-ui`
2. Verify ports 3001 and 8018 are not in use
3. Check Docker network connectivity

### If UI changes don't appear:
1. Clear browser cache completely (Ctrl+Shift+Delete)
2. Hard refresh (Ctrl+F5)
3. Verify container was rebuilt: `docker images | Select-String "ai-automation"`
4. Check container is serving new build: `docker exec ai-automation-ui ls -la /usr/share/nginx/html`

### If backend errors persist:
1. Check service logs: `docker compose logs -f ai-automation-service`
2. Verify database file permissions
3. Check SQLite database integrity

## Related Files

- **Rebuild Script:** `scripts/rebuild-ai-automation-containers.ps1`
- **Docker Compose:** `docker-compose.yml`
- **Frontend Dockerfile:** `services/ai-automation-ui/Dockerfile`
- **Backend Dockerfile:** `services/ai-automation-service/Dockerfile`

---

**Last Updated:** November 18, 2025  
**Next Review:** After container rebuild

