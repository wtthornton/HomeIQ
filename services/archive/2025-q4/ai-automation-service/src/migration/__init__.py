"""
Migration module for Story DI-2.1

Handles data migration from old device discovery system to Device Intelligence Service.
"""

from .data_migration import DataMigrationManager

__all__ = ["DataMigrationManager"]
