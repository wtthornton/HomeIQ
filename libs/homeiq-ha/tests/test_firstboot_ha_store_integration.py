"""Integration test: tier-2 persistence of the minted HA credential (TAP-6572).

`test_firstboot_ha_integration.py` proves the mint against a fresh container.
This module proves what happens to the minted credential *afterwards*: it is
stored AES-GCM-encrypted under the tier-1 DEK, a SECOND OS PROCESS finds it
there and skips onboarding, and a rotated DEK stops the boot rather than
quietly minting a second owner.

Why this is a separate module from the B1 mint test
---------------------------------------------------
HA's `user` onboarding step is irreversible: a container can be onboarded
exactly once. B1's test mints through the library and this module mints through
`scripts/appliance/firstboot_ha.py`, so the two proofs need two virgin
containers and therefore two `docker compose up`/`down -v` cycles. Sharing one
module would have made whichever test ran second silently assert nothing.

Why every boot is a subprocess
------------------------------
Each boot below is a real `python -I scripts/appliance/firstboot_ha.py`, so no
module-level cache, no warm asyncio loop and no fixture-held object can carry
the token from boot one into boot two. A store that persisted nothing would
make boot two re-onboard, and HA would refuse it — which is the failure this
shape exists to catch, and which an in-process "second boot" would hide.

The target comes ONLY from $HIQ_B1_HA_BASE_URL — no fallback to a default host,
none to $HA_TOKEN or $HOME_ASSISTANT_TOKEN, and the subprocess environment is
built up rather than inherited so a stray host token cannot reach the script.
An unset target FAILS the precondition test rather than skipping it, and the
live production HA box (192.168.1.80) is refused outright.
"""

from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from homeiq_ha.agent.onboarding import OnboardingState
from homeiq_ha.secrets.states import DEK_KEY, SecretState
from homeiq_ha.secrets.store import HA_TOKEN_KEY, SECRET_TABLE

pytestmark = pytest.mark.integration

_BASE_URL_ENV = "HIQ_B1_HA_BASE_URL"
_LIVE_HA_HOST = "192.168.1.80"
_THROWAWAY_PORT = 28123


def _read_base_url() -> str:
    return os.environ.get(_BASE_URL_ENV, "")


def test_precondition_base_url_env_is_set_and_targets_the_throwaway_ha() -> None:
    """FAILS (never skips) when the target precondition does not hold.

    An unset $HIQ_B1_HA_BASE_URL, or one pointed anywhere but the throwaway
    container on 127.0.0.1:28123, is a broken test run and not an absent one.
    A skip here would let a misconfigured run — or an env leak pointing at the
    real house — report "nothing to see here".
    """
    base_url = _read_base_url()
    assert base_url, f"{_BASE_URL_ENV} must be set to the throwaway HA base URL"
    parsed = urlparse(base_url)
    assert parsed.hostname != _LIVE_HA_HOST, "refusing to target the live production HA box"
    assert parsed.hostname == "127.0.0.1", f"expected 127.0.0.1, got {parsed.hostname!r}"
    assert parsed.port == _THROWAWAY_PORT, f"expected port 28123, got {parsed.port!r}"


_FIRSTBOOT = Path(__file__).resolve().parents[3] / "scripts" / "appliance" / "firstboot_ha.py"
_SKIP_LINE = "onboarding skipped: reusing stored credential"


def _fresh_dek() -> str:
    return AESGCM.generate_key(bit_length=256).hex()


def _write_tier1(state_dir: Path, dek_hex: str) -> None:
    """Write the one tier-1 key this lane consumes, in firstboot-secrets.sh's format."""
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / ".env").write_text(
        f"# scratch tier-1 file for the integration boots\n{DEK_KEY}={dek_hex}\n",
        encoding="utf-8",
    )


def _boot(state_dir: Path, base_url: str) -> subprocess.CompletedProcess[str]:
    """One first-boot process. A deliberately minimal env: no host HA_TOKEN.

    The environment is built up rather than inherited so a stray
    `HA_TOKEN` / `HOME_ASSISTANT_TOKEN` on the developer's box cannot reach the
    script and make a broken store look like a working one.
    """
    return subprocess.run(
        [sys.executable, "-I", str(_FIRSTBOOT)],
        env={
            "PATH": "/usr/bin:/bin",
            "HA_FIRSTBOOT_BASE_URL": base_url,
            "HOMEIQ_STATE_DIR": str(state_dir),
        },
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )


def _decrypt_stored_token(state_dir: Path, dek_hex: str) -> str:
    """Open the stored row with nothing but the DEK and the file — no library state."""
    payload = json.loads(
        (state_dir / "secrets" / SECRET_TABLE / f"{HA_TOKEN_KEY}.json").read_text()
    )
    return (
        AESGCM(bytes.fromhex(dek_hex))
        .decrypt(
            base64.b64decode(payload["nonce"]),
            base64.b64decode(payload["value"]),
            payload["key"].encode(),
        )
        .decode()
    )


def _http_status(url: str, token: str | None = None) -> int:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    request = urllib.request.Request(url, headers=headers)  # noqa: S310 - literal http:// to 127.0.0.1
    try:
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
            return int(response.status)
    except urllib.error.HTTPError as exc:
        return int(exc.code)


