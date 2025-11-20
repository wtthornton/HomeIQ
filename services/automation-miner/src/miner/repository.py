"""
Corpus Repository

Handles all database operations for the automation corpus.
Uses SQLAlchemy async session management (Context7 pattern).
"""
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .database import CommunityAutomation, MinerState
from .models import AutomationMetadata

logger = logging.getLogger(__name__)


class CorpusRepository:
    """Repository for automation corpus database operations"""

    def __init__(self, session: AsyncSession):
        """
        Initialize repository with async session
        
        Args:
            session: SQLAlchemy AsyncSession
        """
        self.session = session

    async def save_automation(
        self,
        metadata: AutomationMetadata
    ) -> CommunityAutomation:
        """
        Save or update automation in corpus
        
        Args:
            metadata: AutomationMetadata to save
        
        Returns:
            Saved CommunityAutomation instance
        """
        # Check if already exists (by source_id)
        stmt = select(CommunityAutomation).where(
            and_(
                CommunityAutomation.source == metadata.source,
                CommunityAutomation.source_id == metadata.source_id
            )
        )
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing
            existing.title = metadata.title
            existing.description = metadata.description
            existing.devices = metadata.devices
            existing.integrations = metadata.integrations
            existing.triggers = metadata.triggers
            existing.conditions = metadata.conditions
            existing.actions = metadata.actions
            existing.use_case = metadata.use_case
            existing.complexity = metadata.complexity
            existing.quality_score = metadata.quality_score
            existing.vote_count = metadata.vote_count
            existing.updated_at = metadata.updated_at
            existing.last_crawled = datetime.now(timezone.utc)
            existing.extra_metadata = metadata.metadata

            logger.debug(f"Updated automation: {existing.id} - {metadata.title}")
        else:
            # Insert new
            existing = CommunityAutomation(
                source=metadata.source,
                source_id=metadata.source_id,
                title=metadata.title,
                description=metadata.description,
                devices=metadata.devices,
                integrations=metadata.integrations,
                triggers=metadata.triggers,
                conditions=metadata.conditions,
                actions=metadata.actions,
                use_case=metadata.use_case,
                complexity=metadata.complexity,
                quality_score=metadata.quality_score,
                vote_count=metadata.vote_count,
                created_at=metadata.created_at,
                updated_at=metadata.updated_at,
                last_crawled=datetime.now(timezone.utc),
                extra_metadata=metadata.metadata
            )
            self.session.add(existing)

            logger.debug(f"Inserted new automation: {metadata.title}")

        await self.session.commit()
        await self.session.refresh(existing)

        return existing

    async def save_batch(
        self,
        metadata_list: list[AutomationMetadata]
    ) -> int:
        """
        Save multiple automations in a batch
        
        Args:
            metadata_list: List of AutomationMetadata
        
        Returns:
            Number of automations saved
        """
        count = 0
        for metadata in metadata_list:
            await self.save_automation(metadata)
            count += 1

        logger.info(f"Batch saved: {count} automations")
        return count

    async def get_by_id(self, automation_id: int) -> dict[str, Any] | None:
        """
        Get automation by ID
        
        Args:
            automation_id: Database ID
        
        Returns:
            Automation dictionary or None
        """
        stmt = select(CommunityAutomation).where(CommunityAutomation.id == automation_id)
        result = await self.session.execute(stmt)
        automation = result.scalar_one_or_none()

        if not automation:
            return None

        return self._to_dict(automation)

    async def get_by_source_id(
        self,
        source: str,
        source_id: str
    ) -> CommunityAutomation | None:
        """
        Get automation by source and source_id
        
        Args:
            source: 'discourse' or 'github'
            source_id: Unique source identifier
        
        Returns:
            CommunityAutomation or None
        """
        stmt = select(CommunityAutomation).where(
            and_(
                CommunityAutomation.source == source,
                CommunityAutomation.source_id == source_id
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def search(
        self,
        filters: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Search automations with filters
        
        Args:
            filters: Dictionary with optional keys:
                - device: Filter by device type
                - integration: Filter by integration
                - use_case: Filter by use case
                - min_quality: Minimum quality score
                - limit: Maximum results
        
        Returns:
            List of automation dictionaries
        """
        # Build query
        stmt = select(CommunityAutomation)

        # Apply filters
        conditions = []

        # Device filter (JSON contains check)
        if 'device' in filters and filters['device']:
            device = filters['device']
            # SQLite JSON support: json_each for array containment
            conditions.append(
                CommunityAutomation.devices.contains([device])
            )

        # Integration filter
        if 'integration' in filters and filters['integration']:
            integration = filters['integration']
            conditions.append(
                CommunityAutomation.integrations.contains([integration])
            )

        # Use case filter
        if 'use_case' in filters and filters['use_case']:
            use_case = filters['use_case']
            conditions.append(CommunityAutomation.use_case == use_case)

        # Quality filter
        min_quality = filters.get('min_quality', 0.7)
        conditions.append(CommunityAutomation.quality_score >= min_quality)

        # Apply all conditions
        if conditions:
            stmt = stmt.where(and_(*conditions))

        # Order by quality descending
        stmt = stmt.order_by(CommunityAutomation.quality_score.desc())

        # Limit
        limit = filters.get('limit', 50)
        stmt = stmt.limit(limit)

        # Execute query
        result = await self.session.execute(stmt)
        automations = result.scalars().all()

        return [self._to_dict(auto) for auto in automations]

    async def get_all(
        self,
        source: str | None = None,
        min_quality: float = 0.0
    ) -> list[CommunityAutomation]:
        """
        Get all automations (optionally filtered)
        
        Args:
            source: Optional source filter
            min_quality: Minimum quality score
        
        Returns:
            List of CommunityAutomation instances
        """
        stmt = select(CommunityAutomation)

        conditions = []
        if source:
            conditions.append(CommunityAutomation.source == source)
        if min_quality > 0.0:
            conditions.append(CommunityAutomation.quality_score >= min_quality)

        if conditions:
            stmt = stmt.where(and_(*conditions))

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_stats(self) -> dict[str, Any]:
        """
        Get corpus statistics
        
        Returns:
            Dictionary with stats:
                - total: Total automation count
                - avg_quality: Average quality score
                - device_count: Number of unique device types
                - integration_count: Number of unique integrations
                - by_use_case: Count by use case
                - by_complexity: Count by complexity
                - last_crawl_time: Last crawl timestamp
        """
        # Total count
        total_stmt = select(func.count(CommunityAutomation.id))
        total_result = await self.session.execute(total_stmt)
        total = total_result.scalar()

        # Average quality
        avg_stmt = select(func.avg(CommunityAutomation.quality_score))
        avg_result = await self.session.execute(avg_stmt)
        avg_quality = avg_result.scalar() or 0.0

        # Count by use case
        use_case_stmt = select(
            CommunityAutomation.use_case,
            func.count(CommunityAutomation.id)
        ).group_by(CommunityAutomation.use_case)
        use_case_result = await self.session.execute(use_case_stmt)
        by_use_case = {row[0]: row[1] for row in use_case_result.all()}

        # Count by complexity
        complexity_stmt = select(
            CommunityAutomation.complexity,
            func.count(CommunityAutomation.id)
        ).group_by(CommunityAutomation.complexity)
        complexity_result = await self.session.execute(complexity_stmt)
        by_complexity = {row[0]: row[1] for row in complexity_result.all()}

        # Last crawl time
        last_crawl_stmt = select(func.max(CommunityAutomation.last_crawled))
        last_crawl_result = await self.session.execute(last_crawl_stmt)
        last_crawl_time = last_crawl_result.scalar()

        # Collect unique devices and integrations
        all_stmt = select(CommunityAutomation.devices, CommunityAutomation.integrations)
        all_result = await self.session.execute(all_stmt)

        unique_devices = set()
        unique_integrations = set()
        for devices, integrations in all_result.all():
            if devices:
                unique_devices.update(devices)
            if integrations:
                unique_integrations.update(integrations)

        return {
            'total': total,
            'avg_quality': round(avg_quality, 3),
            'device_count': len(unique_devices),
            'integration_count': len(unique_integrations),
            'devices': sorted(list(unique_devices)),
            'integrations': sorted(list(unique_integrations)),
            'by_use_case': by_use_case,
            'by_complexity': by_complexity,
            'last_crawl_time': last_crawl_time.isoformat() if last_crawl_time else None
        }

    async def set_state(self, key: str, value: str):
        """Set miner state value"""
        stmt = select(MinerState).where(MinerState.key == key)
        result = await self.session.execute(stmt)
        state = result.scalar_one_or_none()

        if state:
            state.value = value
            state.updated_at = datetime.now(timezone.utc)
        else:
            state = MinerState(key=key, value=value, updated_at=datetime.now(timezone.utc))
            self.session.add(state)

        await self.session.commit()

    async def get_state(self, key: str) -> str | None:
        """Get miner state value"""
        stmt = select(MinerState).where(MinerState.key == key)
        result = await self.session.execute(stmt)
        state = result.scalar_one_or_none()
        return state.value if state else None

    async def get_last_crawl_timestamp(self) -> datetime | None:
        """Get last crawl timestamp from state"""
        value = await self.get_state('last_crawl_timestamp')
        if value:
            return datetime.fromisoformat(value)
        return None

    async def set_last_crawl_timestamp(self, timestamp: datetime):
        """Set last crawl timestamp"""
        await self.set_state('last_crawl_timestamp', timestamp.isoformat())

    async def is_duplicate(
        self,
        metadata: AutomationMetadata
    ) -> bool:
        """
        Quick check if automation already exists
        
        Args:
            metadata: AutomationMetadata to check
        
        Returns:
            True if duplicate exists
        """
        existing = await self.get_by_source_id(metadata.source, metadata.source_id)
        return existing is not None

    async def prune_low_quality(
        self,
        quality_threshold: float,
        age_days: int
    ) -> int:
        """
        Prune low-quality automations that are old
        
        Removes automations that:
        - Have quality_score < quality_threshold
        - Are older than age_days
        
        Args:
            quality_threshold: Minimum quality score to keep
            age_days: Minimum age in days for pruning (only prune old low-quality items)
        
        Returns:
            Number of automations pruned
        """
        from datetime import timedelta

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=age_days)

        # Find automations to prune
        stmt = select(CommunityAutomation).where(
            and_(
                CommunityAutomation.quality_score < quality_threshold,
                CommunityAutomation.created_at < cutoff_date
            )
        )

        result = await self.session.execute(stmt)
        to_prune = result.scalars().all()

        # Delete them
        pruned_count = 0
        for automation in to_prune:
            await self.session.delete(automation)
            pruned_count += 1

        if pruned_count > 0:
            await self.session.commit()
            logger.info(f"Pruned {pruned_count} low-quality automations (quality < {quality_threshold}, age > {age_days} days)")

        return pruned_count

    def _to_dict(self, automation: CommunityAutomation) -> dict[str, Any]:
        """Convert CommunityAutomation to dictionary"""
        return {
            'id': automation.id,
            'source': automation.source,
            'source_id': automation.source_id,
            'title': automation.title,
            'description': automation.description,
            'devices': automation.devices,
            'integrations': automation.integrations,
            'triggers': automation.triggers,
            'conditions': automation.conditions,
            'actions': automation.actions,
            'use_case': automation.use_case,
            'complexity': automation.complexity,
            'quality_score': automation.quality_score,
            'vote_count': automation.vote_count,
            'created_at': automation.created_at.isoformat(),
            'updated_at': automation.updated_at.isoformat(),
            'last_crawled': automation.last_crawled.isoformat(),
            'metadata': automation.extra_metadata
        }

