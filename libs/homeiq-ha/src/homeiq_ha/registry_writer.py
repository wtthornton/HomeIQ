"""The one path that writes a name or an area to Home Assistant.

Every caller that renames a device or an entity, or moves one into an area,
routes through this module (TAP-6230). Centralising it buys two properties that
no caller had on its own.

**Nothing reports a write it did not make.** Each write re-reads the registry and
compares the stored value against what was asked for. ``sync_name_to_ha`` logged
"Synced name" for months while calling ``homeassistant.update_entity`` -- a
state-refresh service with no ``name`` field -- because a 200 was taken as proof
of a rename. A read-back is the only evidence that survives calling the wrong API
entirely.

**entity_id slugs never move.** They are foreign keys elsewhere in HomeIQ. Home
Assistant renames a slug only when handed ``new_entity_id``, so this module never
sends that field. Renaming a *device* does not touch slugs either: as of HA core
2026.8.2 ``config/device_registry/update`` accepts only ``area_id``,
``disabled_by``, ``labels`` and ``name_by_user``, and never reaches the entity
registry. What a device rename does change is the *friendly name* of its
``has_entity_name`` entities, which HA computes from the device name at read time.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from .client.errors import HAClientError, HACommandError

logger = logging.getLogger(__name__)

#: HA keeps a device's integration-supplied ``name`` read-only and stores the
#: user's override in ``name_by_user``. Entities spell the same thing ``name``.
_DEVICE_NAME_FIELD = "name_by_user"
_ENTITY_NAME_FIELD = "name"


class RegistryWriteError(HAClientError):
    """Base for every refusal or failure raised by the gateway."""


class UnknownTarget(RegistryWriteError):
    """The device, entity or area named does not exist in the registry."""


class WriteNotVerified(RegistryWriteError):
    """Home Assistant accepted the write but the registry does not show it.

    This is the failure ``sync_name_to_ha`` could not raise. It means the command
    succeeded at the transport level and still changed nothing -- a wrong command
    type, a field the schema silently drops, or an id that addressed the wrong
    object.
    """


@dataclass(frozen=True)
class WriteResult:
    """What the registry held before, and what it holds now.

    ``wrote`` is False when the registry already carried the requested value, so
    callers can distinguish "converged" from "changed" without a second read.
    Reaching a caller at all means the value was verified present.
    """

    target: str
    field: str
    requested: str | None
    previous: str | None
    wrote: bool


class HARegistryWriter:
    """Verified name and area writes against the Home Assistant registries.

    Takes anything exposing ``send_command`` -- pass ``client.ws``. Commands go
    out through that one method rather than the typed helpers so the gateway
    composes with the read-only proxy and the test simulator unchanged.
    """

    def __init__(self, ws: Any) -> None:
        self._ws = ws

    # -- entities ----------------------------------------------------------

    async def set_entity_name(self, entity_id: str, name: str | None) -> WriteResult:
        """Set an entity's user-facing name. ``None`` restores the integration's."""
        return await self._write_entity(entity_id, _ENTITY_NAME_FIELD, name)

    async def set_entity_area(self, entity_id: str, area_id: str | None) -> WriteResult:
        """Move an entity into an area. ``None`` clears it back to its device's."""
        await self._require_area(area_id)
        return await self._write_entity(entity_id, "area_id", area_id)

    # -- devices -----------------------------------------------------------

    async def set_device_name(self, device_id: str, name: str | None) -> WriteResult:
        """Set a device's user-facing name. ``None`` restores the integration's.

        Prefer this over renaming each entity: HA recomputes the friendly name of
        every ``has_entity_name`` entity on the device from this one value.
        """
        return await self._write_device(device_id, _DEVICE_NAME_FIELD, name)

    async def set_device_area(self, device_id: str, area_id: str | None) -> WriteResult:
        """Move a device, and every entity that inherits from it, into an area."""
        await self._require_area(area_id)
        return await self._write_device(device_id, "area_id", area_id)

    # -- internals ---------------------------------------------------------

    async def _write_entity(
        self, entity_id: str, field: str, value: str | None
    ) -> WriteResult:
        before = await self._entity(entity_id)
        if before.get(field) == value:
            return WriteResult(entity_id, field, value, value, wrote=False)

        await self._ws.send_command(
            "config/entity_registry/update",
            fields={"entity_id": entity_id, field: value},
        )
        after = await self._entity(entity_id)
        self._assert_landed(entity_id, field, value, after)
        return WriteResult(entity_id, field, value, before.get(field), wrote=True)

    async def _write_device(
        self, device_id: str, field: str, value: str | None
    ) -> WriteResult:
        before = await self._device(device_id)
        if before.get(field) == value:
            return WriteResult(device_id, field, value, value, wrote=False)

        await self._ws.send_command(
            "config/device_registry/update",
            fields={"device_id": device_id, field: value},
        )
        after = await self._device(device_id)
        self._assert_landed(device_id, field, value, after)
        return WriteResult(device_id, field, value, before.get(field), wrote=True)

    @staticmethod
    def _assert_landed(
        target: str, field: str, requested: str | None, after: dict[str, Any]
    ) -> None:
        observed = after.get(field)
        if observed != requested:
            raise WriteNotVerified(
                f"{target}: asked for {field}={requested!r} but the registry "
                f"still reports {observed!r} -- the command was accepted and "
                f"changed nothing"
            )
        logger.info("%s: %s=%r verified in the registry", target, field, requested)

    async def _entity(self, entity_id: str) -> dict[str, Any]:
        try:
            entry = await self._ws.send_command(
                "config/entity_registry/get", fields={"entity_id": entity_id}
            )
        except HACommandError as exc:
            raise UnknownTarget(f"no entity {entity_id!r} in the registry") from exc
        if not entry:
            raise UnknownTarget(f"no entity {entity_id!r} in the registry")
        return dict(entry)

    async def _device(self, device_id: str) -> dict[str, Any]:
        # The device registry has no /get command -- only /list.
        devices = await self._ws.send_command("config/device_registry/list") or []
        for entry in devices:
            if entry.get("id") == device_id:
                return dict(entry)
        raise UnknownTarget(f"no device {device_id!r} in the registry")

    async def _require_area(self, area_id: str | None) -> None:
        """Refuse a dangling area_id.

        HA stores whatever it is given here, so an unknown id would read back
        equal to the request and verify cleanly while leaving the device in an
        area that no dashboard can show.
        """
        if area_id is None:
            return
        areas = await self._ws.send_command("config/area_registry/list") or []
        if area_id not in {a.get("area_id") for a in areas}:
            raise UnknownTarget(f"no area {area_id!r} in the registry")


__all__ = [
    "HARegistryWriter",
    "RegistryWriteError",
    "UnknownTarget",
    "WriteNotVerified",
    "WriteResult",
]
