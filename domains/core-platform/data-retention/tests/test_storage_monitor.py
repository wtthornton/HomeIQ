"""Tests for StorageMonitor alert resolution."""

from datetime import UTC, datetime

import pytest
from src.storage_monitor import StorageMetrics, StorageMonitor


def _metrics(usage_percentage: float) -> StorageMetrics:
    total = 100
    used = int(total * usage_percentage / 100)
    return StorageMetrics(
        timestamp=datetime.now(UTC),
        total_size_bytes=total,
        used_size_bytes=used,
        available_size_bytes=total - used,
        usage_percentage=usage_percentage,
    )


@pytest.mark.asyncio
async def test_resolve_alerts_uses_live_usage_not_frozen_percentage():
    """A critical alert created at 95% (threshold 90) must auto-resolve once
    live usage genuinely drops to 20% — not stay stuck comparing against the
    95% frozen at alert-creation time."""
    monitor = StorageMonitor()

    await monitor._check_alerts(_metrics(95.0))
    assert len(monitor.get_active_alerts()) == 1

    await monitor._check_alerts(_metrics(20.0))

    assert monitor.get_active_alerts() == []


@pytest.mark.asyncio
async def test_resolve_alerts_keeps_alert_active_while_usage_still_high():
    """An alert must remain active while usage stays above the warning
    threshold — the fix must not over-resolve."""
    monitor = StorageMonitor()

    await monitor._check_alerts(_metrics(95.0))
    assert len(monitor.get_active_alerts()) == 1

    await monitor._check_alerts(_metrics(92.0))

    active = monitor.get_active_alerts()
    assert len(active) == 1
    assert active[0].alert_type == "storage_critical"
