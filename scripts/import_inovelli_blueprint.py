#!/usr/bin/env python3
"""
Import Inovelli Matter Switch Tap Sequences blueprint into blueprint-index database.

This script:
1. Fetches the blueprint YAML from GitHub
2. Parses it using BlueprintParser
3. Saves it to the blueprint-index database
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime, timezone

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        # Python < 3.7 - use environment variable only
        pass

# Add services/blueprint-index to path
project_root = Path(__file__).parent.parent
blueprint_index_path = project_root / "services" / "blueprint-index" / "src"
sys.path.insert(0, str(blueprint_index_path))
sys.path.insert(0, str(project_root / "services" / "blueprint-index"))

# Set database path to match Docker volume location
data_dir = project_root / "data"
data_dir.mkdir(exist_ok=True)
# Update config to use the correct database path
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{data_dir / 'blueprint_index.db'}"

import httpx
from src.indexer.blueprint_parser import BlueprintParser
from src.database import get_db_context
from src.models import IndexedBlueprint
from sqlalchemy import select


async def import_inovelli_blueprint():
    """Import the Inovelli blueprint from GitHub."""
    
    # Blueprint details
    blueprint_url = "https://raw.githubusercontent.com/jay-kub/inovelli-matter-switch-tap-sequences/main/inovelli-matter-switch-tap-sequences.yaml"
    source_url = "https://github.com/jay-kub/inovelli-matter-switch-tap-sequences/blob/main/inovelli-matter-switch-tap-sequences.yaml"
    forum_url = "https://community.inovelli.com/t/ha-blueprint-matter-switch-tap-sequences/17642"
    
    print(f"Fetching blueprint from: {blueprint_url}")
    
    # Fetch blueprint YAML
    async with httpx.AsyncClient() as client:
        response = await client.get(blueprint_url)
        response.raise_for_status()
        yaml_content = response.text
    
    print(f"[OK] Fetched blueprint ({len(yaml_content)} bytes)")
    
    # Parse blueprint
    parser = BlueprintParser()
    blueprint = parser.parse_blueprint(
        yaml_content=yaml_content,
        source_url=source_url,
        source_type="github",
        source_id="jay-kub/inovelli-matter-switch-tap-sequences:inovelli-matter-switch-tap-sequences.yaml",
        stars=0,  # Will be updated from GitHub API if needed
        author="jay-kub",
        created_at=datetime(2024, 9, 22, tzinfo=timezone.utc),  # From forum post
        updated_at=datetime(2024, 11, 13, tzinfo=timezone.utc),  # Version 0.3.3 date
    )
    
    if not blueprint:
        print("[FAIL] Failed to parse blueprint")
        return False
    
    print(f"[OK] Parsed blueprint: {blueprint.name}")
    print(f"  - Domain: {blueprint.domain}")
    print(f"  - Required domains: {blueprint.required_domains}")
    print(f"  - Author: {blueprint.author}")
    
    # Initialize database tables
    from src.database import init_db
    print("Initializing database tables...")
    await init_db()
    print("[OK] Database initialized")
    
    # Get database connection
    async with get_db_context() as session:
        stmt = select(IndexedBlueprint).where(
            IndexedBlueprint.source_url == source_url
        )
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            print(f"[WARN] Blueprint already exists (ID: {existing.id})")
            print("  Updating existing blueprint...")
            
            # Update existing blueprint (skip datetime fields from to_dict)
            update_dict = blueprint.to_dict()
            for key, value in update_dict.items():
                if hasattr(existing, key) and key not in ('id', 'created_at', 'updated_at'):
                    # Skip datetime fields - to_dict converts them to ISO strings
                    setattr(existing, key, value)
            
            # Update datetime fields directly from blueprint object
            if blueprint.created_at:
                existing.created_at = blueprint.created_at
            if blueprint.updated_at:
                existing.updated_at = blueprint.updated_at
            
            existing.updated_at = datetime.now(timezone.utc)
            existing.indexed_at = datetime.now(timezone.utc)
            
            await session.commit()
            print(f"[OK] Updated blueprint in database")
        else:
            print("  Inserting new blueprint...")
            
            # Add community metrics from forum
            blueprint.downloads = 335  # Link clicks from forum
            blueprint.community_rating = 0.8  # Estimate based on engagement
            blueprint.vote_count = 15  # Likes from forum
            
            # Add tags
            blueprint.tags = ["inovelli", "matter", "switch", "tap-sequences", "light-binding", "fan-binding"]
            blueprint.use_case = "convenience"
            
            # Store forum URL in description or as metadata
            if blueprint.description:
                blueprint.description += f"\n\nForum: {forum_url}"
            
            session.add(blueprint)
            await session.commit()
            print(f"[OK] Imported blueprint into database (ID: {blueprint.id})")
    
    return True


if __name__ == "__main__":
    print("=== Inovelli Blueprint Import ===")
    print()
    
    try:
        result = asyncio.run(import_inovelli_blueprint())
        if result:
            print()
            print("[OK] Successfully imported blueprint!")
            print()
            print("You can now query it via:")
            print("  GET http://localhost:8038/api/blueprints/search?query=inovelli")
        else:
            print()
            print("[FAIL] Import failed")
            sys.exit(1)
    except Exception as e:
        print(f"[FAIL] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
