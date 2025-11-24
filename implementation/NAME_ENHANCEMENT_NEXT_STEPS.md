# Device Name Enhancement System - Next Steps

**Date:** January 2025  
**Status:** Implementation Complete, Ready for Configuration

---

## ✅ Implementation Complete

All components of the Device Name Enhancement System have been implemented:

1. ✅ Database models (`NameSuggestion`, `NamePreference`)
2. ✅ Pattern-based name generator
3. ✅ Uniqueness validator with in-memory cache
4. ✅ AI name suggester (GPT-4o-mini with caching)
5. ✅ Local LLM support (Ollama)
6. ✅ Preference learner
7. ✅ Batch processor with APScheduler
8. ✅ REST API endpoints
9. ✅ React UI components

---

## 🚀 Next Steps to Enable

### Step 1: Database Tables (Automatic)

The database tables are **automatically created** when the service starts via SQLAlchemy's `Base.metadata.create_all()`. No migration needed!

**Just restart the device-intelligence-service** and the new tables will be created:
- `name_suggestions`
- `name_preferences`

### Step 2: Enable Name Enhancement

Add these environment variables to your `.env` file or Docker Compose:

```bash
# Enable automatic name suggestion generation during device discovery
AUTO_GENERATE_NAME_SUGGESTIONS=true

# Optional: Enable AI name generation (requires OpenAI API key)
OPENAI_API_KEY=sk-...  # Your OpenAI API key

# Optional: Enable local LLM (requires Ollama running)
ENABLE_LOCAL_LLM=false  # Set to true if you have Ollama running
```

**For Docker Compose**, add to `services.device-intelligence-service.environment`:

```yaml
services:
  device-intelligence-service:
    environment:
      AUTO_GENERATE_NAME_SUGGESTIONS: "true"
      OPENAI_API_KEY: "${OPENAI_API_KEY:-}"  # Optional
      ENABLE_LOCAL_LLM: "false"  # Optional
```

### Step 3: Add UI to Navigation

The UI components are ready but need to be added to routing. Add to `services/ai-automation-ui/src/App.tsx`:

```typescript
import { NameEnhancementDashboard } from './components/name-enhancement';

// In your routes:
<Route path="/name-enhancement" element={<NameEnhancementDashboard />} />
```

And add to `services/ai-automation-ui/src/components/Navigation.tsx`:

```typescript
{ path: '/name-enhancement', label: '✏️ Names', icon: '✏️' },
```

### Step 4: Configure API Base URL (UI)

The UI needs to know where the device-intelligence-service is running. Add to your `.env` or environment:

```bash
# For development (if running locally)
VITE_DEVICE_INTELLIGENCE_API=http://localhost:8019

# For production (via nginx proxy)
# VITE_DEVICE_INTELLIGENCE_API=/api/device-intelligence
```

**Note:** If using nginx proxy, you may need to add a proxy rule:

```nginx
location /api/name-enhancement {
    proxy_pass http://device-intelligence-service:8019/api/name-enhancement;
}
```

### Step 5: Restart Services

```bash
# Restart device-intelligence-service to create tables and enable features
docker compose restart device-intelligence-service

# Or if running locally
cd services/device-intelligence-service
python -m src.main
```

### Step 6: Test the System

1. **Check API is working:**
   ```bash
   curl http://localhost:8019/api/name-enhancement/status
   ```

2. **Trigger batch enhancement:**
   ```bash
   curl -X POST http://localhost:8019/api/name-enhancement/batch-enhance \
     -H "Content-Type: application/json" \
     -d '{"device_ids": null, "use_ai": false, "auto_accept_high_confidence": false}'
   ```

3. **View suggestions:**
   ```bash
   curl http://localhost:8019/api/name-enhancement/devices/pending
   ```

4. **Access UI:**
   Navigate to `/name-enhancement` in your browser (after adding to routing)

---

## 📋 Configuration Options

### Pattern-Based Only (No AI, Free)

```bash
AUTO_GENERATE_NAME_SUGGESTIONS=true
# Don't set OPENAI_API_KEY or ENABLE_LOCAL_LLM
```

**Result:** Fast, free name generation using patterns (90% of cases)

### With AI Enhancement (Cost-Optimized)

```bash
AUTO_GENERATE_NAME_SUGGESTIONS=true
OPENAI_API_KEY=sk-...
# Uses GPT-4o-mini with prompt caching (90% discount)
```

**Cost:** ~$0.01-0.05 per 100 devices (with caching)

