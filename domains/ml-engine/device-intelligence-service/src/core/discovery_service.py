"""
Device Intelligence Service - Discovery Service

Main discovery service that orchestrates device discovery from multiple sources.
"""

import asyncio
import contextlib
import json
import logging
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..clients.ha_client import HAArea, HADevice, HAEntity
from ..config import Settings
from ..core.database import get_db_session
from ..services.device_knowledge import DeviceKnowledge
from ..services.device_service import DeviceService
from ..services.hygiene_analyzer import DeviceHygieneAnalyzer
from ..services.name_enhancement import DeviceNameGenerator, NameUniquenessValidator
from .cache import get_device_cache
from .device_parser import DeviceParser, UnifiedDevice

logger = logging.getLogger(__name__)


@dataclass
class DiscoveryStatus:
    """Discovery service status."""

    service_running: bool
    ha_connected: bool
    last_discovery: datetime | None
    devices_count: int
    areas_count: int
    errors: list[str]


class DiscoveryService:
    """Main discovery service orchestrating device discovery from multiple sources."""

    def __init__(self, settings: Settings):
        self.settings = settings

        # Clients - HA client will be initialized with unified connection manager
        self.ha_client = None  # Will be initialized in start() method
        # Parser
        self.device_parser = DeviceParser()

        # Name enhancement components (optional, can be disabled)
        self.auto_generate_name_suggestions = getattr(
            settings, "AUTO_GENERATE_NAME_SUGGESTIONS", False
        )
        self.name_generator = None
        self.name_validator = None
        self.preference_learner = None
        self.batch_processor = None
        if self.auto_generate_name_suggestions:
            from ..services.name_enhancement import PreferenceLearner
            from ..services.name_enhancement.batch_processor import NameEnhancementBatchProcessor

            self.name_generator = DeviceNameGenerator(settings)
            self.name_validator = NameUniquenessValidator()
            self.preference_learner = PreferenceLearner()
            self.batch_processor = NameEnhancementBatchProcessor(self.name_generator, settings)

        # State
        self.running = False
        self.discovery_task: asyncio.Task | None = None
        self.last_discovery: datetime | None = None
        self.errors: list[str] = []

        # Data
        self.unified_devices: dict[str, UnifiedDevice] = {}
        self.ha_devices: list[HADevice] = []
        self.ha_entities: list[HAEntity] = []
        # None until fetched. None means "could not look" and preserves stored
        # values; an empty list means "asked and got nothing" and clears them.
        self.ha_states: list[dict[str, Any]] | None = None
        self.zha_devices: list[dict[str, Any]] | None = None
        # device_id -> {column: why no durable signal established it}
        self.knowledge_exclusions: dict[str, dict[str, str]] = {}
        self.ha_areas: list[HAArea] = []
        self.ha_config_entries: dict[str, str] = {}  # Maps config_entry_id -> domain/integration

    async def start(self) -> bool:
        """Start the discovery service."""
        try:
            logger.info("Starting Device Intelligence Discovery Service")

            # Initialize HA client with configured settings
            from ..clients.ha_client import HomeAssistantClient

            self.ha_client = HomeAssistantClient(
                self.settings.HA_URL,
                None,  # No fallback URL for now
                self.settings.HA_TOKEN,
            )

            # Connect to Home Assistant
            if not await self.ha_client.connect():
                logger.error("Failed to connect to Home Assistant")
                return False

            # Start HA message handler
            await self.ha_client.start_message_handler()

            # Subscribe to registry update events for real-time cache updates
            await self._subscribe_to_registry_updates()

            # Start discovery task
            self.running = True
            self.discovery_task = asyncio.create_task(self._discovery_loop())

            # Start batch processor if enabled
            if self.batch_processor:
                try:
                    self.batch_processor.start()
                    logger.info("Name enhancement batch processor started")
                except Exception as e:
                    logger.warning(f"Failed to start batch processor: {e}")

            logger.info("Discovery service started successfully")
            return True

        except Exception as e:
            logger.error("Failed to start discovery service: %s", e)
            self.errors.append(f"Startup error: {str(e)}")
            return False

    async def stop(self):
        """Stop the discovery service."""
        logger.info("Stopping Discovery Service")

        self.running = False

        # Cancel discovery task
        if self.discovery_task:
            self.discovery_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self.discovery_task

        # Stop batch processor
        if self.batch_processor:
            self.batch_processor.stop()

        # Disconnect clients
        if self.ha_client:
            await self.ha_client.disconnect()

        logger.info("Discovery service stopped")

    async def _discovery_loop(self):
        """Main discovery loop."""
        logger.info("Starting discovery loop")

        # Initial discovery
        await self._perform_discovery()

        # Periodic discovery
        while self.running:
            try:
                await asyncio.sleep(300)  # 5 minutes
                if self.running:
                    await self._perform_discovery()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in discovery loop: %s", e)
                self.errors.append(f"Discovery loop error: {str(e)}")
                await asyncio.sleep(60)  # Wait before retry

    async def _perform_discovery(self):
        """Perform full device discovery."""
        try:
            logger.info("Performing device discovery")

            # Discover Home Assistant data
            await self._discover_home_assistant()

            # Parse and unify device data
            await self._unify_device_data()
            # Entities must land before the analyzer runs: hygiene findings carry
            # a foreign key to device_entities, so an empty table makes every
            # entity-scoped finding unpersistable.
            await self._persist_entities()
            await self._reconcile_absent_devices()
            await self._run_hygiene_analysis()

            # Update last discovery timestamp
            self.last_discovery = datetime.now(UTC)
            logger.info(
                "Discovery completed at %s: %d devices",
                self.last_discovery.isoformat(),
                len(self.unified_devices),
            )

        except Exception as e:
            logger.error("Error during discovery: %s", e)
            self.errors.append(f"Discovery error: {str(e)}")

    async def _safe_states(self) -> list[dict[str, Any]] | None:
        """Current states, or None if they could not be fetched.

        The distinction is load-bearing and must not collapse to a bare `[]`.
        DeviceKnowledge reads an empty list as "Home Assistant was asked and had
        nothing", which authoritatively CLEARS battery_level and power_source —
        so returning `[]` on an exception would let one flaky call wipe those
        columns across the whole fleet. None means "could not look", and the
        stored values stand.
        """
        try:
            return await self.ha_client.get_states()
        except Exception as exc:
            logger.warning(
                "Could not fetch states for device knowledge; leaving battery and "
                "power columns untouched this pass: %s",
                exc,
            )
            return None

    async def _safe_zha_devices(self) -> list[dict[str, Any]] | None:
        """ZHA's own device list, or None if the command could not be run.

        `zha/devices` is a ZHA-specific websocket command and the only source of
        LQI. Same distinction as _safe_states: None preserves the stored values,
        an empty list clears them. A command that errors has told us nothing
        about the mesh, so it must not be allowed to erase it.
        """
        try:
            result = await self.ha_client.send_command("zha/devices")
        except Exception as exc:
            logger.debug("ZHA device list unavailable (no ZHA integration?): %s", exc)
            return None
        if isinstance(result, dict):
            result = result.get("result", [])
        return result if isinstance(result, list) else None

    async def _persist_entities(self):
        """Mirror the Home Assistant entity registry into ``device_entities``.

        Nothing populated this table, while ``device_hygiene_issues.entity_id``
        carries a foreign key to it. The analyzer therefore produced findings on
        every run and lost all of them to a ForeignKeyViolationError, which read
        in the dashboard as "no issues" rather than as a failure.

        ``device_id`` is nulled when the referenced device is absent from
        ``devices``: that column has its own FK, and an entity whose device has
        not synced yet must not take the whole batch down with it. Helper
        entities legitimately carry no device at all.
        """
        if not self.ha_entities:
            return
        try:
            async for session in get_db_session():
                known = set((await session.execute(text("SELECT id FROM devices"))).scalars().all())
                rows = [
                    {
                        "entity_id": e.entity_id,
                        "device_id": e.device_id if e.device_id in known else None,
                        "name": e.name,
                        "original_name": e.original_name,
                        "platform": e.platform or "unknown",
                        "domain": e.domain
                        or e.entity_id.split(".", 1)[0],  # client derives; split is the floor
                        "disabled_by": e.disabled_by,
                        "entity_category": e.entity_category,
                        "hidden_by": e.hidden_by,
                        "has_entity_name": bool(e.has_entity_name),
                        "original_icon": e.original_icon,
                        "unique_id": e.unique_id,
                        "translation_key": e.translation_key,
                        "labels": json.dumps(list(e.labels or [])),
                    }
                    for e in self.ha_entities
                ]
                await session.execute(
                    text(
                        """
                        INSERT INTO device_entities (
                            entity_id, device_id, name, original_name, platform, domain,
                            disabled_by, entity_category, hidden_by, has_entity_name,
                            original_icon, unique_id, translation_key, labels,
                            created_at, updated_at
                        ) VALUES (
                            :entity_id, :device_id, :name, :original_name, :platform, :domain,
                            :disabled_by, :entity_category, :hidden_by, :has_entity_name,
                            :original_icon, :unique_id, :translation_key, CAST(:labels AS JSON),
                            NOW(), NOW()
                        )
                        -- Keyed on HA's own registry tuple, not on entity_id.
                        -- entity_id is an ADDRESS that moves on rename/re-pair,
                        -- so conflicting on it inserted a second row and left
                        -- findings attached to the stale address. Updating it
                        -- here is the point: the row keeps its identity and
                        -- changes its address, and the two FKs cascade.
                        ON CONFLICT (domain, platform, unique_id) DO UPDATE SET
                            entity_id = EXCLUDED.entity_id,
                            device_id = EXCLUDED.device_id,
                            name = EXCLUDED.name,
                            original_name = EXCLUDED.original_name,
                            platform = EXCLUDED.platform,
                            domain = EXCLUDED.domain,
                            disabled_by = EXCLUDED.disabled_by,
                            entity_category = EXCLUDED.entity_category,
                            hidden_by = EXCLUDED.hidden_by,
                            has_entity_name = EXCLUDED.has_entity_name,
                            original_icon = EXCLUDED.original_icon,
                            unique_id = EXCLUDED.unique_id,
                            translation_key = EXCLUDED.translation_key,
                            labels = EXCLUDED.labels,
                            updated_at = NOW()
                        """
                    ),
                    rows,
                )
                await session.commit()
                logger.info("Persisted %d entities to device_entities", len(rows))
                break
        except Exception as e:
            logger.error("Error persisting entities: %s", e)
            self.errors.append(f"Entity persistence error: {str(e)}")

    async def _reconcile_absent_devices(self):
        """Mark devices absent from the current snapshot unavailable — never delete.

        A device in a real home is unplugged for weeks and comes back (TAP-6249).
        Its row must survive with ``last_seen`` retained so findings and history
        stay attached; deletion happens only on explicit registry removal. A
        device present again is restored by the snapshot upsert itself, which
        overwrites ``availability_status`` with the freshly observed value.

        An empty snapshot is a failed discovery, not an empty home — marking
        everything unavailable on it would turn one HA outage into a fleet-wide
        false negative, so it is skipped.
        """
        if not self.unified_devices:
            return
        current_ids = [d.id for d in self.unified_devices.values()]
        try:
            async for session in get_db_session():
                result = await session.execute(
                    text(
                        """
                        UPDATE devices
                        SET availability_status = 'unavailable',
                            availability_updated_at = NOW(),
                            updated_at = NOW()
                        WHERE id NOT IN :current_ids
                          AND availability_status IS DISTINCT FROM 'unavailable'
                        RETURNING id, zigbee_ieee
                        """
                    ).bindparams(bindparam("current_ids", expanding=True)),
                    {"current_ids": current_ids},
                )
                marked = result.fetchall()
                await session.commit()
                if marked:
                    logger.info(
                        "Marked %d device(s) unavailable (absent from snapshot): %s",
                        len(marked),
                        [row[0] for row in marked[:10]],
                    )
                    # Same hardware re-registered under a new HA id is a re-pair,
                    # not a disappearance — surface it. Identity is the ieee,
                    # never the name (.claude/rules/friendly-names.md).
                    current_ieees = {
                        identifier[1]
                        for d in self.unified_devices.values()
                        if d.ha_device and d.ha_device.identifiers
                        for identifier in d.ha_device.identifiers
                        if len(identifier) >= 2 and identifier[0] == "zha"
                    }
                    for row in marked:
                        if row[1] and row[1] in current_ieees:
                            logger.warning(
                                "Device %s is absent but its ieee %s is present "
                                "under a new HA id — a re-pair minted a new "
                                "registry entry",
                                row[0],
                                row[1],
                            )
                break
        except Exception as e:
            logger.error("Error reconciling absent devices: %s", e)
            self.errors.append(f"Device reconciliation error: {str(e)}")

    async def _run_hygiene_analysis(self):
        """Analyze device hygiene and persist findings."""
        try:
            async for session in get_db_session():
                analyzer = DeviceHygieneAnalyzer(session)
                await analyzer.analyze(self.ha_devices, self.ha_entities, self.ha_areas)
                break
        except Exception as e:
            logger.error("Error during hygiene analysis: %s", e)
            self.errors.append(f"Hygiene analysis error: {str(e)}")

    async def _discover_home_assistant(self):
        """Discover devices, entities, and areas from Home Assistant."""
        try:
            logger.info("Discovering Home Assistant data")

            # Get config entries first (needed to resolve integrations)
            self.ha_config_entries = await self.ha_client.get_config_entries()

            # Get device registry
            self.ha_devices = await self.ha_client.get_device_registry()

            # Get entity registry
            self.ha_entities = await self.ha_client.get_entity_registry()
            self.ha_states = await self._safe_states()
            self.zha_devices = await self._safe_zha_devices()

            # Get area registry
            self.ha_areas = await self.ha_client.get_area_registry()

            # Update parser with areas and config entries
            self.device_parser.update_areas(self.ha_areas)
            self.device_parser.update_config_entries(self.ha_config_entries)

            logger.info(
                "HA Discovery: %d devices, %d entities, %d areas, %d config entries",
                len(self.ha_devices),
                len(self.ha_entities),
                len(self.ha_areas),
                len(self.ha_config_entries),
            )

        except Exception as e:
            logger.error("Error discovering Home Assistant data: %s", e)
            raise

    async def _subscribe_to_registry_updates(self):
        """
        Subscribe to entity and device registry update events.

        This keeps the cache fresh by triggering discovery when entities/devices
        are added, removed, or modified in Home Assistant.
        """
        try:

            async def handle_entity_registry_update(event_data: dict[str, Any]):
                """Handle entity registry update event."""
                action = event_data.get("event", {}).get("action", "unknown")
                entity_id = event_data.get("event", {}).get("entity_id", "unknown")
                logger.info("Entity registry updated: %s - %s", action, entity_id)

                # Trigger incremental update for entity changes
                if action in ["create", "update", "remove"]:
                    logger.info("Triggering incremental discovery due to entity %s", action)
                    # Perform a lightweight discovery update (just HA entities)
                    await self._discover_home_assistant()
                    await self._unify_device_data()

            async def handle_device_registry_update(event_data: dict[str, Any]):
                """Handle device registry update event."""
                action = event_data.get("event", {}).get("action", "unknown")
                device_id = event_data.get("event", {}).get("device_id", "unknown")
                logger.info("Device registry updated: %s - %s", action, device_id)

                # Trigger incremental update for device changes
                if action in ["create", "update", "remove"]:
                    logger.info("Triggering incremental discovery due to device %s", action)
                    # Perform a lightweight discovery update (just HA devices/entities)
                    await self._discover_home_assistant()
                    await self._unify_device_data()

            await self.ha_client.subscribe_to_registry_updates(
                entity_callback=handle_entity_registry_update,
                device_callback=handle_device_registry_update,
            )

            logger.info("Subscribed to registry update events")

        except Exception as e:
            logger.warning("Failed to subscribe to registry updates: %s", e)
            # Don't fail startup if subscriptions fail - we still have periodic discovery

    async def _unify_device_data(self):
        """Unify device data from all sources."""
        try:
            logger.info("Unifying device data from all sources")

            # Parse devices
            unified_devices = self.device_parser.parse_devices(self.ha_devices, self.ha_entities)

            # Update unified devices in memory
            self.unified_devices = {device.id: device for device in unified_devices}

            # Store devices in database
            await self._store_devices_in_database(unified_devices)

            # Invalidate cache for all updated devices (device-level invalidation)
            cache = get_device_cache()
            for device in unified_devices:
                await cache.delete(device.id)

            if unified_devices:
                logger.info("Unified %d devices and invalidated cache", len(self.unified_devices))

        except Exception as e:
            logger.error("Error unifying device data: %s", e)
            raise

    async def _store_devices_in_database(self, unified_devices: list[UnifiedDevice]):
        """Store unified devices and their capabilities in the database."""
        try:
            logger.info("Storing %d devices in database", len(unified_devices))

            # Convert UnifiedDevice objects to database format
            devices_data = []
            capabilities_data = []
            missing_integrations = []

            knowledge = DeviceKnowledge(
                self.ha_entities,
                self.ha_states,
                self.zha_devices,
            )
            knowledge_exclusions: dict[str, dict[str, str]] = {}

            for device in unified_devices:
                integration_value = (device.integration or "").strip()
                if not integration_value:
                    missing_integrations.append(device.id)
                    integration_value = "unknown"

                device_data = {
                    "id": device.id,
                    "name": device.name,
                    "manufacturer": device.manufacturer,
                    "model": device.model,
                    "area_id": device.area_id,
                    "area_name": device.area_name,  # Include area_name
                    "integration": integration_value,
                    "device_class": device.device_class,
                    "sw_version": device.sw_version,
                    "hw_version": device.hw_version,
                    "via_device_id": device.via_device_id,
                    "disabled_by": device.disabled_by,
                    "last_seen": device.last_seen,
                    "health_score": device.health_score,
                    # is_battery_powered is DELIBERATELY absent, like the other
                    # columns DeviceKnowledge owns. Seeding it here put it in
                    # every upsert, so on the preserve path — where power_source
                    # is omitted and the stored value stands — the flag was
                    # still written False, recreating the exact contradiction
                    # (power_source='battery' with is_battery_powered=false)
                    # that removing the earlier derivation had fixed.
                    "created_at": device.created_at,
                    "updated_at": device.updated_at,
                    # Initialize all optional fields with None to ensure consistency
                    "config_entry_id": None,
                    "connections_json": None,
                    "identifiers_json": None,
                    "zigbee_ieee": None,
                    "name_by_user": None,
                    "suggested_area": None,
                    "entry_type": None,
                    "configuration_url": None,
                    "battery_low": None,
                }

                # device_type, power_source, lqi, battery_level,
                # availability_status, source and their *_updated_at companions
                # are DELIBERATELY not initialised here. DeviceKnowledge owns
                # them, and it distinguishes three outcomes that a blanket None
                # would flatten into one:
                #
                #   value present  -> establish it
                #   explicit None  -> authoritatively clear it
                #   key absent     -> could not evaluate; leave the stored value
                #
                # Pre-seeding None made the third case indistinguishable from the
                # second, which is why the columns were reset on every pass.

                # Replace the initialised Nones with whatever the durable rules
                # could establish. Anything they could not establish stays None
                # and carries a written reason, which is logged once per pass
                # rather than silently dropped (TAP-6393).
                established, missing = knowledge.for_device(device)
                device_data.update(established)
                # is_battery_powered is derived from power_source, so it must
                # follow whatever was just established rather than the
                # pre-enrichment registry value.

                if missing:
                    knowledge_exclusions[device.id] = missing

                # Override with actual values if available
                if device.ha_device:
                    if device.ha_device.config_entries:
                        device_data["config_entry_id"] = (
                            device.ha_device.config_entries[0]
                            if device.ha_device.config_entries
                            else None
                        )
                    # SKIP JSON fields for now due to SQLAlchemy insert issues
                    # if device.ha_device.connections:
                    #     device_data["connections_json"] = json.dumps(device.ha_device.connections)
                    # if device.ha_device.identifiers:
                    #     device_data["identifiers_json"] = json.dumps(device.ha_device.identifiers)
                    # Extract zigbee IEEE address if present
                    if device.ha_device.identifiers:
                        for identifier in device.ha_device.identifiers:
                            if len(identifier) >= 2 and identifier[0] == "zha":
                                device_data["zigbee_ieee"] = identifier[1]
                                break
                    # Add new HA device attributes
                    device_data["name_by_user"] = device.ha_device.name_by_user
                    device_data["suggested_area"] = device.ha_device.suggested_area
                    device_data["entry_type"] = device.ha_device.entry_type
                    device_data["configuration_url"] = device.ha_device.configuration_url

                # Remove the JSON fields that were initialized to None to avoid SQLAlchemy issues
                device_data.pop("connections_json", None)
                device_data.pop("identifiers_json", None)

                devices_data.append(device_data)

                # Store capabilities for this device
                if device.capabilities:
                    for capability in device.capabilities:
                        capability_data = {
                            "device_id": device.id,
                            "capability_name": capability.get("name", ""),
                            "capability_type": capability.get("type", ""),
                            "properties": capability.get("properties", {}),
                            "exposed": capability.get("exposed", True),
                            "configured": capability.get("configured", True),
                            "source": capability.get("source", "unknown"),
                            "last_updated": datetime.now(UTC),
                        }
                        capabilities_data.append(capability_data)

            if missing_integrations:
                logger.warning(
                    "%d devices missing integration metadata (showing up to 5 IDs): %s",
                    len(missing_integrations),
                    missing_integrations[:5],
                )

            # Store in database using DeviceService
            async for session in get_db_session():
                device_service = DeviceService(session)
                # Retained so every NULL is traceable to the rule that declined
                # to fill it. An aggregate log line is not checkable per device.
                self.knowledge_exclusions = knowledge_exclusions

                if knowledge_exclusions:
                    by_column = Counter(
                        column for reasons in knowledge_exclusions.values() for column in reasons
                    )
                    logger.info(
                        "Device knowledge: %d of %d devices carry at least one column "
                        "with no durable signal; unfilled by column: %s",
                        len(knowledge_exclusions),
                        len(devices_data),
                        dict(by_column),
                    )

                await device_service.bulk_upsert_devices(devices_data)

                # Store capabilities if any
                if capabilities_data:
                    await device_service.bulk_upsert_capabilities(capabilities_data)

                # NEW: Generate name suggestions (optional, non-blocking)
                if self.auto_generate_name_suggestions and self.name_generator:
                    # Load validator cache if needed
                    if self.name_validator and not self.name_validator._cache_loaded:
                        await self.name_validator.load_cache(session)

                    # Generate suggestions in background (don't block discovery)
                    asyncio.create_task(
                        self._generate_name_suggestions_async(unified_devices, session)
                    )

                break  # Only need one session

            logger.info(
                "Stored %d devices and %d capabilities in database",
                len(devices_data),
                len(capabilities_data),
            )

        except Exception as e:
            logger.error("Error storing devices in database: %s", e)
            raise

    async def force_refresh(self) -> bool:
        """Force a complete discovery refresh."""
        try:
            logger.info("Forcing discovery refresh")
            await self._perform_discovery()
            return True
        except Exception as e:
            logger.error("Error during forced refresh: %s", e)
            return False

    def get_status(self) -> DiscoveryStatus:
        """Get discovery service status."""
        return DiscoveryStatus(
            service_running=self.running,
            ha_connected=self.ha_client.is_connected() if self.ha_client else False,
            last_discovery=self.last_discovery,
            devices_count=len(self.unified_devices),
            areas_count=len(self.ha_areas),
            errors=self.errors[-10:],  # Last 10 errors
        )

    def get_devices(self) -> list[UnifiedDevice]:
        """Get all discovered devices."""
        return list(self.unified_devices.values())

    def get_device(self, device_id: str) -> UnifiedDevice | None:
        """Get specific device by ID."""
        return self.unified_devices.get(device_id)

    def get_devices_by_area(self, area_id: str) -> list[UnifiedDevice]:
        """Get devices by area ID."""
        return [d for d in self.unified_devices.values() if d.area_id == area_id]

    def get_devices_by_integration(self, integration: str) -> list[UnifiedDevice]:
        """Get devices by integration type."""
        return [d for d in self.unified_devices.values() if d.integration == integration]

    def get_areas(self) -> list[HAArea]:
        """Get all discovered areas."""
        return self.ha_areas.copy()

    async def _generate_name_suggestions_async(
        self, unified_devices: list[UnifiedDevice], db_session: AsyncSession
    ):
        """Generate name suggestions asynchronously (non-blocking)"""
        if not self.name_generator or not self.name_validator:
            return

        try:
            from sqlalchemy import select

            from ..models.database import Device, DeviceEntity
            from ..models.name_enhancement import NameSuggestion

            suggestions_created = 0

            for unified_device in unified_devices:
                try:
                    # Get device from database
                    result = await db_session.execute(
                        select(Device).where(Device.id == unified_device.id)
                    )
                    device = result.scalar_one_or_none()

                    if not device:
                        continue

                    # Skip if device already has name_by_user (user customized)
                    if device.name_by_user:
                        continue

                    # Get primary entity for this device
                    entity_result = await db_session.execute(
                        select(DeviceEntity).where(DeviceEntity.device_id == device.id).limit(1)
                    )
                    entity = entity_result.scalar_one_or_none()

                    # Generate suggestion
                    suggestion = await self.name_generator.generate_suggested_name(device, entity)

                    # Only store high-confidence suggestions
                    if suggestion.confidence >= 0.7:
                        # Validate uniqueness
                        validation = await self.name_validator.validate_uniqueness(
                            suggestion.name,
                            device_id=device.id,
                            entity_id=entity.entity_id if entity else None,
                            db_session=db_session,
                        )

                        if not validation.is_unique:
                            # Generate unique variant
                            unique_name = await self.name_validator.generate_unique_variant(
                                suggestion.name, device, db_session=db_session
                            )
                            suggestion.name = unique_name

                        # Check if suggestion already exists
                        existing_result = await db_session.execute(
                            select(NameSuggestion).where(
                                NameSuggestion.device_id == device.id,
                                NameSuggestion.suggested_name == suggestion.name,
                                NameSuggestion.status == "pending",
                            )
                        )
                        if existing_result.scalar_one_or_none():
                            continue  # Already exists

                        # Store suggestion
                        name_suggestion = NameSuggestion(
                            device_id=device.id,
                            entity_id=entity.entity_id if entity else None,
                            original_name=device.name or "Unknown",
                            suggested_name=suggestion.name,
                            confidence_score=suggestion.confidence,
                            suggestion_source=suggestion.source,
                            status="pending",
                            reasoning=suggestion.reasoning,
                        )
                        db_session.add(name_suggestion)
                        suggestions_created += 1

                        # Add to validator cache
                        self.name_validator.name_cache.add(
                            self.name_validator._normalize_name(suggestion.name)
                        )

                except Exception as e:
                    logger.warning(
                        f"Failed to generate name suggestion for device {unified_device.id}: {e}"
                    )
                    continue

            if suggestions_created > 0:
                await db_session.commit()
                logger.info("Generated %d name suggestions", suggestions_created)

        except Exception as e:
            logger.warning(f"Name suggestion generation failed: {e}")
            # Graceful degradation: continue without suggestions
