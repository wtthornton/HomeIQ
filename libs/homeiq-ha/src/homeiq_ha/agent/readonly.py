"""Read-only enforcement for ``audit`` mode.

``audit`` is the default mode and the only one safe to run unattended, so
"it writes nothing" must be a property of the code rather than a promise in a
docstring. :func:`read_only` wraps an :class:`~homeiq_ha.client.HAClient` in a
proxy that raises :class:`ReadOnlyViolation` the moment a recipe attempts a
write — the call never reaches Home Assistant.

A recipe with a buggy ``check()`` therefore fails loudly during an audit
instead of quietly mutating someone's home.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeiq_ha.client.errors import HAClientError

if TYPE_CHECKING:
    from homeiq_ha.client import HAClient

#: WebSocket command suffixes that only read.
_READ_SUFFIXES = ("/list", "/get")

#: Whole command types that only read.
_READ_COMMANDS = frozenset(
    {
        "get_states",
        "get_config",
        "get_services",
        "auth/current_user",
        "backup/info",
        "backup/config/info",
        "backup/agents/info",
    }
)


class ReadOnlyViolation(HAClientError):
    """A recipe attempted a write while running in read-only mode."""

    def __init__(self, operation: str) -> None:
        super().__init__(
            f"Write blocked in read-only mode: {operation}. "
            "check() and plan() must not mutate Home Assistant."
        )
        self.operation = operation


def is_read_command(command_type: str, fields: dict[str, Any] | None = None) -> bool:
    """Classify a WebSocket command as read-only.

    ``supervisor/api`` is judged by the HTTP method it carries, since the same
    command both reads Supervisor state and installs add-ons.
    """
    if command_type == "supervisor/api":
        method = str((fields or {}).get("method", "get")).lower()
        return method in {"get", "head"}
    if command_type in _READ_COMMANDS:
        return True
    return command_type.endswith(_READ_SUFFIXES)


class _ReadOnlyWebSocket:
    """WebSocket proxy that refuses write commands."""

    def __init__(self, inner: Any, journal: list[str]) -> None:
        self._inner = inner
        self._journal = journal

    async def send_command(
        self,
        command_type: str,
        *,
        timeout: float | None = None,
        fields: dict[str, Any] | None = None,
        **payload: Any,
    ) -> Any:
        if not is_read_command(command_type, fields):
            raise ReadOnlyViolation(f"ws {command_type}")
        self._journal.append(f"ws {command_type}")
        return await self._inner.send_command(
            command_type, timeout=timeout, fields=fields, **payload
        )

    def __getattr__(self, item: str) -> Any:
        # Named helpers (list_entities, update_device, ...) are thin wrappers
        # over send_command. Rebind them onto this proxy so their internal
        # send_command call is the guarded one.
        attr = getattr(type(self._inner), item, None)
        if callable(attr):
            return attr.__get__(self, type(self._inner))
        return getattr(self._inner, item)


class _ReadOnlyRest:
    """REST proxy that refuses any non-GET request."""

    def __init__(self, inner: Any, journal: list[str]) -> None:
        self._inner = inner
        self._journal = journal

    async def request(self, method: str, path: str, **kwargs: Any) -> Any:
        if method.upper() not in {"GET", "HEAD"}:
            raise ReadOnlyViolation(f"rest {method.upper()} {path}")
        self._journal.append(f"rest {method.upper()} {path}")
        return await self._inner.request(method, path, **kwargs)

    def __getattr__(self, item: str) -> Any:
        attr = getattr(type(self._inner), item, None)
        if callable(attr):
            return attr.__get__(self, type(self._inner))
        return getattr(self._inner, item)


class ReadOnlyHAClient:
    """An :class:`HAClient` that cannot write.

    Attributes:
        journal: Every call that was allowed through, in order. The audit
            report cites this as evidence of what was read.
    """

    def __init__(self, inner: HAClient) -> None:
        self.journal: list[str] = []
        self._inner = inner
        self.ws = _ReadOnlyWebSocket(inner.ws, self.journal)
        self.rest = _ReadOnlyRest(inner.rest, self.journal)

    @property
    def base_url(self) -> str:
        return self._inner.base_url


def read_only(ha: HAClient) -> ReadOnlyHAClient:
    """Wrap ``ha`` so every write raises :class:`ReadOnlyViolation`."""
    return ReadOnlyHAClient(ha)
