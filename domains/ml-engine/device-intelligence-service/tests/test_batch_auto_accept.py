"""Batch auto-accept is HA-first (TAP-6233).

The batch processor used to flip suggestions to ``accepted`` and set
``name_by_user`` with no Home Assistant contact at all -- the same
report-success-without-writing defect the accept endpoint had, one code path
over. These tests pin the gate: ``accepted`` only when the verified write
confirms, ``pending`` otherwise.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from src.services.name_enhancement import batch_processor as bp_module
from src.services.name_enhancement.batch_processor import NameEnhancementBatchProcessor


class FakeSession:
    def __init__(self) -> None:
        self.added: list[Any] = []
        self.commits = 0

    async def execute(self, _query: Any) -> Any:
        class Result:
            def scalar_one_or_none(self) -> None:
                return None

            def __iter__(self):
                return iter([])

        return Result()

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def commit(self) -> None:
        self.commits += 1


class FakeDevice:
    id = "dev0"
    name = "WLED 0"
    name_by_user: str | None = None


class FakeGenerated:
    name = "Office Ceiling"
    confidence = 0.95
    source = "pattern"
    reasoning = "test"


async def _run_batch(sync_returns: bool) -> tuple[FakeDevice, list[Any], FakeSession]:
    processor = NameEnhancementBatchProcessor(name_generator=AsyncMock())
    device = FakeDevice()
    session = FakeSession()

    with (
        patch.object(
            processor,
            "_process_single_device",
            new=AsyncMock(return_value=(FakeGenerated(), device)),
        ),
        patch.object(
            bp_module, "sync_name_to_ha", new=AsyncMock(return_value=sync_returns)
        ) as sync,
    ):
        await processor.process_batch(
            [device], use_ai=False, auto_accept=True, session=session
        )

    assert sync.await_count == 1  # the gate was consulted
    return device, session.added, session


@pytest.mark.asyncio
async def test_auto_accept_marks_accepted_only_after_ha_confirms():
    device, added, _session = await _run_batch(sync_returns=True)

    assert added[0].status == "accepted"
    assert device.name_by_user == "Office Ceiling"


@pytest.mark.asyncio
async def test_auto_accept_leaves_the_suggestion_pending_when_ha_refuses():
    device, added, _session = await _run_batch(sync_returns=False)

    assert added[0].status == "pending"
    assert device.name_by_user is None  # local rename never happened
