"""TAP-7586 round 2: room_occupancy retention must be enforced, not declared.

Round 1 added ``RETENTION_ROOM_OCCUPANCY = "90d"`` to ``InfluxDBSchema`` and a
test that the label exists. Nothing read that label: every point — including
room_occupancy — was written to the single shared ``home_assistant_events``
bucket, which is unbounded in practice (data-retention's tiered service is
disabled on this InfluxDB 2.x instance). These tests fail unless:

1. room_occupancy points are actually routed to a bucket distinct from the
   shared default bucket (VAL-0/VAL-1), and
2. the provisioning config that creates that bucket declares a finite
   retention (VAL-1), read from the same setting ``InfluxDBSchema`` declares
   rather than a second, independent literal (VAL-2).

VAL-3's negative control lives here too: mutate a throwaway copy of the init
script to InfluxDB's spelling of infinite retention ("0") and show the
finite-retention check catches it.
"""

from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import AsyncMock

from src.influxdb_batch_writer import InfluxDBBatchWriter
from src.influxdb_schema import InfluxDBSchema

INIT_SCRIPT = (
    Path(__file__).resolve().parents[4] / "infrastructure" / "influxdb" / "init-influxdb.sh"
)


def _room_occupancy_retention_in_init_script(script_text: str, bucket_name: str) -> str | None:
    """Extract the --retention value passed to `influx bucket create` for
    the named bucket. None if the script does not provision that bucket.
    """
    pattern = re.compile(
        r"influx bucket create.*?--name\s+\"?[^\"\n]*?"
        + re.escape(bucket_name)
        + r"[^\"\n]*\"?.*?--retention\s+\"?([^\"\s]+)\"?",
        re.DOTALL,
    )
    match = pattern.search(script_text)
    return match.group(1) if match else None


def _is_finite_retention(value: str | None) -> bool:
    """InfluxDB spells "keep forever" as retention 0 (or the flag omitted)."""
    if not value:
        return False
    resolved = value.strip("\"'")
    # Resolve a shell env-var-with-default form: "${VAR:-90d}" -> "90d"
    default_match = re.search(r":-([^}]+)\}$", resolved)
    if default_match:
        resolved = default_match.group(1)
    if resolved in ("0", "0s", ""):
        return False
    return bool(re.fullmatch(r"\d+[smhdw]", resolved))


class TestRoomOccupancyBucketRouting:
    """VAL-0/VAL-1: the write path must target a distinct, dedicated bucket."""

    async def test_room_occupancy_writes_to_a_dedicated_bucket_not_the_shared_one(self):
        manager = AsyncMock()
        manager.bucket = "home_assistant_events"
        written_buckets: list[str | None] = []

        async def _capture_write_points(points, bucket=None):
            written_buckets.append(bucket)
            return True

        manager.write_points = _capture_write_points

        batch_writer = InfluxDBBatchWriter(connection_manager=manager, batch_size=100)

        assert await batch_writer.write_room_occupancy(
            area_id="office", state="detected", contributing_entity_count=1
        )
        await batch_writer._process_current_batch()

        assert written_buckets, "room_occupancy point was never flushed to InfluxDB"
        assert written_buckets[0] is not None, (
            "room_occupancy point was written with no explicit bucket — it "
            "fell through to the shared default bucket"
        )
        assert written_buckets[0] != manager.bucket, (
            "room_occupancy landed in the same bucket as every other "
            "measurement, so the 90d label enforces nothing"
        )
        assert written_buckets[0] == InfluxDBSchema().BUCKET_ROOM_OCCUPANCY


class TestRoomOccupancyBucketProvisioning:
    """VAL-1/VAL-2: the provisioning config must exist and declare a finite
    retention read from the same setting as the declaration.
    """

    def test_init_script_provisions_room_occupancy_with_finite_retention(self):
        schema = InfluxDBSchema()
        script_text = INIT_SCRIPT.read_text()

        retention = _room_occupancy_retention_in_init_script(
            script_text, schema.BUCKET_ROOM_OCCUPANCY
        )

        assert retention is not None, (
            f"{INIT_SCRIPT} does not provision a bucket named "
            f"{schema.BUCKET_ROOM_OCCUPANCY!r} at all"
        )
        assert _is_finite_retention(retention), (
            f"room_occupancy bucket retention {retention!r} is not finite"
        )

    def test_negative_control_infinite_retention_is_caught(self):
        """VAL-3: flip the init script's retention flag to InfluxDB's "0"
        (infinite) in a throwaway copy and prove the check goes red.
        """
        script_text = INIT_SCRIPT.read_text()
        schema = InfluxDBSchema()

        infinite_script = re.sub(
            r'(--retention\s+"?)\$\{INFLUXDB_ROOM_OCCUPANCY_RETENTION:-90d\}("?)',
            r"\g<1>0\g<2>",
            script_text,
        )
        assert infinite_script != script_text, (
            "mutation did not match the script's retention flag — "
            "negative control is not exercising the real pattern"
        )

        retention = _room_occupancy_retention_in_init_script(
            infinite_script, schema.BUCKET_ROOM_OCCUPANCY
        )
        assert not _is_finite_retention(retention)
