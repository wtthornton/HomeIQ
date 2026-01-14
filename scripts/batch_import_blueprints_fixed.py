#!/usr/bin/env python3
"""
Batch import home improvement blueprints into blueprint-index database.

This script:
1. Fetches device inventory from data-api
2. Searches for relevant blueprints from known sources
3. Downloads and imports blueprints into the blueprint-index database
"""

import asyncio
import sys
import os
import re
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Optional

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# Add services/blueprint-index to path
project_root = Path(__file__).parent.parent
blueprint_index_path = project_root / "services" / "blueprint-index" / "src"
sys.path.insert(0, str(blueprint_index_path))
sys.path.insert(0, str(project_root / "services" / "blueprint-index"))

# Set database path to match Docker volume location
data_dir = project_root / "data"
data_dir.mkdir(exist_ok=True)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{data_dir / 'blueprint_index.db'}"

import httpx
from src.indexer.blueprint_parser import BlueprintParser
from src.database import init_db, get_db_context
from src.models.blueprint import IndexedBlueprint, BlueprintInput
from sqlalchemy import select


# Known blueprint sources for home improvement
# URLs from hablueprints.directory and official Home Assistant core
BLUEPRINT_SOURCES = [
    # Official Home Assistant blueprints (from hablueprints.directory)
    {
        "name": "Motion-activated Light",
        "url": "https://raw.githubusercontent.com/home-assistant/core/dev/homeassistant/components/automation/blueprints/motion_light.yaml",
        "category": "lighting",
        "description": "Turn on a light when motion is detected"
    },
]


async def fetch_blueprint_yaml(url: str) -> Optional[str]:
    """Fetch blueprint YAML from URL."""
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text
    except Exception as e:
        print(f"[WARN] Failed to fetch {url}: {e}")
        return None


async def import_blueprint(
    blueprint_url: str,
    source_type: str = "github",
    source_id: Optional[str] = None,
    source_forum_url: Optional[str] = None
) -> bool:
    """Import a single blueprint into the database."""
    print(f"\n=== Importing: {blueprint_url} ===")
    
    yaml_content = await fetch_blueprint_yaml(blueprint_url)
    if not yaml_content:
        print("[FAIL] Could not fetch blueprint YAML")
        return False
    
    print(f"[OK] Fetched blueprint ({len(yaml_content)} bytes)")
    
    parser = BlueprintParser()
    parsed_blueprint = parser.parse_yaml(yaml_content)
    
    if not parsed_blueprint or not parser.is_blueprint(parsed_blueprint):
        print("[FAIL] Not a valid blueprint YAML")
        return False
    
    # Use BlueprintParser.parse_blueprint to get IndexedBlueprint object
    # Generate source_id if not provided
    if not source_id:
        # Extract from GitHub URL: owner/repo/path/file.yaml
        match = re.search(r'github\.com/([^/]+)/([^/]+)/[^/]+/([^/]+\.yaml)', blueprint_url)
        if match:
            source_id = f"{match.group(1)}/{match.group(2)}:{match.group(3)}"
        else:
            source_id = blueprint_url.split('/')[-1]
    
    # Parse dates from description if available
    created_at = datetime.now(timezone.utc)
    updated_at = datetime.now(timezone.utc)
    
    # Use the parser's parse_blueprint method which returns IndexedBlueprint
    blueprint = parser.parse_blueprint(
        yaml_content=yaml_content,
        source_url=blueprint_url,
        source_type=source_type,
        source_id=source_id,
        stars=0,
        author=None,
        created_at=created_at,
        updated_at=updated_at,
    )
    
    if not blueprint:
        print("[FAIL] Failed to parse blueprint")
        return False
    
    # Ensure yaml_content is set (parse_blueprint doesn't include it)
    blueprint.yaml_content = yaml_content
    
    print(f"[OK] Parsed blueprint: {blueprint.name}")
    print(f"  - Domain: {blueprint.domain}")
    print(f"  - Author: {blueprint.author or 'Unknown'}")
    
    async with get_db_context() as session:
        # Check if blueprint already exists
        existing_query = select(IndexedBlueprint).where(IndexedBlueprint.source_url == blueprint_url)
        existing_result = await session.execute(existing_query)
        existing_blueprint = existing_result.scalar_one_or_none()
        
        if existing_blueprint:
            print(f"[WARN] Blueprint already exists (ID: {existing_blueprint.id})")
            print("  Updating existing blueprint...")
            
            # Update existing blueprint with new data
            for key, value in blueprint.__dict__.items():
                if key not in ['id', 'created_at', '_sa_instance_state']:
                    if key == 'updated_at' or key == 'indexed_at':
                        setattr(existing_blueprint, key, datetime.now(timezone.utc))
                    else:
                        setattr(existing_blueprint, key, value)
            
            # Ensure yaml_content is updated
            existing_blueprint.yaml_content = yaml_content
            
            # Update inputs_rel - delete old and add new
            await session.execute(
                BlueprintInput.__table__.delete().where(
                    BlueprintInput.blueprint_id == existing_blueprint.id
                )
            )
            # Re-parse inputs for the existing blueprint
            parsed_blueprint = parser.parse_yaml(yaml_content)
            if parsed_blueprint:
                inputs_raw = parsed_blueprint.get('blueprint', {}).get('input', {})
                for input_name, input_def in inputs_raw.items():
                    if isinstance(input_def, dict):
                        # Determine input type from selector
                        selector = input_def.get('selector', {})
                        input_type = 'text'
                        if 'entity' in selector:
                            input_type = selector['entity'].get('domain', 'entity')
                        elif 'device' in selector:
                            input_type = 'device'
                        elif 'target' in selector:
                            input_type = 'target'
                        elif 'number' in selector:
                            input_type = 'number'
                        elif 'boolean' in selector:
                            input_type = 'boolean'
                        
                        input_obj = BlueprintInput(
                            blueprint_id=existing_blueprint.id,
                            input_name=input_name,
                            input_type=input_type,
                            description=input_def.get('description'),
                        )
                        session.add(input_obj)
            
            await session.commit()
            print("[OK] Updated blueprint in database")
            return True
        else:
            print("  Inserting new blueprint...")
            
            # Add the blueprint to session
            session.add(blueprint)
            await session.commit()
            await session.refresh(blueprint)
            
            # Add associated BlueprintInput entries
            parsed_blueprint = parser.parse_yaml(yaml_content)
            if parsed_blueprint:
                inputs_raw = parsed_blueprint.get('blueprint', {}).get('input', {})
                for input_name, input_def in inputs_raw.items():
                    if isinstance(input_def, dict):
                        # Determine input type from selector
                        selector = input_def.get('selector', {})
                        input_type = 'text'
                        if 'entity' in selector:
                            input_type = selector['entity'].get('domain', 'entity')
                        elif 'device' in selector:
                            input_type = 'device'
                        elif 'target' in selector:
                            input_type = 'target'
                        elif 'number' in selector:
                            input_type = 'number'
                        elif 'boolean' in selector:
                            input_type = 'boolean'
                        
                        input_obj = BlueprintInput(
                            blueprint_id=blueprint.id,
                            input_name=input_name,
                            input_type=input_type,
                            description=input_def.get('description'),
                        )
                        session.add(input_obj)
            await session.commit()
            
            print(f"[OK] Imported blueprint into database (ID: {blueprint.id})")
            return True


