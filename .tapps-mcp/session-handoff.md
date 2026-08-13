# Session handoff
**Updated:** 2026-08-13T15:20:00Z
**Git:** d52467d3 (feat/ha-init-agent-activation — UNPUSHED; history was rewritten this session, see below)
**Linear P0:** Sub-goal 3 remainder (TAP-5431, TAP-5430), then Sub-goal 4 (Wave 8 MCP server epic TAP-5282, Urgent)

## Resume-as (re-enter the goal loop — the standing instruction)
- Next session re-enters the multi-run loop via the drain prompt: paste/execute — `Read prompts/homeiq-backlog-drain.md in full, then execute it as a goal loop — run the Loop section repeatedly until Done-when holds, printing the SCORE line every iteration. Establish your own preconditions per Sub-goal 0; work sub-goals in order; do not stop unless an Autonomy hard-stop fires.` **Linear must be authenticated (`/mcp`).**
- **History rewrite (this session):** the triage-store scrub (TAP-5942) rewrote commits — old hashes `9ff4f658`/`d6eac06a` are DEAD. Cite only current hashes. Branch is unpushed; PR #82 still OPEN (merge is the human's call — hard-stop).

## Done this session (Sub-goals 1–3, all adversarial-verifier-passed)
- **Sub-goal 1 (Wave 7 wizard, epic TAP-5942):** TAP-5946 (readiness triggers), TAP-5947 (triage add/ignore/later), epic 5942 — 3-panel gate (correctness/security/repro) round 1 FAIL→fixed→round 2 3/3 PASS.
- **Sub-goal 2 (Wave 1, epic TAP-5281):** TAP-5291 (CI regression checks, 4-round verifier hardening) + epic close.
- **Sub-goal 3 (defect batch):** TAP-5993 (compose credential defaults), TAP-6027 (backup summary/details), TAP-5994 (data_sources_active real method), TAP-5999 (docker socket GID + 503), TAP-6007 (value-embedded credential predicate + unauth router), TAP-5997 (event search → InfluxDB direct).
- **Follow-ups filed:** TAP-6034 (wizard page wiring), 6035 (DNS-rebinding guard), 6036 (env.test/prod committed creds), 6037 (libs tests in CI).
- Floors: homeiq-ha **222**, ha-setup-service **56** (trees SEPARATE — combined run breaks collection). admin-api 393, data-api search 6.

## Open (resume here)
- **TAP-5431** (Local Calendar config-flow + Powercalc HACS install + template aliases) — LARGE, live-HA-apply; read flow schemas from a LIVE flow, never guess; Powercalc install may force an HA restart (heavier apply — gateway path). HACS unblocked.
- **TAP-5430** (recorder + http recipes only; automation editor already delivered) — file-access add-ons installed/unblocked; **CHECK docs/ha-init-agent-design.md rows 3.5/3.6 for the remote-YAML-write mechanism — if undecided, that is decide-work: surface, don't guess.**
- Then Sub-goals 4–8: Wave 8 MCP server (epic TAP-5282, **Urgent** — 5292 tool catalogue gates everything), Wave 9 genome/safety, Wave 10 HA integration, Wave 11 data-plane collapse (destructive, last).

## Owner-gated items surfaced (recorded on their tickets, not executed)
- TAP-5993: rotate every previously-committed credential (public git history retains them).
- TAP-6007: `REVOKE CONNECT ON DATABASE homeiq FROM PUBLIC;` and `influx bucket update -i 4a563089aca2d2a3 --retention 2160h` (the latter deletes >90d points).

## Standing / blocked
- Wave 4 TAP-6018 (Aqara FP1E quirk) — re-checked this run, still Backlog. Splittable: quirk authoring is agent-workable in-repo; only the HA-host file drop is human-gated.
- Pre-existing, out of scope: legacy files (events_endpoints/config_manager/stats_endpoints/influxdb_query_client) fail the quality gate on file-wide lint debt — every this-session change was neutral-to-positive; the drifted homeiq-ci-local-pg container makes ~106 data-api DB tests error (unrelated).

## Blockers
- none (Linear authenticated; caps not hit — clean checkpoint at the two large live-apply tickets)
