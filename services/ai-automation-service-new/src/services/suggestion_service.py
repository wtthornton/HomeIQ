"""
Suggestion Service

Epic 39, Story 39.10: Automation Service Foundation
Core service for generating and managing automation suggestions.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..clients.data_api_client import DataAPIClient
from ..clients.openai_client import OpenAIClient
from ..database.models import Suggestion

logger = logging.getLogger(__name__)


class SuggestionService:
    """
    Service for generating and managing automation suggestions.
    
    Features:
    - Generate suggestions from patterns
    - List and filter suggestions
    - Store suggestions in database
    - Track usage statistics
    """

    def __init__(
        self,
        db: AsyncSession,
        data_api_client: DataAPIClient,
        openai_client: OpenAIClient
    ):
        """
        Initialize suggestion service.
        
        Args:
            db: Database session
            data_api_client: Client for fetching data from Data API
            openai_client: Client for generating suggestions via OpenAI
        """
        self.db = db
        self.data_api_client = data_api_client
        self.openai_client = openai_client

    async def generate_suggestions(
        self,
        pattern_ids: list[str] | None = None,
        days: int = 30,
        limit: int = 10
    ) -> list[dict[str, Any]]:
        """
        Generate automation suggestions from detected patterns.
        
        Args:
            pattern_ids: Optional list of pattern IDs to generate suggestions for
            days: Number of days of data to analyze
            limit: Maximum number of suggestions to generate
        
        Returns:
            List of suggestion dictionaries
        """
        try:
            # Fetch events from Data API
            logger.info(f"Fetching events for suggestion generation (days={days}, limit=10000)")
            events = await self.data_api_client.fetch_events(days=days, limit=10000)
            
            logger.info(f"Received {len(events) if events else 0} events from Data API")
            
            if not events:
                logger.warning("No events found for suggestion generation")
                return []
            
            # TODO: Epic 39, Story 39.13 - Integrate with pattern detection service
            # Current: Generate suggestions directly from events
            # Future: Use detected patterns from pattern-detection-service for better suggestions
            
            suggestions = []
            
            # Calculate how many suggestions we can generate (1 per 100 events)
            max_suggestions = len(events) // 100
            actual_limit = min(limit, max_suggestions)
            logger.info(f"Can generate up to {max_suggestions} suggestions, requested {limit}, will generate {actual_limit}")
            
            # Generate suggestions using OpenAI
            for i in range(actual_limit):
                try:
                    # Get batch of events for this suggestion
                    event_batch = events[i * 100:(i + 1) * 100]
                    
                    # Generate description using OpenAI
                    description = await self.openai_client.generate_suggestion_description(
                        pattern_data={"events": event_batch}
                    )
                    
                    # Create suggestion dictionary (matches Suggestion model fields)
                    suggestion = {
                        "title": f"Automation Suggestion {i + 1}",
                        "description": description,
                        "status": "draft",
                    }
                    suggestions.append(suggestion)
                    
                    logger.debug(f"Generated suggestion {i + 1}/{actual_limit}")
                    
                except Exception as e:
                    logger.error(f"Failed to generate suggestion {i + 1}: {e}")
                    continue
            
            # Store suggestions in database
            stored_suggestions = []
            for suggestion_data in suggestions:
                try:
                    suggestion = Suggestion(
                        title=suggestion_data["title"],
                        description=suggestion_data["description"],
                        status=suggestion_data["status"]
                        # Note: pattern_data is stored in automation_json field if needed
                    )
                    self.db.add(suggestion)
                    await self.db.flush()
                    await self.db.refresh(suggestion)
                    
                    stored_suggestions.append({
                        "id": suggestion.id,
                        "title": suggestion.title,
                        "description": suggestion.description,
                        "status": suggestion.status,
                        "created_at": suggestion.created_at.isoformat() if suggestion.created_at else None
                    })
                except Exception as e:
                    logger.error(f"Failed to store suggestion: {e}")
                    continue
            
            await self.db.commit()
            
            logger.info(f"Generated {len(stored_suggestions)} suggestions")
            return stored_suggestions
            
        except Exception as e:
            logger.error(f"Failed to generate suggestions: {e}")
            await self.db.rollback()
            raise

    async def list_suggestions(
        self,
        limit: int = 50,
        offset: int = 0,
        status: str | None = None
    ) -> dict[str, Any]:
        """
        List automation suggestions with filtering and pagination.
        
        Args:
            limit: Maximum number of suggestions to return
            offset: Number of suggestions to skip
            status: Optional filter by status (pending, approved, rejected, deployed)
        
        Returns:
            Dictionary with suggestions list and pagination info
        """
        try:
            # Build query
            query = select(Suggestion)
            
            if status:
                query = query.where(Suggestion.status == status)
            
            # Get total count (efficient SQL COUNT)
            count_query = select(func.count()).select_from(Suggestion)
            if status:
                count_query = count_query.where(Suggestion.status == status)
            
            total_result = await self.db.execute(count_query)
            total = total_result.scalar() or 0
            
            # Apply pagination
            query = query.order_by(Suggestion.created_at.desc())
            query = query.limit(limit).offset(offset)
            
            # Execute query
            result = await self.db.execute(query)
            suggestions = result.scalars().all()
            
            # Convert to dictionaries
            suggestions_list = []
            for suggestion in suggestions:
                suggestions_list.append({
                    "id": suggestion.id,
                    "title": suggestion.title,
                    "description": suggestion.description,
                    "status": suggestion.status,
                    "created_at": suggestion.created_at.isoformat() if suggestion.created_at else None,
                    "updated_at": suggestion.updated_at.isoformat() if suggestion.updated_at else None
                })
            
            return {
                "suggestions": suggestions_list,
                "total": total,
                "limit": limit,
                "offset": offset
            }
            
        except Exception as e:
            logger.error(f"Failed to list suggestions: {e}")
            raise

    async def get_suggestion(self, suggestion_id: int) -> dict[str, Any] | None:
        """
        Get a specific suggestion by ID.
        
        Args:
            suggestion_id: Suggestion ID
        
        Returns:
            Suggestion dictionary or None if not found
        """
        try:
            query = select(Suggestion).where(Suggestion.id == suggestion_id)
            result = await self.db.execute(query)
            suggestion = result.scalar_one_or_none()
            
            if not suggestion:
                return None
            
            return {
                "id": suggestion.id,
                "title": suggestion.title,
                "description": suggestion.description,
                "status": suggestion.status,
                "automation_yaml": suggestion.automation_yaml,
                "created_at": suggestion.created_at.isoformat() if suggestion.created_at else None,
                "updated_at": suggestion.updated_at.isoformat() if suggestion.updated_at else None,
                "deployed_at": suggestion.deployed_at.isoformat() if suggestion.deployed_at else None
            }
            
        except Exception as e:
            logger.error(f"Failed to get suggestion {suggestion_id}: {e}")
            raise

    async def update_suggestion_status(
        self,
        suggestion_id: int,
        status: str
    ) -> bool:
        """
        Update suggestion status.
        
        Args:
            suggestion_id: Suggestion ID
            status: New status (pending, approved, rejected, deployed)
        
        Returns:
            True if successful
        """
        try:
            query = select(Suggestion).where(Suggestion.id == suggestion_id)
            result = await self.db.execute(query)
            suggestion = result.scalar_one_or_none()
            
            if not suggestion:
                return False
            
            suggestion.status = status
            suggestion.updated_at = datetime.now(timezone.utc)
            
            await self.db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to update suggestion status: {e}")
            await self.db.rollback()
            raise

    async def get_usage_stats(self) -> dict[str, Any]:
        """
        Get suggestion usage statistics.
        
        Returns:
            Dictionary with usage statistics
        """
        try:
            # Get counts by status
            query = select(Suggestion)
            result = await self.db.execute(query)
            all_suggestions = result.scalars().all()
            
            stats = {
                "total": len(all_suggestions),
                "by_status": {},
                "openai_usage": self.openai_client.get_usage_stats() if self.openai_client else {}
            }
            
            # Count by status
            for suggestion in all_suggestions:
                status = suggestion.status or "unknown"
                stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get usage stats: {e}")
            raise

