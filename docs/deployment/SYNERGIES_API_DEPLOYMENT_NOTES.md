# Synergies API Deployment Notes

**Date:** December 29, 2025  
**Status:** ✅ Fixed and Verified  
**Issue:** Route matching order causing 404 errors

## Deployment Requirements

### Critical: Full Container Restart

**After modifying `services/ai-pattern-service/src/api/synergy_router.py`:**

**❌ DO NOT USE:**
```bash
docker compose restart ai-pattern-service
```

**✅ USE INSTEAD:**
```bash
docker compose down ai-pattern-service
docker compose up -d ai-pattern-service
```

**Why:** FastAPI route registration order is determined at container startup. A simple `restart` may not apply route order changes correctly.

### Route Order Verification

After deployment, verify route order is correct:

```bash
docker exec ai-pattern-service python3 -c "
from src.main import app
from fastapi.routing import APIRoute
routes = [(r.path, r.endpoint.__name__ if hasattr(r, 'endpoint') else 'N/A') 
          for r in app.routes 
          if isinstance(r, APIRoute) and 'synerg' in r.path.lower()]
print('Route order:')
for i, (p, h) in enumerate(routes):
    print(f'{i+1}. {p:45} {h}')
"
```

**Expected Output:**
```
Route order:
1. /api/v1/synergies/stats                       get_synergy_stats
2. /api/v1/synergies/list                        list_synergies
3. /api/v1/synergies/{synergy_id}                get_synergy
4. /api/v1/synergies/{synergy_id}/feedback       submit_synergy_feedback
```

**Critical:** `/stats` must be first. If it's not, the fix didn't apply correctly.

## Post-Deployment Verification

### 1. Test Direct Endpoint

```bash
# Test pattern service directly
curl http://localhost:8034/api/v1/synergies/stats

# Expected: 200 OK with JSON stats data
```

### 2. Test Proxy Endpoint

```bash
# Test via automation service proxy
curl http://localhost:8025/api/synergies/stats

# Expected: 200 OK with JSON stats data
```

### 3. Test Frontend Integration

```bash
# Test via frontend proxy (nginx)
curl http://localhost:3001/api/synergies/stats

# Expected: 200 OK with JSON stats data
```

### 4. Verify Frontend

1. Open browser: `http://localhost:3001/synergies`
2. Check browser console for errors
3. Verify statistics display correctly
4. Verify synergies list loads

## Troubleshooting

### If `/stats` Still Returns 404

1. **Check route order** (see above)
2. **Verify file changes** were applied:
   ```bash
   docker exec ai-pattern-service grep -n "@router.get(\"/stats\")" /app/src/api/synergy_router.py
   ```
   Should show line 50 or 51

3. **Check container logs:**
   ```bash
   docker logs ai-pattern-service --tail 50 | grep -i "stats\|route\|synerg"
   ```

4. **Force full restart:**
   ```bash
   docker compose down ai-pattern-service
   docker compose rm -f ai-pattern-service
   docker compose up -d ai-pattern-service
   ```

### If Route Order is Wrong

1. **Verify route definition order in file:**
   ```bash
   grep -n "@router.get" services/ai-pattern-service/src/api/synergy_router.py
   ```
   `/stats` should appear before `/{synergy_id}`

2. **Clear Python cache:**
   ```bash
   docker exec ai-pattern-service find /app -name "*.pyc" -delete
   docker exec ai-pattern-service find /app -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
   docker compose restart ai-pattern-service
   ```

3. **Full rebuild:**
   ```bash
   docker compose build ai-pattern-service
   docker compose up -d ai-pattern-service
   ```

## Deployment Checklist

- [ ] Route changes applied to `synergy_router.py`
- [ ] Full container restart performed (`down/up`, not `restart`)
- [ ] Route order verified ( `/stats` first)
- [ ] Direct endpoint test passes (200 OK)
- [ ] Proxy endpoint test passes (200 OK)
- [ ] Frontend integration test passes (no console errors)
- [ ] Statistics display correctly in UI

## Related Documentation

- [Synergies API Fix Complete](../implementation/SYNERGIES_API_FIX_COMPLETE.md)
- [Deployment Runbook](./DEPLOYMENT_RUNBOOK.md)
- [Deployment Fixes December 2025](./DEPLOYMENT_FIXES_DECEMBER_2025.md)

---

**Maintainer:** DevOps Team  
**Last Updated:** December 29, 2025

