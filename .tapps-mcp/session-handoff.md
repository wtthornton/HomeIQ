# Session handoff
**Updated:** 2026-08-01T19:17:09Z
**Git:** baf05c74
**Linear P0:** TAP-5415

## Done
- **HomeIQ is live against the new Home Assistant** (HA 2026.7.4, Supervised, Raspberry Pi @ `http://192.168.1.80:8123`). 58/58 containers healthy. Event flow proven end-to-end: real `state_changed` events from the home land in InfluxDB. Agentic path verified (ai-query → OpenAI → suggestion).
- Merged PR #72 (7 round-1 audit fixes) and PR #73 (live-deployment prep: SecretStr for HA/OpenAI credentials, sanitized `infrastructure/env.production` which held 3 real HA tokens + MQTT creds + the shared API key, de-hardcoded the previous owner's `192.168.1.86`, rebuilt `infrastructure/env.example`, repaired deploy scripts).
- Repaired 4 rotted test suites: ai-query 37 passed / 0 errors (was 6F/9E), data-retention 138 passed (was 5F/22E + collection failure, and a real `create_backup` 201-unreachable bug), sports-api 8 passed (was uncollectable), websocket-ingestion 522 passed.
- Parameterized 10 colliding host ports (this box also runs AgentForge/tapps/nlt stacks). Built all 49 images.
- **Databases audited clean** — HomeIQ's `core.entities`/`core.devices` match HA's registries exactly (164/164, 19/19, zero orphans). Removed my two bring-up test artifacts.
- **Deep research + design** for an HA init/setup agent → `docs/ha-init-agent-design.md` (4 parallel research streams: repo dependency matrix, HA 2026 best practices, HACS ecosystem, automation-capability matrix).
- **Filed 2 Linear epics + 12 stories**: TAP-5405 (HA Init/Setup Agent, children 5406-5412) and TAP-5413 (Dashboard red-to-green, children 5414-5418).
- **Wrote the orchestration prompt** `prompts/close-ha-and-dashboard-epics.md` + companion `.claude/workflows/phantom-endpoint-map.js` to drive both epics to a provable finish.

## Open
- Both epics are filed but **no implementation has started** — 12 stories all in Backlog.
- **The health dashboard renders red**: 18 of ~36 endpoints fail (nginx routing, stale-DNS 502s, auth header mismatch, 9 phantom routes, an evaluations 500). Two of the 502s were triggered by this session restarting services after the OpenAI key landed; nginx caches upstream IPs forever with static `proxy_pass`.
- **Nothing has been configured on the live Home Assistant** — the user's standing instruction is "do not set anything up." HA still has zero backups, zero add-ons, no HACS.
- `uv.lock` has 308 uncommitted lines adding auth libs (bcrypt, cryptography, passlib, python-jose) — provenance unclear, not from this session's venv installs. Left uncommitted deliberately; needs an owner to confirm before committing.
- Pre-existing test debt untouched: proactive-agent 16F/6E, ai-training 24 DB-fixture errors, openvino health-shape rot.
- 4 blocking product decisions live in the stories: evaluations datastore (TAP-5418), whether `homeiq_csrf` is issued at all (TAP-5416), build-or-drop the 2 unmatched panels (TAP-5417), off-site backup target + Team Tracker teams (TAP-5408/5411).

## Next (P0)
- Start the dashboard epic by writing the contract-verify script and recording the 18-of-36 baseline, since every other story in both epics reports against that gate. The fastest path is running the orchestration prompt cold-start line from a fresh session, which sequences the rest automatically.

## Blockers
- none

## Changed files
- `prompts/close-ha-and-dashboard-epics.md` (new — the orchestration loop)
- `.claude/workflows/phantom-endpoint-map.js` (new — 9-endpoint resolve/refute fan-out)
- `docs/ha-init-agent-design.md`, `docs/operations/dashboard-triage-2026-08-01.md`
- `.env` (gitignored — HA token, OpenAI key, generated secrets, host-port overrides, lat/long)

## Verify
- `docker ps --filter name=homeiq --format '{{.Status}}' | grep -c healthy` — expect 58
- Per-service tests use **`/home/wtthornton/code/HomeIQ/.venv/bin/python -m pytest`**; system `python3` has no pytest
- Host ports are overridden: dashboard 13000, admin-api 18004, websocket 18001, postgres 15432, retention 18080, jaeger 16687
- `docker buildx bake` needs `-f docker-bake.hcl`; several compose services have `build:` with no `image:`, so bake output is NOT what compose runs — rebuild via `docker compose ... up -d --build <service>`
- Live HA is **read-only** for now: `curl -s -H "Authorization: Bearer $HA_TOKEN" http://192.168.1.80:8123/api/` returns `{"message":"API running."}`

## Success criterion
- Both epics closed with ground-truth proof: contract script 36/36, pytest 0 failures across the touched suites, and the setup agent's audit running read-only against live HA with an idempotency test passing — without any write to the live home.
