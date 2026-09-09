# scripts/appliance/

First-boot entry points for the appliance. Not a package — invoked directly.

## `firstboot_ha.py` (TAP-6570, TAP-6572)

Drives HA's onboarding flow against a running HA instance, mints the per-install
long-lived token, and persists it in the tier-2 store so a later boot reuses it. Thin CLI wrapper around the stable function
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

- **Secret persistence (TAP-6572, done)**: the script now reads the store
  *before* it calls HA, per the ADR, and writes `result.credential.token` to
  `ha_token` on `COMPLETED`. See "Tier-2 persistence" below.
- **Lane A3 (readiness probe)**: call `run_first_boot` (or inspect a
  persisted result) and treat `COMPLETED` / `ALREADY_ONBOARDED` as "HA has an
  owner", any other state as "not ready yet".

## CLI usage

```bash
HA_FIRSTBOOT_BASE_URL=http://127.0.0.1:28123 \
  HOMEIQ_STATE_DIR=/var/lib/homeiq \
  python scripts/appliance/firstboot_ha.py
```

Prints one line of JSON to stdout: `{"state": ..., "detail": ..., "key": ..., "username": ...}`.
**The token is not printed.** Lane B1 returned it on stdout because it had
nowhere to put it; it now has the store, and the credential leaves the process
only encrypted. A boot log therefore contains neither the token nor the DEK.

| Exit | Meaning |
|---|---|
| `0` | the credential is in the store — minted and written this boot (`completed`), or already present and reused (`reused`) |
| `1` | a named onboarding failure: `unreachable`, `user_step_rejected`, `token_exchange_failed`, `long_lived_mint_failed` |
| `2` | no base URL. A failed precondition, never a silent fallback to a default host |
| `75` | `SecretStoreUnavailable` — the store is down, not wrong. Retryable |
| `79` | `SecretStoreUnsealed` — the DEK is missing, malformed, or no longer the one the stored row was written under |
| `80` | `SecretNotProvisioned` — HA is already onboarded by something else and this appliance holds no row for it |

`75`/`79`/`80` come from `homeiq_ha.secrets.states.EXIT_CODES`, so this script,
`firstboot-secrets.sh` and the ADR's failure table use one set of numbers.

## Tier-2 persistence (TAP-6572)

`homeiq_ha.secrets.store.ApplianceSecretStore` holds runtime secrets as AES-GCM
ciphertext under the tier-1 `HOMEIQ_SECRET_DEK`: a fresh 12-byte `os.urandom`
nonce per write, and the key name as associated data, so a blob written for
`ha_token` will not decrypt as anything else.

The ADR mandates Postgres (`core.appliance_secret`), and
`PostgresSecretBackend` is that adapter — same SQL, same four columns, the ADR's
`SecretStoreUnavailable` on an unreachable server and `SecretNotProvisioned` on a
missing row, unit-tested against a fake connection. What is wired into the boot
path today is `FileSecretBackend`, which writes identical rows under
`$HOMEIQ_STATE_DIR/secrets/core.appliance_secret/<key>.json` at mode `0600`.
Both satisfy the same `SecretBackend` protocol and the same wire format, so
moving the appliance onto Postgres is a constructor change.

**Consumers call one function.** A HomeIQ service or the AgentForge publish step
obtains the Home Assistant credential with:

```python
from homeiq_ha.secrets.store import load_ha_token

token = load_ha_token()          # $HOMEIQ_STATE_DIR, or /var/lib/homeiq
```

It raises `SecretStoreError(SecretNotProvisioned)` before the appliance has been
onboarded. That is the documented standby state and belongs on `/ready` as
not-ready — it is **never** an empty string, because an empty token builds an
anonymous client that reports Home Assistant's refusal as a Home Assistant
problem.

### The boot order, and why it is the ADR's

The script reads the store first and calls HA second. Two of its three
interesting outcomes depend on that:

- **A second boot is a store read.** HA is never contacted, so no transient HA
  failure can be mistaken for a fresh appliance. The boot logs
  `onboarding skipped: reusing stored credential` and exits `0`.
- **A rotated or absent DEK is caught before any onboarding call.** The stored
  row will not decrypt, the boot reports `SecretStoreUnsealed` and exits `79`,
  and HA's onboarding state is untouched. Onboarding again would mint a *second*
  owner and orphan the credential the appliance is already using.

There is no plaintext fallback, no re-mint on a decrypt failure, and no reading
of `HA_TOKEN` / `HOME_ASSISTANT_TOKEN` from the host environment.

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