def _onboarding_user_done(base_url: str) -> bool:
    request = urllib.request.Request(f"{base_url}/api/onboarding")  # noqa: S310
    with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
        steps = json.loads(response.read())
    return any(step["step"] == "user" and step["done"] for step in steps)


def _require_throwaway_target() -> str:
    base_url = _read_base_url()
    assert base_url, f"{_BASE_URL_ENV} must be set to the throwaway HA base URL"
    parsed = urlparse(base_url)
    assert parsed.hostname != _LIVE_HA_HOST, "refusing to target the live production HA box"
    assert parsed.hostname == "127.0.0.1", f"expected 127.0.0.1, got {parsed.hostname!r}"
    assert parsed.port == _THROWAWAY_PORT, f"expected port 28123, got {parsed.port!r}"
    return base_url


@pytest.fixture(scope="module")
def first_boot(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, str, str]:
    """Onboard the container once and return ``(state_dir, dek_hex, token)``.

    Module-scoped because HA's ``user`` step is irreversible: the container can
    be onboarded exactly once, so both tests below share that one first boot
    rather than pretending each can start from a fresh instance.
    """
    base_url = _require_throwaway_target()
    state_dir = tmp_path_factory.mktemp("hiq-b3-state")
    dek_hex = _fresh_dek()
    _write_tier1(state_dir, dek_hex)

    boot = _boot(state_dir, base_url)
    assert boot.returncode == 0, f"boot 1 failed: {boot.stdout}\n{boot.stderr}"
    payload = json.loads(boot.stdout)
    assert payload["state"] == OnboardingState.COMPLETED.value, payload
    assert payload["key"] == HA_TOKEN_KEY

    token = _decrypt_stored_token(state_dir, dek_hex)
    assert len(token) > 20
    # Boot 1 must not have printed the credential it just stored.
    assert token not in boot.stdout
    assert token not in boot.stderr
    assert dek_hex not in boot.stdout + boot.stderr
    return state_dir, dek_hex, token


def test_a_second_boot_skips_onboarding_and_reuses_the_stored_credential(
    first_boot: tuple[Path, str, str],
) -> None:
    """VAL-070: the documented skip line, and the reused token still authenticates."""
    state_dir, dek_hex, token = first_boot
    base_url = _require_throwaway_target()

    second = _boot(state_dir, base_url)

    assert second.returncode == 0, f"{second.stdout}\n{second.stderr}"
    assert _SKIP_LINE in second.stderr, second.stderr
    assert json.loads(second.stdout)["state"] == "reused"

    # The stored row is unchanged and still opens to the same token...
    assert _decrypt_stored_token(state_dir, dek_hex) == token
    # ...and HA still accepts it, which is what "reused" has to mean.
    assert _http_status(f"{base_url}/api/", token) == 200
    assert _http_status(f"{base_url}/api/") == 401
    # Neither the token nor the DEK reached any log line.
    assert token not in second.stdout + second.stderr
    assert dek_hex not in second.stdout + second.stderr


def test_a_rotated_dek_reports_unsealed_and_never_re_onboards(
    first_boot: tuple[Path, str, str],
) -> None:
    """The DEK-rotation control: stop, do not mint a second owner.

    A store that fell back to plaintext, or that treated an undecryptable row as
    an absent one, would onboard again here. HA would either refuse (a confusing
    failure) or issue a second owner token, orphaning the credential the
    appliance is already using. Both are silent; the assertions below are not.
    """
    state_dir, dek_hex, token = first_boot
    base_url = _require_throwaway_target()
    assert _onboarding_user_done(base_url), "precondition: HA is already onboarded"

    _write_tier1(state_dir, _fresh_dek())
    try:
        rotated = _boot(state_dir, base_url)
    finally:
        _write_tier1(state_dir, dek_hex)

    payload = json.loads(rotated.stdout)
    assert payload["state"] == SecretState.SECRET_STORE_UNSEALED.value, payload
    assert rotated.returncode == 79, rotated.stderr

    # HA was not touched: the owner step is still done and still exactly one
    # owner's token works — the original one.
    assert _onboarding_user_done(base_url)
    assert _http_status(f"{base_url}/api/", token) == 200
    # And the row itself is intact: the original DEK still opens it.
    assert _decrypt_stored_token(state_dir, dek_hex) == token


def test_the_state_dir_precondition_fails_rather_than_skipping(
    tmp_path: Path,
) -> None:
    """A boot with no tier-1 DEK anywhere is SecretStoreUnsealed, not a mint.

    This is the counterpart of the base-URL precondition above: a missing
    precondition must FAIL loudly. An appliance whose tier-1 file never got
    written must not quietly onboard and hold the credential in memory.
    """
    base_url = _require_throwaway_target()
    empty_state = tmp_path / "no-tier1"
    empty_state.mkdir()

    boot = _boot(empty_state, base_url)

    assert boot.returncode == 79, f"{boot.stdout}\n{boot.stderr}"
    assert json.loads(boot.stdout)["state"] == SecretState.SECRET_STORE_UNSEALED.value
