"""CLI commands package."""

from .config import app as config_app
from .diagnostics import app as diagnostics_app
from .events import app as events_app
from .export import app as export_app
from .system import app as system_app

__all__ = ["system_app", "events_app", "config_app", "export_app", "diagnostics_app"]
