#!/usr/bin/env python3
"""
Reprocess Patterns Script - Story AI1.23 Phase 2
=================================================

Regenerates automation suggestions using OpenAI description generation.
This script:
1. Deletes all existing suggestions
2. Fetches all patterns from database
3. Generates OpenAI-powered descriptions (NO placeholders)
4. Fetches device capabilities
5. Stores in 'draft' status

Usage:
    python scripts/reprocess_patterns.py

Requirements:
    - Database must be initialized with new schema
    - OpenAI API key must be set in environment
    - ai-automation-service must be running
    - data-api must be running (for capabilities)
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent / "src"))

import logging
from datetime import datetime

from clients.data_api_client import DataAPIClient
from database.models import Pattern, Suggestion, get_db_session, init_db
from llm.description_generator import DescriptionGenerator

# Phase 2: Import OpenAI and description generator
from openai import AsyncOpenAI
from sqlalchemy import delete, select

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def delete_all_suggestions():
    """Delete all existing suggestions (Alpha clean slate)"""
    async with get_db_session() as db:
        result = await db.execute(select(Suggestion))
        suggestions = result.scalars().all()
        count = len(suggestions)

        logger.info(f"🗑️  Deleting {count} existing suggestions...")

        await db.execute(delete(Suggestion))
        await db.commit()

        logger.info(f"✅ Deleted {count} suggestions")
        return count


async def fetch_all_patterns():
    """Fetch all patterns from database"""
    async with get_db_session() as db:
        result = await db.execute(
            select(Pattern).order_by(Pattern.confidence.desc()),
        )
        patterns = result.scalars().all()
        logger.info(f"📊 Found {len(patterns)} patterns to process")
        return patterns


async def generate_description_with_openai(
    pattern: Pattern,
    description_generator: DescriptionGenerator,
    data_api_client: DataAPIClient,
) -> tuple[str, dict]:
    """
    Generate OpenAI-powered description for the pattern.

    Phase 2: Real OpenAI generation with device capabilities!

    Returns:
        Tuple of (description, capabilities)
    """
    # Build pattern dict for OpenAI
    pattern_dict = {
        "pattern_type": pattern.pattern_type,
        "device_id": pattern.device_id,
        "confidence": pattern.confidence,
        "occurrences": pattern.occurrences,
        "metadata": pattern.pattern_metadata or {},
    }

    # Extract specific fields for different pattern types
    metadata = pattern.pattern_metadata or {}

    if pattern.pattern_type == "time_of_day":
        pattern_dict["hour"] = int(metadata.get("avg_time_decimal", 0))
        pattern_dict["minute"] = int((metadata.get("avg_time_decimal", 0) % 1) * 60)

    elif pattern.pattern_type == "co_occurrence":
        # Device ID format: "device1+device2"
        if "+" in pattern.device_id:
            device1, device2 = pattern.device_id.split("+", 1)
            pattern_dict["device1"] = device1
            pattern_dict["device2"] = device2

    # Fetch device capabilities from data-api
    try:
        capabilities = await data_api_client.fetch_device_capabilities(pattern.device_id)

        device_context = {
            "name": capabilities.get("friendly_name", pattern.device_id),
            "area": capabilities.get("area", ""),
            "domain": capabilities.get("domain", "unknown"),
            "capabilities": capabilities.get("supported_features", {}),
        }
    except Exception as e:
        logger.warning(f"Failed to fetch capabilities for {pattern.device_id}: {e}")
        device_context = None
        capabilities = {}

    # Generate description via OpenAI
    try:
        description = await description_generator.generate_description(
            pattern=pattern_dict,
            device_context=device_context,
        )

        return description, capabilities

    except Exception as e:
        logger.exception(f"OpenAI generation failed for {pattern.pattern_type}: {e}")
        # Fallback to basic description
        fallback = generate_fallback_description(pattern)
        return fallback, capabilities


def generate_fallback_description(pattern: Pattern) -> str:
    """
    Generate fallback description if OpenAI fails.
    Better than placeholders, still readable.
    """
    pattern_type = pattern.pattern_type
    device_id = pattern.device_id
    friendly_name = device_id.split(".")[-1].replace("_", " ").title() if "." in device_id else device_id

    if pattern_type == "time_of_day":
        metadata = pattern.pattern_metadata or {}
        hour = int(metadata.get("avg_time_decimal", 0))
        minute = int((metadata.get("avg_time_decimal", 0) % 1) * 60)
        return f"Automatically control {friendly_name} at {hour:02d}:{minute:02d} based on consistent usage pattern"

    if pattern_type == "co_occurrence":
        metadata = pattern.pattern_metadata or {}
        if "+" in device_id:
            d1, d2 = device_id.split("+", 1)
            name1 = d1.split(".")[-1].replace("_", " ").title()
            name2 = d2.split(".")[-1].replace("_", " ").title()
            return f"When {name1} activates, automatically turn on {name2}"
        return f"Automate {friendly_name} based on co-occurrence pattern"

    if pattern_type == "anomaly":
        return f"Get notified when {friendly_name} shows unusual activity"

    return f"Automate {friendly_name} based on detected usage pattern"


def generate_title_placeholder(pattern: Pattern) -> str:
    """Generate a placeholder title"""
    pattern_type = pattern.pattern_type.replace("_", " ").title()
    device_name = pattern.device_id.split(".")[-1].replace("_", " ").title()
    return f"{device_name} {pattern_type}"


def infer_category(pattern: Pattern) -> str:
    """Infer category from device ID"""
    device_id = pattern.device_id.lower()

    if any(k in device_id for k in ["light", "switch"]):
        return "convenience"
    if any(k in device_id for k in ["climate", "thermostat", "temperature"]):
        return "comfort"
    if any(k in device_id for k in ["alarm", "lock", "door", "camera", "motion"]):
        return "security"
    if any(k in device_id for k in ["energy", "power"]):
        return "energy"
    return "convenience"


def infer_priority(confidence: float) -> str:
    """Infer priority from confidence score"""
    if confidence >= 0.85:
        return "high"
    if confidence >= 0.65:
        return "medium"
    return "low"


async def create_suggestion_from_pattern(
    pattern: Pattern,
    description_generator: DescriptionGenerator,
    data_api_client: DataAPIClient,
) -> Suggestion:
    """
    Create a new suggestion from a pattern.

    Phase 2: Uses OpenAI to generate real descriptions with device capabilities!
    """
    # Generate OpenAI description and fetch capabilities
    description, capabilities = await generate_description_with_openai(
        pattern,
        description_generator,
        data_api_client,
    )

    return Suggestion(
        pattern_id=pattern.id,

        # NEW: Description-first fields (Phase 2: Real OpenAI!)
        description_only=description,
        conversation_history=[],
        device_capabilities=capabilities,  # Cached from data-api
        refinement_count=0,

        # YAML (NULL until approved)
        automation_yaml=None,
        yaml_generated_at=None,

        # Status
        status="draft",

        # Legacy fields
        title=generate_title_placeholder(pattern),
        category=infer_category(pattern),
        priority=infer_priority(pattern.confidence),
        confidence=pattern.confidence,

        # Timestamps
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        approved_at=None,
        deployed_at=None,
        ha_automation_id=None,
    )



async def reprocess_all_patterns():
    """Main reprocessing logic with OpenAI integration (Phase 2)"""
    logger.info("="*80)
    logger.info("🔄 Starting pattern reprocessing with OpenAI (Phase 2)")
    logger.info("="*80)

    # Check for OpenAI API key
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        logger.error("❌ OPENAI_API_KEY environment variable not set!")
        logger.error("   Set it with: export OPENAI_API_KEY='sk-...'")
        return

    logger.info(f"✅ OpenAI API key found: {openai_api_key[:10]}...")

    # Initialize database
    await init_db()

    # Initialize OpenAI client and description generator
    logger.info("🤖 Initializing OpenAI description generator...")
    openai_client = AsyncOpenAI(api_key=openai_api_key)
    description_generator = DescriptionGenerator(openai_client, model="gpt-4o-mini")

    # Initialize data-api client for capabilities
    logger.info("📡 Initializing data-api client...")
    data_api_client = DataAPIClient(base_url="http://localhost:8006")

    # Step 1: Delete existing suggestions
    deleted_count = await delete_all_suggestions()

    # Step 2: Fetch all patterns
    patterns = await fetch_all_patterns()

    if not patterns:
        logger.warning("⚠️  No patterns found! Run pattern detection first.")
        logger.info("   Command: python scripts/detect_patterns.py")
        return

    # Step 3: Generate new suggestions with OpenAI
    logger.info(f"🤖 Generating {len(patterns)} new suggestions with OpenAI...")
    logger.info("   Model: gpt-4o-mini (cost-effective)")
    logger.info("   Temperature: 0.7 (natural language)")
    logger.info("")

    async with get_db_session() as db:
        created_count = 0
        failed_count = 0
        openai_calls = 0
        fallback_count = 0

        for i, pattern in enumerate(patterns, 1):
            try:
                # This makes an OpenAI API call!
                suggestion = await create_suggestion_from_pattern(
                    pattern,
                    description_generator,
                    data_api_client,
                )

                db.add(suggestion)
                created_count += 1
                openai_calls += 1

                # Check if fallback was used
                if "usage pattern" in suggestion.description_only.lower():
                    fallback_count += 1

                logger.info(
                    f"  ✅ [{i}/{len(patterns)}] {suggestion.title} "
                    f"(confidence: {suggestion.confidence:.0%})",
                )
                logger.debug(f"     Description: {suggestion.description_only[:60]}...")

            except Exception as e:
                failed_count += 1
                logger.exception(f"  ❌ [{i}/{len(patterns)}] Failed: {pattern.pattern_type} - {e}")

        # Commit all suggestions
        await db.commit()

    # Get token usage stats
    usage_stats = description_generator.get_usage_stats()

    # Summary
    logger.info("")
    logger.info("="*80)
    logger.info("✅ Reprocessing complete!")
    logger.info("="*80)
    logger.info(f"   Deleted:         {deleted_count} old suggestions")
    logger.info(f"   Created:         {created_count} new suggestions")
    logger.info(f"   Failed:          {failed_count}")
    logger.info("   Status:          All in 'draft' state")
    logger.info("")
    logger.info("OpenAI Usage:")
    logger.info(f"   API calls:       {openai_calls}")
    logger.info(f"   Fallbacks used:  {fallback_count}")
    logger.info(f"   Total tokens:    {usage_stats['total_tokens']}")
    logger.info(f"   Input tokens:    {usage_stats['input_tokens']}")
    logger.info(f"   Output tokens:   {usage_stats['output_tokens']}")
    logger.info(f"   Estimated cost:  ${usage_stats['estimated_cost_usd']:.6f}")
    logger.info("="*80)

    # Next steps
    logger.info("")
    logger.info("Next steps:")
    logger.info("  1. Restart ai-automation-service (if needed)")
    logger.info("  2. Visit http://localhost:3001/suggestions")
    logger.info("  3. You should see OpenAI-generated descriptions!")
    logger.info("")
    logger.info("✨ Phase 2 complete: Real OpenAI descriptions generated!")


if __name__ == "__main__":
    try:
        asyncio.run(reprocess_all_patterns())
    except KeyboardInterrupt:
        logger.info("\n⚠️  Interrupted by user")
    except Exception as e:
        logger.exception(f"❌ Fatal error: {e}")
        raise

