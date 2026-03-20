"""
Entity Safety Blacklist — Epic 93

Loads entity_blacklist.yaml and provides query methods for determining
whether an entity is blocked, warned, or safe for AI automation.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_CONFIG_PATH = Path(__file__).parent / "entity_blacklist.yaml"


class EntityBlacklist:
    """Central blacklist for security-sensitive HA entities.

    Defence-in-depth: entities matched here are filtered from LLM context
    (Story 93.2) **and** rejected at YAML validation (Story 93.3).
    """

    def __init__(self, config_path: str | Path | None = None) -> None:
        self._config_path = Path(config_path) if config_path else _CONFIG_PATH
        self._blocked_domains: set[str] = set()
        self._blocked_entities: set[str] = set()
        self._blocked_services: set[str] = set()
        self._warn_domains: set[str] = set()
        self._override_domains: set[str] = set()
        self._load()

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Load config from YAML and apply env-var overrides."""
        data = self._read_yaml()
        self._blocked_domains = set(data.get("blocked_domains") or [])
        self._blocked_entities = {
            e.lower() for e in (data.get("blocked_entities") or [])
        }
        self._blocked_services = set(data.get("blocked_services") or [])
        self._warn_domains = set(data.get("warn_domains") or [])

        # ENTITY_BLACKLIST_OVERRIDE=lock,alarm_control_panel  → unblock those domains
        override_raw = os.environ.get("ENTITY_BLACKLIST_OVERRIDE", "").strip()
        if override_raw:
            self._override_domains = {
                d.strip() for d in override_raw.split(",") if d.strip()
            }
            self._blocked_domains -= self._override_domains
            # Also remove overridden domains from blocked_services
            self._blocked_services = {
                s for s in self._blocked_services
                if s.split(".")[0] not in self._override_domains
            }
            logger.warning(
                "Entity blacklist override active — unblocked domains: %s",
                self._override_domains,
            )

        logger.info(
            "Entity blacklist loaded: %d blocked domains, %d blocked entities, "
            "%d blocked services, %d warn domains",
            len(self._blocked_domains),
            len(self._blocked_entities),
            len(self._blocked_services),
            len(self._warn_domains),
        )

    def _read_yaml(self) -> dict[str, Any]:
        try:
            with open(self._config_path, encoding="utf-8") as fh:
                return yaml.safe_load(fh) or {}
        except FileNotFoundError:
            logger.warning(
                "Entity blacklist config not found at %s — using empty blacklist",
                self._config_path,
            )
            return {}
        except Exception:
            logger.exception("Failed to load entity blacklist config")
            return {}

    # ------------------------------------------------------------------
    # Query API
    # ------------------------------------------------------------------

    def is_blocked(self, entity_id: str) -> bool:
        """Return True if *entity_id* must be hidden from AI and rejected in validation."""
        entity_id_lower = entity_id.lower()

        # Exact entity match
        if entity_id_lower in self._blocked_entities:
            return True

        # Domain match
        domain = entity_id_lower.split(".")[0] if "." in entity_id_lower else ""
        return domain in self._blocked_domains

    def is_warned(self, entity_id: str) -> bool:
        """Return True if *entity_id* should be annotated with a safety warning."""
        if self.is_blocked(entity_id):
            return False  # blocked entities are hidden, not warned
        domain = entity_id.lower().split(".")[0] if "." in entity_id.lower() else ""
        return domain in self._warn_domains

    def is_service_blocked(self, service: str) -> bool:
        """Return True if *service* (e.g. ``lock.unlock``) is blocked."""
        return service in self._blocked_services

    # ------------------------------------------------------------------
    # Accessors (for external consumers like yaml-validation-service)
    # ------------------------------------------------------------------

    @property
    def blocked_domains(self) -> set[str]:
        return set(self._blocked_domains)

    @property
    def blocked_entities(self) -> set[str]:
        return set(self._blocked_entities)

    @property
    def blocked_services(self) -> set[str]:
        return set(self._blocked_services)

    @property
    def warn_domains(self) -> set[str]:
        return set(self._warn_domains)

    @property
    def override_active(self) -> bool:
        return bool(self._override_domains)
