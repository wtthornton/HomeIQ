# Story 6.5: Quick Reference Card

**Execution Date**: 2026-03-10 (after 14-day stabilization)
**Duration**: 3–4 hours
**Complexity**: Medium
**Risk**: Low

---

## Pre-Cutover Checklist (Must ALL Pass)

```bash
# 1. Check PostgreSQL uptime
scripts/check-pg-stability.sh --min-uptime 336h  # 14 days
# Expected: OVERALL: PASS

# 2. Verify schema structure
python scripts/validate-migration/check_schemas.py \
  --postgres-url "$DATABASE_URL" \
  --schemas core automation agent blueprints energy devices patterns rag
# Expected: Overall: PASS

# 3. Spot-check data parity
python scripts/validate-migration/validate_data.py \
  --postgres-url "$DATABASE_URL" \
  --sqlite-dir ./data/ \
  --schemas core agent
# Expected: exit code 0 (PASS)

# 4. Verify backup works
scripts/backup-postgres.sh
# Expected: backup files created
```

---

## 8-Step Cutover Procedure

### 1️⃣ Backups & Validation (30 min)
```bash
scripts/backup-all.sh
ls -lh backups/
```

### 2️⃣ Remove SQLite Fallback Code (90 min, 14 files)
Services: data-api, ai-automation, ha-ai-agent, ai-query, ai-training, rag, device-intelligence, proactive-agent, automation-miner, blueprint-index, blueprint-suggestion, ha-setup, ai-pattern, api-automation-edge

**Pattern**: Remove `if/else DATABASE_URL.startswith("sqlite")` blocks, require `POSTGRES_URL` only.

### 3️⃣ Remove aiosqlite from Requirements (30 min, 15 files)
```bash
# Remove `aiosqlite>=0.19.0` from all:
domains/*/*/requirements*.txt
```

### 4️⃣ Remove SQLite Env Vars from Compose (30 min)
```bash
# Remove from docker-compose files:
- DATABASE_URL=sqlite+aiosqlite://...
- SQLITE_TIMEOUT
- SQLITE_CACHE_SIZE
```

### 5️⃣ Remove Docker Volumes (5 min)
```bash
docker compose down
docker volume rm homeiq_sqlite-data homeiq_ai_automation_data # etc.
docker volume ls | grep postgres  # verify postgres_data still exists
```

### 6️⃣ Archive Migration Scripts (5 min)
```bash
mkdir -p scripts/archive/sqlite-migration
mv scripts/validate-databases.sh scripts/archive/sqlite-migration/
mv scripts/migrate-data/ scripts/archive/sqlite-migration/
```

### 7️⃣ Update Docs (30 min)
- Update MEMORY.md (remove SQLite references)
- Update .env.example (PostgreSQL-only)
- Create docs/operations/6.5-cutover-summary.md

### 8️⃣ Rebuild & Validate (90 min)
```bash
docker buildx bake full
docker compose up -d
sleep 30
scripts/check-pg-stability.sh
python scripts/validate-migration/check_schemas.py --postgres-url "$DATABASE_URL"
```

---

## Post-Cutover Validation (Must ALL Pass)

```bash
# Health checks
docker compose ps
scripts/check-service-health.sh

# Data integrity
scripts/check-pg-stability.sh
# Expected: 8/8 checks PASS

# Code cleanup
docker compose logs | grep -i "sqlite\|aiosqlite"
# Expected: empty

# E2E tests
pytest tests/e2e/ -v
# Expected: all passing

# Volume cleanup
docker volume ls | grep -i sqlite
# Expected: empty
```

---

## Git Commits Summary

```
docs: 6.5 baseline snapshot before cutover
chore: 6.5 — remove SQLite fallback from [14 services]
chore: 6.5 — remove aiosqlite dependency from all services
chore: 6.5 — remove SQLite environment variables from compose
chore: 6.5 — archive SQLite migration scripts
docs: 6.5 — update documentation post-cutover
```

---

## Rollback (if needed, < 5 minutes)

```bash
docker compose down
git revert --no-edit HEAD~5..HEAD
docker buildx bake full
docker compose up -d
# Services will auto-activate SQLite fallback
```

---

## Key Files to Modify

### Database Init (14 files)
```
data-api/src/database.py
ai-automation-service-new/src/database/__init__.py
ha-ai-agent-service/src/database.py
ai-query-service/src/database/__init__.py
ai-training-service/src/database/__init__.py
rag-service/src/database/session.py
device-intelligence-service/src/core/database.py
proactive-agent-service/src/database.py
automation-miner/src/miner/database.py
blueprint-index/src/database.py
blueprint-suggestion-service/src/database.py
ha-setup-service/src/database.py
ai-pattern-service/src/database/__init__.py
api-automation-edge/src/registry/database.py
```

### Requirements Files (15 files)
```
domains/*/*/requirements.txt
domains/*/*/requirements-prod.txt
```

### Compose Files (3 primary)
```
domains/core-platform/compose.yml
docker-compose.dev.yml
docker-compose.minimal.yml
```

---

## Success Criteria

✅ All 15 services start & stay running
✅ PostgreSQL stability check: 8/8 PASS
✅ Schema validation: all 8 schemas PASS
✅ Zero sqlite/aiosqlite in logs/packages
✅ E2E tests passing

---

## Support

**Issue during cutover?**
1. Check `docker compose logs [service] --tail=50`
2. Check PostgreSQL: `docker compose exec postgres psql -U homeiq -d homeiq -c "SELECT 1;"`
3. If unresolved in 30 min → trigger rollback
4. Document in `docs/operations/6.5-incident-[date].md`

**Detailed guide**: See `docs/planning/story-6.5-sqlite-cutover-plan.md`
