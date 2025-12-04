# YAML Validation Consolidation - Deployment Guide

**Date:** January 2025  
**Status:** ✅ **READY FOR DEPLOYMENT**

---

## 🚀 **Quick Deployment**

### **Option 1: Use Deployment Script (Recommended)**

**Linux/Mac:**
```bash
./scripts/deploy-yaml-validation-changes.sh
```

**Windows PowerShell:**
```powershell
.\scripts\deploy-yaml-validation-changes.ps1
```

### **Option 2: Manual Deployment**

Run these commands in order:

```bash
# 1. Stop affected services
docker-compose stop ai-automation-service ha-ai-agent-service ai-automation-ui

# 2. Rebuild services
docker-compose build --no-cache ai-automation-service
docker-compose build --no-cache ha-ai-agent-service
docker-compose build --no-cache ai-automation-ui

# 3. Start services
docker-compose up -d ai-automation-service ha-ai-agent-service ai-automation-ui

# 4. Check status
docker-compose ps | grep -E "(ai-automation-service|ha-ai-agent-service|ai-automation-ui)"
```

---

## 📋 **Services to Deploy**

### **1. ai-automation-service**
- **Port:** 8024 (mapped from 8018)
- **Changes:**
  - New validation router (`src/api/yaml_validation_router.py`)
  - Updated main.py (router registration)
  - New test file

**Note:** Source code is mounted as volume, but new router file needs to be in image.

### **2. ha-ai-agent-service**
- **Port:** 8030
- **Changes:**
  - New AI automation client (`src/clients/ai_automation_client.py`)
  - Updated tools (`src/tools/ha_tools.py`)
  - Updated service (`src/services/tool_service.py`)
  - Updated config (`src/config.py`)
  - Updated main.py
  - New test file
  - Updated test file

**Note:** Source code is NOT mounted, so rebuild is required.

### **3. ai-automation-ui**
- **Port:** 3001 (mapped from 80)
- **Changes:**
  - Updated API service (`src/services/api.ts`)
  - Updated Deployed page (`src/pages/Deployed.tsx`)

**Note:** UI is built at build time, so rebuild is required.

---

## 🔍 **Verification**

After deployment, verify the services are working:

### **1. Check Service Health**

```bash
# Check all services
docker-compose ps

# Check specific service logs
docker-compose logs -f ai-automation-service
docker-compose logs -f ha-ai-agent-service
docker-compose logs -f ai-automation-ui
```

### **2. Test Validation Endpoint**

```bash
# Test the new validation endpoint
curl -X POST http://localhost:8024/api/v1/yaml/validate \
  -H "Content-Type: application/json" \
  -d '{
    "yaml": "alias: Test\ntrigger:\n  - platform: state\n    entity_id: light.test\naction:\n  - service: light.turn_on\n    target:\n      entity_id: light.test",
    "validate_entities": false,
    "validate_safety": false
  }'
```

Expected response:
```json
{
  "valid": true,
  "errors": [],
  "warnings": [],
  "stages": {
    "syntax": true,
    "structure": true
  },
  "summary": "✅ All validation checks passed"
}
```

### **3. Test HA AI Agent Service**

```bash
# Check health endpoint
curl http://localhost:8030/health
```

### **4. Test UI**

Open in browser:
- **AI Automation UI:** http://localhost:3001
- Navigate to "Deployed" tab
- Try the "Self-Correct" button on a deployed automation

---

## 🔧 **Troubleshooting**

### **Service Won't Start**

1. **Check logs:**
   ```bash
   docker-compose logs ai-automation-service
   docker-compose logs ha-ai-agent-service
   docker-compose logs ai-automation-ui
   ```

2. **Check dependencies:**
   - Ensure `data-api` is running (required by both services)
   - Ensure `device-intelligence-service` is running (required by ha-ai-agent-service)

3. **Check environment variables:**
   - Verify `.env` file exists and has required values
   - Check `infrastructure/env.ai-automation` for ai-automation-service

### **Validation Endpoint Not Found**

If you get 404 errors:
- Verify the router is registered in `main.py`
- Check that the service rebuilt successfully
- Look for import errors in logs

### **Client Connection Errors**

If ha-ai-agent-service can't connect to ai-automation-service:
- Verify both services are on the same Docker network (`homeiq-network`)
- Check that `AI_AUTOMATION_SERVICE_URL` is set correctly (default: `http://ai-automation-service:8000`)
- Note: ai-automation-service port is 8018 internally, but mapped to 8024 externally

### **UI Not Loading**

1. **Check build logs:**
   ```bash
   docker-compose logs ai-automation-ui | grep -i error
   ```

2. **Verify port mapping:**
   - UI should be accessible on port 3001
   - Check for port conflicts

3. **Clear browser cache:**
   - Hard refresh (Ctrl+Shift+R or Cmd+Shift+R)

---

## 📊 **Deployment Checklist**

- [ ] Backup current containers (optional)
- [ ] Stop affected services
- [ ] Rebuild ai-automation-service
- [ ] Rebuild ha-ai-agent-service
- [ ] Rebuild ai-automation-ui
- [ ] Start all services
- [ ] Verify service health
- [ ] Test validation endpoint
- [ ] Test HA AI Agent Service
- [ ] Test UI functionality
- [ ] Check logs for errors

---

## 🔄 **Rollback Procedure**

If something goes wrong, you can rollback:

```bash
# Stop new containers
docker-compose stop ai-automation-service ha-ai-agent-service ai-automation-ui

# Remove new images (optional)
docker rmi homeiq-ai-automation-service homeiq-ha-ai-agent-service homeiq-ai-automation-ui

# Restore from git (if needed)
git checkout services/ai-automation-service/
git checkout services/ha-ai-agent-service/
git checkout services/ai-automation-ui/

# Rebuild from previous version
docker-compose build ai-automation-service ha-ai-agent-service ai-automation-ui
docker-compose up -d ai-automation-service ha-ai-agent-service ai-automation-ui
```

---

## 📝 **Post-Deployment Notes**

1. **Monitor logs** for the first few minutes after deployment
2. **Test the validation endpoint** with various YAML inputs
3. **Verify self-correct button** works in the UI
4. **Check for any error patterns** in logs

---

## 🎯 **Expected Behavior**

### **After Deployment:**

1. **ai-automation-service** should have:
   - New endpoint: `/api/v1/yaml/validate`
   - Router registered and accessible
   - All existing endpoints still working

2. **ha-ai-agent-service** should:
   - Use consolidated validation when creating automations
   - Fall back gracefully if AI automation service unavailable
   - Log validation calls

3. **ai-automation-ui** should:
   - Show validation step in self-correct flow
   - Display validation results
   - Use fixed YAML when available

---

**Deployment Date:** January 2025  
**Status:** ✅ **READY**

