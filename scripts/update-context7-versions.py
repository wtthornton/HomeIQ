#!/usr/bin/env python3
"""
Update Context7 KB cache with correct library versions from project dependencies.

This script:
1. Extracts library versions from requirements.txt and package.json files
2. Resolves Context7 library IDs with version-specific paths
3. Updates KB cache with version-specific documentation
4. Updates index.yaml with correct version information
"""

import os
import re
import json
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone

# Project root
PROJECT_ROOT = Path(__file__).parent.parent
KB_CACHE_DIR = PROJECT_ROOT / "docs" / "kb" / "context7-cache"
INDEX_FILE = KB_CACHE_DIR / "index.yaml"

# Library name mappings (project name -> Context7 library name)
LIBRARY_MAPPINGS = {
    # Python libraries
    "fastapi": "fastapi",
    "aiohttp": "aiohttp",
    "pytest": "pytest",
    "alembic": "alembic",
    "influxdb-client": "influxdb",
    "pydantic": "pydantic",
    "sqlalchemy": "sqlalchemy",
    "transformers": "huggingface-transformers",
    "sentence-transformers": "sentence-transformers",
    "docker": "docker",
    "python-logging": "python-logging",
    
    # JavaScript libraries
    "react": "react",
    "typescript": "typescript",
    "vite": "vite",
    "vitest": "vitest",
    "@playwright/test": "playwright",
    "playwright": "playwright",
    "test": "playwright",  # @playwright/test -> test -> playwright
    "tailwindcss": "tailwindcss",
    "puppeteer": "puppeteer",
    "@heroicons/react": "heroicons",
    "heroicons": "heroicons",
}

# Context7 library ID patterns (base -> version pattern)
CONTEXT7_ID_PATTERNS = {
    "fastapi": "/tiangolo/fastapi",
    "aiohttp": "/aio-libs/aiohttp",
    "pytest": "/pytest-dev/pytest",
    "alembic": "/sqlalchemy/alembic",
    "influxdb": "/influxdata/influxdb",
    "pydantic": "/pydantic/pydantic",
    "sqlalchemy": "/sqlalchemy/sqlalchemy",
    "huggingface-transformers": "/huggingface/transformers",
    "sentence-transformers": "/ukplab/sentence-transformers",
    "docker": "/docker/docker",
    "python-logging": "/python/logging",
    "react": "/reactjs/react.dev",
    "typescript": "/microsoft/typescript",
    "vite": "/vitejs/vite",
    "vitest": "/vitest-dev/vitest",
    "playwright": "/microsoft/playwright",
    "tailwindcss": "/tailwindlabs/tailwindcss",
    "puppeteer": "/puppeteer/puppeteer",
    "heroicons": "/tailwindlabs/heroicons",
    "homeassistant": "/home-assistant/core",
}

# Version-specific Context7 ID patterns (when version is needed in path)
VERSIONED_LIBS = {
    "vitest": lambda v: f"/vitest-dev/vitest/v{v.replace('^', '').replace('~', '')}",
    "puppeteer": lambda v: f"/puppeteer/puppeteer/puppeteer-v{v.replace('^', '').replace('~', '')}",
    "playwright": lambda v: f"/microsoft/playwright/v{v.replace('^', '').replace('~', '')}",
}


