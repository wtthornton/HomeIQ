# Session handoff
**Updated:** 2026-08-21T19:35:00Z
**Git:** aa73bafa (master, pushed)
**Linear P0:** TAP-6393

## Done
- **TAP-6399 closed.** Re-decided the MQTT credential question against public disclosure. Two claims in the disposition were false and are corrected in `aa73bafa`, with the false rows struck through rather than overwritten.
  - "Exactly one occurrence / not reused" was a **working-tree grep that never read history**. The same string (fp `2d184279`) is in **17 files across 13 commits** from **2025-08-23** — 79 days before `3df40097`. It was one shared secret: MQTT password, Grafana admin password, InfluxDB admin password, **and the InfluxDB admin API token**. Public exposure ~12 months, not nine.
  - Five other secret families were never assessed: **6 HA long-lived tokens** (6 distinct accounts, committed repo day one `efa2843a`, nominally valid to 2035), 6 Context7 keys, an OpenWeatherMap key, weak `.env.backup*` values, 3x 469KB HA state dumps.
  - **Liveness measured, not inferred: nothing leaked still works.** All 6 HA tokens 401. Leaked string rejected by live Grafana and by InfluxDB under `Token` auth (its real scheme — the first Basic-auth probe was the wrong test). InfluxDB `/health` 200 recorded as the control, so the 401s are real rejections not an unreachable host.
  - Owner re-answered: treat the password **and its construction pattern** as burned. Supersedes the earlier "unique to this dead broker".
  - History rewrite still declined, but on **inverted** reasoning — the original ground ("repo is private") was void; it stands because rotation is the control. Recorded as tidiness, not containment.
  - **14 remote branches** serving the plaintext at tip deleted, all verified merged, SHAs saved. `origin` now holds **only master**.
- **TAP-6432 filed** (High): `check-secrets.py` has no `token` keyword in any of its 7 patterns and its API-key rule can't cross a JSON closing quote, so token/API-key leaks scan CLEAN. Verified by reading the regexes at `scripts/check-secrets.py:19-98`.
- **TAP-6393 criteria restated** on measured denominators, and deliberately only the unreachable ones.

## Open
- **TAP-6393 (P0), still In Progress.** 4 of 6 columns are at their true ceiling; 2 gaps are real work:
  - `power_source` **48, target 53** — 5 rows have a known `device_type` but no power source: HP Tango printer, TP-Link Archer BE800, Hue Bridge, 2x Aqara FP1E. All mains. Needs a rule, not a restatement.
  - `device_capabilities` **48 of 93**, criterion needs >=88 — TAP-6428.
  - "Five sampled rows traced to the producing rule" — not yet done.
- **Owner action, outside the repo:** 6 Context7 API keys are public in history and need revoking at Context7. The current key is NOT among them (never committed).
- **Local branch `device-knowledge-completion`** still materializes the plaintext on checkout. Merged into master, so deleting loses nothing. Left for the owner.
- **MQTT is dead but its residue is everywhere** — no broker, 1883 closed, no compose service, and the only MQTT-capable code path (`ai-pattern-service/src/main.py:97-115`) is gated off and logs "MQTT broker not configured". Yet **19 running containers carry placeholder `MQTT_*` env vars** and **4 manifests still pull MQTT clients** (`paho-mqtt` is in `requirements-base.txt:75`, so it installs almost everywhere). Worth a ticket; not filed.
- `CI - ML Engine` and `E2E & Integration Tests` permanently red on master, failure sets byte-identical across commits, so no regression signal.
- TAP-6396, TAP-6397 unstarted. TAP-6402 at 30 of 39, no fresh init-audit row. VAL-02 has two adversarial rounds, no confirming third.

## Next (P0)
- Implement the `power_source` rule for the 5 known-type mains devices, then re-measure (expect 53). Then trace five sampled rows to their producing rule. `device_capabilities` is TAP-6428's scope, not TAP-6393's to fix.

## Blockers
- none

## Changed files
- `docs/security/secret-disposition-mqtt-broker-credential.md` (committed `aa73bafa`)

## Verify
- `docker exec homeiq-postgres psql -U homeiq -d homeiq -c "SELECT count(*), count(device_type), count(power_source), count(lqi), count(battery_level), max(updated_at), now() FROM devices.devices"` — expect 93/52/48/5/8 with max(updated_at) inside one 300s pass. This is the real write-path check; `devices_count` reports devices read from HA, not rows persisted, and lies during an outage.
- Establishable denominators are **not** 93: 41 rows are Hue groups, HA Core/OS/Supervisor/App, HACS entries, service integrations (sun/met/TTS/backup), the Pi host, 2 coordinator radios and the BT adapter. `device_type` ceiling is **52**.
- HA cross-check: `/api/states` reports exactly **8** live `device_class=battery` entities (table holds 8, exact) and **zero** LQI/signal_strength entities (so LQI's 5 come from ZHA device attributes, not entities).
- Do **not** trust `scripts/check-secrets.py` exit 0 as evidence of no secrets until TAP-6432 lands.

## Success criterion
- `power_source` reaches 53 by a real producer rule, and five sampled rows are each traceable to the rule that produced them — so TAP-6393 closes on measured numbers with no criterion restated away.
