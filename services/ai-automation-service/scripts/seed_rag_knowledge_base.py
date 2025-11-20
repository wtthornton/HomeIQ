"""
Seed RAG Knowledge Base

Extracts and stores semantic knowledge from:
1. Successful queries (AskAIQuery table)
2. Common patterns (common_patterns.py)
3. Deployed automations (Suggestion table)

Usage:
    python scripts/seed_rag_knowledge_base.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging

import src.database.models as db_models
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.models import AskAIQuery, Suggestion, init_db
from src.patterns.common_patterns import PATTERNS
from src.services.rag import RAGClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def seed_from_queries(db: AsyncSession, rag_client: RAGClient) -> int:
    """
    Seed knowledge base from successful queries.
    
    Args:
        db: Database session
        rag_client: RAG client instance
        
    Returns:
        Number of queries seeded
    """
    logger.info("📚 Seeding from successful queries...")

    # Get successful queries (high confidence, deployed, or no clarification needed)
    stmt = select(AskAIQuery).where(
        (AskAIQuery.confidence >= 0.85) |  # High confidence
        (AskAIQuery.original_query.isnot(None))  # Has query text
    ).order_by(AskAIQuery.created_at.desc())

    result = await db.execute(stmt)
    queries = result.scalars().all()

    count = 0
    for query in queries:
        try:
            # Calculate success score based on confidence
            success_score = query.confidence if query.confidence else 0.5

            # Store query
            await rag_client.store(
                text=query.original_query,
                knowledge_type='query',
                metadata={
                    'query_id': query.query_id,
                    'confidence': query.confidence,
                    'user_id': query.user_id,
                    'created_at': query.created_at.isoformat() if query.created_at else None
                },
                success_score=success_score
            )
            count += 1

            if count % 10 == 0:
                logger.info(f"  Processed {count} queries...")

        except Exception as e:
            logger.warning(f"Failed to seed query {query.query_id}: {e}")
            continue

    logger.info(f"✅ Seeded {count} queries")
    return count


async def seed_from_patterns(db: AsyncSession, rag_client: RAGClient) -> int:
    """
    Seed knowledge base from common patterns.
    
    Args:
        db: Database session
        rag_client: RAG client instance
        
    Returns:
        Number of patterns seeded
    """
    logger.info("📚 Seeding from common patterns...")

    count = 0
    for pattern_id, pattern in PATTERNS.items():
        try:
            # Create descriptive text from pattern
            pattern_text = f"{pattern.name}. {pattern.description}. Keywords: {', '.join(pattern.keywords)}"

            # Store pattern
            await rag_client.store(
                text=pattern_text,
                knowledge_type='pattern',
                metadata={
                    'pattern_id': pattern_id,
                    'category': pattern.category,
                    'keywords': pattern.keywords,
                    'priority': pattern.priority
                },
                success_score=0.9  # Patterns are high-quality, hand-crafted
            )
            count += 1

        except Exception as e:
            logger.warning(f"Failed to seed pattern {pattern_id}: {e}")
            continue

    logger.info(f"✅ Seeded {count} patterns")
    return count


async def seed_from_suggestions(db: AsyncSession, rag_client: RAGClient) -> int:
    """
    Seed knowledge base from deployed automations.
    
    Args:
        db: Database session
        rag_client: RAG client instance
        
    Returns:
        Number of automations seeded
    """
    logger.info("📚 Seeding from deployed automations...")

    # Get deployed suggestions (status = 'deployed')
    stmt = select(Suggestion).where(
        Suggestion.status == 'deployed'
    ).order_by(Suggestion.created_at.desc())

    result = await db.execute(stmt)
    suggestions = result.scalars().all()

    count = 0
    for suggestion in suggestions:
        try:
            # Create descriptive text from suggestion
            automation_text = suggestion.description or suggestion.title or "Automation"

            # Store automation
            await rag_client.store(
                text=automation_text,
                knowledge_type='automation',
                metadata={
                    'suggestion_id': suggestion.id,
                    'status': suggestion.status,
                    'confidence': suggestion.confidence,
                    'created_at': suggestion.created_at.isoformat() if suggestion.created_at else None
                },
                success_score=suggestion.confidence if suggestion.confidence else 0.8  # Deployed = successful
            )
            count += 1

            if count % 10 == 0:
                logger.info(f"  Processed {count} automations...")

        except Exception as e:
            logger.warning(f"Failed to seed suggestion {suggestion.id}: {e}")
            continue

    logger.info(f"✅ Seeded {count} automations")
    return count


async def main():
    """Main seeding function"""
    logger.info("🌱 Starting RAG knowledge base seeding...")

    # Initialize database
    await init_db()

    # Get async_session from models module (set by init_db)
    async_session = db_models.async_session

    async with async_session() as db:
        # Initialize RAG client
        openvino_url = os.getenv("OPENVINO_SERVICE_URL", "http://openvino-service:8019")
        rag_client = RAGClient(
            openvino_service_url=openvino_url,
            db_session=db
        )

        total_count = 0

        # Seed from queries
        query_count = await seed_from_queries(db, rag_client)
        total_count += query_count

        # Seed from patterns
        pattern_count = await seed_from_patterns(db, rag_client)
        total_count += pattern_count

        # Seed from suggestions
        suggestion_count = await seed_from_suggestions(db, rag_client)
        total_count += suggestion_count

        # Close RAG client
        await rag_client.close()

        logger.info(f"🎉 Seeding complete! Total entries: {total_count}")
        logger.info(f"  - Queries: {query_count}")
        logger.info(f"  - Patterns: {pattern_count}")
        logger.info(f"  - Automations: {suggestion_count}")


if __name__ == "__main__":
    asyncio.run(main())

