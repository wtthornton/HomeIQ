# Phase 1 Story 2: Validate Service Requirements Compatibility

**Epic:** Phase 1 — Critical Compatibility Fixes  
**Story:** 2 — Validate that all service requirements files are compatible with Phase 1 updates  
**Status:** Checklist and scan reference for DevOps

---

## Objective

Ensure all Python service `requirements.txt` files under `domains/` are compatible with Phase 1 base versions (SQLAlchemy 2.0.46, aiosqlite 0.22.1, FastAPI 0.119.0+).

---

## Scan Results (Executed Phase 1)

| Domain | Service | Uses base | Phase 1 aligned |
|--------|---------|-----------|-----------------|
| core-platform | data-api | No (own deps) | Yes (updated to 2.0.46 / 0.22.1) |
| core-platform | websocket-ingestion | No | N/A (no SQLAlchemy in file) |
| core-platform | admin-api | No | FastAPI 0.123+ |
| core-platform | data-retention | No | FastAPI 0.123+ |
| automation-core | ha-ai-agent-service | No | Yes (pinned 2.0.46 / 0.22.1) |
| automation-core | ai-automation-service-new | No | Yes (updated) |
| automation-core | ai-query-service | No | Yes (updated) |
| automation-core | automation-linter | No | FastAPI 0.119.0 |
| pattern-analysis | ai-pattern-service | No | Yes (pinned 2.0.46 / 0.22.1) |
| pattern-analysis | api-automation-edge | No | Yes (updated) |
| blueprints | blueprint-suggestion-service | No | Yes (updated) |
| blueprints | blueprint-index | No | Yes (updated) |
| blueprints | automation-miner | No | Yes (pinned 2.0.46 / 0.22.1) |
| energy-analytics | proactive-agent-service | No | Yes (updated) |
| ml-engine | device-intelligence-service | No | Yes (updated) |
| ml-engine | ai-training-service | No | Yes (updated) |
| ml-engine | rag-service | No | Yes (updated) |
| device-management | ha-setup-service | No | Yes (updated) |

**Note:** No service uses `-r requirements-base.txt`; each has its own requirements.txt. All listed services with SQLAlchemy/aiosqlite have been updated to Phase 1 targets (2.0.46 / 0.22.1) or already had them.

**How to generate:**  
- Scan all `domains/*/*/requirements.txt`.  
- Identify lines like `-r ../../requirements-base.txt` or `-r ../../../requirements-base.txt`.  
- Note any direct pins for SQLAlchemy, aiosqlite, FastAPI.

---

## Compatibility Matrix (Phase 1 Targets)

| Package | Current (base) | Phase 1 Target |
|---------|-----------------|----------------|
| SQLAlchemy | 2.0.45 | 2.0.46 |
| aiosqlite | 0.21.0 | 0.22.1 |
| FastAPI | 0.128.0 | 0.119.0+ (keep current or latest) |
| Pydantic | 2.12.5 | Keep (v2) |
| httpx | 0.28.1+ | Keep current |

---

## Update Strategy per Service Category

1. **Services using only base:** No change if `requirements-base.txt` is updated in Story 1.
2. **Services with pinned versions:** Review pins; align to Phase 1 targets or document exception.
3. **Conflicts:** Document and resolve before rebuild (Stories 4–10).

---

## Verification Commands

```powershell
# List all Python requirements files
Get-ChildItem -Path domains -Recurse -Filter requirements.txt | Select-Object FullName

# Check for base reference
Select-String -Path "domains\*\*\requirements.txt" -Pattern "requirements-base"
```

---

## Completion Criteria (Story 2)

- [x] All Python service requirements files under `domains/` reviewed.
- [x] Services using base identified (none use -r base; each has own file).
- [x] Pinned versions documented and updated to Phase 1 where needed.
- [x] Update strategy defined: align all SQLAlchemy/aiosqlite to 2.0.46 / 0.22.1.
- [x] Compatibility matrix and checklist completed.