async def get_device_inventory() -> Dict:
    """Fetch device inventory from data-api."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get("http://localhost:8006/api/devices?limit=1000")
            response.raise_for_status()
            return response.json()
    except Exception as e:
        print(f"[WARN] Could not fetch device inventory: {e}")
        return {"devices": []}


async def main():
    """Main function to batch import blueprints."""
    print("=== Batch Blueprint Import ===")
    print(f"Found {len(BLUEPRINT_SOURCES)} blueprint sources to import\n")
    
    # Initialize database
    print("Initializing database...")
    await init_db()
    print("[OK] Database initialized\n")
    
    # Get device inventory for reference
    print("Fetching device inventory...")
    device_data = await get_device_inventory()
    device_count = len(device_data.get("devices", []))
    print(f"[OK] Found {device_count} devices in system\n")
    
    # Import blueprints
    success_count = 0
    fail_count = 0
    
    for blueprint_source in BLUEPRINT_SOURCES:
        try:
            success = await import_blueprint(
                blueprint_url=blueprint_source["url"],
                source_type="github",
                source_id=None  # Will be auto-generated
            )
            if success:
                success_count += 1
            else:
                fail_count += 1
        except Exception as e:
            print(f"[FAIL] Error importing {blueprint_source['name']}: {e}")
            fail_count += 1
        
        # Small delay to avoid rate limiting
        await asyncio.sleep(1)
    
    print("\n=== Import Summary ===")
    print(f"Successfully imported: {success_count}")
    print(f"Failed: {fail_count}")
    print(f"Total: {len(BLUEPRINT_SOURCES)}")
    print("\n[OK] Batch import complete!")
    print(f"\nYou can now query blueprints via:")
    print(f"  GET http://localhost:8038/api/blueprints/search?query=energy")
    print(f"  GET http://localhost:8038/api/blueprints/search?query=lighting")


if __name__ == "__main__":
    asyncio.run(main())
