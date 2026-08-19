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

## Zigbee mesh health (TAP-5982)

`zigbee.mesh_health` emits one row per ZHA device — name, IEEE, LQI,
availability, `last_seen` — sorted weakest-LQI-first.

**It blocks now; it did not always.** The check was originally report-only and
returned `satisfied` regardless of what it saw. On 2026-08-18 an Aqara presence
sensor was found to have been off the mesh since 2026-08-12, and **six
consecutive nightly audits had rendered it as a green "6 device(s); 1
unavailable" line**. An unreachable non-coordinator device now degrades the
check to `blocked_on_human` and names the device in `human_action`, because
restoring one means going to the hardware.

Two deliberate scoping decisions:

- **Availability is ZHA's verdict, not a threshold invented here.** ZHA marks a
  device unavailable only after `consider_unavailable_mains` (2 h) or
  `consider_unavailable_battery` (6 h), so anything still flagged at audit time
  has been quiet for hours. This also avoids parsing `last_seen`, which ZHA
  reports as a **naive local timestamp** that a UTC container would misread by
  the whole offset.
- **The coordinator is excluded.** It has no availability of its own, and
  `zigbee.coordinator_watchdog` owns it. Counting it here would double-report.

LQI stays informational — weak links are worth seeing but do not yet imply an
action.

## The SSH write path to `/config`

Recipes that must edit files on the HA host (currently `zha.aqara_fp1e_quirk`)
reach it through the **Terminal & SSH (`core_ssh`) add-on**.
`host_files.SSHHostFiles` shells out to `ssh`; there is no SSH client library
in the dependency tree.

Three things must all be true, or the recipe reports `not_applicable`:

1. **`openssh-client` is in the image.** Added to the `ha-setup-service`
   Dockerfile 2026-08-18. Before that the recipe could never do more than
   report `not_applicable`, because the binary it invokes was absent.
2. **`/home/appuser/.ssh` exists and is writable.** `ssh` runs with
   `StrictHostKeyChecking=accept-new` and writes `known_hosts` there on first
   contact.
3. **The key is mounted and readable.** `HOMEIQ_HA_SSH_KEY` is overridden in
   compose to `/run/secrets/ha_agent_key`; the `.env` value names a **host**
   path and is meaningless inside the container.

### Why the key is a separate copy

A bind mount keeps the host file's ownership, so for the container user
(uid 1001) to open it at all the file must be group-readable — and a
group-readable private key is exactly what OpenSSH refuses. Loosening the
operator's real key would also make `ssh` on the host reject it.

The resolution: mount a **separate 0640 copy** (default
`~/.homeiq-secrets/ha_agent_key`, overridable via `HOMEIQ_HA_SSH_KEY_HOST`),
and let `SSHHostFiles._key_file()` restage it at 0600 under the runtime user's
own `~/.ssh` before invoking `ssh`.

> **This grants the container root SSH to Home Assistant.** To disable the
> write path entirely, drop the mount and the `HOMEIQ_HA_SSH_KEY` override;
> dependent recipes then report `not_applicable` rather than failing.

### `zha.aqara_fp1e_quirk`

Deploys `libs/homeiq-ha/src/homeiq_ha/agent/quirks/aqara_fp1e.py` to
`/config/custom_zha_quirks`, adds the `zha:` config block, and restarts core.
The quirk gives the sensor an occupancy `binary_sensor` it otherwise lacks:
upstream `zha-quirks` registers `lumi.sensor_occupy.agl1`, these units report
`agl8`, so nothing matches them and `quirk_applied` stays `False`.

`check()` buckets units into **quirked / unquirked / uninterviewed**. A unit
whose Basic cluster never answered reads `manufacturer: unk_manufacturer`, and
no quirk can match it — the registry keys on the exact string. Since 2026-08-18
**any uninterviewed unit returns `blocked_on_human`**, even when another unit is
quirked; reporting `satisfied` because *some* unit matched demoted "this
presence sensor has no occupancy entity" to a suffix on a green line.

Recovering an uninterviewed unit needs physical access: factory-reset the
sensor (10 rapid button presses on an FP300 — the 5-second hold is only a
network reset), re-pair it, then run ZHA **Reconfigure** while tapping its
button to keep the radio awake. On HA 2026.6+ reconfigure performs a full
re-interview. The interview truncates because the sensor sleeps partway
through, which is why keeping it awake is the operative step.

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
