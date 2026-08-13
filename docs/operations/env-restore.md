# Restoring `.env` keys from a backup — key-name level only

The 2026-08-01 Home Assistant migration rewrote the root `.env` from 86 keys
down to 43 and silently dropped every external-feed credential (TAP-5902).
This is the procedure that recovered it, written so it can be repeated
without ever printing a secret value.

## Ground rules

- **Never print values.** Every command below works on key *names*. Agent
  tooling is deny-ruled from reading `.env` content at all.
- **Backups are the only copy of several credentials.** As of 2026-08-12 that
  is `.env.backup-pre-new-ha-20260801`. Do not delete backups until the
  manifest check passes against the restored file.
- `env.required` (repo root) is the committed manifest of which keys the
  stack needs. `scripts/preflight-env.sh` is its checker.

## Procedure

1. **Diff by name.** List keys present in the backup but absent or empty in
   the current file — names only:

   ```bash
   comm -23 \
     <(grep -oE '^[A-Z_][A-Z0-9_]*' .env.backup-pre-new-ha-20260801 | sort -u) \
     <(grep -E '^[A-Z_][A-Z0-9_]*=..*' .env | grep -oE '^[A-Z_][A-Z0-9_]*' | sort -u)
   ```

2. **Decide per key against the manifest.** Keys in `env.required` as
   `required` must come back. `conditional` keys come back if their feed is
   wanted. Keys in neither are candidates for staying gone — the 2026-08-01
   set that should NOT return: `*_PORT` keys superseded by
   `HOMEIQ_*_HOST_PORT`, `LOCAL_HA_URL`/`LOCAL_HA_TOKEN` (retired HA),
   the `SIMULATOR_*` block, `ENABLE_MOCK_DATA_CREATION`,
   `ENABLE_SYNTHETIC_DATA_GENERATION`.

3. **Copy line-wise without display.** For each key to restore:

   ```bash
   grep '^KEY_NAME=' .env.backup-pre-new-ha-20260801 >> .env
   ```

4. **Verify.** `bash scripts/preflight-env.sh` must exit 0 with no missing
   required keys. Then restart affected services
   (`docker compose -f domains/<d>/compose.yml --env-file .env --profile production up -d <service>`
   — single-service deploys need `--env-file`) and probe their real data
   routes, not `/health`.

## Why the preflight exists

`${VAR:-}` compose defaults turn a missing credential into an empty string,
which every consumer treats as "configured, just blank"; combined with
uptime-only health checks (TAP-5903), a credential-dead service looks
healthy. The preflight makes the loss loud at deploy time instead.
