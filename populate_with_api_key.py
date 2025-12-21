#!/usr/bin/env python3
"""
Populate Context7 KB cache using API key.

This script uses the Context7 API key to fetch and store documentation
properly through the Context7 integration.
"""

import asyncio
import os
import sys
from pathlib import Path

# Set API key
CONTEXT7_API_KEY = "ctx7sk-a2043cb5-8c75-46cc-8ee1-0d137fdc56cc"
os.environ["CONTEXT7_API_KEY"] = CONTEXT7_API_KEY

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
    print("  Context7 KB Cache Population (with API Key)")
    print("=" * 70)
    print()
    
    # Load config
    config = load_config()
    if not config.context7 or not config.context7.enabled:
        print("[X] Context7 is not enabled in config")
        return False
    
    # Initialize Context7 helper
    # Note: MCP Gateway is None, will use HTTP fallback with API key
    helper = Context7AgentHelper(
        config=config,
        mcp_gateway=None,  # Will use HTTP fallback
        project_root=project_root
    )
    
    if not helper.enabled:
        print("[X] Context7 helper is not enabled")
        return False
    
    print(f"[i] Cache location: {helper.cache_structure.cache_root}")
    print(f"[i] API Key: {'*' * 20}...{CONTEXT7_API_KEY[-8:]}")
    print()
    
    # Fetch and store documentation
    success_count = 0
    error_count = 0
    cache_hit_count = 0
    
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
                if source == "cache":
                    print(f"[OK] Cache hit")
                    cache_hit_count += 1
                else:
                    print(f"[OK] {source} (stored in cache)")
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
    print(f"[OK] Successfully processed: {success_count}")
    print(f"[i] Cache hits: {cache_hit_count}")
    print(f"[i] New entries fetched: {success_count - cache_hit_count}")
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
                print("=" * 70)
                print("  Final Cache Status")
                print("=" * 70)
                print(f"[OK] Cache entries: {metrics.get('total_entries', 0)}")
                print(f"[OK] Libraries: {metrics.get('total_libraries', 0)}")
                print(f"[i] Cache hits: {metrics.get('cache_hits', 0)}")
                print(f"[i] Cache misses: {metrics.get('cache_misses', 0)}")
                print(f"[i] API calls: {metrics.get('api_calls', 0)}")
                hit_rate = metrics.get("hit_rate", 0.0)
                print(f"[i] Hit rate: {hit_rate:.1f}%")
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

