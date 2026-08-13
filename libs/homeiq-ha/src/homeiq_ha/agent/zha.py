"""ZHA onboarding for a network-attached Zigbee coordinator.

The one recipe in the set with an irreversible failure mode: re-forming the
Zigbee network over an existing config entry orphans every paired device.
Both guard layers live here — see :class:`ZHARecipe`.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from .integration import IntegrationRecipe
from .recipe import ApplyResult, Change, VerifyResult

if TYPE_CHECKING:
    from homeiq_ha.client import HAClient

#: The live coordinator: SMLIGHT network-attached, Zigbee socket on :6638.
#: Overridden per instance via ``ZHARecipe(serial_path=...)``.
ZHA_SERIAL_PATH = "socket://192.168.1.121:6638"


class ZHAFormationRefused(RuntimeError):
    """Raised when apply would form a Zigbee network over an existing entry.

    Re-forming the network on an instance with a loaded entry orphans every
    paired device. This is the one irreversible trap in the recipe set, so it
    is a raised error, not a logged warning.
    """


class ZHARecipe(IntegrationRecipe):
    """ZHA over a network-attached coordinator (SMLIGHT, ``socket://`` path).

    ``check``/``plan`` are inherited: a loaded ``zha`` entry is ``SATISFIED``,
    so on an instance that already has one the engine never calls ``apply``.

    ``apply`` is guarded twice over: it re-reads config entries itself and
    raises :class:`ZHAFormationRefused` if *any* zha entry exists — loaded or
    not — before a single flow call is made. Network formation only ever runs
    against an instance with no zha entry at all.

    The flow itself (captured live 2026-08-11, entry 01KZSE6SJ789RGEFCBRBA0VHDG):
    ``user`` → ``choose_serial_port`` (form, plain ``{"path": ...}``) →
    ``verify_radio`` (form, empty submit) → ``choose_setup_strategy`` (menu →
    ``setup_strategy_recommended``) → ``form_new_network`` — a **progress**
    step, ~2-3 minutes of real hardware I/O polled with empty POSTs — →
    ``create_entry``. ``run_config_flow`` raises ``HAHumanGateRequired`` on
    progress steps, so this recipe drives the flow itself; formation is
    hardware work, not a human gate.
    """

    #: The menu choice that lets ZHA form a new network with recommended settings.
    _STRATEGY = "setup_strategy_recommended"

    def __init__(
        self,
        serial_path: str,
        *,
        formation_timeout: float = 300.0,
        poll_interval: float = 5.0,
    ) -> None:
        super().__init__("zha", title="Zigbee Home Automation")
        self.serial_path = serial_path
        self.formation_timeout = formation_timeout
        self.poll_interval = poll_interval

    async def apply(self, ha: HAClient) -> ApplyResult:
        entries = await self._entries(ha)
        if entries:
            raise ZHAFormationRefused(
                f"a zha config entry already exists "
                f"({entries[0].get('entry_id')}, state={entries[0].get('state')}); "
                "re-forming the network would orphan every paired device"
            )
        await self._form_network(ha)
        return ApplyResult(
            (Change("configure integration", "zha", after="loaded"),),
            "ZHA configured; network formed",
        )

    async def _form_network(self, ha: HAClient) -> None:
        from homeiq_ha.client.errors import HAFlowError

        step = await ha.rest.start_config_flow(self.domain)
        deadline = asyncio.get_running_loop().time() + self.formation_timeout

        while True:
            step_type = ha.rest.classify_flow_step(step)
            if step_type == "create_entry":
                return
            if step_type == "abort":
                raise HAFlowError(f"zha config flow aborted: {step.get('reason', 'unknown')}", step)

            flow_id = step.get("flow_id")
            if not flow_id:
                raise HAFlowError("zha config flow step has no flow_id", step)

            if step_type == "progress":
                # Real hardware I/O (network formation), not a human gate.
                if asyncio.get_running_loop().time() > deadline:
                    raise HAFlowError(
                        f"zha network formation exceeded {self.formation_timeout}s",
                        step,
                    )
                await asyncio.sleep(self.poll_interval)
                step = await ha.rest.advance_config_flow(flow_id, {})
                continue

            if step_type == "menu":
                step = await ha.rest.advance_config_flow(flow_id, {"next_step_id": self._STRATEGY})
                continue

            if step_type == "form":
                fields = {str(field.get("name")) for field in step.get("data_schema") or []}
                user_input = {"path": self.serial_path} if "path" in fields else {}
                step = await ha.rest.advance_config_flow(flow_id, user_input)
                continue

            raise HAFlowError(
                f"zha config flow returned an unsupported step type {step_type!r}",
                step,
            )

    async def verify(self, ha: HAClient) -> VerifyResult:
        # Formation lands asynchronously: the entry exists immediately but
        # reaches state == "loaded" only once ZHA finishes starting the radio.
        # Re-read until then rather than trusting the flow's final response.
        deadline = asyncio.get_running_loop().time() + self.formation_timeout
        while True:
            entries = await self._entries(ha)
            loaded = [e for e in entries if e.get("state") == "loaded"]
            if loaded:
                return VerifyResult(
                    True,
                    f"zha entry {loaded[0].get('entry_id')} is loaded",
                    {"entry_ids": [e.get("entry_id") for e in loaded]},
                )
            if asyncio.get_running_loop().time() > deadline:
                return VerifyResult(
                    False,
                    "no loaded zha entry within "
                    f"{self.formation_timeout}s "
                    f"(states: {[e.get('state') for e in entries]})",
                )
            await asyncio.sleep(self.poll_interval)


__all__ = ["ZHA_SERIAL_PATH", "ZHAFormationRefused", "ZHARecipe"]
