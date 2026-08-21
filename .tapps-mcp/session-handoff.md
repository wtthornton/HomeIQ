# Session handoff
**Updated:** 2026-08-21T20:18:54Z
**Git:** 5156a6c2
**Linear P0:** TAP-6393

## Done
- **TAP-6399 closed** (`aa73bafa`). Re-decided the MQTT credential against public disclosure. Two disposition claims were false, corrected with the bad rows struck through, not overwritten:
  - "Not reused" was a **working-tree grep that never read history**. The string (fp `2d184279`) is in **17 files / 13 commits from 2025-08-23** — 79 days before `3df40097` — serving as MQTT password, Grafana admin pw, InfluxDB admin pw, **and the InfluxDB admin API token**. Exposure ~12 months, not 9.
  - Five other secret families were never assessed: **6 HA long-lived tokens** (committed repo day one `efa2843a`, nominally valid to 2035), 6 Context7 keys, an OWM key, weak `.env.backup*` values, 3x 469KB HA state dumps.
  - **Measured, not inferred: nothing leaked still works.** 6/6 HA tokens 401; leaked string rejected by live Grafana and by InfluxDB under `Token` auth (Basic was the wrong scheme). InfluxDB `/health` 200 as control, so the 401s are real rejections.
  - Rewrite still declined but on **inverted** reasoning: original ground ("repo is private") was void; stands because rotation is the control. Tidiness, not containment.
  - **14 remote branches** carrying the plaintext at tip deleted (all verified merged, SHAs saved). `origin` now holds **only master**.
- **TAP-6432 filed** (High): `check-secrets.py` has no `token` keyword in any of its 7 patterns, and its API-key rule can't cross a JSON closing quote — token/API-key leaks scan CLEAN.
- **TAP-6393 criteria restated** on measured denominators — deliberately only the unreachable ones.

## Open
- **TAP-6393 (P0), In Progress.** 4 of 6 columns at true ceiling; 2 gaps are real work:
  - `power_source` **48, target 53** — 5 rows have `device_type` but no power source: HP Tango printer, TP-Link Archer BE800, Hue Bridge, 2x Aqara FP1E. All mains. Needs a rule, not a restatement.
  - `device_capabilities` **48/93**, needs >=88 — TAP-6428's scope.
  - Five sampled rows traced to producing rule — not done.
- **Owner, outside repo:** 6 Context7 keys public in history need revoking at Context7 (current key NOT among them).
- Local branch `device-knowledge-completion` still materializes the plaintext on checkout; merged, so deleting loses nothing.
- **MQTT dead but residue everywhere**: no broker, 1883 closed, no compose service, only code path (`ai-pattern-service/src/main.py:97-115`) gated off. Yet 19 containers carry placeholder `MQTT_*` vars and `paho-mqtt` sits in `requirements-base.txt:75`. Unticketed.
- `CI - ML Engine` + `E2E & Integration Tests` permanently red on master, failures byte-identical across commits — no regression signal.
- TAP-6396/6397 unstarted. TAP-6402 at 30/39. VAL-02 has 2 adversarial rounds, no confirming third.

## Next (P0)
- Implement the `power_source` rule for the 5 known-type mains devices, re-measure (expect 53), then trace five sampled rows to their producing rule.

## Blockers
- none

## Verify
- `docker exec homeiq-postgres psql -U homeiq -d homeiq -c "SELECT count(*), count(device_type), count(power_source), count(lqi), count(battery_level), max(updated_at), now() FROM devices.devices"` — expect 93/52/48/5/8, max(updated_at) inside one 300s pass. This is the real write-path check; `devices_count` counts devices read from HA, not rows persisted, and lies during an outage.
- Denominators are **not** 93: 41 rows are Hue groups, HA Core/OS/Supervisor/App, HACS, service integrations, the Pi host, 2 coordinator radios, BT adapter. `device_type` ceiling is **52**.
- HA `/api/states`: exactly **8** live `device_class=battery` entities (table has 8, exact) and **zero** LQI entities — LQI's 5 come from ZHA device attributes.
- Do **not** trust `check-secrets.py` exit 0 as evidence until TAP-6432 lands.

## Success criterion
- `power_source` reaches 53 via a real producer rule and five rows trace to their rule, so TAP-6393 closes on measured numbers with nothing restated away.