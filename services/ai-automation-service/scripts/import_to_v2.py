#!/usr/bin/env python3
"""
Import legacy v1.x data into v2 conversation structure.

Reads exported JSON from export_legacy_data.py and imports it into
the new v2 conversation tables with proper conversation_id mapping.

Usage:
    python scripts/import_to_v2.py [--input legacy_export.json] [--dry-run]
"""

import argparse
import asyncio
import json
import logging
import sys
import uuid
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def import_to_v2(input_path: Path, dry_run: bool = False) -> bool:
    """Import legacy data into v2 structure"""

    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        return False

    # Load export data
    logger.info(f"Loading export data from: {input_path}")
    with open(input_path, encoding="utf-8") as f:
        export_data = json.load(f)

    queries = export_data.get("queries", [])
    sessions = export_data.get("clarification_sessions", [])

    logger.info(f"Found {len(queries)} queries and {len(sessions)} sessions to import")

    if dry_run:
        logger.info("DRY RUN MODE - No changes will be made")
        logger.info(f"Would import {len(queries)} queries as conversations")
        logger.info(f"Would import {len(sessions)} clarification sessions")
        return True

    # Connect to database
    db_path = Path(__file__).parent.parent / "data" / "ai_automation.db"
    db_url = f"sqlite+aiosqlite:///{db_path}"
    engine = create_async_engine(db_url, echo=False)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Mapping: old query_id -> new conversation_id
    query_id_mapping: dict[str, str] = {}
    session_id_mapping: dict[str, str] = {}

    try:
        async with async_session() as session:
            # Import queries as conversations
            logger.info("Importing queries as conversations...")

            for query_data in queries:
                old_query_id = query_data["query_id"]
                conversation_id = f"conv-{uuid.uuid4().hex[:12]}"
                query_id_mapping[old_query_id] = conversation_id

                # Determine conversation type from parsed_intent
                intent = query_data.get("parsed_intent", "general")
                conversation_type = "automation" if intent in ["automate", "automation"] else "information"

                # Determine status
                status = "completed" if query_data.get("suggestions") else "active"

                # Insert conversation
                await session.execute(text("""
                    INSERT INTO conversations (
                        conversation_id, user_id, conversation_type, status,
                        initial_query, context, metadata, created_at
                    ) VALUES (
                        :conversation_id, :user_id, :conversation_type, :status,
                        :initial_query, :context, :metadata, :created_at
                    )
                """), {
                    "conversation_id": conversation_id,
                    "user_id": query_data.get("user_id", "anonymous"),
                    "conversation_type": conversation_type,
                    "status": status,
                    "initial_query": query_data.get("original_query", ""),
                    "context": json.dumps({
                        "legacy_query_id": old_query_id,
                        "parsed_intent": query_data.get("parsed_intent"),
                        "extracted_entities": query_data.get("extracted_entities"),
                    }),
                    "metadata": json.dumps({
                        "processing_time_ms": query_data.get("processing_time_ms"),
                        "confidence": query_data.get("confidence"),
                    }),
                    "created_at": query_data.get("created_at") or datetime.utcnow().isoformat(),
                })

                # Create initial turn
                turn_number = 1
                await session.execute(text("""
                    INSERT INTO conversation_turns (
                        conversation_id, turn_number, role, content,
                        response_type, intent, extracted_entities,
                        confidence, processing_time_ms, created_at
                    ) VALUES (
                        :conversation_id, :turn_number, :role, :content,
                        :response_type, :intent, :extracted_entities,
                        :confidence, :processing_time_ms, :created_at
                    )
                """), {
                    "conversation_id": conversation_id,
                    "turn_number": turn_number,
                    "role": "user",
                    "content": query_data.get("original_query", ""),
                    "response_type": "automation_generated" if query_data.get("suggestions") else "information_provided",
                    "intent": query_data.get("parsed_intent"),
                    "extracted_entities": json.dumps(query_data.get("extracted_entities") or []),
                    "confidence": query_data.get("confidence"),
                    "processing_time_ms": query_data.get("processing_time_ms"),
                    "created_at": query_data.get("created_at") or datetime.utcnow().isoformat(),
                })

                # Import suggestions if any
                suggestions = query_data.get("suggestions") or []
                for i, suggestion in enumerate(suggestions):
                    suggestion_id = f"sug-{uuid.uuid4().hex[:12]}"
                    await session.execute(text("""
                        INSERT INTO automation_suggestions (
                            suggestion_id, conversation_id, turn_id,
                            title, description, automation_yaml,
                            confidence, response_type, validated_entities,
                            status, created_at
                        ) VALUES (
                            :suggestion_id, :conversation_id, :turn_id,
                            :title, :description, :automation_yaml,
                            :confidence, :response_type, :validated_entities,
                            :status, :created_at
                        )
                    """), {
                        "suggestion_id": suggestion_id,
                        "conversation_id": conversation_id,
                        "turn_id": turn_number,  # Link to the turn
                        "title": suggestion.get("title", f"Suggestion {i+1}"),
                        "description": suggestion.get("description", ""),
                        "automation_yaml": suggestion.get("automation_yaml"),
                        "confidence": suggestion.get("confidence", query_data.get("confidence", 0.5)),
                        "response_type": "automation_generated",
                        "validated_entities": json.dumps(suggestion.get("validated_entities", {})),
                        "status": "draft",
                        "created_at": query_data.get("created_at") or datetime.utcnow().isoformat(),
                    })

            logger.info(f"✅ Imported {len(queries)} conversations")

            # Import clarification sessions
            logger.info("Importing clarification sessions...")

            for session_data in sessions:
                old_session_id = session_data["session_id"]
                old_query_id = session_data["original_query_id"]

                # Find corresponding conversation_id
                conversation_id = query_id_mapping.get(old_query_id)
                if not conversation_id:
                    logger.warning(f"⚠️ No conversation found for query_id {old_query_id}, skipping session {old_session_id}")
                    continue

                # Update conversation with clarification context
                await session.execute(text("""
                    UPDATE conversations
                    SET context = json_set(
                        COALESCE(context, '{}'),
                        '$.clarification_session_id', :session_id,
                        '$.questions', :questions,
                        '$.answers', :answers
                    )
                    WHERE conversation_id = :conversation_id
                """), {
                    "session_id": old_session_id,
                    "questions": json.dumps(session_data.get("questions", [])),
                    "answers": json.dumps(session_data.get("answers", [])),
                    "conversation_id": conversation_id,
                })

            logger.info(f"✅ Imported {len(sessions)} clarification sessions")

            await session.commit()

            logger.info("✅ Import completed successfully")
            logger.info(f"   - Created {len(query_id_mapping)} conversations")
            logger.info(f"   - Mapped {len(session_id_mapping)} clarification sessions")

            # Save mapping file for reference
            mapping_file = input_path.parent / f"{input_path.stem}_mapping.json"
            with open(mapping_file, "w") as f:
                json.dump({
                    "query_id_mapping": query_id_mapping,
                    "session_id_mapping": session_id_mapping,
                    "import_date": datetime.utcnow().isoformat(),
                }, f, indent=2)

            logger.info(f"✅ Saved ID mapping to: {mapping_file}")

            return True

    except Exception as e:
        logger.error(f"❌ Import failed: {e}", exc_info=True)
        return False
    finally:
        await engine.dispose()


async def main():
    parser = argparse.ArgumentParser(description="Import legacy data into v2 structure")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path(__file__).parent.parent / "data" / "legacy_export.json",
        help="Input JSON file from export_legacy_data.py",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying")
    args = parser.parse_args()

    success = await import_to_v2(args.input, dry_run=args.dry_run)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())

