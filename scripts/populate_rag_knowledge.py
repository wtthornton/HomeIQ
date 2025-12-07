#!/usr/bin/env python3
"""
Populate RAG Knowledge Bases for HomeIQ Experts

This script:
1. Creates knowledge base directories for each expert domain
2. Maps existing HomeIQ documentation to expert domains
3. Copies/symlinks relevant documentation files
4. Optionally fetches 2025 best practices from web sources
"""

import shutil
from pathlib import Path
from typing import Dict, List
import json

# Project root
PROJECT_ROOT = Path(__file__).parent.parent
DOCS_DIR = PROJECT_ROOT / "docs"
KB_DIR = PROJECT_ROOT / ".tapps-agents" / "knowledge"
TAPPS_KB_DIR = PROJECT_ROOT / ".tapps-agents" / "knowledge"

# Domain mappings: domain_name -> list of doc patterns/files
DOMAIN_MAPPINGS = {
    "iot-home-automation": [
        "HA_WEBSOCKET_CALL_TREE.md",
        "HA_FALLBACK_MECHANISM.md",
        "epic-32-home-assistant-validation.md",
        "WEBSOCKET_TROUBLESHOOTING.md",
        "context7-home-assistant-websocket-api.md",
        "architecture/tech-stack.md",
        "architecture/websocket-ingestion",
    ],
    "time-series-analytics": [
        "HYBRID_DATABASE_ARCHITECTURE.md",
        "DATA_BACKEND_IMPLEMENTATION_GUIDE.md",
        "DATA_ENHANCEMENT_QUICK_REFERENCE.md",
        "DATA_SOURCES_AND_STRUCTURES_ENHANCEMENT.md",
        "architecture/tech-stack.md",
        "influxdb",
        "architecture/data-api",
    ],
    "ai-machine-learning": [
        "AI_AUTOMATION_COMPREHENSIVE_GUIDE.md",
        "AI_AUTOMATION_CALL_TREE.md",
        "API_DOCUMENTATION_AI_AUTOMATION.md",
        "architecture/ai-automation-service",
        "architecture/device-intelligence",
        "kb/context7-cache/ai-ml-recommendation-systems-best-practices.md",
        "kb/context7-cache/huggingface-vs-traditional-ml-for-pattern-detection.md",
    ],
    "microservices-architecture": [
        "ARCHITECTURE_OVERVIEW.md",
        "architecture.md",
        "SERVICES_COMPREHENSIVE_REFERENCE.md",
        "SERVICES_OVERVIEW.md",
        "DOCKER_COMPOSE_SERVICES_REFERENCE.md",
        "EPIC_39_SERVICE_COMMUNICATION.md",
        "architecture/tech-stack.md",
        "architecture/",
    ],
    "security-privacy": [
        "SECURITY_CONFIGURATION.md",
        "architecture/security",
    ],
    "energy-management": [
        "architecture/energy-correlator",
        "architecture/electricity-pricing-service",
        "architecture/carbon-intensity-service",
    ],
    "frontend-ux": [
        "CONVERSATIONAL_UI_USER_GUIDE.md",
        "USER_MANUAL.md",
        "architecture/tech-stack.md",
        "architecture/health-dashboard",
        "architecture/ai-automation-ui",
        "kb/context7-cache/react-dashboard-ui-patterns.md",
        "kb/ux-pattern-quick-reference.md",
    ],
    "home-assistant": [
        "HA_WEBSOCKET_CALL_TREE.md",
        "HA_FALLBACK_MECHANISM.md",
        "epic-32-home-assistant-validation.md",
        "WEBSOCKET_TROUBLESHOOTING.md",
        "context7-home-assistant-websocket-api.md",
        "architecture/tech-stack.md",
        "kb/context7-cache/HOME_ASSISTANT_API_KB_UPDATE_2025-10-12.md",
        "kb/context7-cache/HOME_ASSISTANT_AUTOMATION_DELETION_API_2025-10-20.md",
        "kb/context7-cache/HOME_ASSISTANT_KB_UPDATE_2025-10-20.md",
        "kb/context7-cache/HOME_ASSISTANT_QUICK_REF.md",
        "kb/context7-cache/libraries/homeassistant",
    ],
}


