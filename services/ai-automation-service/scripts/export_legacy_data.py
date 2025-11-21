#!/usr/bin/env python3
"""
Export legacy v1.x data for migration to v2.

Exports ask_ai_queries and clarification_sessions to JSON format
for import into the new v2 conversation structure.

Usage:
    python scripts/export_legacy_data.py [--output output.json]
"""

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from src.database.models import AskAIQuery, ClarificationSessionDB

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def export_legacy_data(output_path: Path) -> bool:
    """Export legacy data to JSON"""

    db_path = Path(__file__).parent.parent / "data" / "ai_automation.db"

    if not db_path.exists():
        logger.error(f"Database not found: {db_path}")
        return False

    db_url = f"sqlite+aiosqlite:///{db_path}"
    engine = create_async_engine(db_url, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session() as session:
            # Export ask_ai_queries
            logger.info("Exporting ask_ai_queries...")
            result = await session.execute(select(AskAIQuery))
            queries = result.scalars().all()

            queries_data = []
            for query in queries:
                queries_data.append({
                    "query_id": query.query_id,
                    "original_query": query.original_query,
                    "user_id": query.user_id,
                    "parsed_intent": query.parsed_intent,
                    "extracted_entities": query.extracted_entities,
                    "suggestions": query.suggestions,
                    "confidence": query.confidence,
                    "processing_time_ms": query.processing_time_ms,
                    "created_at": query.created_at.isoformat() if query.created_at else None,
                })

            logger.info(f"✅ Exported {len(queries_data)} queries")

            # Export clarification_sessions
            logger.info("Exporting clarification_sessions...")
            result = await session.execute(select(ClarificationSessionDB))
            sessions = result.scalars().all()

            sessions_data = []
            for session in sessions:
                sessions_data.append({
                    "session_id": session.session_id,
                    "original_query_id": session.original_query_id,
                    "original_query": session.original_query,
                    "user_id": session.user_id,
                    "questions": session.questions,
                    "answers": session.answers,
                    "ambiguities": session.ambiguities,
                    "status": session.status,
                    "rounds_completed": session.rounds_completed,
                    "max_rounds": session.max_rounds,
                    "current_confidence": session.current_confidence,
                    "confidence_threshold": session.confidence_threshold,
                    "created_at": session.created_at.isoformat() if session.created_at else None,
                    "updated_at": session.updated_at.isoformat() if session.updated_at else None,
                    "completed_at": session.completed_at.isoformat() if session.completed_at else None,
                    "clarification_query_id": session.clarification_query_id,
                })

            logger.info(f"✅ Exported {len(sessions_data)} clarification sessions")

            # Combine export data
            export_data = {
                "export_version": "1.0",
                "export_date": datetime.utcnow().isoformat(),
                "source_database": str(db_path),
                "queries": queries_data,
                "clarification_sessions": sessions_data,
                "statistics": {
                    "total_queries": len(queries_data),
                    "total_sessions": len(sessions_data),
                    "queries_with_suggestions": sum(1 for q in queries_data if q.get("suggestions")),
                    "active_sessions": sum(1 for s in sessions_data if s.get("status") == "in_progress"),
                },
            }

            # Write to file
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            logger.info(f"✅ Export completed: {output_path}")
            logger.info(f"   - {len(queries_data)} queries")
            logger.info(f"   - {len(sessions_data)} clarification sessions")

            return True

    except Exception as e:
        logger.error(f"❌ Export failed: {e}", exc_info=True)
        return False
    finally:
        await engine.dispose()


async def main():
    parser = argparse.ArgumentParser(description="Export legacy v1.x data for migration")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parent.parent / "data" / "legacy_export.json",
        help="Output JSON file path",
    )
    args = parser.parse_args()

    success = await export_legacy_data(args.output)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())

