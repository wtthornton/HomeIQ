"""
Alias Service for Entity Resolution

Provides user-defined alias/nickname management for entities.
Allows users to create personalized names for devices (e.g., "bedroom light" → "sleepy light").
"""

import logging

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.models import EntityAlias

logger = logging.getLogger(__name__)


class AliasService:
    """Service for managing user-defined entity aliases"""

    def __init__(self, db: AsyncSession):
        """
        Initialize alias service.

        Args:
            db: Database session
        """
        self.db = db

    async def get_aliases_for_entity(
        self,
        entity_id: str,
        user_id: str = "anonymous",
    ) -> list[str]:
        """
        Get all aliases for a specific entity.

        Args:
            entity_id: Entity ID to get aliases for
            user_id: User ID (default: "anonymous")

        Returns:
            List of alias strings
        """
        try:
            result = await self.db.execute(
                select(EntityAlias.alias)
                .where(EntityAlias.entity_id == entity_id)
                .where(EntityAlias.user_id == user_id),
            )
            aliases = [row[0] for row in result.fetchall()]
            logger.debug(f"Found {len(aliases)} aliases for entity {entity_id} (user: {user_id})")
            return aliases
        except Exception as e:
            logger.exception(f"Error getting aliases for entity {entity_id}: {e}")
            return []

    async def get_entity_for_alias(
        self,
        alias: str,
        user_id: str = "anonymous",
    ) -> str | None:
        """
        Get entity_id for a given alias (exact match lookup).

        This is the primary method used in entity resolution - fast indexed lookup.

        Args:
            alias: Alias string to look up
            user_id: User ID (default: "anonymous")

        Returns:
            Entity ID if alias found, None otherwise
        """
        try:
            alias_lower = alias.lower().strip()
            result = await self.db.execute(
                select(EntityAlias.entity_id)
                .where(EntityAlias.alias == alias_lower)
                .where(EntityAlias.user_id == user_id)
                .limit(1),
            )
            row = result.first()
            if row:
                entity_id = row[0]
                logger.debug(f"Alias '{alias}' → entity_id: {entity_id}")
                return entity_id
            return None
        except Exception as e:
            logger.exception(f"Error looking up alias '{alias}': {e}")
            return None

    async def create_alias(
        self,
        entity_id: str,
        alias: str,
        user_id: str = "anonymous",
    ) -> EntityAlias | None:
        """
        Create a new alias for an entity.

        Args:
            entity_id: Entity ID to alias
            alias: Alias string
            user_id: User ID (default: "anonymous")

        Returns:
            Created EntityAlias object, or None if creation failed
        """
        try:
            alias_lower = alias.lower().strip()

            # Check if alias already exists for this user
            existing = await self.get_entity_for_alias(alias_lower, user_id)
            if existing:
                logger.warning(f"Alias '{alias}' already exists for user {user_id} → {existing}")
                return None

            # Create new alias
            entity_alias = EntityAlias(
                entity_id=entity_id,
                alias=alias_lower,
                user_id=user_id,
            )
            self.db.add(entity_alias)
            await self.db.commit()
            await self.db.refresh(entity_alias)

            logger.info(f"Created alias '{alias}' → {entity_id} (user: {user_id})")
            return entity_alias
        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Error creating alias '{alias}' → {entity_id}: {e}")
            return None

    async def delete_alias(
        self,
        alias: str,
        user_id: str = "anonymous",
    ) -> bool:
        """
        Delete an alias.

        Args:
            alias: Alias to delete
            user_id: User ID (default: "anonymous")

        Returns:
            True if deleted, False otherwise
        """
        try:
            alias_lower = alias.lower().strip()
            result = await self.db.execute(
                delete(EntityAlias)
                .where(EntityAlias.alias == alias_lower)
                .where(EntityAlias.user_id == user_id),
            )
            await self.db.commit()

            deleted = result.rowcount > 0
            if deleted:
                logger.info(f"Deleted alias '{alias}' for user {user_id}")
            else:
                logger.debug(f"Alias '{alias}' not found for user {user_id}")

            return deleted
        except Exception as e:
            await self.db.rollback()
            logger.exception(f"Error deleting alias '{alias}': {e}")
            return False

    async def get_all_aliases(
        self,
        user_id: str = "anonymous",
    ) -> dict[str, list[str]]:
        """
        Get all aliases for a user, grouped by entity_id.

        Args:
            user_id: User ID (default: "anonymous")

        Returns:
            Dictionary mapping entity_id → list of aliases
        """
        try:
            result = await self.db.execute(
                select(EntityAlias.entity_id, EntityAlias.alias)
                .where(EntityAlias.user_id == user_id),
            )

            aliases_by_entity: dict[str, list[str]] = {}
            for row in result.fetchall():
                entity_id, alias = row
                if entity_id not in aliases_by_entity:
                    aliases_by_entity[entity_id] = []
                aliases_by_entity[entity_id].append(alias)

            logger.debug(f"Found aliases for {len(aliases_by_entity)} entities (user: {user_id})")
            return aliases_by_entity
        except Exception as e:
            logger.exception(f"Error getting all aliases for user {user_id}: {e}")
            return {}

