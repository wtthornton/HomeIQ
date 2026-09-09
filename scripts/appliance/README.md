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