def extract_python_versions() -> Dict[str, str]:
    """Extract Python library versions from requirements.txt files."""
    versions = {}
    services_dir = PROJECT_ROOT / "services"
    
    for req_file in services_dir.rglob("requirements.txt"):
        with open(req_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                
                # Match: package==version or package>=version, etc.
                match = re.match(r'^([a-zA-Z0-9_-]+)[=<>!]+([0-9.]+)', line)
                if match:
                    pkg_name, version = match.groups()
                    # Normalize package name
                    pkg_name = pkg_name.lower().replace('_', '-')
                    
                    # Keep the highest version if multiple found (compare as tuples)
                    if pkg_name not in versions:
                        versions[pkg_name] = version
                    else:
                        # Compare versions properly (e.g., "2.12.4" > "2.8.2")
                        current_parts = [int(x) for x in versions[pkg_name].split('.')]
                        new_parts = [int(x) for x in version.split('.')]
                        # Pad to same length
                        max_len = max(len(current_parts), len(new_parts))
                        current_parts.extend([0] * (max_len - len(current_parts)))
                        new_parts.extend([0] * (max_len - len(new_parts)))
                        if new_parts > current_parts:
                            versions[pkg_name] = version
    
    return versions


def extract_js_versions() -> Dict[str, str]:
    """Extract JavaScript library versions from package.json files."""
    versions = {}
    package_files = [
        PROJECT_ROOT / "package.json",
        PROJECT_ROOT / "services" / "health-dashboard" / "package.json",
        PROJECT_ROOT / "tests" / "e2e" / "package.json",
    ]
    
    for pkg_file in package_files:
        if not pkg_file.exists():
            continue
            
        with open(pkg_file, 'r') as f:
            data = json.load(f)
            
            # Check dependencies and devDependencies
            for deps_key in ['dependencies', 'devDependencies']:
                if deps_key in data:
                    for pkg_name, version_spec in data[deps_key].items():
                        # Remove ^, ~, etc. and extract version
                        clean_version = re.sub(r'[\^~>=<]', '', version_spec)
                        # Normalize package name (remove @scope/ if present)
                        # Special case: @playwright/test -> playwright
                        if pkg_name == "@playwright/test":
                            clean_name = "playwright"
                        else:
                            clean_name = pkg_name.split('/')[-1]
                        
                        if clean_name not in versions:
                            versions[clean_name] = clean_version
                        else:
                            # Compare versions properly
                            try:
                                current_parts = [int(x) for x in versions[clean_name].split('.')]
                                new_parts = [int(x) for x in clean_version.split('.')]
                                max_len = max(len(current_parts), len(new_parts))
                                current_parts.extend([0] * (max_len - len(current_parts)))
                                new_parts.extend([0] * (max_len - len(new_parts)))
                                if new_parts > current_parts:
                                    versions[clean_name] = clean_version
                            except ValueError:
                                # If version parsing fails, keep the longer string
                                if len(clean_version) > len(versions[clean_name]):
                                    versions[clean_name] = clean_version
    
    return versions


def get_context7_library_id(library: str, version: Optional[str] = None) -> str:
    """Get Context7-compatible library ID, optionally with version."""
    base_id = CONTEXT7_ID_PATTERNS.get(library)
    if not base_id:
        return None
    
    # Check if this library needs version in the path
    if library in VERSIONED_LIBS and version:
        try:
            return VERSIONED_LIBS[library](version)
        except Exception:
            return base_id
    
    return base_id


def load_index() -> dict:
    """Load the KB index.yaml file."""
    if not INDEX_FILE.exists():
        return {}
    
    with open(INDEX_FILE, 'r') as f:
        return yaml.safe_load(f) or {}


def save_index(index_data: dict):
    """Save the KB index.yaml file."""
    INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(INDEX_FILE, 'w') as f:
        yaml.dump(index_data, f, default_flow_style=False, sort_keys=False)


def update_library_version_in_index(
    index_data: dict,
    library: str,
    version: str,
    context7_id: str
):
    """Update a library's version information in the index."""
    if 'libraries' not in index_data:
        index_data['libraries'] = {}
    
    if library not in index_data['libraries']:
        index_data['libraries'][library] = {}
    
    lib_data = index_data['libraries'][library]
    lib_data['version'] = version
    lib_data['context7_id'] = context7_id
    lib_data['last_version_check'] = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    
    # Update last_fetched if not present
    if 'last_fetched' not in lib_data:
        lib_data['last_fetched'] = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def main():
    """Main execution function."""
    import sys
    import io
    
    # Fix encoding for Windows console
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    
    print("[*] Extracting library versions from project dependencies...")
    
    # Extract versions
    python_versions = extract_python_versions()
    js_versions = extract_js_versions()
    
    print(f"   Found {len(python_versions)} Python libraries")
    print(f"   Found {len(js_versions)} JavaScript libraries")
    
    # Load current index
    index_data = load_index()
    
    # Process Python libraries
    print("\n[*] Processing Python libraries...")
    updates = []
    
    for pkg_name, version in python_versions.items():
        library = LIBRARY_MAPPINGS.get(pkg_name)
        if not library:
            continue
        
        context7_id = get_context7_library_id(library, version)
        if not context7_id:
            continue
        
        update_library_version_in_index(index_data, library, version, context7_id)
        updates.append((library, version, context7_id))
        print(f"   [OK] {library}: {version} -> {context7_id}")
    
    # Process JavaScript libraries
    print("\n[*] Processing JavaScript libraries...")
    
    for pkg_name, version in js_versions.items():
        library = LIBRARY_MAPPINGS.get(pkg_name)
        if not library:
            continue
        
        context7_id = get_context7_library_id(library, version)
        if not context7_id:
            continue
        
        update_library_version_in_index(index_data, library, version, context7_id)
        updates.append((library, version, context7_id))
        print(f"   [OK] {library}: {version} -> {context7_id}")
    
    # Update index metadata
    if 'metadata' not in index_data:
        index_data['metadata'] = {}
    
    index_data['metadata']['last_version_update'] = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    index_data['metadata']['total_libraries_with_versions'] = len(updates)
    
    # Save updated index
    save_index(index_data)
    
    print(f"\n[OK] Updated {len(updates)} libraries in Context7 KB index")
    print(f"   Index saved to: {INDEX_FILE}")
    
    print("\n[*] Summary of updates:")
    for library, version, context7_id in sorted(updates):
        print(f"   {library:30} {version:15} {context7_id}")
    
    print("\n[*] Next steps:")
    print("   1. Review the updated index.yaml file")
    print("   2. Use *context7-docs commands to refresh documentation for each library")
    print("   3. The version-specific Context7 IDs will be used for future lookups")


if __name__ == "__main__":
    main()

