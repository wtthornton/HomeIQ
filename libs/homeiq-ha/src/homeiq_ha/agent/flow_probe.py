"""Ask a config flow what it actually wants, then leave no trace.

There is no manifest field that answers "does this flow need credentials".
``iot_class`` in particular does not: Roborock is ``local_polling`` and still
opens with username + region. The only honest answer comes from starting the
flow, reading its rendered first step, and aborting it.

Starting a flow mutates, so nothing here may be called from a recipe's
``check`` — only from ``plan`` and ``apply``.
"""

from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from homeiq_ha.client import HAClient


#: Form fields the agent can fill from what it already observed. These name a
#: network location, not a secret: the fingerprint store knows the device's IP
#: because Zeek watched it take a DHCP lease.
_SATISFIABLE_FIELDS = frozenset({"host", "ip_address", "address", "ip"})


@dataclass(frozen=True)
class FlowProbe:
    """What a config flow's first step actually asks for.

    Obtained by starting the flow, reading its rendered schema, and aborting —
    never by inferring from the manifest. ``iot_class`` does not answer this:
    Roborock is ``local_polling`` and still opens with username + region.
    """

    domain: str
    kind: str
    required: tuple[str, ...] = ()

    @property
    def automatable(self) -> bool:
        """True when every required field is one the agent can fill itself."""
        return self.kind == "form" and all(f in _SATISFIABLE_FIELDS for f in self.required)

    def describe(self) -> str:
        if self.kind != "form":
            return f"{self.domain}: {self.kind} step — needs a browser, cannot be automated"
        if self.automatable:
            return f"{self.domain}: form, no secrets required"
        return f"{self.domain}: form requires {', '.join(self.required)}"


async def probe_flow(ha: HAClient, domain: str) -> FlowProbe:
    """Start ``domain``'s config flow, read its first step, and abort it.

    Aborting is in a ``finally`` because a flow left running shows up as a
    pending discovery in the owner's UI. This mutates, so it belongs in
    ``plan``/``apply`` and must never be called from ``check``.
    """
    step = await ha.rest.start_config_flow(domain)
    flow_id = step.get("flow_id")
    try:
        kind = ha.rest.classify_flow_step(step)
        required = tuple(
            str(field["name"])
            for field in step.get("data_schema") or []
            if field.get("required") and field.get("name")
        )
        return FlowProbe(domain, kind, required)
    finally:
        if flow_id:
            with suppress(Exception):
                await ha.rest.abort_config_flow(flow_id)


__all__ = ["FlowProbe", "probe_flow"]
