"""Backup rotation is bounded (TAP-6242).

Three timestamped copies accumulated inside one three-second training window
before the prune existed; nothing ever deleted them.
"""

from pathlib import Path

from src.core.predictive_analytics import PredictiveAnalyticsEngine


def test_prune_keeps_only_the_newest_backups(tmp_path: Path):
    artifact = tmp_path / "failure_prediction_model.pkl"
    artifact.write_bytes(b"current")
    for ts in (
        "20260819_010101",
        "20260819_010102",
        "20260819_010103",
        "20260819_010104",
        "20260819_010105",
    ):
        (tmp_path / f"{artifact.name}.backup_{ts}").write_bytes(b"old")

    engine = PredictiveAnalyticsEngine.__new__(PredictiveAnalyticsEngine)
    engine._prune_backups(artifact)

    remaining = sorted(p.name for p in tmp_path.glob(f"{artifact.name}.backup_*"))
    assert len(remaining) == PredictiveAnalyticsEngine.BACKUP_RETAIN
    assert remaining == [
        f"{artifact.name}.backup_20260819_010103",
        f"{artifact.name}.backup_20260819_010104",
        f"{artifact.name}.backup_20260819_010105",
    ]
    assert artifact.exists()  # the live artifact is never touched
