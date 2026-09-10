"""Regression test (TAP-7365): the calendar adapter's InfluxDB bucket.

The adapter must resolve an InfluxDB bucket name that the compose file for
this service actually configures. Before the fix, the calendar adapter read
``CALENDAR_INFLUXDB_BUCKET`` (code default ``"events"``), but
``domains/data-collectors/compose.yml`` never sets that variable for the
``collectors`` service — only a comment claims it does. The result was every
calendar write 404ing against a bucket ("events") that exists nowhere,
InfluxDB or compose.
"""

import os
import re
from pathlib import Path
from unittest.mock import patch

import pytest

COMPOSE_PATH = Path(__file__).resolve().parents[3] / "compose.yml"


def _bucket_names_in_compose(compose_text: str, var_names: tuple[str, ...]) -> set[str]:
    """Return the bucket name(s) the `collectors` service's compose environment
    would actually resolve to for the given candidate env var names.

    Only counts a name if the compose file's `collectors.environment` list
    declares that variable (as `- VAR=${VAR:-default}` or a plain literal) —
    a variable merely mentioned in a comment resolves to nothing.
    """
    block_match = re.search(r"\n  collectors:\n(.*?)\n  \S", compose_text, re.DOTALL)
    assert block_match, "could not isolate the `collectors` service block in compose.yml"
    block = block_match.group(1)

    names: set[str] = set()
    for var_name in var_names:
        line_match = re.search(rf"^\s*-\s*{var_name}=(\S+)\s*$", block, re.MULTILINE)
        if not line_match:
            continue
        value = line_match.group(1)
        default_match = re.fullmatch(r"\$\{" + var_name + r":-([^}]*)\}", value)
        names.add(default_match.group(1) if default_match else value)
    return names


def test_compose_never_sets_calendar_influxdb_bucket():
    """Sanity check on the diagnosis: the comment names a var compose never sets."""
    compose_text = COMPOSE_PATH.read_text()
    assert "CALENDAR_INFLUXDB_BUCKET" not in _collectors_environment_var_names(compose_text)


def _collectors_environment_var_names(compose_text: str) -> set[str]:
    block_match = re.search(r"\n  collectors:\n(.*?)\n  \S", compose_text, re.DOTALL)
    assert block_match
    return set(re.findall(r"^\s*-\s*([A-Z_]+)=", block_match.group(1), re.MULTILINE))


def test_calendar_service_resolves_a_compose_configured_bucket():
    """The bucket the calendar adapter actually writes to must be one that
    `domains/data-collectors/compose.yml` configures for `collectors` —
    via `CALENDAR_INFLUXDB_BUCKET` if compose sets it, else via the shared
    `INFLUXDB_BUCKET` every other adapter uses. It must NOT fall back to a
    code-only default that no compose environment variable ever produces.
    """
    compose_text = COMPOSE_PATH.read_text()
    resolvable = _bucket_names_in_compose(
        compose_text, ("CALENDAR_INFLUXDB_BUCKET", "INFLUXDB_BUCKET")
    )
    assert resolvable, (
        "neither CALENDAR_INFLUXDB_BUCKET nor INFLUXDB_BUCKET is configured for "
        "`collectors` in compose.yml — nothing to resolve against"
    )

    with patch.dict(os.environ, {"INFLUXDB_TOKEN": "test-token"}, clear=True):
        from src.config import Settings

        fresh_settings = Settings()

        with patch("src.adapters.calendar.settings", new=fresh_settings):
            from src.adapters.calendar import CalendarService

            service = CalendarService()

    assert service.influxdb_bucket in resolvable, (
        f"calendar adapter resolved bucket {service.influxdb_bucket!r}, which compose "
        f"never configures (compose-resolvable: {resolvable!r}) — writes will 404"
    )


@pytest.mark.asyncio
async def test_startup_opens_influxdb_client_against_the_resolved_bucket():
    """End-to-end through startup(): the InfluxDB3 client must be constructed
    with the same compose-configured bucket as its `database`, not a stray
    code default.
    """
    from unittest.mock import AsyncMock, MagicMock

    compose_text = COMPOSE_PATH.read_text()
    resolvable = _bucket_names_in_compose(
        compose_text, ("CALENDAR_INFLUXDB_BUCKET", "INFLUXDB_BUCKET")
    )

    with patch.dict(os.environ, {"INFLUXDB_TOKEN": "test-token"}, clear=True):
        from src.config import Settings

        fresh_settings = Settings()

        with patch("src.adapters.calendar.settings", new=fresh_settings):
            from src.adapters.calendar import CalendarService

            service = CalendarService()

            mock_connection = MagicMock()
            mock_connection.name = "test-connection"
            mock_connection.url = "ws://localhost:8123/api/websocket"
            mock_connection.token = "test-token"

            with (
                patch("src.adapters.calendar.ha_connection_manager") as mock_ha_manager,
                patch("src.adapters.calendar.InfluxDBClient3") as mock_influx_cls,
            ):
                mock_ha_manager.get_connection_with_circuit_breaker = AsyncMock(
                    return_value=mock_connection
                )
                mock_ha_client = AsyncMock()
                mock_ha_client.test_connection = AsyncMock(return_value=True)
                mock_ha_client.get_calendars = AsyncMock(return_value=[])

                with patch(
                    "src.adapters.calendar.HomeAssistantCalendarClient",
                    return_value=mock_ha_client,
                ):
                    await service.startup()

    _, kwargs = mock_influx_cls.call_args
    assert kwargs["database"] in resolvable, (
        f"InfluxDBClient3 opened against database={kwargs['database']!r}, which "
        f"compose never configures (compose-resolvable: {resolvable!r})"
    )
