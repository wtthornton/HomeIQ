"""First-boot Home Assistant onboarding and credential minting (TAP-6484).

Drives HA's onboarding API on a fresh appliance to create the owner account and
mint one long-lived token, with no human input.

Why generated rather than baked
-------------------------------
A single *shared* credential is the right shape for an appliance where one owner
process drives everything. A single *constant* credential is not: baking a token
into the image would put the same secret on every appliance ever shipped,
readable by anyone who pulls it. Shared and constant are different properties and
only the first was wanted.

The flow, verified against `ghcr.io/home-assistant/home-assistant:2026.8.3`
--------------------------------------------------------------------------
1. ``GET  /api/onboarding`` -- lists steps and whether each is ``done``. The
   ``user`` step is the one that matters; it is the only irreversible one.
2. ``POST /api/onboarding/users`` (JSON) -- creates the owner, returns
   ``{"auth_code": ...}``. Only callable while ``user`` is not done; afterwards
   HA rejects it, which is what makes step 1 the idempotency check.
3. ``POST /auth/token`` (**form-encoded**, not JSON) with
   ``grant_type=authorization_code`` -- exchanges the code for a short-lived
   ``access_token``. Observed ``expires_in`` is 1800s, so this token is a means,
   never the thing we store.
4. WebSocket ``auth/long_lived_access_token`` -- mints the durable token. This is
   a websocket command with no REST equivalent, which is why this module needs a
   socket at all.

Failures surface as :class:`OnboardingError` with a named
:class:`OnboardingState`. There is deliberately no fallback to a default
credential: a silent fallback would reintroduce the constant-secret problem the
generation exists to avoid.

Dormant: nothing calls this yet
-------------------------------
Nothing outside the tests constructs :class:`HAOnboarder`, and it is exported
from no ``__init__``. That is deliberate, not an oversight. A production caller
has to put the minted token *somewhere*, and the appliance secret store has not
been chosen yet -- that decision is TAP-6571. Wiring a caller up before it lands
would pick a storage mechanism by accident, in the one place nobody would think
to look for the choice.

TAP-6572 wires this into the boot path once TAP-6571 resolves. Until then the
module is complete and tested but intentionally unreachable from production.
"""

from __future__ import annotations

import logging
import secrets
import string
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any
from urllib.parse import urlencode

import aiohttp

if TYPE_CHECKING:
    from collections.abc import Sequence

logger = logging.getLogger(__name__)

#: Long-lived token lifespan in days. HA accepts an int; 10 years is effectively
#: "for the life of the appliance", and rotation is a separate decision
#: (deliberately deferred in the appliance-packaging ADR).
DEFAULT_LIFESPAN_DAYS = 3650

#: Password alphabet. Deliberately excludes shell metacharacters: these values are
#: written into env files and compose interpolation, where a `$` or a quote turns
#: a valid secret into a parse error or a silently truncated value.
_PASSWORD_ALPHABET = string.ascii_letters + string.digits

_OWNER_USERNAME = "homeiq"
_OWNER_NAME = "HomeIQ Owner"
_CLIENT_NAME = "HomeIQ Appliance"


class OnboardingState(StrEnum):
    """Named outcomes. Never a silent fallback to a default credential."""

    COMPLETED = "completed"
    ALREADY_ONBOARDED = "already_onboarded"
    UNREACHABLE = "unreachable"
    USER_STEP_REJECTED = "user_step_rejected"
    TOKEN_EXCHANGE_FAILED = "token_exchange_failed"
    LONG_LIVED_MINT_FAILED = "long_lived_mint_failed"


class OnboardingError(RuntimeError):
    """Onboarding failed at a named step."""

    def __init__(self, state: OnboardingState, detail: str) -> None:
        super().__init__(f"{state.value}: {detail}")
        self.state = state
        self.detail = detail


@dataclass(slots=True)
class OwnerCredential:
    """What a first boot produces. ``token`` is the only durable output."""

    token: str
    username: str
    password: str
    state: OnboardingState = OnboardingState.COMPLETED

    def __repr__(self) -> str:
        """Never render the secrets — repr lands in logs and tracebacks."""
        return (
            f"OwnerCredential(username={self.username!r}, "
            f"token=<redacted {len(self.token)} chars>, "
            f"password=<redacted>, state={self.state.value})"
        )


def generate_password(length: int = 32) -> str:
    """A URL- and shell-safe random password from ``secrets``."""
    if length < 16:
        msg = f"password length {length} is below the 16-character floor"
        raise ValueError(msg)
    return "".join(secrets.choice(_PASSWORD_ALPHABET) for _ in range(length))


def generate_secret(nbytes: int = 32) -> str:
    """A URL-safe token for deployment secrets (API keys, JWT signing keys)."""
    if nbytes < 16:
        msg = f"secret size {nbytes} is below the 16-byte floor"
        raise ValueError(msg)
    return secrets.token_urlsafe(nbytes)


def generate_deployment_secrets(keys: Sequence[str]) -> dict[str, str]:
    """One distinct secret per key.

    Distinctness is the point: reusing one value across `POSTGRES_PASSWORD`,
    `API_KEY` and `JWT_SECRET_KEY` would make a single leak total. Callers pass
    only genuinely secret keys — URLs and usernames in ``env.required`` are
    deployment values, not secrets, and cannot be generated.
    """
    return {key: generate_secret() for key in keys}


