"""
Global MetricsBuffer instance.

Separate module to avoid circular imports between main.py and
analytics_endpoints.py — both import from here.
"""

from .metrics_buffer import MetricsBuffer

metrics_buffer = MetricsBuffer()
