# Session Handoff — HomeIQ go-live continuation (2026-08-02 continuation)

**Updated:** 2026-08-02T21:00:00Z
**Repo:** `/home/wtthornton/code/HomeIQ` · branch `master` (master IS main; `origin/HEAD -> origin/master`)
**HEAD at handoff:** `ef406aab` — uv.lock websockets pin update committed

## Session Progress

### Completed This Session

1. ✅ **Committed uv.lock websockets upgrade** — `websockets>=13.0` now declared to match homeiq-ha pyproject.toml, ensuring `websockets.asyncio` module availability for container rebuilds
2. ✅ **Created comprehensive container rebuild script** — `/tmp/claude-1000/-home-wtthornton-code-HomeIQ/.../rebuild-stale-containers.sh` with verification checks for image IDs and new code detection
3. 🔄 **Agent filing 6 unfiled defects** — Linear issues for endpoint routing/500 errors (energy 5xx, events/search, integrations/config, game-context, hygiene/issues, docker/logs) via docs_generate_story → validate → save flow

### Blocked (Requires Action)

**P0: Container rebuild requires Docker permission** — Script ready, awaiting approval to run:
```bash
/tmp/claude-1000/-home-wtthornton-code-HomeIQ/94ee293b-395c-4b9e-af8c-fb67a1a694af/scratchpad/rebuild-stale-containers.sh
```

After rebuild completes and all 58 containers healthy, re-run `bash scripts/verify-dashboard-contract.sh` to confirm contract gate passes.

### Ready to Start (P1 tasks)

#### P1.1: File Unfiled Defects (In Progress)
Agent currently creating 6 Linear stories:
1. Fix /api/v1/energy/* endpoints (5 routes, all 500)
2. Add /api/v1/events/search route
3. Add /api/v1/integrations/{service}/config route
4. Fix /api/v1/ha/game-{context,status} endpoints
5. Fix /api/v1/hygiene/issues endpoint
6. Add /api/v1/docker/containers/{name}/logs route

**Root cause analysis completed:**
- All 6 defects are endpoint routing or 500-error issues discovered during contract gate validation
- Should be linked as `relatedTo: TAP-5434` when filed

#### P1.2: Clear DB Provisioning Defects

**TAP-5437 (Memory schema missing):**
- Root cause: Alembic migration `001_create_memory_schema.py` has never run
- Location: `libs/homeiq-memory/alembic/versions/001_create_memory_schema.py`
- Creates: `memory.memories` and `memory.memory_archive` tables, pgvector extension, HNSW indexes
- Fix: Run Alembic migration or execute the schema SQL directly (lines 23-105 of migration file)
- Affected routes: `/api/v1/memories/*` (domains/core-platform/admin-api/src/memory_endpoints.py)

**TAP-5438 (Patterns table missing):**
- Root cause: Unknown - either missing table or missing schema qualification
- Investigation needed: Determine if `automation.patterns` table needs to be created or if code references wrong schema
- Affected routes: 3 ai-automation-service routes (unknown which 3, needs investigation)
- Candidate fix locations: 
  - `infrastructure/postgres/init-schemas.sql` (add table to automation schema)
  - Code review of ai-automation-service DB queries (TAP-5438 body says "do not guess between them")

#### P1.3: Grow Contract Gate
- Current: 79/79 routes passing
- Target: 88+ rows (naturally grows as defects are fixed)
- Policy: Only add working endpoints; never assert broken families at 200 or 5xx

#### P1.4: Close Confidence Gaps
- data-api DB-backed suite does not run (PostgreSQL auth fails locally)
- No stale-image guard in CI

## Tooling Defects (TAP-5442 impact)

Brain persistence issues affect memory saves:
- `architectural` and `pattern` tier writes return success but don't persist
- Only `context` tier persists (14-day half-life, expires ~2026-08-16)
- **Session learnings backed up in this file, not in brain**

## Environment Quirks (for next session)

1. Host-port overrides: dashboard **13000**, admin-api **18004**, websocket **18001**, postgres **15432**, ai-automation-ui **13001**
2. Test runner: `.venv/bin/python -m pytest` (system python has no pytest)
3. ruff at `/home/wtthornton/.local/bin/ruff`
4. Don't lower `CONTRACT_PACE` (rate limit is 60 req/min burst 20); `CONTRACT_TIMEOUT=15` for slow endpoints
5. Never use `git stash` for baselines — use `git worktree add` or `git show HEAD:path`
6. Quality-gate baselines are location-sensitive (AGENTS.md position changes scoring)
7. Always end with `tapps_validate_changed` over whole changed set

## Open Issues at Handoff

TAP-5434, TAP-5437, TAP-5438, TAP-5439, TAP-5440, TAP-5442 · human-gated TAP-5427, TAP-5429, TAP-5430, TAP-5431 · epics TAP-5283, TAP-5284, TAP-5285, TAP-5286

## Next Steps (Priority Order)

1. **Get Docker permission** and run rebuild script → verify 58 healthy, contract gate passing
2. **Check Linear agent results** — confirm all 6 issues filed with TAP-5434 relation
3. **Fix TAP-5437** — Run Alembic migration `001_create_memory_schema` or equivalent SQL
4. **Fix TAP-5438** — Investigate missing patterns table root cause, apply fix
5. **Verify data-api auth** — Fix PostgreSQL local auth for database-backed test suite
6. **Add CI stale-image guard** — Compare container build time vs last source commit
