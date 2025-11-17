"""
Query RAG Knowledge Base Statistics

Shows:
- Total entries
- Entries by knowledge_type
- Most recent update
- Oldest entry
- Average success score
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select, func, desc
from datetime import datetime
import logging

from src.database.models import SemanticKnowledge
from src.database.database import init_database

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def get_rag_statistics(db: AsyncSession):
    """Get comprehensive statistics about the RAG knowledge base"""
    
    # Total count
    total_result = await db.execute(select(func.count(SemanticKnowledge.id)))
    total_count = total_result.scalar()
    
    if total_count == 0:
        print("\n⚠️  RAG Knowledge Base is EMPTY")
        print("   Run: python scripts/seed_rag_knowledge_base.py")
        return
    
    # Count by knowledge_type
    type_result = await db.execute(
        select(
            SemanticKnowledge.knowledge_type,
            func.count(SemanticKnowledge.id).label('count')
        ).group_by(SemanticKnowledge.knowledge_type)
    )
    type_counts = type_result.all()
    
    # Most recent update
    recent_result = await db.execute(
        select(SemanticKnowledge)
        .order_by(desc(SemanticKnowledge.updated_at))
        .limit(1)
    )
    most_recent = recent_result.scalar_one_or_none()
    
    # Oldest entry
    oldest_result = await db.execute(
        select(SemanticKnowledge)
        .order_by(SemanticKnowledge.created_at)
        .limit(1)
    )
    oldest = oldest_result.scalar_one_or_none()
    
    # Average success score
    avg_score_result = await db.execute(
        select(func.avg(SemanticKnowledge.success_score))
    )
    avg_score = avg_score_result.scalar()
    
    # Print statistics
    print("\n" + "="*60)
    print("RAG KNOWLEDGE BASE STATISTICS")
    print("="*60)
    
    print(f"\n📊 Total Entries: {total_count}")
    
    print(f"\n📚 Entries by Type:")
    for type_name, count in type_counts:
        percentage = (count / total_count) * 100
        print(f"   - {type_name:20s}: {count:4d} ({percentage:5.1f}%)")
    
    print(f"\n📈 Success Score:")
    print(f"   - Average: {avg_score:.3f}")
    
    if most_recent:
        print(f"\n🕐 Most Recent Update:")
        print(f"   - Date: {most_recent.updated_at}")
        print(f"   - Type: {most_recent.knowledge_type}")
        print(f"   - Text: {most_recent.text[:80]}...")
        print(f"   - Success Score: {most_recent.success_score:.3f}")
    
    if oldest:
        print(f"\n📅 Oldest Entry:")
        print(f"   - Date: {oldest.created_at}")
        print(f"   - Type: {oldest.knowledge_type}")
        print(f"   - Text: {oldest.text[:80]}...")
        print(f"   - Success Score: {oldest.success_score:.3f}")
    
    # Age of knowledge base
    if oldest and most_recent:
        age_days = (most_recent.updated_at - oldest.created_at).days
        print(f"\n⏱️  Knowledge Base Age:")
        print(f"   - {age_days} days between oldest and most recent")
    
    print("\n" + "="*60)


async def main():
    """Main function"""
    logger.info("Querying RAG knowledge base statistics...")
    
    # Initialize database
    engine, async_session = await init_database()
    
    async with async_session() as db:
        await get_rag_statistics(db)


if __name__ == "__main__":
    asyncio.run(main())

