# Init gateway — audit, converge, and the Zigbee watchdog

The HA init agent (`libs/homeiq-ha/src/homeiq_ha/agent/`) is served over HTTP by
`ha-setup-service` (container `homeiq-setup-service`, host port **8024**,
routes in `domains/device-management/ha-setup-service/src/routes_init.py`).

## Endpoints

| Route | Method | Semantics |
|---|---|---|
| `/api/v1/init/audit` | GET | Runs every recipe's `check()` behind a read-only proxy (`readonly.py`) that raises on any write. Always safe. Returns one outcome row per recipe: `status` (`satisfied` / `needs_apply` / `blocked_on_human` / `not_applicable`), `summary`, `details`, `human_action`. |
| `/api/v1/init/converge` | POST `{"phase": N, "only": "<recipe>"}` (both optional) | Backup-gated plan→apply→verify. A backup is taken before every phase past the gate; a `blocked_on_human` outcome halts later phases (`engine.py`). HA writes go ONLY through this path. |

## Nightly audit artifact

`scripts/init-agent-nightly-audit.sh` (cron `15 3 * * *`) curls the audit
endpoint and writes `.tapps-mcp/init-audit-<date>.json` atomically. These
artifacts contain real-home data (IEEE addresses, coordinator IP, area names)
and are gitignored — never commit them.

## Zigbee coordinator watchdog (TAP-5983)

`zigbee.coordinator_watchdog` alerts — a `blocked_on_human` row with a
`human_action` — when any `zha`/`smlight` config entry is in a state other
than `loaded`/`setup_in_progress`, or when the coordinator's TCP socket does
not accept a connection. The probe connects and sends zero bytes, which the
SLZB-06 series tolerates alongside ZHA's live session.

### Staging the alert (no code edit needed)

The probe target defaults to `ZHA_SERIAL_PATH` (`homeiq_ha/agent/zha.py`) and
is overridable via the `HOMEIQ_ZHA_SERIAL_PATH` environment variable, read by
`default_recipes()` at call time. To stage a coordinator-unreachable alert
against production wiring without touching the live coordinator:

```bash
docker exec -e HOMEIQ_ZHA_SERIAL_PATH=socket://192.168.1.121:9999 \
  -i homeiq-setup-service python - <<'EOF'
import asyncio, json
from homeiq_ha.agent import HAInitAgent
from homeiq_ha.agent.recipes import default_recipes
from homeiq_ha.client import HAClient

async def main():
    agent = HAInitAgent(default_recipes())
    async with HAClient.from_env() as ha:
        report = await agent.audit(ha, only="zigbee.coordinator_watchdog")
        o = report.outcomes[0]
        print(json.dumps({"status": o.check.status.value,
                          "summary": o.check.summary,
                          "human_action": o.check.human_action}, indent=2))

asyncio.run(main())
EOF
```

Expected: `status: blocked_on_human`, a summary starting `ZIGBEE ALERT:
coordinator ... unreachable`, and a power-cycle `human_action`. Port 9999 is
closed on the SLZB, so the connect is refused instantly and harmlessly.

## Supervisor logs

The WS `supervisor/api` passthrough cannot transport text logs (HA core
JSON-decodes every Supervisor response — log endpoints return `text/plain`
and die as `unknown_error`; verified on HA 2026.8.1). The supported path is
`HARestClient.get_supervisor_logs("/core/logs")` → `GET /api/hassio/core/logs`,
which returns journald text (ANSI codes included). `supervisor_api()` refuses
log endpoints up front and names that method (TAP-5984).

## Related evaluations

Device-configuration decisions made through this gateway's read paths are
recorded as evidence docs — e.g. the Inovelli smart-bulb-mode evaluation
(`docs/operations/smart-bulb-mode-evaluation.md`, TAP-5988).

## Rebuilding the gateway

The lib is baked into the image — after any `libs/homeiq-ha` change:

```bash
docker compose -f domains/device-management/compose.yml --env-file .env \
  --profile production up -d --build ha-setup-service
```

`--env-file .env` is required on single-service deploys (wrong postgres
password otherwise). Verify by identity, not by build exit code:

```bash
docker exec homeiq-setup-service python -c \
  "from homeiq_ha.agent.recipes import default_recipes; print([r.name for r in default_recipes()])"
```
