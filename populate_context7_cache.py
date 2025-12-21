#!/usr/bin/env python3
"""
Populate Context7 KB cache with common library documentation.

This script uses the tapps-agents Context7 integration to properly
fetch and store documentation in the KB cache.
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
    from tapps_agents.context7.agent_integration import Context7AgentHelper
    from tapps_agents.core.config import load_config
except ImportError as e:
    print(f"Error importing tapps_agents: {e}")
    print(f"Make sure you're running from the project root")
    sys.exit(1)


# Libraries and topics to populate
LIBRARIES_TO_POPULATE = [
    # Backend
    ("fastapi", "routing"),
    ("fastapi", "dependency-injection"),
    ("fastapi", "async"),
    ("pydantic", "validation"),
    ("pydantic", "settings"),
    ("sqlalchemy", "async"),
    # Testing
    ("pytest", "async"),
    ("pytest", "fixtures"),
    # Database
    ("aiosqlite", "async"),
    # Project-specific
    ("homeassistant", "websocket"),
    ("influxdb", "write"),
]


async def populate_cache():
    """Populate Context7 KB cache with documentation."""
    print("=" * 70)
    print("  Context7 KB Cache Population")
    print("=" * 70)
    print()
    
    # Load config
    config = load_config()
    if not config.context7 or not config.context7.enabled:
        print("[X] Context7 is not enabled in config")
        return False
    
    # Initialize Context7 helper
    # Note: MCP Gateway is None here - will use HTTP fallback if needed
    helper = Context7AgentHelper(
        config=config,
        mcp_gateway=None,  # Will use HTTP fallback
        project_root=project_root
    )
    
    if not helper.enabled:
        print("[X] Context7 helper is not enabled")
        return False
    
    print(f"[i] Cache location: {helper.cache_structure.cache_root}")
    print()
    
    # Fetch and store documentation
    success_count = 0
    error_count = 0
    
    for library, topic in LIBRARIES_TO_POPULATE:
        print(f"[*] Fetching: {library}/{topic}...", end=" ", flush=True)
        
        try:
            result = await helper.get_documentation(
                library=library,
                topic=topic,
                use_fuzzy_match=True
            )
            
            if result:
                source = result.get("source", "unknown")
                print(f"[OK] {source}")
                success_count += 1
            else:
                print(f"[!] No result")
                error_count += 1
                
        except Exception as e:
            print(f"[X] Error: {e}")
            error_count += 1
    
    print()
    print("=" * 70)
    print("  Population Summary")
    print("=" * 70)
    print(f"[OK] Successfully cached: {success_count}")
    print(f"[X] Errors: {error_count}")
    print(f"[i] Total: {len(LIBRARIES_TO_POPULATE)}")
    print()
    
    # Check final cache status
    try:
        from tapps_agents.context7.commands import Context7Commands
        commands = Context7Commands(project_root=project_root)
        if commands.enabled:
            status = await commands.cmd_status()
            if status.get("success"):
                metrics = status.get("metrics", {})
                print(f"[i] Cache entries: {metrics.get('total_entries', 0)}")
                print(f"[i] Libraries: {metrics.get('total_libraries', 0)}")
                print(f"[i] Cache size: {status.get('cache_size_mb', 0):.2f} MB")
    except Exception as e:
        print(f"[!] Could not check cache status: {e}")
    
    return success_count > 0


if __name__ == "__main__":
    try:
        result = asyncio.run(populate_cache())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\n[!] Population interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n[X] Population failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

