# Device findings — discovery, hygiene analysis, and where they surface

HomeIQ continuously inspects the Home Assistant registries and files
**hygiene findings**: duplicate device names, unassigned areas, placeholder
names, stale discoveries, and disabled entities. This is the "what's wrong with
my setup" surface.

It runs in `device-intelligence-service` (container `homeiq-device-intelligence`,
host port **8028**).

> **This pipeline produced zero rows from the day it was built until
> 2026-08-18.** Three independent defects stacked, each of which rendered as
> "no issues found" in the dashboard rather than as a failure. The history is
> in [Failure modes](#failure-modes) below — worth reading before trusting a
> green result from anything in this area.

## The chain

```
DiscoveryService._discovery_loop        every 300 s, started at boot
  └─ _discover_home_assistant()         WS registries: devices, entities, areas, config entries
  └─ _unify_device_data()               merge into UnifiedDevice
  └─ _persist_entities()                mirror entity registry -> devices.device_entities
  └─ _run_hygiene_analysis()            DeviceHygieneAnalyzer.analyze()
       └─ devices.device_hygiene_issues upsert keyed on issue_key
```

Ordering is load-bearing. `device_hygiene_issues.entity_id` carries a foreign
key to `device_entities`, so entities must land **before** the analyzer runs or
every entity-scoped finding is rejected.

## Detectors

| `issue_type` | Severity | Trigger | `suggested_action` |
|---|---|---|---|
| `duplicate_name` | high | two devices share a name | `rename_device` |
| `placeholder_name` | high | name matches `^new device$`, `^unnamed( device)?$`, `^device \d+$` | `rename_device` |
| `missing_area` | medium | device has no `area_id` | `assign_area` |
| `pending_configuration` | medium | discovered >30 days ago, no config entries, no entities | `start_config_flow` |
| `disabled_entity` | low | entity disabled, excluding diagnostic/config categories | `enable_entity` |

Findings are upserted on `issue_key`. Anything that disappears from a run is
auto-flipped `open` → `resolved`; a finding marked `ignored` stays ignored.

## Where they surface

- **API** — `GET /api/hygiene/issues` on device-intelligence, proxied by
  data-api at `domains/core-platform/data-api/src/hygiene_endpoints.py:84`
- **Dashboard** — the "Device Health" tab
  (`domains/core-platform/health-dashboard/src/components/tabs/HygieneTab.tsx`)
- **Remediation** — `remediation_service.apply_action()` writes back to HA:
  `_rename_device`, `_assign_area`, `_enable_entity`, `_start_config_flow`

## Verifying it works

```bash
docker logs homeiq-device-intelligence 2>&1 | grep -E "Persisted|Hygiene|HA Discovery"
```

Expect three lines per cycle:

```
HA Discovery: 93 devices, 767 entities, 17 areas, 52 config entries
Persisted 767 entities to device_entities
Hygiene analyzer produced 88 findings
```

Then confirm the rows landed — the logs alone are not proof, since the analyzer
counted findings correctly for months while failing to persist any of them:

```sql
SELECT issue_type, severity, count(*)
FROM devices.device_hygiene_issues GROUP BY 1,2 ORDER BY 3 DESC;
```

An empty `device_entities` table means `_persist_entities()` is not running,
and every entity-scoped finding is being silently dropped on the FK.

## Failure modes

Each of these presented as "no issues" rather than as an error. That pattern —
an empty result and a healthy one being indistinguishable — is the thing to
watch for here.

**1. The WebSocket client could not connect (fixed 2026-08-18).**
`domains/ml-engine/device-intelligence-service/src/clients/ha_client.py`
called `websockets.connect(..., extra_headers=…)`. That keyword was removed
in websockets 14 in favour of `additional_headers`, and the image
ships 17.x, so every attempt raised `TypeError` before the handshake. The header
was redundant anyway — HA authenticates the WebSocket in-band — so it was
dropped rather than renamed, which is version-proof.

**2. Discovery never started (fixed 2026-08-18).**
`lifespan.on_startup` registered only `database` and `analytics-engine`. The
service was constructed lazily as a FastAPI dependency of the
`/api/discovery/*` routes, and nothing polls those, so the 5-minute loop never
ran. It is now a startup hook; a failure there is logged and swallowed so an
unreachable HA leaves the rest of the service serving.

A related latent bug: `get_discovery_service()` assigned the singleton *before*
`start()`, so one failed start cached a stopped service for the life of the
process. It now publishes only on success.

**3. Every finding was rejected by a foreign key (fixed 2026-08-18).**
`device_hygiene_issues.entity_id` references `device_entities`, and **nothing
ever populated that table**. The analyzer ran, produced findings, and lost all
of them to `ForeignKeyViolationError`. `_persist_entities()` now mirrors the
entity registry ahead of the analyzer, nulling `device_id` when the referenced
device has not synced yet so one unsynced entity cannot take down the batch.

## Related

- Zigbee-specific checks and the nightly audit live in
  `docs/operations/init-gateway.md`
- **No area or room inference exists in HomeIQ.** `missing_area` reports the
  gap and relays Home Assistant's own `suggested_area` when present, which on
  a WebSocket-sourced registry is never — HA does not return that field from
  `device_registry/list`. Name-based area suggestion exists separately in
  `ha-setup-service`; see TAP-6228.
