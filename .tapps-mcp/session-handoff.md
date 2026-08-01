# Session handoff
**Updated:** 2026-08-01T04:00:00Z (live-deployment prep session)
**Git:** master @ f84cfbf2, all branches merged and deleted, tree clean (except this file)
**Linear P0:** none

## Done (this session)
- **PR #72 merged** (audit rounds 1+2, all 4 services `ship`) and **PR #73 merged** (live-deployment prep, 4 parallel workstreams + follow-ups). master carries everything; no other branches or worktrees exist.
- **Credential hygiene:** HA/Nabu Casa tokens (websocket-ingestion) and `openai_api_key` (proactive-agent, device-intelligence, ai-training) are `SecretStr`, unwrapped only at client-construction boundaries. Regression tests assert repr-masking and unwrap-at-use.
- **Committed secrets sanitized:** `infrastructure/env.production` (3 real HA JWTs, MQTT creds, shared API key, weather keys) is now a placeholder template; ~30 scripts had JWT/API-key defaults stripped; leaked `API_KEY` compose fallbacks removed in 4 domains. **User must revoke the old HA tokens + rotate the shared API key** (still in git history).
- **New-HA readiness:** zero live-code references to the previous owner's HA remain (`192.168.1.86`, committed Nabu Casa URL). Services fail loudly when unconfigured. `infrastructure/env.example` rebuilt as the single authoritative template incl. the HA_URL WS-vs-HTTP footgun doc.
- **Deploy tooling repaired:** exec bits on 14 scripts, `start-prod.sh` → shim onto `start-stack.sh`, `domain.sh verify <domain>` implemented, smoke-test ADMIN_URL → 8004, all 9 domain compose files parse against `env.example` (verified). `docker buildx bake` requires `-f docker-bake.hcl` (root compose volumes conflict otherwise — docs still say the bare form). ha-simulator was unbuildable from a fresh clone (gitignored `data/`) — fixed with tracked empty dir (f84cfbf2).
- **Test debt cleared:** ai-query 37P/4S/0F/0E (was 6F/9E); data-retention FULL suite 138P/0F/0E (was 5F/22E+collection fail; real src bug fixed: backup 201 was unreachable); sports-api 8P (was uncollectable; fixture names + E402 bootstrap fixed); websocket-ingestion 522P (+7); admin-api 376P; proactive-agent 84P (+2, pre-existing 16F/6E unchanged); device-intelligence + openvino conftest `parents[3]`→`parents[4]` (suites collect now).
- Venv gained: boto3, aiosqlite, pandas, pyarrow≥18, influxdb3-python, paho-mqtt, joblib, scikit-learn.

## In flight at session end
- `docker buildx bake -f docker-bake.hcl full` running in background (53 images, ~25-30 min cold). If interrupted: re-run the same command; it resumes from cache.

## 🔑 CREDENTIAL GATE — blocked on user for live deploy
Need from the user (new HA instance is installed + logged in):
1. **New HA base URL** (e.g. `http://<lan-ip>:8123`)
2. **HA long-lived access token** (HA → Profile → Security → Long-Lived Access Tokens)
3. **OpenAI API key** (required — ha-ai-agent-service refuses to boot without it)
4. Optional: Nabu Casa URL+token, Anthropic key, weather/AirNow/WattTime/pricing keys

## Live bring-up sequence (once credentials arrive)
1. Copy `infrastructure/env.example` → `.env` (root `.env` exists with stale/old-HA values — REVIEW before overwrite, it is permission-blocked for reads in agent sessions). Set: HA quartet (`HA_HTTP_URL`, `HA_WS_URL`, `HA_TOKEN`, `HA_URL`=http form) + legacy `HOME_ASSISTANT_*` aliases, `OPENAI_API_KEY`, and generate strong `API_KEY`, `JWT_SECRET_KEY`, `POSTGRES_PASSWORD`, `INFLUXDB_TOKEN`/`INFLUXDB_PASSWORD`, `ADMIN_PASSWORD` (compose defaults are known-leaked values).
2. `bash scripts/validate-ha-connection.sh` (TCP→HTTP→WS→auth→/api/states)
3. `bash scripts/start-stack.sh` (core-platform first, health-gated, then 8 domains)
4. `bash scripts/check-service-health.sh`; smoke: `bash scripts/run-smoke-tests.sh`
5. Real proof: toggle an entity in HA → verify `state_changed` lands in InfluxDB via data-api; check discovery pulled entity/device registries.

## Open / follow-ups (non-blocking)
- device-intelligence full suite: unblocked at collection but a run appeared to hang after paho-mqtt install (suspected real-network MQTT attempt in a test) — killed; targeted tests pass. Also one of its tests trains a real model and writes into `models/` (worktree pollution; should use tmp_path).
- openvino-service `test_openvino_service.py`: rotted vs `StandardHealthCheck` refactor (old bespoke health shape asserted) — needs a test-module rewrite; Tier 3, not deploy-blocking.
- proactive-agent pre-existing 16F/6E; ai-training 24 DB-fixture errors (need live PG) — untouched.
- `192.168.1.86` remains in tests/docs/generated caches only. Old HA tokens + shared API key remain in git history — rotate; optional history scrub.
- No true HA→ingest→InfluxDB e2e test exists; ha-simulator is wired in dev compose but unused by CI.
- CI gate (af-agent-gate.yml) still needs operator runner + secrets. `.github/workflows/deploy-production.yml` runs bare `docker compose up -d` from root (contradicts docs, omits `--profile production`) — fix before relying on CI deploys.

## Verify
- `git log --oneline -6` — f84cfbf2 (ha-simulator), 947bf8fb (PR #73 merge), 29076310, a479c39e, 62c02838, 51f373fd
- Suites: per-service `/home/wtthornton/code/HomeIQ/.venv/bin/python -m pytest tests/ -q` (system python3 has no pytest); counts above
- `for d in <9 domains>; do docker compose -f domains/$d/compose.yml --env-file infrastructure/env.example config --quiet; done` — all parse
- `grep -rn 192.168.1.86 domains/ scripts/ infrastructure/ --include='*.py' --include='*.yml' | grep -v tests/` — empty

## Success criterion
Stack deploys against the new HA with `state_changed` events verifiably landing in InfluxDB, all Tier-1 health checks green.
