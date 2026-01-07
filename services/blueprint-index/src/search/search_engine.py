"""Search engine implementation for Blueprint Index Service."""

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..api.schemas import (
    BlueprintResponse,
    BlueprintSearchRequest,
    BlueprintSearchResponse,
    BlueprintSummary,
    IndexingStatusResponse,
    PatternMatchRequest,
    PatternMatchResponse,
)
from ..models import IndexedBlueprint, IndexingJob
from .ranking import BlueprintRanker

logger = logging.getLogger(__name__)


class BlueprintSearchEngine:
    """
    Search engine for querying indexed blueprints.
    
    Supports:
    - Domain/device class filtering
    - Pattern-based matching (trigger/action)
    - Text search
    - Quality and community rating filters
    - Flexible sorting
    """
    
    def __init__(self, db: AsyncSession):
        """Initialize search engine with database session."""
        self.db = db
        self.ranker = BlueprintRanker()
    
    async def search(self, request: BlueprintSearchRequest) -> BlueprintSearchResponse:
        """
        Execute search query and return matching blueprints.
        
        Args:
            request: Search parameters
            
        Returns:
            Search response with matching blueprints
        """
        try:
            # Build query
            query = select(IndexedBlueprint)
            conditions = []
            
            # Domain filter
            if request.domains:
                # Use JSON contains for array fields
                for domain in request.domains:
                    conditions.append(
                        IndexedBlueprint.required_domains.contains([domain])
                    )
            
            # Device class filter
            if request.device_classes:
                for device_class in request.device_classes:
                    conditions.append(
                        IndexedBlueprint.required_device_classes.contains([device_class])
                    )
            
            # Pattern matching (trigger/action)
            if request.trigger_domain:
                conditions.append(
                    IndexedBlueprint.required_domains.contains([request.trigger_domain])
                )
            
            if request.action_domain:
                # Action domain should be in action_services or required_domains
                conditions.append(
                    or_(
                        IndexedBlueprint.required_domains.contains([request.action_domain]),
                        func.json_extract(
                            IndexedBlueprint.action_services, "$"
                        ).like(f"%{request.action_domain}%")
                    )
                )
            
            # Use case filter
            if request.use_case:
                conditions.append(IndexedBlueprint.use_case == request.use_case)
            
            # Domain type filter
            if request.domain_type:
                conditions.append(IndexedBlueprint.domain == request.domain_type)
            
            # Text search
            if request.query:
                search_term = f"%{request.query}%"
                conditions.append(
                    or_(
                        IndexedBlueprint.name.ilike(search_term),
                        IndexedBlueprint.description.ilike(search_term),
                    )
                )
            
            # Tag filter
            if request.tags:
                for tag in request.tags:
                    conditions.append(IndexedBlueprint.tags.contains([tag]))
            
            # Quality filters
            conditions.append(IndexedBlueprint.quality_score >= request.min_quality_score)
            conditions.append(IndexedBlueprint.community_rating >= request.min_community_rating)
            
            # Apply conditions
            if conditions:
                query = query.where(and_(*conditions))
            
            # Count total
            count_query = select(func.count()).select_from(query.subquery())
            total_result = await self.db.execute(count_query)
            total = total_result.scalar() or 0
            
            # Sorting
            sort_column = getattr(IndexedBlueprint, request.sort_by, IndexedBlueprint.quality_score)
            if request.sort_order == "desc":
                query = query.order_by(sort_column.desc())
            else:
                query = query.order_by(sort_column.asc())
            
            # Pagination
            query = query.offset(request.offset).limit(request.limit)
            
            # Execute query
            result = await self.db.execute(query)
            blueprints = result.scalars().all()
            
            # Convert to response format
            summaries = [self._to_summary(bp) for bp in blueprints]
            
            return BlueprintSearchResponse(
                blueprints=summaries,
                total=total,
                limit=request.limit,
                offset=request.offset,
                has_more=(request.offset + len(summaries)) < total,
            )
            
        except Exception as e:
            logger.error(f"Search query failed: {e}", exc_info=True)
            raise
    
    async def find_by_pattern(self, request: PatternMatchRequest) -> PatternMatchResponse:
        """
        Find blueprints matching a trigger-action pattern.
        
        This is optimized for synergy-to-blueprint matching.
        
        Args:
            request: Pattern match parameters
            
        Returns:
            Matching blueprints ranked by relevance
        """
        try:
            query = select(IndexedBlueprint)
            conditions = []
            
            # Trigger domain must be in required domains
            conditions.append(
                IndexedBlueprint.required_domains.contains([request.trigger_domain])
            )
            
            # Action domain should match action services or required domains
            conditions.append(
                or_(
                    IndexedBlueprint.required_domains.contains([request.action_domain]),
                    func.json_extract(
                        IndexedBlueprint.action_services, "$"
                    ).like(f"%{request.action_domain}%")
                )
            )
            
            # Device class filter (optional)
            if request.trigger_device_class:
                conditions.append(
                    IndexedBlueprint.required_device_classes.contains([request.trigger_device_class])
                )
            
            # Quality filter
            conditions.append(IndexedBlueprint.quality_score >= request.min_quality_score)
            
            # Apply conditions
            query = query.where(and_(*conditions))
            
            # Sort by quality and community rating
            query = query.order_by(
                IndexedBlueprint.quality_score.desc(),
                IndexedBlueprint.community_rating.desc(),
            )
            
            # Limit results
            query = query.limit(request.limit)
            
            # Execute query
            result = await self.db.execute(query)
            blueprints = result.scalars().all()
            
            # Rank results
            ranked = self.ranker.rank_for_pattern(
                blueprints,
                request.trigger_domain,
                request.action_domain,
                request.trigger_device_class,
                request.action_device_class,
            )
            
            # Convert to response format
            summaries = [self._to_summary(bp) for bp in ranked]
            
            return PatternMatchResponse(
                blueprints=summaries,
                match_count=len(summaries),
            )
            
        except Exception as e:
            logger.error(f"Pattern match failed: {e}", exc_info=True)
            raise
    
    async def get_by_id(self, blueprint_id: str) -> Optional[BlueprintResponse]:
        """
        Get full blueprint details by ID.
        
        Args:
            blueprint_id: Blueprint ID
            
        Returns:
            Blueprint response or None if not found
        """
        try:
            query = select(IndexedBlueprint).where(IndexedBlueprint.id == blueprint_id)
            result = await self.db.execute(query)
            blueprint = result.scalar_one_or_none()
            
            if not blueprint:
                return None
            
            return self._to_response(blueprint)
            
        except Exception as e:
            logger.error(f"Get blueprint failed: {e}", exc_info=True)
            raise
    
    async def get_indexing_status(self) -> IndexingStatusResponse:
        """
        Get current indexing status and statistics.
        
        Returns:
            Indexing status response
        """
        try:
            # Count total blueprints
            total_query = select(func.count()).select_from(IndexedBlueprint)
            total_result = await self.db.execute(total_query)
            total = total_result.scalar() or 0
            
            # Count by source type
            github_query = select(func.count()).select_from(IndexedBlueprint).where(
                IndexedBlueprint.source_type == "github"
            )
            github_result = await self.db.execute(github_query)
            github_count = github_result.scalar() or 0
            
            discourse_query = select(func.count()).select_from(IndexedBlueprint).where(
                IndexedBlueprint.source_type == "discourse"
            )
            discourse_result = await self.db.execute(discourse_query)
            discourse_count = discourse_result.scalar() or 0
            
            # Get last indexed timestamp
            last_indexed_query = select(func.max(IndexedBlueprint.indexed_at))
            last_indexed_result = await self.db.execute(last_indexed_query)
            last_indexed = last_indexed_result.scalar()
            
            # Check for running jobs
            running_job_query = select(IndexingJob).where(
                IndexingJob.status == "running"
            ).order_by(IndexingJob.started_at.desc())
            running_job_result = await self.db.execute(running_job_query)
            running_job = running_job_result.scalar_one_or_none()
            
            # Calculate progress if job is running
            progress = None
            if running_job and running_job.total_items > 0:
                progress = running_job.processed_items / running_job.total_items
            
            return IndexingStatusResponse(
                total_blueprints=total,
                github_blueprints=github_count,
                discourse_blueprints=discourse_count,
                last_indexed_at=last_indexed,
                indexing_in_progress=running_job is not None,
                current_job_id=running_job.id if running_job else None,
                current_job_progress=progress,
            )
            
        except Exception as e:
            logger.error(f"Get indexing status failed: {e}", exc_info=True)
            raise
    
    def _to_summary(self, blueprint: IndexedBlueprint) -> BlueprintSummary:
        """Convert database model to summary schema."""
        return BlueprintSummary(
            id=blueprint.id,
            name=blueprint.name,
            description=blueprint.description,
            source_url=blueprint.source_url,
            source_type=blueprint.source_type,
            domain=blueprint.domain or "automation",
            use_case=blueprint.use_case,
            required_domains=blueprint.required_domains or [],
            required_device_classes=blueprint.required_device_classes or [],
            community_rating=blueprint.community_rating or 0.0,
            quality_score=blueprint.quality_score or 0.5,
            stars=blueprint.stars or 0,
            complexity=blueprint.complexity or "medium",
            author=blueprint.author,
        )
    
    def _to_response(self, blueprint: IndexedBlueprint) -> BlueprintResponse:
        """Convert database model to full response schema."""
        return BlueprintResponse(
            id=blueprint.id,
            name=blueprint.name,
            description=blueprint.description,
            source_url=blueprint.source_url,
            source_type=blueprint.source_type,
            source_id=blueprint.source_id,
            domain=blueprint.domain or "automation",
            required_domains=blueprint.required_domains or [],
            required_device_classes=blueprint.required_device_classes or [],
            optional_domains=blueprint.optional_domains or [],
            optional_device_classes=blueprint.optional_device_classes or [],
            inputs=blueprint.inputs or {},
            trigger_platforms=blueprint.trigger_platforms or [],
            action_services=blueprint.action_services or [],
            use_case=blueprint.use_case,
            tags=blueprint.tags or [],
            stars=blueprint.stars or 0,
            downloads=blueprint.downloads or 0,
            installs=blueprint.installs or 0,
            community_rating=blueprint.community_rating or 0.0,
            vote_count=blueprint.vote_count or 0,
            quality_score=blueprint.quality_score or 0.5,
            complexity=blueprint.complexity or "medium",
            author=blueprint.author,
            ha_min_version=blueprint.ha_min_version,
            created_at=blueprint.created_at,
            updated_at=blueprint.updated_at,
            yaml_content=blueprint.yaml_content,
        )