def find_docs(pattern: str, base_dir: Path = DOCS_DIR) -> List[Path]:
    """Find documentation files matching pattern."""
    results = []
    
    # Exact file match
    exact_file = base_dir / pattern
    if exact_file.exists() and exact_file.is_file():
        results.append(exact_file)
    
    # Directory match
    if "/" in pattern or pattern.endswith("/"):
        dir_path = base_dir / pattern.rstrip("/")
        if dir_path.exists() and dir_path.is_dir():
            # Find all .md files in directory
            results.extend(dir_path.rglob("*.md"))
    
    # Pattern match (contains)
    if not results:
        for md_file in base_dir.rglob("*.md"):
            if pattern.lower() in str(md_file).lower():
                results.append(md_file)
    
    return results


def create_knowledge_base_structure():
    """Create knowledge base directories for each domain."""
    KB_DIR.mkdir(parents=True, exist_ok=True)
    
    for domain in DOMAIN_MAPPINGS.keys():
        domain_dir = KB_DIR / domain
        domain_dir.mkdir(parents=True, exist_ok=True)
        print(f"✓ Created directory: {domain_dir.relative_to(PROJECT_ROOT)}")


def populate_domain_knowledge(domain: str, patterns: List[str]):
    """Populate knowledge base for a specific domain."""
    domain_dir = KB_DIR / domain
    copied_files = []
    
    for pattern in patterns:
        found_files = find_docs(pattern)
        
        for source_file in found_files:
            # Create target filename
            target_name = source_file.name
            
            # Avoid duplicates
            if (domain_dir / target_name).exists():
                # Add prefix if duplicate
                target_name = f"{source_file.stem}_{source_file.suffix}"
            
            target_file = domain_dir / target_name
            
            try:
                # Copy file
                shutil.copy2(source_file, target_file)
                copied_files.append(target_file.relative_to(PROJECT_ROOT))
                print(f"  ✓ Copied: {source_file.name} → {domain}/{target_name}")
            except Exception as e:
                print(f"  ✗ Error copying {source_file.name}: {e}")
    
    return copied_files


def create_index_file(domain: str, files: List[Path]):
    """Create an index.md file listing all knowledge files."""
    domain_dir = KB_DIR / domain
    index_file = domain_dir / "README.md"
    
    content = f"""# {domain.replace('-', ' ').title()} Knowledge Base

This knowledge base contains documentation and best practices for the {domain} domain.

## Files

"""
    
    for file_path in sorted(files):
        rel_path = Path(file_path).name
        content += f"- [{rel_path}]({rel_path})\n"
    
    content += f"""
## Usage

This knowledge base is automatically used by the {domain} expert when RAG is enabled.

Files are searched using keyword matching. Use descriptive headers and keywords in your documentation for better retrieval.

## Last Updated

Generated automatically by populate_rag_knowledge.py
"""
    
    index_file.write_text(content, encoding='utf-8')
    print(f"  ✓ Created index: {domain}/README.md")


def main():
    """Main execution."""
    print("=" * 60)
    print("Populating RAG Knowledge Bases for HomeIQ Experts")
    print("=" * 60)
    print()
    
    # Create structure
    print("Creating knowledge base structure...")
    create_knowledge_base_structure()
    print()
    
    # Populate each domain
    all_files = {}
    for domain, patterns in DOMAIN_MAPPINGS.items():
        print(f"Populating {domain}...")
        files = populate_domain_knowledge(domain, patterns)
        all_files[domain] = files
        
        if files:
            create_index_file(domain, files)
        
        print(f"  → {len(files)} files added")
        print()
    
    # Summary
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    total_files = sum(len(files) for files in all_files.values())
    print(f"Total files copied: {total_files}")
    print()
    
    for domain, files in all_files.items():
        if files:
            print(f"{domain}: {len(files)} files")
    
    print()
    print("✓ Knowledge bases populated successfully!")
    print()
    print("Next steps:")
    print("1. Review the knowledge files in .tapps-agents/knowledge/")
    print("2. Add any additional 2025 best practices manually")
    print("3. Test with: @enhancer *enhance 'your prompt'")


if __name__ == "__main__":
    main()

