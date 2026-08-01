# Session handoff
**Updated:** 2026-08-01T09:20:00Z (LIVE DEPLOY session)
**Git:** master @ f09d6da7, tree clean, no other branches
**Linear P0:** none

## 🟢 THE STACK IS LIVE against the new HA
- HA 2026.7.4 @ `http://192.168.1.80:8123` (resolved from homeassistant.local; containers need the IP — mDNS doesn't work in Docker DNS). **User should set a DHCP reservation for 192.168.1.80.**
- **57/58 containers healthy.** Only `ha-ai-agent-service` down — crash-loops with a clear "OPENAI_API_KEY is required" error. 🔑 **Waiting on the user's OpenAI key**; add to `.env` (`OPENAI_API_KEY=`) then `docker compose -f domains/automation-core/compose.yml --env-file .env --profile production up -d ha-ai-agent-service`.
- **Event flow PROVEN end-to-end:** synthetic `sensor.homeiq_deploy_test` AND real home traffic (Family Room TV media_player events) landed in InfluxDB `home_assistant_events` bucket within seconds. Test sensor deleted afterwards.
- **Smoke suite 8/8 passed (4/4 critical).** `validate-ha-connection.sh` 4/5 (its own WS probe tool is the warning; the service connects fine).

## Environment facts (needed to operate this deploy)
- Root `.env` (gitignored, mode 600) holds: HA quartet + token, fresh-generated `API_KEY`/`JWT_SECRET_KEY`/`POSTGRES_PASSWORD`/`INFLUXDB_TOKEN`/`INFLUXDB_PASSWORD`/`ADMIN_PASSWORD`/`AI_CORE_API_KEY`, `ZEEK_INTERFACE=enp87s0`, and **host-port overrides** (this box runs AgentForge/tapps/other stacks): postgres→15432, websocket→18001, admin→18004, dashboard→13000, retention→18080, carbon→18010, OTLP gRPC→14317, OTLP HTTP→14318, jaeger UI→16687, UI→13001. Old .env backed up at `.env.backup-pre-new-ha-20260801`.
- Compose ports are `${HOMEIQ_*_HOST_PORT:-<documented>}` (commit b8569059). Smoke tests honor the same overrides (f09d6da7).
- `docker buildx bake` REQUIRES `-f docker-bake.hcl` (root compose volume conflict). NOTE: several compose services have `build:` but no `image:` — bake-built images are NOT what compose runs for those; rebuild via `docker compose ... up -d --build <service>` (bit us on device-intelligence).
- Fleet ops: `bash scripts/domain.sh start|stop|verify <domain>`; health: `bash scripts/check-service-health.sh`; smoke: `PATH=<repo>/.venv/bin:$PATH ADMIN_URL=http://localhost:18004 bash scripts/run-smoke-tests.sh --admin-url http://localhost:18004`.

## Fixed during bring-up (all committed)
- device-intelligence crash-loop: `MQTT_BROKER=""` now means "unconfigured → Zigbee discovery off" (validator + DiscoveryService guards + 5 regression tests).
- Smoke wrapper/script drift (`--admin-url` unsupported) fixed.
- zeek needed `ZEEK_INTERFACE=enp87s0` (host NIC; default eth0 doesn't exist). zeek + zeek-network-service healthy after.
- dashboard nginx crash-loops until ALL upstream services exist (ai-automation-service-new, ha-setup-service) — start order matters; it self-heals on restart once upstreams are up.
- ha-simulator unbuildable from fresh clone (gitignored data/) — fixed f84cfbf2.

## Open / follow-ups
1. 🔑 **OPENAI_API_KEY** from user → ha-ai-agent-service up → fleet 58/58.
2. User should **revoke old HA tokens & rotate the burned shared API key** (still in git history; optional history scrub).
3. postgres data: fresh volumes, schemas created by services + init-schemas.sql. InfluxDB org `homeiq`, bucket `home_assistant_events`, admin user `homeiq_admin` (creds in .env).
4. Pre-existing test debt still open: proactive-agent 16F/6E, ai-training 24 DB-fixture errors, openvino health-shape rot, device-intelligence full suite (one test hangs on real MQTT connect; one test writes real model artifacts into models/ — should use tmp_path).
5. No CI e2e for HA→Influx flow (ha-simulator unused); deploy-production.yml still contradicts docs.
6. grafana/prometheus/alertmanager up but dashboards/alerts not yet reviewed against the new install.

## Verify
- `docker ps --filter name=homeiq` → 57 healthy + ha-ai-agent restarting
- Event flow: toggle any entity in HA, then
  `docker exec homeiq-influxdb influx query 'from(bucket: "home_assistant_events") |> range(start: -5m) |> limit(n:5)' --org homeiq --token "$INFLUXDB_TOKEN"`
- `curl http://localhost:18001/health` (websocket-ingestion), `curl http://localhost:18004/api/v1/health` (admin-api)

## Success criterion
Met (partial→full pending OpenAI key): stack live against new HA, events verifiably in InfluxDB, smoke 8/8. Full = 58/58 after key arrives.
