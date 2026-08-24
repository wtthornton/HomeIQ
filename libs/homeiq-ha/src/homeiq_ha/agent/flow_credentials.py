"""Owner-supplied config-flow credentials, passed in by the caller.

Most integrations worth adding open with an account form — Ring wants
username + password, Roborock wants username + region. The agent must never
invent those, so they arrive as an argument from whoever is driving the run.

They are deliberately **not** read from the environment. HomeIQ ships to
consumers who have a browser and no shell, so a design that asks someone to
edit a file on the Docker host is an unshipped feature — and it asks them to
put an account password next to a public git checkout. The runtime source is
the setup wizard (TAP-6469); this module only decides whether what arrived is
enough to fill a given form.

Nothing here is stored and nothing is logged. A field with no supplied value
is simply absent, which makes the flow un-fillable and leaves the integration
reported rather than half-configured.
"""

from __future__ import annotations

from collections.abc import Mapping

#: Credentials for one domain, keyed by config-flow field name.
DomainCredentials = Mapping[str, str]

#: Credentials for several domains, keyed by integration domain.
SuppliedCredentials = Mapping[str, DomainCredentials]


def credentials_for(
    fields: tuple[str, ...],
    supplied: DomainCredentials | None,
) -> dict[str, str] | None:
    """Return every requested field, or ``None`` if any one is missing.

    All-or-nothing on purpose: submitting a form with half its fields filled
    makes Home Assistant render a validation error, which is indistinguishable
    from a wrong password and leaves a flow running in the owner's UI.

    Args:
        fields: The config-flow field names the form requires.
        supplied: What the caller has for this domain, or ``None``.
    """
    if not fields:
        return {}
    if not supplied:
        return None
    values: dict[str, str] = {}
    for field in fields:
        value = str(supplied.get(field) or "").strip()
        if not value:
            return None
        values[field] = value
    return values


def missing_fields(
    fields: tuple[str, ...],
    supplied: DomainCredentials | None,
) -> list[str]:
    """The field names still needed before ``fields`` can be submitted."""
    if not supplied:
        return list(fields)
    return [field for field in fields if not str(supplied.get(field) or "").strip()]


__all__ = [
    "DomainCredentials",
    "SuppliedCredentials",
    "credentials_for",
    "missing_fields",
]
