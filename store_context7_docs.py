#!/usr/bin/env python3
"""
Store Context7 documentation in KB cache.

This script takes documentation content and stores it in the KB cache
using the proper cache structure.
"""

import sys
from pathlib import Path
from datetime import datetime, UTC

# Add TappsCodingAgents to path
project_root = Path(__file__).parent
tapps_path = project_root / "TappsCodingAgents"
if tapps_path.exists():
    sys.path.insert(0, str(tapps_path))

try:
    from tapps_agents.context7.kb_cache import KBCache, CacheEntry
    from tapps_agents.context7.cache_structure import CacheStructure
    from tapps_agents.context7.metadata import MetadataManager
    from tapps_agents.core.config import load_config
except ImportError as e:
    print(f"Error importing tapps_agents: {e}")
    sys.exit(1)


def store_documentation(library: str, topic: str, content: str, context7_id: str = None):
    """Store documentation in KB cache."""
    try:
        # Load config
        config = load_config()
        if not config.context7 or not config.context7.enabled:
            print(f"[X] Context7 not enabled for {library}/{topic}")
            return False
        
        # Initialize cache
        cache_root = project_root / config.context7.knowledge_base.location
        cache_structure = CacheStructure(cache_root)
        cache_structure.initialize()
        
        metadata_manager = MetadataManager(cache_structure)
        kb_cache = KBCache(cache_structure.cache_root, metadata_manager)
        
        # Store in cache
        entry = kb_cache.store(
            library=library,
            topic=topic,
            content=content,
            context7_id=context7_id,
            trust_score=0.8,  # Default trust score
            snippet_count=0,  # Will be updated if available
        )
        
        print(f"[OK] Stored: {library}/{topic}")
        return True
        
    except Exception as e:
        print(f"[X] Error storing {library}/{topic}: {e}")
        return False


# Documentation content placeholders - these would be filled with actual fetched content
# For now, we'll create a script that can be used to store docs after fetching them

if __name__ == "__main__":
    print("=" * 70)
    print("  Context7 Documentation Storage Script")
    print("=" * 70)
    print()
    print("This script stores documentation in the KB cache.")
    print("It should be called with documentation content after fetching via MCP.")
    print()
    print("Usage: This script is designed to be called programmatically")
    print("       with documentation content from MCP tools.")
    print()
    
    # Example: Store a test entry
    test_content = """# FastAPI Routing

FastAPI routing documentation.

## Basic Routing

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/items/{item_id}")
async def read_item(item_id: str):
    return {"item_id": item_id}
```

This is a test entry to verify cache storage works.
"""
    
    print("Storing test entry...")
    result = store_documentation(
        library="fastapi",
        topic="routing",
        content=test_content,
        context7_id="/fastapi/fastapi"
    )
    
    if result:
        print("[OK] Test entry stored successfully!")
        print("[i] Run 'python verify_context7.py' to verify cache status")
    else:
        print("[X] Failed to store test entry")

