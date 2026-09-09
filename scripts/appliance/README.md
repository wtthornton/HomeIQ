# scripts/appliance/

First-boot entry points for the appliance. Not a package — invoked directly.

## `firstboot_ha.py` (TAP-6570)

Drives HA's onboarding flow against a running HA instance and mints the
per-install long-lived token. Thin CLI wrapper around the stable function
other lanes should import instead of shelling out to this script:

```python
async def run_first_boot(
    base_url: str,
    *,
    timeout: float = 60.0,
    username: str = "homeiq",
    password: str | None = None,
    lifespan_days: int = 3650,
) -> FirstBootResult:
    ...

@dataclass(slots=True)
class FirstBootResult:
    state: OnboardingState
    credential: OwnerCredential | None = None
    detail: str = ""
```

`homeiq_ha.agent.onboarding.run_first_boot` — never raises for an expected
outcome. `result.state` is always one of `OnboardingState`:
`COMPLETED`, `ALREADY_ONBOARDED`, `UNREACHABLE`, `USER_STEP_REJECTED`,
`TOKEN_EXCHANGE_FAILED`, `LONG_LIVED_MINT_FAILED`. `result.credential` is set
only on `COMPLETED`.

- **Lane B3 (secret persistence)**: call `run_first_boot`, and on
  `COMPLETED` persist `result.credential.token` to the appliance secret
  store. On `ALREADY_ONBOARDED`, load the previously stored credential
  instead — HA will not re-issue it.
- **Lane A3 (readiness probe)**: call `run_first_boot` (or inspect a
  persisted result) and treat `COMPLETED` / `ALREADY_ONBOARDED` as "HA has an
  owner", any other state as "not ready yet".

## CLI usage

```bash
HA_FIRSTBOOT_BASE_URL=http://127.0.0.1:28123 python scripts/appliance/firstboot_ha.py
```

Prints one line of JSON to stdout: `{"state": ..., "detail": ..., "token": ..., "username": ...}`
(`token`/`username` present only when `state` is `completed`). Exit code `0`
for `completed`/`already_onboarded`, `1` for any other named failure, `2` if
no base URL was given — an unset target is a failed precondition, never a
silent fallback to a default host.

## `firstboot-secrets.sh` (TAP-6573)

Mints the appliance's **tier-1** secrets on the first boot and leaves them alone
on every later one. Tier 1 is the set that has to exist *before* Postgres starts,
so it cannot live in the Postgres-backed store it bootstraps — see
`docs/architecture/adr-appliance-secret-store.md`.

```bash
scripts/appliance/firstboot-secrets.sh          # generate, or check and reuse
scripts/appliance/firstboot-secrets.sh --list-keys
scripts/appliance/firstboot-secrets.sh --list-compose-markers
```

Writes `$HOMEIQ_STATE_DIR/.env` (default `/var/lib/homeiq/.env`) at mode `0600`,
through a temp file created under `umask 077` in the same directory, so the file
is never world-readable and never half-written. `HOMEIQ_STATE_DIR` exists so the
tests can run unprivileged against a scratch directory; it changes the location
and nothing else.

Ten keys: the ADR's tier-1 six, plus `HOMEIQ_SECRET_DEK` (the key that seals the
tier-2 table), plus `ADMIN_PASSWORD`, `HOMEIQ_MCP_READ_TOKENS` and
`INFLUXDB_PASSWORD` — the remaining `${VAR:?required}` markers in
`domains/*/compose.yml`, without which `docker compose config` cannot render.
`POSTGRES_USER` is a fixed non-secret account name (`homeiq`); every other value
is 256 bits of randomness, unique per install.

Consumers need no change: the start script passes
`--env-file /var/lib/homeiq/.env` and Compose's existing interpolation does the
rest. The marker set is pinned in the script and compared against the live
compose files by `test_pinned_compose_markers_match_the_live_compose_files`, so a
new `${VAR:?required}` anywhere turns the suite red rather than surfacing as a
boot failure on a customer's appliance.

**No fallbacks.** On a later boot a key that is missing or empty exits `78` naming
the key, and the file is neither repaired nor regenerated — a re-minted
`POSTGRES_PASSWORD` is an unopenable `postgres_data`. The tier-2 counterparts of
that rule (`SecretStoreUnsealed`, `SecretStoreUnavailable`,
`SecretNotProvisioned`) are named constants in
`homeiq_ha.secrets.states`, which is where Lane B3's store reads them from.

Nothing generated ever reaches stdout, stderr or a log line, and the script
deliberately has no `set -x`.
