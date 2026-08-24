# Session handoff

**Updated:** 2026-08-24T00:46:00Z

## Where things stand

`master` is at **`4ed6d769`**. Five PRs merged (#125–#129), **none open**, tree
clean. Production services **48 → 42**; ratchet updated in
`infrastructure/container-budget.json` (fails in both directions).

Live stack **unchanged** — compose was edited, containers were not restarted.
The six observability containers still run. Restarting is also what unblocks an
honest memory re-measurement.

## Decisions — see `docs/architecture/adr-appliance-packaging.md`

1. **HomeIQ owns a headless HA**, pre-provisioned at build time. HACS is
   build-time only; no Supervisor. `AddonRecipe` was the sole caller of
   `ws.supervisor_api`, and every add-on existed to install software or let a
   human edit files.
2. **One shared HA credential, generated per install** via HA's onboarding API.
   Shared ≠ constant; only the first was wanted. **Rotation is deferred**
   (owner) — shape settled, mechanism not being built.
3. **Installer + pinned compose bundle**, not one fused image: Zeek's `NET_RAW`
   + host networking would otherwise cover HA and litellm's provider key.
4. **Zeek ships opt-in**, default off. `hacs.json` removed, HACS distribution
   deferred.

## Shipped

Appliance ADR + 6 corrected docs (`ha-init-agent-design.md` superseded).
**ner-service 16.3 GB → 3.39 GB** (missing CPU wheel index) — the rebuild also
proved it **could not build at all**; only Dockerfile of 39 with an incomplete
lib closure. Observability tier gated behind an `observability` profile;
tracing export now opt-in. **Epic TAP-6460 closed** (6461/6462/6463 + 6492).
TAP-6492: ha-setup-service had no migration chain; 001 now creates all five
tables and runs at startup.

## Next (P0)

**TAP-6464 — Provision and own the HA instance HomeIQ ships.** Urgent, 7
stories, none started. Start **TAP-6483** (pre-provisioned image): testable
today against the `home-assistant-test` fixture, unblocks 6484/6485/6486.

Then TAP-6469 → TAP-6474 → TAP-6478. TAP-6490 (installer) last — blocked by
TAP-6464 and TAP-5283.

## Open, not blocking

1. **Zeek retention** — opt-in says whether, not what is kept or how long.
   Blocks the wizard step only.
2. **Does tapps-brain ship?** AgentForge degrades fine when it is unreachable,
   but its compose has a required-value token and an external network owned by
   tapps-brain, so it ships unless someone does the escape-hatch work.
3. TAP-6490's 4 stories are described but **deliberately not filed** — the
   installer design is open.

## Traps

- **CI reds carry no signal.** `E2E & Integration Tests` and `CI — ML Engine`
  are red on master head; `Docker Build and Test` / `Docker Test` are 12/12 red
  on every branch, never green. Security Scan = Trivy missing
  `scan-<svc>:latest`, infrastructure not findings. **Always diff reds against
  master head.**
- **Linear auto-closes on PR merge regardless of acceptance.** TAP-6461 and
  TAP-6463 both closed with criteria unmet. Re-run acceptance against `master`.
- `pytest libs/` from root → 28 collection errors (`tests.conftest` collision),
  pre-existing on master. CI runs per-lib and is green.
- **Stacked PRs do not auto-retarget** if the base branch still exists. #126
  merged into its base, not master; fixed by retargeting via REST (`gh pr edit`
  fails on a Projects-classic GraphQL deprecation).
- `devices` schema is shared by two services with separate alembic chains; each
  needs its own `version_table`.

## Verify first

```bash
git log --oneline -1                       # 4ed6d769
grep -rn HOMEIQ_INTEGRATION . --exclude-dir=.git   # zero
python3 scripts/check-container-budget.py  # OK: 42 production services
python -m pytest libs/homeiq-ha/tests/ -q  # 414 passed
```

## Success criterion

TAP-6483 merged: pinned HA image carrying Powercalc, Team Tracker and the Aqara
quirk in `/config/custom_components/`, no HACS at runtime, and a checked-in
vendored-component version manifest CI verifies.
