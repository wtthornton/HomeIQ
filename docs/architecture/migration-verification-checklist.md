# Migration Verification Checklist

**Purpose:** Epic 5 Story 10 — Runnable checklist to verify Domain Architecture Restructuring (Epics 1–4) is complete and correct.  
**Use:** Run through each section and check off items; fix any failures before closing Epic 5.

---

## 1. Service Count Assertions

| Domain | Expected Services | Actual (count under `domains/<name>/`) | ✓ |
|--------|-------------------|----------------------------------------|---|
| core-platform | 6 | | |
| data-collectors | 8 | | |
| ml-engine | 10 | | |
| automation-core | 7 | | |
| blueprints | 4 | | |
| energy-analytics | 3 | | |
| device-management | 8 | | |
| pattern-analysis | 2 | | |
| frontends | 4 | | |
| **Total** | **52** | | |

**How to verify:**  
`Get-ChildItem -Path domains -Directory | ForEach-Object { $name = $_.Name; $count = (Get-ChildItem $_.FullName -Directory).Count; "$name : $count" }`

---

## 2. Docker Build

- [ ] `docker buildx bake full` (or project equivalent) completes without errors.
- [ ] All 50+ service images appear in `docker image ls`.
- [ ] No bloated layers from broken `COPY` paths (inspect image sizes).

---

## 3. Docker Stack Runtime

- [ ] `docker compose up -d` (root or per-domain) starts all intended services.
- [ ] All services pass `/health` within 60 seconds.
- [ ] No restart loops or CrashLoopBackOff.

---

## 4. Import Resolution

- [ ] No `ModuleNotFoundError` or `ImportError` when running tests or starting services.
- [ ] All imports use `domains/` and `libs/` paths (no stale `services/` or `shared/` in code).

---

## 5. CI Trigger Paths

- [ ] CI config (e.g. GitHub Actions) uses correct paths per domain (e.g. `domains/core-platform/**`).
- [ ] No workflows still referencing old `services/` paths.

---

## 6. Path References in Code and Docs

- [ ] `grep -r "services/" docs/` (or equivalent) returns no stale flat-path references (or only intentional historical mentions).
- [ ] README and onboarding docs reference `domains/` and `libs/`.

---

## 7. Health Check Verification

- [ ] Each service’s `/health` endpoint responds (manual or scripted).
- [ ] Core path: websocket-ingestion → InfluxDB → data-api → health-dashboard works.

---

## 8. Test Suites

- [ ] 152+ shared pattern tests pass: `libs/homeiq-patterns/tests/`.
- [ ] Per-service unit tests pass for services that have test suites.

---

## 9. E2E / Critical Path

- [ ] HA → websocket-ingestion → InfluxDB write works.
- [ ] InfluxDB → data-api query works.
- [ ] data-api → health-dashboard rendering works.

---

## Sign-Off

| Role | Name | Date |
|------|------|------|
| Platform / Build | | |
| Quality / Tests | | |
| Documentation | | |

Once all items are checked and any issues fixed, Epic 5 (Validation and Cleanup) can be marked complete.
