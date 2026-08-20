# Session handoff
**Updated:** 2026-08-19T23:49:57Z · **Git:** `fd5b0dc9` on **master** — all work UNCOMMITTED (~40 paths)
**Driver:** `prompts/homeiq-dna-rewrite.md` goal loop, SG0→SG4.
**Read first:** `tapps_memory search "wayfind homeiq dna rewrite"` — then the keys it links (`rule-friendly-names-customer-only`, `homeiq-device-entities-durable-key`, `homeiq-naming-gateway-and-rubric-fixes`, `homeiq-colocation-correlation-confounders`, `homeiq-atlas-no-actionable-placement`). Do not re-derive what they hold.

## Standing rule (owner, 2026-08-19)
**A friendly name is for talking to the customer, never for the system.** `.claude/rules/friendly-names.md`. Allowed: render to a person, score a name's quality, match what a user typed then resolve to a stable id. Forbidden: name as join key, inferring area from a name, letting a name confer confidence. Test: **"would a rename break this?"** — if yes it is the name. The dangerous case is a name match one hop removed wearing a better label.

## Done
VAL-001..007 green, each with a pasted artifact: working-tree triage, dna-core drift gate, `dna-core/packs/` + zero-packs hard fail, `home-atlas` re-authored from measured state, durable key `(domain, platform, unique_id)`, name/area gateway made HA-first. Plus 4 friendly-name violations — worst was `suggestion_engine` scoring 100% on a name match into a `>=80` gate reaching a path that writes an area to HA, so a rename could relocate a device. ieee: `...0e:8f`=Office=**unsuffixed**, `...11:ef`=Bar=`_2`.

## Live state
HA 2026.8.2 @192.168.1.80 (635 states/93 devices/768 entities/17 areas). Baseline `.tapps-mcp/dna-baseline-20260819T193431Z.json`. AF 4.59.1 `scoped_probe=ok`, 24 genes/0 degraded. `homeiq-mcp` 202 POST/48h — AF→HomeIQ transport proven. Container current; **app is at `/app/src`**. DB migrated: unique registry key, FKs `ON UPDATE CASCADE`, `labels JSON` at 135/768.

## Open — start here
1. **VAL-012 BLOCKED on owner input.** `scripts/correlate_colocation.py` works (28 tests) but yields **co-location, not a room name** — a label needs an axiom. Need one dated attestation per cluster **against a stable id**, never a name: C01 `binary_sensor.office_office_motion_area`, C02 `binary_sensor.office_presence_2`, C03 **CONTESTED** (both Inovelli dimmers on one Aqara sensor — needs a physical check).
2. Engine is a local script, **not a published AF gene**. Traps: `kind: task`; `$name` not `{{name}}`; terminal state `complete`; `output_schema` on the workflow NODE; agents before workflows; unchanged-hash republish returns 200 and does NOT activate — pass `--activate`.
3. VAL-008 `AUTO_GENERATE_NAME_SUGGESTIONS` still False. VAL-009 duplicate generations both published. SG5 untouched — `homeiq-ha-automation-tester` was called "complete" but FAILED the validator; fixed, still unpublished.
4. Branch before committing. Do NOT commit `device-intelligence-service/models/model_metadata.json` — runtime artifact.

## Blockers
Tests hardcode `localhost:5432`, which belongs to **another project** — HomeIQ is **15432**. `asyncpg InvalidPasswordError` blocks `test_remediation_service.py`, `test_hygiene_router.py`, 2 ha-ai-agent-service context tests. Owner decision: repoint or containerise. Full device-intelligence suite exceeds 115s, never measured green.

## Verify
`cd scripts && python validate.py` → exit 0 "kit is publishable" · `pytest scripts/tests/ -q` → 54 · ha-setup-service → 63 · device-intelligence `-k "naming or name_enhancement or friendly"` → 63 passed 4 skipped · `scripts/sql/val006_repair_regression.sql` via `docker exec -i` → 3x PASS

## Gotchas
`docker exec` WITHOUT `-i` silently discards a heredoc — a migration "succeeded" and changed 0 rows. `influx query` takes `-` **positionally**. Prove a gate is wired by **breaking** it, not by grep.

## Success criterion
One atlas cluster carries a room whose provenance terminates in a dated `attestation` against a stable id, and the gene returns that room with evidence for a confident case and abstains with a reason for a weak one.
