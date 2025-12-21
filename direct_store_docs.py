#!/usr/bin/env python3
"""
Directly store Context7 documentation in KB cache.

This script bypasses some locking mechanisms to directly store
documentation in the cache structure.
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
    from tapps_agents.context7.cache_structure import CacheStructure
    from tapps_agents.context7.metadata import MetadataManager
    from tapps_agents.core.config import load_config
except ImportError as e:
    print(f"Error importing tapps_agents: {e}")
    sys.exit(1)


def store_doc_direct(library: str, topic: str, content: str, context7_id: str = None):
    """Directly store documentation in cache."""
    try:
        # Load config
        config = load_config()
        if not config.context7 or not config.context7.enabled:
            print(f"[X] Context7 not enabled")
            return False
        
        # Initialize cache structure
        cache_root = project_root / config.context7.knowledge_base.location
        cache_structure = CacheStructure(cache_root)
        cache_structure.initialize()
        
        # Ensure library directory exists
        cache_structure.ensure_library_dir(library)
        
        # Write documentation file
        doc_file = cache_structure.get_library_doc_file(library, topic)
        
        # Create markdown content with metadata
        markdown_content = f"""<!--
library: {library}
topic: {topic}
context7_id: {context7_id or ''}
cached_at: {datetime.now(UTC).isoformat()}Z
cache_hits: 0
-->

{content}
"""
        
        doc_file.write_text(markdown_content, encoding="utf-8")
        print(f"[OK] Stored: {library}/{topic} -> {doc_file}")
        
        # Update metadata
        metadata_manager = MetadataManager(cache_structure)
        metadata_manager.update_library_metadata(
            library, context7_id=context7_id, topic=topic
        )
        
        # Update cache index
        metadata_manager.update_cache_index(
            library, topic, context7_id=context7_id
        )
        
        return True
        
    except Exception as e:
        print(f"[X] Error: {e}")
        import traceback
        traceback.print_exc()
        return False


# Store test documentation
if __name__ == "__main__":
    print("=" * 70)
    print("  Direct Context7 Documentation Storage")
    print("=" * 70)
    print()
    
    # Test content
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

## Path Parameters

FastAPI automatically converts path parameters to function arguments.
"""
    
    print("Storing test entry...")
    result = store_doc_direct(
        library="fastapi",
        topic="routing",
        content=test_content,
        context7_id="/fastapi/fastapi"
    )
    
    if result:
        print()
        print("[OK] Test entry stored successfully!")
        print("[i] Run 'python verify_context7.py' to verify")
    else:
        print()
        print("[X] Failed to store entry")

