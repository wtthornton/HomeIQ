#!/usr/bin/env python3
"""
Populate Context7 KB cache using MCP tools and manual storage.

This script fetches documentation via MCP tools and stores it
directly in the KB cache using the KBCache class.
"""

import asyncio
import sys
from pathlib import Path

# Add TappsCodingAgents to path
project_root = Path(__file__).parent
tapps_path = project_root / "TappsCodingAgents"
if tapps_path.exists():
    sys.path.insert(0, str(tapps_path))

try:
    from tapps_agents.context7.kb_cache import KBCache
    from tapps_agents.context7.cache_structure import CacheStructure
    from tapps_agents.context7.metadata import MetadataManager
    from tapps_agents.core.config import load_config
except ImportError as e:
    print(f"Error importing tapps_agents: {e}")
    sys.exit(1)


# Library mappings: (library_name, topic, context7_id)
LIBRARIES_TO_POPULATE = [
    ("fastapi", "routing", "/fastapi/fastapi"),
    ("fastapi", "dependency-injection", "/fastapi/fastapi"),
    ("fastapi", "async", "/fastapi/fastapi"),
    ("pydantic", "validation", "/pydantic/pydantic"),
    ("pydantic", "settings", "/pydantic/pydantic"),
    ("sqlalchemy", "async", "/sqlalchemy/sqlalchemy"),
    ("pytest", "async", "/pytest-dev/pytest"),
    ("pytest", "fixtures", "/pytest-dev/pytest"),
    ("aiosqlite", "async", "/omnilib/aiosqlite"),
    ("homeassistant", "websocket", "/home-assistant/core"),
    ("influxdb", "write", "/influxdata/influxdb-client-python"),
]


async def fetch_and_store(library: str, topic: str, context7_id: str, kb_cache: KBCache):
    """Fetch documentation via MCP and store in cache."""
    print(f"[*] Fetching: {library}/{topic}...", end=" ", flush=True)
    
    try:
        # Import MCP tools (these are available in Cursor)
        # We'll use the MCP tools that were used earlier
        # For now, we'll create a placeholder that shows the structure
        
        # In a real scenario, you would call:
        # result = await mcp_Context7_get-library-docs(
        #     context7CompatibleLibraryID=context7_id,
        #     topic=topic,
        #     mode="code"
        # )
        
        # For demonstration, we'll note that the docs were already fetched
        # and we need to store them. Since we can't re-fetch here without
        # MCP Gateway, we'll create a note about manual storage needed.
        
        print(f"[!] Requires MCP Gateway access")
        return False
        
    except Exception as e:
        print(f"[X] Error: {e}")
        return False


async def populate_cache():
    """Populate Context7 KB cache."""
    print("=" * 70)
    print("  Context7 KB Cache Population (MCP Method)")
    print("=" * 70)
    print()
    
    # Load config
    config = load_config()
    if not config.context7 or not config.context7.enabled:
        print("[X] Context7 is not enabled")
        return False
    
    # Initialize cache
    cache_root = project_root / config.context7.knowledge_base.location
    cache_structure = CacheStructure(cache_root)
    cache_structure.initialize()
    
    metadata_manager = MetadataManager(cache_structure)
    kb_cache = KBCache(cache_structure.cache_root, metadata_manager)
    
    print(f"[i] Cache location: {cache_structure.cache_root}")
    print()
    print("[!] Note: This script requires MCP Gateway access.")
    print("[!] Since MCP tools are called via Cursor, we need to use")
    print("[!] the Context7 commands instead.")
    print()
    print("=" * 70)
    print("  Recommended: Use Context7 Commands")
    print("=" * 70)
    print()
    print("Run these commands in Cursor with @bmad-master:")
    print()
    
    for library, topic, _ in LIBRARIES_TO_POPULATE:
        print(f"  *context7-docs {library} {topic}")
    
    print()
    print("These commands will:")
    print("  1. Check KB cache first")
    print("  2. Fetch from Context7 API if cache miss")
    print("  3. Automatically store in KB cache")
    print("  4. Return documentation")
    print()
    
    return False


if __name__ == "__main__":
    try:
        result = asyncio.run(populate_cache())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\n[!] Interrupted")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n[X] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

