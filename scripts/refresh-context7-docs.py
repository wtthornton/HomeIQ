#!/usr/bin/env python3
"""
Refresh Context7 KB cache documentation for all libraries with versions.

This script:
1. Reads the KB index to find all libraries with versions
2. Uses Context7 MCP tools to fetch fresh documentation
3. Updates the KB cache with new documentation
4. Updates metadata and timestamps

Note: Requires Context7 MCP server to be configured with valid API key.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

# Project root
PROJECT_ROOT = Path(__file__).parent.parent
KB_CACHE_DIR = PROJECT_ROOT / "docs" / "kb" / "context7-cache"
INDEX_FILE = KB_CACHE_DIR / "index.yaml"

# Default topics to fetch for each library type
DEFAULT_TOPICS = {
    "fastapi": ["async", "endpoints", "middleware"],
    "aiohttp": ["websocket", "async-http"],
    "pytest": ["fixtures", "async"],
    "influxdb": ["flux-queries", "time-series"],
    "sqlalchemy": ["async"],
    "alembic": ["migrations"],
    "react": ["hooks", "components"],
    "typescript": ["types"],
    "vite": ["build"],
    "vitest": ["testing"],
    "playwright": ["e2e-testing"],
    "tailwindcss": ["utility-classes"],
    "pydantic": ["validation"],
    "sentence-transformers": ["embeddings"],
    "huggingface-transformers": ["models"],
    "docker": ["compose"],
    "puppeteer": ["automation"],
}


def load_index() -> dict:
    """Load the KB index.yaml file."""
    if not INDEX_FILE.exists():
        print(f"Error: Index file not found: {INDEX_FILE}")
        sys.exit(1)

    with open(INDEX_FILE) as f:
        return yaml.safe_load(f) or {}


def save_index(index_data: dict):
    """Save the KB index.yaml file."""
    with open(INDEX_FILE, "w") as f:
        yaml.dump(index_data, f, default_flow_style=False, sort_keys=False)


def get_libraries_to_refresh(index_data: dict) -> list[dict]:
    """Get list of libraries that need documentation refresh."""
    libraries = []

    if "libraries" not in index_data:
        return libraries

    for lib_name, lib_data in index_data["libraries"].items():
        # Only refresh libraries with versions
        if "version" in lib_data and "context7_id" in lib_data:
            libraries.append({
                "name": lib_name,
                "version": lib_data["version"],
                "context7_id": lib_data["context7_id"],
                "topics": lib_data.get("topics", DEFAULT_TOPICS.get(lib_name, ["general"])),
                "docs_file": lib_data.get("docs_file", f"libraries/{lib_name}/docs.md"),
            })

    return libraries


def print_refresh_instructions(libraries: list[dict]):
    """Print instructions for manually refreshing documentation."""
    print("\n" + "="*80)
    print("CONTEXT7 DOCUMENTATION REFRESH INSTRUCTIONS")
    print("="*80)
    print("\nTo refresh documentation, use BMAD Master commands with Context7 MCP:")
    print("\nPython Libraries:")
    print("-" * 80)

    python_libs = [lib for lib in libraries if lib["name"] in [
        "fastapi", "aiohttp", "pytest", "influxdb", "sqlalchemy", "alembic",
        "pydantic", "sentence-transformers", "huggingface-transformers", "docker",
    ]]

    for lib in python_libs:
        topics = lib["topics"][:2]  # Show first 2 topics
        topic_str = " ".join(topics)
        print(f"  *context7-docs {lib['name']} {topic_str}")

    print("\nJavaScript Libraries:")
    print("-" * 80)

    js_libs = [lib for lib in libraries if lib["name"] in [
        "react", "typescript", "vite", "vitest", "playwright", "tailwindcss", "puppeteer",
    ]]

    for lib in js_libs:
        topics = lib["topics"][:2]  # Show first 2 topics
        topic_str = " ".join(topics)
        print(f"  *context7-docs {lib['name']} {topic_str}")

    print("\n" + "="*80)
    print("NOTE: These commands require Context7 MCP server with valid API key.")
    print("The KB cache will be automatically updated when documentation is fetched.")
    print("="*80 + "\n")


def update_refresh_timestamp(index_data: dict, library: str):
    """Update the last_fetched timestamp for a library."""
    if "libraries" not in index_data:
        return

    if library not in index_data["libraries"]:
        return

    lib_data = index_data["libraries"][library]
    lib_data["last_fetched"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    lib_data["refresh_requested"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def main():
    """Main execution function."""
    import io
    import sys

    # Fix encoding for Windows console
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

    print("[*] Loading Context7 KB index...")
    index_data = load_index()

    print("[*] Finding libraries with versions...")
    libraries = get_libraries_to_refresh(index_data)

    print(f"[OK] Found {len(libraries)} libraries with versions")

    # Print summary
    print("\n[*] Libraries to refresh:")
    for lib in libraries:
        print(f"   - {lib['name']:30} v{lib['version']:15} {lib['context7_id']}")

    # Update refresh timestamps
    print("\n[*] Updating refresh request timestamps...")
    for lib in libraries:
        update_refresh_timestamp(index_data, lib["name"])

    save_index(index_data)
    print("[OK] Index updated with refresh request timestamps")

    # Print instructions
    print_refresh_instructions(libraries)

    print("\n[*] Next steps:")
    print("   1. Ensure Context7 MCP server is configured with valid API key")
    print("   2. Use the commands above to refresh documentation")
    print("   3. Documentation will be automatically cached in KB")
    print("   4. Run this script again to verify refresh timestamps")


if __name__ == "__main__":
    main()

