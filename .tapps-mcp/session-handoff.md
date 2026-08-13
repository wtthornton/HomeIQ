# Session Handoff — HomeIQ backlog burndown (2026-08-13, Wave 6 complete)

Branch `feat/ha-init-agent-activation` (PR #82, draft). All work committed and
pushed. Test floors: `libs/homeiq-ha` **175 passed** (run it and the
ha-setup-service tree SEPARATELY — combining them fails collection on a
`tests` package-name collision), ha-setup-service 29 passed.

## Waves complete — do NOT redo

- **Waves 1–3, 5** — see git history of this file + brain keys `burndown-wave-*`.
  Wave 5 (Zigbee health, epic TAP-5981) closed with 3-verifier panel + all
  findings fixed (`79f23dd8`).
- **Wave 6 (switch comfort + closeout, epic TAP-5985) COMPLETE 2026-08-13.**
  All stories Done/dispositioned, each refute-verified; 3-verifier panel run
  (correctness PASS, no-residue PASS, reproducibility FAIL-narrow) and all
  findings fixed same session:
  - TAP-5921 zigbee2mqtt probes deleted; recipes.py 947→409 (gate 70.2);
    harness → `tests/simulators.py` (gate 70.5 after panel fix) + new
    `test_simulators.py`/`test_backup.py`/`test_registry.py`/`test_manifest.py`.
  - TAP-5987 gesture catalogue: 24 `switch_gestures` rows in the manifest,
    ALL `selected: null` — owner selects by editing the manifest; NO consumer
    exists by design.
  - TAP-5988 smart-bulb-mode evaluation:
    `docs/operations/smart-bulb-mode-evaluation.md` — Office = ENABLE after a
    10-second paddle check (third-world conventional-load risk; both dimmers
    are `Three Way AUX`), Bar = leave as-is. NOTHING was changed on the
    switches (recorder-history-proven).
  - TAP-5989 fourth-switch wiring check recorded (ledger + Linear; LOCATION
    of the switch was never recorded — ask owner which box).
  - TAP-5990 ADR `docs/architecture/adr-goal-loop-operator-pattern.md` +
    new `docs/ARCHITECTURE.md` index.
  - TAP-5991 re-scope: TAP-5429 Canceled (superseded by PR #82 delivery),
    TAP-5430 narrowed to http+recorder recipes, TAP-5431 kept (HACS
    prerequisite cleared).

## Blocked / standing (unchanged)

- **Wave 4 (TAP-5977) HUMAN-BLOCKED on TAP-6018** (FP1E quirk). Skip
  5978/5979/5980; office stays on input_boolean proxies.
- PR #82 merge = human decision. GitHub Actions slimming recommendations
  delivered to owner — NOT approved yet, do not implement.
- Pending owner actions: fourth-switch wiring check (TAP-5989, room unknown —
  ask), office dimmer 10-second paddle check before smart-bulb-mode enable
  (TAP-5988), gesture catalogue selections (TAP-5987).

## Next (Wave 7 — setup wizard, epic TAP-5942 — IN PROGRESS)

- TAP-5943 DONE (queue API live, verifier round-trip complete).
- TAP-5945 implemented + hardened (verifier round 1 FAIL -> all 6 gaps
  fixed: group_add 1000 writable mount proven on a copy, YAML-injection
  quoting + rollback in NEW manifest_edit.py, typed unwritable failure,
  team-flow create_entry/abort handling, EOF/empty-section guards,
  websockets frame-logger pinned). TAP-5944 implemented (/setup page,
  headless-chrome render proof: 12 items, 7 readiness badges).
  **Combined 5944+5945 verifier was killed by the account session limit
  (resets 7:30pm PT) — RE-DISPATCH IT before closing either story.**
- Then TAP-5946 readiness triggers (permit root cause documented at
  ws.py:200-206, fix 2f0f9087; command zha/devices/permit duration=N),
  TAP-5947 triage (add/ignore/later; verify config_entries/ignore_flow
  shape), wave panel, close epic TAP-5942. Suite floor now 194 + 29.
Then Waves 8–11.

## Key mechanics (stable)

- Live HA reads: `docker exec -i homeiq-setup-service python -` with
  `homeiq_ha.client`. Writes ONLY via `POST :8024/api/v1/init/converge`.
- Gateway rebuild (needed after any libs/homeiq-ha change):
  `docker compose -f domains/device-management/compose.yml --env-file .env
  --profile production up -d --build ha-setup-service`; verify by identity.
- Runbook: `docs/operations/init-gateway.md`. Read-only allowlist:
  `homeiq_ha/agent/readonly.py`. New recipes: small modules re-exported from
  the recipes hub.
- Known artifact bug (follow-up story filed): `safety.backup_schedule` audit
  row says satisfied/"automatic backups configured" while its own detail has
  `automatic_backups_configured: false` — summary-vs-detail contradiction in
  `BackupScheduleRecipe.check`.
- ai-automation tests: `TEST_DATABASE_URL=postgresql+asyncpg://homeiq_test_ci:homeiq-test-only@localhost:15432/homeiq_test`.
