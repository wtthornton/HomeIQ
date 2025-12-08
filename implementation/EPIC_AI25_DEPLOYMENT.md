# Epic AI-25: Deployment Guide

**Epic:** AI-25 - HA Agent UI Enhancements  
**Status:** ✅ Ready for Deployment  
**Date:** January 2025

---

## Pre-Deployment Checklist

### ✅ Completed
- [x] All 3 stories implemented
- [x] QA review complete (all PASSED)
- [x] All "Must Fix" items resolved
- [x] Unit tests passing (14/14)
- [x] Build successful
- [x] No TypeScript errors
- [x] No linting errors

### Build Verification
```bash
cd services/ai-automation-ui
npm run build
# ✅ Build successful
# ✅ dist/ folder created with production assets
```

---

## Deployment Steps

### Option 1: Docker Compose Deployment (Recommended)

The `ai-automation-ui` service is configured in `docker-compose.yml`:

```yaml
ai-automation-ui:
  build:
    context: .
    dockerfile: services/ai-automation-ui/Dockerfile
  container_name: ai-automation-ui
  ports:
    - "3001:3001"
```

**Deploy Steps:**

1. **Rebuild the service:**
   ```bash
   docker-compose build ai-automation-ui
   ```

2. **Restart the service:**
   ```bash
   docker-compose up -d ai-automation-ui
   ```

3. **Verify deployment:**
   ```bash
   docker-compose ps ai-automation-ui
   docker-compose logs ai-automation-ui
   ```

4. **Check health:**
   ```bash
   curl http://localhost:3001
   ```

### Option 2: Production Docker Compose

If using `docker-compose.prod.yml`:

1. **Add service to production compose** (if not already present)
2. **Rebuild and deploy:**
   ```bash
   docker-compose -f docker-compose.prod.yml build ai-automation-ui
   docker-compose -f docker-compose.prod.yml up -d ai-automation-ui
   ```

### Option 3: Manual Deployment

1. **Build the application:**
   ```bash
   cd services/ai-automation-ui
   npm run build
   ```

2. **Serve the dist/ folder:**
   - Use nginx, Apache, or any static file server
   - Point to `services/ai-automation-ui/dist/`
   - Configure reverse proxy if needed

---

## Post-Deployment Verification

### 1. Service Health Check
```bash
# Check if service is running
docker ps | grep ai-automation-ui

# Check logs
docker logs ai-automation-ui

# Check health endpoint (if available)
curl http://localhost:3001/health
```

### 2. UI Functionality Tests

**Test Structured Proposals:**
1. Open HA Agent chat interface
2. Request an automation (e.g., "Turn on lights at sunset")
3. Verify proposal renders with structured sections:
   - ✅ What it does
   - ✅ When it runs
   - ✅ What's affected
   - ✅ How it works

**Test CTA Buttons:**
1. After proposal appears, verify CTA buttons are visible
2. Click "Approve" or "Create" button
3. Verify automation is created successfully

**Test Markdown Rendering:**
1. Send a message with markdown (bold, bullets, code)
2. Verify markdown is properly formatted

**Test Enhancement Button:**
1. Verify enhancement button shows warning when prerequisites missing
2. Verify button enables when prerequisites are present

### 3. Browser Console Check
- Open browser DevTools
- Check for console errors
- Verify no React errors
- Check network requests are successful

### 4. Accessibility Check
- Test with screen reader (if available)
- Verify ARIA labels are present
- Test keyboard navigation

---

## Rollback Plan

If issues are detected:

1. **Stop the new service:**
   ```bash
   docker-compose stop ai-automation-ui
   ```

2. **Revert to previous version:**
   ```bash
   # If using git tags
   git checkout <previous-tag>
   docker-compose build ai-automation-ui
   docker-compose up -d ai-automation-ui
   ```

3. **Or restore from backup:**
   ```bash
   # Restore previous Docker image
   docker load < ai-automation-ui-backup.tar
   docker-compose up -d ai-automation-ui
   ```

---

## Monitoring

### Key Metrics to Monitor

1. **Service Health:**
   - Container status
   - Memory usage
   - CPU usage
   - Response times

2. **User Experience:**
   - Page load times
   - Error rates
   - User interactions (button clicks, proposals viewed)

3. **Errors:**
   - JavaScript errors (Sentry, console)
   - API errors
   - Build/deployment errors

### Logs to Watch

```bash
# Service logs
docker logs -f ai-automation-ui

# Application logs (if configured)
tail -f logs/ai-automation-ui.log
```

---

## Known Issues & Workarounds

### None Currently
All issues resolved in "Must Fix" phase.

---

## Support

If deployment issues occur:

1. Check logs: `docker logs ai-automation-ui`
2. Verify build: `npm run build` in service directory
3. Check dependencies: `npm install` if needed
4. Review this deployment guide
5. Check Epic AI-25 implementation status document

---

## Deployment Summary

**Epic AI-25 Features Deployed:**
- ✅ Structured automation proposal rendering
- ✅ Interactive CTA buttons (Approve, Create, Yes, Go Ahead)
- ✅ Enhanced markdown rendering
- ✅ Enhancement button warning indicators
- ✅ Error boundaries for graceful error handling
- ✅ Full ARIA label support for accessibility
- ✅ Unit tests (14/14 passing)

**Build Status:** ✅ Successful  
**Test Status:** ✅ All Passing  
**Production Ready:** ✅ Yes

---

**Last Updated:** January 2025  
**Deployment Status:** Ready

