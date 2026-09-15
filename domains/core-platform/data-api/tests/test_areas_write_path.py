"""
Tests for the areas write path (TAP-7584 round 2).

Round 1 gave areas a table and a read path (`/api/areas` LEFT JOINs `Area` to
entities so a zero-entity area is not dropped) but nothing ever wrote a row
except the one-time migration backfill — a `SELECT DISTINCT` over
`core.entities`, which can never see an area HA knows about with zero
entities. `/internal/areas/bulk_upsert` is the write path a discovery pass
calls to close that gap.
"""

import pytest
import pytest_asyncio
import src.database as _database
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from src.cache import cache
from src.database import init_db
from src.main import app
from src.models import Area


def AsyncSessionLocal():  # noqa: N802
    """Resolve the session factory at call time.

    src.database exposes AsyncSessionLocal as a module-level alias that
    starts as None and is only populated by init_db(); a module-level
    from-import would capture None permanently.
    """
    return _database.AsyncSessionLocal()


@pytest_asyncio.fixture
async def test_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_zero_entity_area_acquires_a_row_after_bulk_upsert(test_client):
    """VAL-0/VAL-1: an area HA knows about with zero entities gets a row.

    This is what a discovery pass does on the wire: POST the area registry
    payload to the internal bulk-upsert endpoint, then read it back through
    the same `/api/areas`-backed read path round 1 built.
    """
    await init_db()
    await cache.clear()

    resp = await test_client.post(
        "/internal/areas/bulk_upsert",
        json=[{"area_id": "empty_attic", "name": "Empty Attic"}],
    )
    assert resp.status_code == 200
    assert resp.json()["upserted"] == 1

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Area).where(Area.area_id == "empty_attic"))
        area = result.scalar_one()
        assert area.name == "Empty Attic"

    list_resp = await test_client.get("/internal/areas/list")
    assert list_resp.status_code == 200
    areas_by_id = {a["area_id"]: a for a in list_resp.json()["areas"]}
    assert "empty_attic" in areas_by_id
    assert areas_by_id["empty_attic"]["entity_count"] == 0


@pytest.mark.asyncio
async def test_registry_sourced_area_carries_source_ha_registry(test_client):
    """VAL-2: source="ha_registry" is actually written by the bulk-upsert path,
    not just declared in the model comment."""
    await init_db()

    await test_client.post(
        "/internal/areas/bulk_upsert",
        json=[{"area_id": "office", "name": "Office"}],
    )

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Area).where(Area.area_id == "office"))
        area = result.scalar_one()
        assert area.source == "ha_registry"


@pytest.mark.asyncio
async def test_floor_id_populated_when_ha_supplies_a_floor(test_client):
    """VAL-3 (populated case)."""
    await init_db()

    await test_client.post(
        "/internal/areas/bulk_upsert",
        json=[
            {
                "area_id": "kitchen",
                "name": "Kitchen",
                "floor_id": "ground_floor",
                "floor_name": "Ground Floor",
            }
        ],
    )

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Area).where(Area.area_id == "kitchen"))
        area = result.scalar_one()
        assert area.floor_id == "ground_floor"
        assert area.floor_name == "Ground Floor"


@pytest.mark.asyncio
async def test_floor_id_null_when_ha_supplies_no_floor(test_client):
    """VAL-3 (null case) — box 5: never fabricate a floor default."""
    await init_db()

    await test_client.post(
        "/internal/areas/bulk_upsert",
        json=[{"area_id": "garage", "name": "Garage"}],
    )

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Area).where(Area.area_id == "garage"))
        area = result.scalar_one()
        assert area.floor_id is None
        assert area.floor_name is None


@pytest.mark.asyncio
async def test_two_discovery_passes_leave_exactly_one_row_per_area(test_client):
    """VAL-4: idempotence — a repeated discovery pass upserts, never duplicates."""
    await init_db()

    payload = [{"area_id": "office", "name": "Office"}]

    first = await test_client.post("/internal/areas/bulk_upsert", json=payload)
    assert first.status_code == 200
    assert first.json()["upserted"] == 1

    second = await test_client.post("/internal/areas/bulk_upsert", json=payload)
    assert second.status_code == 200
    assert second.json()["upserted"] == 1

    async with AsyncSessionLocal() as session:
        count = await session.scalar(
            select(func.count()).select_from(Area).where(Area.area_id == "office")
        )
        assert count == 1


@pytest.mark.asyncio
async def test_bulk_upsert_updates_existing_area_fields(test_client):
    """A second pass with a changed name/floor updates the row in place rather
    than leaving it stuck at whatever the first pass wrote."""
    await init_db()

    await test_client.post(
        "/internal/areas/bulk_upsert",
        json=[{"area_id": "office", "name": "Office"}],
    )
    await test_client.post(
        "/internal/areas/bulk_upsert",
        json=[
            {
                "area_id": "office",
                "name": "Home Office",
                "floor_id": "first_floor",
                "floor_name": "First Floor",
            }
        ],
    )

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Area).where(Area.area_id == "office"))
        area = result.scalar_one()
        assert area.name == "Home Office"
        assert area.floor_id == "first_floor"
        assert area.floor_name == "First Floor"


@pytest.mark.asyncio
async def test_bulk_upsert_skips_entries_without_area_id(test_client):
    """An off-contract entry (missing area_id) is skipped, not a crash."""
    await init_db()

    resp = await test_client.post(
        "/internal/areas/bulk_upsert",
        json=[{"name": "No ID"}, {"area_id": "hallway", "name": "Hallway"}],
    )

    assert resp.status_code == 200
    assert resp.json()["upserted"] == 1

    async with AsyncSessionLocal() as session:
        count = await session.scalar(select(func.count()).select_from(Area))
        assert count == 1