### With Local LLM (Privacy-First)

```bash
AUTO_GENERATE_NAME_SUGGESTIONS=true
ENABLE_LOCAL_LLM=true
# Requires Ollama running on http://ollama:11434
```

**Cost:** $0 (local processing)  
**Performance:** 3-5s per device (slower but private)

---

## 🔍 Monitoring

### Check Status

```bash
# Get enhancement statistics
curl http://localhost:8019/api/name-enhancement/status

# Response:
{
  "total_suggestions": 42,
  "by_status": {
    "pending": 35,
    "accepted": 5,
    "rejected": 2
  },
  "by_confidence": {
    "high": 20,
    "medium": 15,
    "low": 7
  }
}
```

### View Logs

```bash
# Docker
docker compose logs -f device-intelligence-service | grep -i "name"

# Local
# Check console output for name enhancement logs
```

---

## 🐛 Troubleshooting

### Tables Not Created

**Issue:** `name_suggestions` table doesn't exist

**Solution:**
1. Check service logs for errors
2. Verify database file is writable
3. Restart service (tables auto-create on startup)

### No Suggestions Generated

**Issue:** Suggestions not appearing

**Check:**
1. `AUTO_GENERATE_NAME_SUGGESTIONS=true` is set
2. Service restarted after setting env var
3. Devices exist in database (check `/api/discovery/status`)
4. Check logs for errors: `grep -i "name.*suggestion" logs`

### AI Not Working

**Issue:** AI suggestions not generating

**Check:**
1. `OPENAI_API_KEY` is set and valid
2. API key has credits/quota
3. Check logs for API errors
4. Try pattern-based first (set `use_ai: false`)

### UI Not Loading

**Issue:** Dashboard shows no data

**Check:**
1. Route is added to `App.tsx`
2. `VITE_DEVICE_INTELLIGENCE_API` is set correctly
3. CORS is configured (if cross-origin)
4. Check browser console for errors

---

## 📚 API Documentation

### Get Suggestions for Device

```bash
GET /api/name-enhancement/devices/{device_id}/suggestions
```

### Accept Suggestion

```bash
POST /api/name-enhancement/devices/{device_id}/accept
{
  "suggested_name": "Office Back Left Light",
  "sync_to_ha": false
}
```

### Reject Suggestion

```bash
POST /api/name-enhancement/devices/{device_id}/reject?suggested_name=...
```

### Batch Enhance

```bash
POST /api/name-enhancement/batch-enhance
{
  "device_ids": null,  // null = all devices
  "use_ai": false,
  "auto_accept_high_confidence": false
}
```

### Get Pending Suggestions (Bulk)

```bash
GET /api/name-enhancement/devices/pending?limit=50
```

---

## 🎯 Expected Behavior

### Automatic Generation

- **When:** During device discovery (if `AUTO_GENERATE_NAME_SUGGESTIONS=true`)
- **Frequency:** Every time a new device is discovered
- **Method:** Pattern-based (fast, no AI cost)
- **Storage:** Suggestions stored in `name_suggestions` table with status="pending"

### Batch Processing

- **Schedule:** Daily at 4 AM (configurable)
- **Processes:** Devices without `name_by_user` or with low-quality names
- **Method:** Pattern-based first, AI for complex cases (if enabled)
- **Result:** New suggestions stored for user review

### User Review

- **UI:** Navigate to `/name-enhancement` dashboard
- **Actions:** Accept, reject, or ignore suggestions
- **Learning:** Accepted names train the preference learner
- **Update:** Device `name_by_user` field is updated

---

## ✅ Verification Checklist

- [ ] Environment variables set (`AUTO_GENERATE_NAME_SUGGESTIONS=true`)
- [ ] Service restarted
- [ ] Database tables created (check logs)
- [ ] API endpoints accessible (`/api/name-enhancement/status`)
- [ ] UI route added to `App.tsx`
- [ ] Navigation link added
- [ ] Test batch enhancement works
- [ ] Test accept/reject works
- [ ] Check suggestions appear in UI

---

## 📖 Additional Resources

- **Design Document:** `cursor-plan://8a8dd5e9-99fe-4506-bddb-9ccf178c5d46/Device Name Enhancement System.plan.md`
- **API Endpoints:** `services/device-intelligence-service/src/api/name_enhancement_router.py`
- **UI Components:** `services/ai-automation-ui/src/components/name-enhancement/`

---

**Ready to use!** Once configured, the system will automatically generate name suggestions during device discovery and provide a UI for review.

