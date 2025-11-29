"""
Statistics Metadata Service (Epic 45.1)

Manages statistics metadata tracking and entity eligibility detection.
"""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models.entity import Entity
from ..models.statistics_meta import StatisticsMeta

logger = logging.getLogger(__name__)


class StatisticsMetadataService:
    """Service for managing statistics metadata and entity eligibility"""

    @staticmethod
    async def is_statistics_eligible(entity_id: str, session: AsyncSession) -> bool:
        """
        Check if an entity is eligible for statistics aggregation.
        
        Args:
            entity_id: Entity ID to check
            session: Database session
            
        Returns:
            True if entity is eligible, False otherwise
        """
        result = await session.execute(
            select(StatisticsMeta).where(StatisticsMeta.statistic_id == entity_id)
        )
        meta = result.scalar_one_or_none()
        return meta is not None

    @staticmethod
    async def get_metadata(entity_id: str, session: AsyncSession) -> Optional[StatisticsMeta]:
        """
        Get statistics metadata for an entity.
        
        Args:
            entity_id: Entity ID
            session: Database session
            
        Returns:
            StatisticsMeta instance or None
        """
        result = await session.execute(
            select(StatisticsMeta).where(StatisticsMeta.statistic_id == entity_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def sync_metadata_from_entity(
        entity: Entity,
        state_class: Optional[str] = None,
        unit_of_measurement: Optional[str] = None,
        session: AsyncSession = None
    ) -> StatisticsMeta:
        """
        Sync statistics metadata from entity registry entry.
        
        Args:
            entity: Entity model instance
            state_class: State class from Home Assistant state attributes
            unit_of_measurement: Unit of measurement (from entity or state)
            session: Database session (optional, will create if not provided)
            
        Returns:
            StatisticsMeta instance
        """
        if session is None:
            async for db_session in get_db():
                session = db_session
                break

        # Use unit_of_measurement from entity if not provided
        if not unit_of_measurement:
            unit_of_measurement = entity.unit_of_measurement

        # Determine eligibility based on state_class
        is_eligible = False
        has_mean = False
        has_sum = False

        if state_class == "measurement":
            # Measurement entities (temperature, humidity, power, etc.)
            is_eligible = True
            has_mean = True
            has_sum = False
        elif state_class == "total_increasing":
            # Total increasing entities (energy meters, counters)
            is_eligible = True
            has_mean = False
            has_sum = True
        elif state_class == "total":
            # Total entities (can reset)
            is_eligible = True
            has_mean = False
            has_sum = True
        elif unit_of_measurement and entity.domain == "sensor":
            # Fallback: If entity has unit_of_measurement and is a sensor,
            # assume it's a measurement entity (lenient approach)
            is_eligible = True
            has_mean = True
            has_sum = False
            state_class = "measurement"  # Default assumption

        if not is_eligible:
            logger.debug(f"Entity {entity.entity_id} not eligible for statistics (state_class={state_class}, unit={unit_of_measurement})")
            return None

        # Check if metadata already exists
        result = await session.execute(
            select(StatisticsMeta).where(StatisticsMeta.statistic_id == entity.entity_id)
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing metadata
            existing.state_class = state_class
            existing.unit_of_measurement = unit_of_measurement
            existing.has_mean = has_mean
            existing.has_sum = has_sum
            existing.updated_at = datetime.utcnow()
            await session.commit()
            logger.debug(f"Updated statistics metadata for {entity.entity_id}")
            return existing
        else:
            # Create new metadata
            meta = StatisticsMeta(
                statistic_id=entity.entity_id,
                source="state",
                unit_of_measurement=unit_of_measurement,
                state_class=state_class,
                has_mean=has_mean,
                has_sum=has_sum
            )
            session.add(meta)
            await session.commit()
            logger.info(f"Created statistics metadata for {entity.entity_id} (state_class={state_class})")
            return meta

    @staticmethod
    async def sync_all_eligible_entities(session: AsyncSession) -> int:
        """
        Sync statistics metadata for all eligible entities.
        
        This should be called after device/entity registry updates.
        
        Args:
            session: Database session
            
        Returns:
            Number of entities synced
        """
        # Get all entities with unit_of_measurement (potential candidates)
        result = await session.execute(
            select(Entity).where(Entity.unit_of_measurement.isnot(None))
        )
        entities = result.scalars().all()

        synced_count = 0
        for entity in entities:
            # Try to sync metadata (will determine eligibility)
            # Note: state_class would come from Home Assistant state attributes
            # For now, we'll use unit_of_measurement as a proxy
            meta = await StatisticsMetadataService.sync_metadata_from_entity(
                entity,
                state_class=None,  # Will be determined from unit_of_measurement
                session=session
            )
            if meta:
                synced_count += 1

        logger.info(f"Synced statistics metadata for {synced_count} entities")
        return synced_count

    @staticmethod
    async def get_all_eligible_entity_ids(session: AsyncSession) -> list[str]:
        """
        Get list of all entity IDs eligible for statistics.
        
        Args:
            session: Database session
            
        Returns:
            List of entity IDs
        """
        result = await session.execute(select(StatisticsMeta.statistic_id))
        return [row[0] for row in result.fetchall()]

