# Redeploy AI Automation Services - Cache Clearing & Restart Instructions

## ✅ Cache Clearing Complete

The following caches have been cleared:
- ✅ Vite cache (`node_modules/.vite`)
- ✅ Frontend build output (`dist/`)
- ✅ Python `__pycache__` directories
- ✅ Frontend dependencies reinstalled

## 🔄 Restart Instructions

### Backend Service (AI Automation Service)

**Port:** 8018

1. **Stop the current service:**
   - If running in a terminal, press `Ctrl+C`
   - Or find and kill the process:
     ```powershell
     Get-Process python | Where-Object {$_.CommandLine -like "*uvicorn*ai-automation*"} | Stop-Process
     ```

2. **Restart the service:**
   ```powershell
   cd services\ai-automation-service
   python -m uvicorn src.main:app --host 0.0.0.0 --port 8018 --reload
   ```

### Frontend Service (AI Automation UI)

**Port:** 3001

1. **Rebuild and restart the Docker container:**
   ```powershell
   docker compose build ai-automation-ui
   docker compose up -d ai-automation-ui
   ```

2. **Or restart the existing container:**
   ```powershell
   docker compose restart ai-automation-ui
   ```

## 🌐 Browser Cache Clearing

**IMPORTANT:** After restarting services, clear your browser cache:

### Option 1: Hard Refresh
- **Windows/Linux:** Press `Ctrl + F5` or `Ctrl + Shift + R`
- **Mac:** Press `Cmd + Shift + R`

### Option 2: Clear Cache via Settings
1. Press `Ctrl + Shift + Delete` (Windows/Linux) or `Cmd + Shift + Delete` (Mac)
2. Select "Cached images and files"
3. Click "Clear data"

### Option 3: DevTools (Recommended for Development)
1. Open DevTools (`F12`)
2. Go to **Network** tab
3. Check **"Disable cache"** checkbox
4. Keep DevTools open while testing

## ✅ Verify Changes Are Deployed

After restarting and clearing cache:

1. **Navigate to:** http://localhost:3001/ask-ai
2. **Check for:**
   - ✅ Confidence improvement indicators (✨ +X% badge)
   - ✅ Confidence summary in message content
   - ✅ Correct friendly names from Home Assistant (not user query terms)
   - ✅ Confidence delta display in ClarificationDialog

3. **Test the flow:**
   - Ask a question that triggers clarification
   - Answer the questions
   - Verify confidence improvements are shown
   - Check that device names match Home Assistant friendly names

## 📝 Recent Changes Deployed

### Backend Changes:
- ✅ `ask_ai_router.py`: Enhanced `entity_id_annotations` to include actual friendly names from HA Entity Registry

### Frontend Changes:
- ✅ `AskAI.tsx`: 
  - Added confidence improvement fields to ChatMessage interface
  - Enhanced message content with confidence improvement info
  - Prioritized `entity_id_annotations` for friendly names
  - Pass confidence improvement props to suggestion cards
- ✅ `ConversationalSuggestionCard.tsx`: 
  - Added confidence improvement badge display
  - Shows ✨ +X% indicator when confidence improves
- ✅ `api.ts`: 
  - Added confidence improvement fields to API type definitions
- ✅ `ClarificationDialog.tsx`: 
  - Already had confidence improvement display (should work now with proper data)

## 🐛 Troubleshooting

If changes still don't appear:

1. **Check service logs:**
   - Backend: `docker compose logs -f ai-automation-service`
   - Frontend: `docker compose logs -f ai-automation-ui`

2. **Verify files are saved:**
   ```powershell
   # Check file modification times
   Get-ChildItem services\ai-automation-ui\src\pages\AskAI.tsx | Select-Object LastWriteTime
   Get-ChildItem services\ai-automation-service\src\api\ask_ai_router.py | Select-Object LastWriteTime
   ```

3. **Force browser reload:**
   - Close all browser tabs with localhost:3001
   - Clear browser cache completely
   - Restart browser
   - Open fresh tab to http://localhost:3001/ask-ai

4. **Verify Docker container is running:**
   - Check status: `docker compose ps`
   - If container is not running, rebuild: `docker compose build ai-automation-ui && docker compose up -d ai-automation-ui`

## 📞 Quick Restart Commands

**Restart both services with Docker (run from project root):**

```powershell
# Restart both services
docker compose restart ai-automation-service ai-automation-ui

# Or rebuild and restart
docker compose build ai-automation-service ai-automation-ui
docker compose up -d ai-automation-service ai-automation-ui
```

