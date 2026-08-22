"""Owner-supplied config-flow credentials, read from the environment.

Most integrations worth adding open with an account form — Ring wants
username + password, Roborock wants username + region. The agent must never
invent those, but it also should not make the owner click through a UI when
they have already said "you do it". So the owner puts each secret in one place
once and the init agent fills the form.

Naming is mechanical: ``HOMEIQ_INTEGRATION_<DOMAIN>_<FIELD>``, both uppercased
with non-alphanumerics as underscores. Ring's form therefore reads

    HOMEIQ_INTEGRATION_RING_USERNAME
    HOMEIQ_INTEGRATION_RING_PASSWORD

Nothing here has a default and nothing is logged. A field with no variable set
is simply absent, which makes the flow un-fillable and leaves the integration
reported rather than half-configured.
"""

from __future__ import annotations

import os
import re

ENV_PREFIX = "HOMEIQ_INTEGRATION"


def env_var_for(domain: str, field: str) -> str:
    """The environment variable that supplies ``field`` for ``domain``."""
    part = re.sub(r"[^A-Za-z0-9]+", "_", f"{domain}_{field}").strip("_").upper()
    return f"{ENV_PREFIX}_{part}"


def credentials_for(domain: str, fields: tuple[str, ...]) -> dict[str, str] | None:
    """Return every requested field, or ``None`` if any one is missing.

    All-or-nothing on purpose: submitting a form with half its fields filled
    makes Home Assistant render a validation error, which is indistinguishable
    from a wrong password and leaves a flow running in the owner's UI.
    """
    if not fields:
        return {}
    values: dict[str, str] = {}
    for field in fields:
        value = os.environ.get(env_var_for(domain, field), "").strip()
        if not value:
            return None
        values[field] = value
    return values


def missing_env_vars(domain: str, fields: tuple[str, ...]) -> list[str]:
    """The variables a person would need to set for ``domain`` to be fillable."""
    return [
        env_var_for(domain, field)
        for field in fields
        if not os.environ.get(env_var_for(domain, field), "").strip()
    ]


__all__ = ["ENV_PREFIX", "credentials_for", "env_var_for", "missing_env_vars"]