@dataclass(slots=True)
class HAOnboarder:
    """Drives a fresh HA instance to a usable long-lived token."""

    base_url: str
    timeout: float = 60.0
    session: aiohttp.ClientSession | None = field(default=None, repr=False)

    @property
    def _client_id(self) -> str:
        # HA validates client_id as a URL matching the request origin.
        return self.base_url.rstrip("/") + "/"

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout))
        return self.session

    async def onboarding_steps(self) -> dict[str, bool]:
        """Map step name to done. Raises UNREACHABLE if HA is not answering."""
        session = await self._get_session()
        try:
            async with session.get(f"{self.base_url}/api/onboarding") as response:
                response.raise_for_status()
                payload = await response.json()
        except (aiohttp.ClientError, TimeoutError) as exc:
            raise OnboardingError(OnboardingState.UNREACHABLE, str(exc)) from exc
        return {str(step["step"]): bool(step["done"]) for step in payload}

    async def _create_owner(self, username: str, password: str) -> str:
        session = await self._get_session()
        body = {
            "client_id": self._client_id,
            "name": _OWNER_NAME,
            "username": username,
            "password": password,
            "language": "en",
        }
        async with session.post(f"{self.base_url}/api/onboarding/users", json=body) as response:
            if response.status != 200:
                detail = f"HTTP {response.status}: {(await response.text())[:200]}"
                raise OnboardingError(OnboardingState.USER_STEP_REJECTED, detail)
            payload = await response.json()
        code = payload.get("auth_code")
        if not code:
            raise OnboardingError(
                OnboardingState.USER_STEP_REJECTED, "response carried no auth_code"
            )
        return str(code)

    async def _exchange_code(self, auth_code: str) -> str:
        """Trade the auth code for a short-lived access token.

        Form-encoded, not JSON — HA's /auth/token rejects a JSON body.
        """
        session = await self._get_session()
        form = urlencode(
            {
                "client_id": self._client_id,
                "grant_type": "authorization_code",
                "code": auth_code,
            }
        )
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        async with session.post(
            f"{self.base_url}/auth/token", data=form, headers=headers
        ) as response:
            if response.status != 200:
                detail = f"HTTP {response.status}: {(await response.text())[:200]}"
                raise OnboardingError(OnboardingState.TOKEN_EXCHANGE_FAILED, detail)
            payload = await response.json()
        access = payload.get("access_token")
        if not access:
            raise OnboardingError(
                OnboardingState.TOKEN_EXCHANGE_FAILED, "response carried no access_token"
            )
        return str(access)

    async def _mint_long_lived(self, access_token: str, lifespan_days: int) -> str:
        """Mint the durable token over the websocket.

        There is no REST equivalent for ``auth/long_lived_access_token``; this is
        the only reason onboarding needs a socket.
        """
        session = await self._get_session()
        ws_url = self.base_url.replace("https://", "wss://").replace("http://", "ws://")
        try:
            async with session.ws_connect(f"{ws_url}/api/websocket") as socket:
                await socket.receive_json()  # auth_required
                await socket.send_json({"type": "auth", "access_token": access_token})
                auth_result = await socket.receive_json()
                if auth_result.get("type") != "auth_ok":
                    raise OnboardingError(
                        OnboardingState.LONG_LIVED_MINT_FAILED,
                        f"websocket auth returned {auth_result.get('type')!r}",
                    )
                await socket.send_json(
                    {
                        "id": 1,
                        "type": "auth/long_lived_access_token",
                        "client_name": _CLIENT_NAME,
                        "lifespan": lifespan_days,
                    }
                )
                result = await socket.receive_json()
        except (aiohttp.ClientError, TimeoutError) as exc:
            raise OnboardingError(OnboardingState.LONG_LIVED_MINT_FAILED, str(exc)) from exc

        if not result.get("success") or not result.get("result"):
            raise OnboardingError(
                OnboardingState.LONG_LIVED_MINT_FAILED, str(result.get("error", result))
            )
        return str(result["result"])

    async def onboard(
        self,
        *,
        username: str = _OWNER_USERNAME,
        password: str | None = None,
        lifespan_days: int = DEFAULT_LIFESPAN_DAYS,
    ) -> OwnerCredential:
        """Create the owner and mint a long-lived token.

        Idempotent by design: a second boot sees ``user`` already done and
        returns ALREADY_ONBOARDED rather than failing or re-onboarding. The
        caller is expected to have stored the credential from the first boot —
        HA will not re-issue it.
        """
        steps = await self.onboarding_steps()
        if steps.get("user", False):
            logger.info("HA owner already exists; skipping onboarding")
            raise OnboardingError(
                OnboardingState.ALREADY_ONBOARDED,
                "the user step is already done; load the stored credential instead",
            )

        password = password or generate_password()
        auth_code = await self._create_owner(username, password)
        access_token = await self._exchange_code(auth_code)
        token = await self._mint_long_lived(access_token, lifespan_days)
        logger.info("minted long-lived HA token for %s", username)
        return OwnerCredential(token=token, username=username, password=password)

    async def close(self) -> None:
        if self.session is not None and not self.session.closed:
            await self.session.close()

    async def __aenter__(self) -> HAOnboarder:
        return self

    async def __aexit__(self, *_exc: Any) -> None:
        await self.close()
