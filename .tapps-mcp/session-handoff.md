# Session handoff
**Updated:** 2026-08-26T18:21:19Z
**Git:** c4f37a5e (master)
**Linear P0:** TAP-6571 follow-up (ADR key inventory), then TAP-6577

## Done
- **#132**: Security Scan red was a TOKEN SCOPE, not a vulnerable image — no `permissions:`, so `upload-sarif` failed while Trivy passed. Added `security-events: write` on `scan-images`. Matrix still 11, no `continue-on-error`. Plus vitest 4.1.11 (devDeps only). Verified on master by **dispatch**: run 32997650711, all 11 `scan-images` success.
- **#131**: HAOnboarder landed **dormant**. Handoff called it "docstring only" — that was its top commit; the PR was 485 lines. Gate 76.98, 431 tests, `onboard` has `callers: []`.
- **TAP-6571 decided + closed.** ADR merged (#133,#134): `docs/architecture/adr-appliance-secret-store.md`. Two stores split on boot ordering. Tier 1 = generated bootstrap keys in a root-owned 0600 file via existing `${VAR:?required}` interpolation, zero compose changes. Tier 2 = `core.appliance_secret`, AES-GCM under a tier-1 DEK. Named failure states, no fallback.
- Lessons pass merged (#135).

## Next (P0)
1. **Fix the ADR key inventory — defect shipped THIS session.** (a) Tier 1 lists `JWT_SECRET_KEY`, which **no code reads** (grep = one docstring + one test fixture). Admin-api JWTs are signed with `ADMIN_API_JWT_SECRET`, `libs/homeiq-data/src/homeiq_data/auth.py:69`, set nowhere, falling to `secrets.token_urlsafe(32)` per process (=TAP-6580). The ADR currently tells TAP-6573 to generate the wrong key. (b) `AGENTFORGE_API_KEY` is required (`env.required:35`) but in no tier — externally *issued*, not generated, a third category. Note `env.required:46` marks `JWT_SECRET_KEY` conditional while `compose.yml:267` enforces `:?required`. **Do NOT re-litigate the two-tier split, the ordering argument, the Postgres/vault eliminations, the failure states or the survival matrix — all stand.**
2. **TAP-6577** — now the SOLE reason Docker Security Scan reports red. Nine `include:` entries need `env_file: .env` (gitignored -> Compose dies at file resolution before any build), and the Trivy step has `exit-code: '0'` so it cannot fail on findings.

## Open
- **TAP-6572/6573 bodies stale**: both still say "blocked by TAP-6571 ... do not start" and "names no storage mechanism"; TAP-6572 still lists `blockedBy: TAP-6571` though it is Done. Comments carry the tiers, the body contradicts them. TAP-6573=tier 1, TAP-6572=tier 2.
- **TAP-6580** blast radius unmeasured (JWT path vs API key). Coupled to P0 #1.
- **Master CI** last 40 runs: E2E 0/8, ML Engine 0/1, Security Scan 0/2 (scan-all only), Frontends 1/2, Core Platform 2/3, rest green. `prompts/ci-pipeline-full-repair.md` ready, ~10h.
- **tapps-mcp #280 unmerged — NOT mine** (other repo; `agent-scope.md`). `learnings.md` at 39.0/40 KB — next pass should prune.

## Blockers
- none

## Changed files
- new: `docs/architecture/adr-appliance-secret-store.md`; edited: `orchestration-prompt/learnings.md`

## Verify
- **The scan workflow has NO `push` trigger** (`pull_request` on `**/Dockerfile*`, `schedule`, `workflow_dispatch`). Merging NEVER re-runs it — master's check-runs stay frozen at the last cron and master keeps LOOKING red. Use `gh workflow run docker-security-scan.yml --ref master`. "Merge so master goes green" is unreachable by construction.
- Cron/dispatch vs PR run: `Security Scan All Services` present => cron/dispatch, absent => PR.
- **Run conclusion != job conclusion.** Run 32997650711 is `failure` though all 11 `scan-images` passed, because `scan-all` fails. Never say "Security Scan is green" — say which jobs.
- Read `.conclusion` from check-runs, never `gh pr checks` (cancelled renders as fail).
- `uv run python -m pytest libs/homeiq-ha/tests/ -q` — 431 passed.
- **Do NOT build the secret store.** Fixing the ADR's key list is a docs edit.

## Success criterion
- ADR names `ADMIN_API_JWT_SECRET` and places `AGENTFORGE_API_KEY` so TAP-6573 generates the right keys; TAP-6577 fixed so the scan RUN (not just its 11 jobs) can go green; TAP-6572/6573 bodies no longer say "blocked, do not start".
