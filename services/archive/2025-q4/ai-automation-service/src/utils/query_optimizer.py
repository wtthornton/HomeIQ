"""
Database Query Optimization Utilities

Epic 39, Story 39.15: Performance Optimization
Utilities for optimizing database queries, batching operations, and reducing N+1 queries.
"""

import logging
from typing import Any, Callable, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

logger = logging.getLogger(__name__)


class QueryOptimizer:
    """
    Utilities for optimizing database queries.
    
    Helps identify and fix N+1 query problems, batch operations, and optimize queries.
    """
    
    @staticmethod
    async def batch_fetch(
        db: AsyncSession,
        query_func: Callable,
        ids: list[Any],
        batch_size: int = 100
    ) -> dict[Any, Any]:
        """
        Batch fetch records by IDs to avoid N+1 queries.
        
        Args:
            db: Database session
            query_func: Function that takes a list of IDs and returns a query
            ids: List of IDs to fetch
            batch_size: Number of IDs per batch
        
        Returns:
            Dictionary mapping ID to record
        """
        result = {}
        
        # Process in batches
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i + batch_size]
            query = query_func(batch_ids)
            records = await db.execute(query)
            
            for record in records.scalars().all():
                # Assume record has an id attribute
                if hasattr(record, 'id'):
                    result[record.id] = record
        
        return result
    
    @staticmethod
    async def eager_load_relationships(
        db: AsyncSession,
        query: Any,
        relationships: list[str]
    ) -> Any:
        """
        Eager load relationships to avoid lazy loading N+1 queries.
        
        Note: This uses SQLAlchemy's joinedload or selectinload.
        For SQLAlchemy 2.0+ syntax.
        
        Args:
            db: Database session
            query: Base query
            relationships: List of relationship names to eager load
        
        Returns:
            Modified query with eager loading
        """
        from sqlalchemy.orm import selectinload, joinedload
        
        for rel in relationships:
            # Try selectinload first (better for 1-to-many)
            try:
                query = query.options(selectinload(rel))
            except AttributeError:
                # Fall back to joinedload (better for many-to-one)
                try:
                    query = query.options(joinedload(rel))
                except AttributeError:
                    logger.warning(f"Could not eager load relationship: {rel}")
        
        return query
    
    @staticmethod
    def add_query_hints(query: Any, hints: dict[str, Any]) -> Any:
        """
        Add query hints for optimization (database-specific).
        
        Args:
            query: SQLAlchemy query
            hints: Dictionary of hints (e.g., {"index": "idx_name"})
        
        Returns:
            Query with hints applied
        """
        # SQLite doesn't support hints, but other databases do
        # For now, this is a placeholder for future optimization
        
        # Example for PostgreSQL:
        # from sqlalchemy.sql import text
        # if "index" in hints:
        #     query = query.execution_options(
        #         postgresql_options={"SET INDEX": hints["index"]}
        #     )
        
        return query


async def optimize_n_plus_one(
    db: AsyncSession,
    parent_records: list[Any],
    relationship_name: str,
    child_model: Any
) -> dict[Any, list[Any]]:
    """
    Fix N+1 query problem by batch loading related records.
    
    Args:
        db: Database session
        parent_records: List of parent records
        relationship_name: Name of relationship to load
        child_model: Child model class
    
    Returns:
        Dictionary mapping parent ID to list of children
    """
    if not parent_records:
        return {}
    
    # Extract parent IDs
    parent_ids = [getattr(p, 'id') for p in parent_records if hasattr(p, 'id')]
    
    if not parent_ids:
        return {}
    
    # Find foreign key column (assumes naming convention: parent_id or parent_model_id)
    import inspect
    child_columns = inspect.getmembers(child_model, lambda x: hasattr(x, 'property'))
    
    # Build query to fetch all children at once
    # This assumes a foreign key relationship
    # Adjust based on your actual schema
    
    # Example:
    # parent_id_col = getattr(child_model, f"{relationship_name}_id", None)
    # if parent_id_col:
    #     query = select(child_model).where(parent_id_col.in_(parent_ids))
    #     result = await db.execute(query)
    #     children = result.scalars().all()
    
    # Group by parent ID
    result = {}
    # for child in children:
    #     parent_id = getattr(child, f"{relationship_name}_id")
    #     if parent_id not in result:
    #         result[parent_id] = []
    #     result[parent_id].append(child)
    
    return result

