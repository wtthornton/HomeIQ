"""Data loading and preprocessing modules."""

from .feedback_store import FeedbackStore

__all__ = ["FeedbackStore", "WyzeDataLoader", "WYZE_TO_HA_DOMAIN_MAPPING"]


def __getattr__(name: str):
    """Lazy-load heavy dependencies (polars/duckdb) only when needed."""
    if name in ("WyzeDataLoader", "WYZE_TO_HA_DOMAIN_MAPPING"):
        from .wyze_loader import WYZE_TO_HA_DOMAIN_MAPPING, WyzeDataLoader
        globals().update(
            WyzeDataLoader=WyzeDataLoader,
            WYZE_TO_HA_DOMAIN_MAPPING=WYZE_TO_HA_DOMAIN_MAPPING,
        )
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
