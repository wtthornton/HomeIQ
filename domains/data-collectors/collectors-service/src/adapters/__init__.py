"""Collector adapters — one former standalone service each."""

from .base import CollectorAdapter, with_adapter_timeout

__all__ = ["CollectorAdapter", "with_adapter_timeout"]
