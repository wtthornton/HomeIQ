#!/usr/bin/env python3
"""
Analyze Device Matching Fix

This script:
1. Finds recent queries about "office lights" or "blink"
2. Extracts debugging JSON from suggestions
3. Verifies validated_entities are correct
4. Checks if devices_involved matches validated_entities
"""

import json
import sqlite3
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

def find_database() -> Optional[Path]:
    """Find the database file in common locations."""
    root_dir = Path(__file__).parent.parent
    db_paths = [
        root_dir / "data" / "ai_automation.db",
        Path("data") / "ai_automation.db",
        Path("/app/data/ai_automation.db"),
        root_dir / "services" / "ai-automation-service" / "data" / "ai_automation.db",
    ]
    
    for db_path in db_paths:
        if db_path.exists():
            return db_path.resolve()
    
    return None

def search_queries(db_path: Path, search_text: str = "office", limit: int = 10) -> List[Dict[str, Any]]:
    """Search for queries containing the search text."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # First check if table exists
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='ask_ai_queries'"
    )
    if not cursor.fetchone():
        print(f"⚠️  Table 'ask_ai_queries' does not exist in database")
        print("Available tables:")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        for table in tables:
            print(f"  - {table[0]}")
        conn.close()
        return []
    
    cursor.execute(
        """
        SELECT query_id, original_query, suggestions, created_at, confidence
        FROM ask_ai_queries
        WHERE original_query LIKE ?
        ORDER BY created_at DESC
        LIMIT ?
        """,
        (f"%{search_text}%", limit)
    )
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

def analyze_suggestion(suggestion: Dict[str, Any], query_id: str) -> Dict[str, Any]:
    """Analyze a single suggestion for device matching issues."""
    analysis = {
        "suggestion_id": suggestion.get("suggestion_id", "Unknown"),
        "query_id": query_id,
        "description": suggestion.get("description", "")[:100],
        "issues": [],
        "warnings": [],
        "info": [],
    }
    
    # Get devices_involved
    devices_involved = suggestion.get("devices_involved", [])
    validated_entities = suggestion.get("validated_entities", {})
    entity_id_annotations = suggestion.get("entity_id_annotations", {})
    
    # Check 1: Are all devices_involved in validated_entities?
    if devices_involved and validated_entities:
        validated_device_names = set(validated_entities.keys())
        unmatched_devices = [d for d in devices_involved if d not in validated_device_names]
        
        if unmatched_devices:
            analysis["issues"].append({
                "type": "unmatched_devices_in_devices_involved",
                "message": f"Found {len(unmatched_devices)} devices in devices_involved that are NOT in validated_entities",
                "devices": unmatched_devices[:10],  # Limit to first 10
            })
        else:
            analysis["info"].append({
                "type": "devices_involved_validated",
                "message": f"All {len(devices_involved)} devices in devices_involved are in validated_entities",
            })
    
    # Check 2: Are validated_entities reasonable?
    if validated_entities:
        analysis["info"].append({
            "type": "validated_entities_count",
            "message": f"Found {len(validated_entities)} validated entities",
            "entities": list(validated_entities.items())[:5],  # First 5
        })
    else:
        analysis["issues"].append({
            "type": "no_validated_entities",
            "message": "No validated_entities found - this suggestion will fail",
        })
    
    # Check 3: Check entity_id_annotations
    if entity_id_annotations:
        annotation_entity_ids = set()
        for annotation in entity_id_annotations.values():
            if isinstance(annotation, dict) and annotation.get("entity_id"):
                annotation_entity_ids.add(annotation["entity_id"])
        
        analysis["info"].append({
            "type": "entity_id_annotations",
            "message": f"Found {len(entity_id_annotations)} entity_id_annotations with {len(annotation_entity_ids)} unique entity IDs",
        })
    
    # Check 4: Debug data
    debug = suggestion.get("debug", {})
    if debug:
        device_selection = debug.get("device_selection", [])
        if device_selection:
            analysis["info"].append({
                "type": "device_selection_debug",
                "message": f"Found {len(device_selection)} device selection entries in debug data",
            })
    
    # Check 5: Office-specific checks
    description_lower = suggestion.get("description", "").lower()
    if "office" in description_lower:
        office_devices = [d for d in devices_involved if "office" in d.lower()]
        office_validated = {k: v for k, v in validated_entities.items() if "office" in k.lower()}
        
        if office_devices:
            analysis["info"].append({
                "type": "office_devices",
                "message": f"Found {len(office_devices)} office devices in devices_involved: {office_devices}",
            })
        
        if office_validated:
            analysis["info"].append({
                "type": "office_validated",
                "message": f"Found {len(office_validated)} office devices in validated_entities",
                "entities": list(office_validated.items()),
            })
    
    return analysis

def print_analysis(analysis: Dict[str, Any]):
    """Print analysis results in a readable format."""
    print("=" * 80)
    print(f"Suggestion ID: {analysis['suggestion_id']}")
    print(f"Query ID: {analysis['query_id']}")
    print(f"Description: {analysis['description']}")
    print("=" * 80)
    
    if analysis["issues"]:
        print("\n❌ ISSUES FOUND:")
        for issue in analysis["issues"]:
            print(f"  - {issue['type']}: {issue['message']}")
            if "devices" in issue:
                print(f"    Devices: {issue['devices']}")
    
    if analysis["warnings"]:
        print("\n⚠️  WARNINGS:")
        for warning in analysis["warnings"]:
            print(f"  - {warning['type']}: {warning['message']}")
    
    if analysis["info"]:
        print("\nℹ️  INFO:")
        for info in analysis["info"]:
            print(f"  - {info['type']}: {info['message']}")
            if "entities" in info:
                print(f"    Entities: {info['entities']}")
            if "devices" in info:
                print(f"    Devices: {info['devices']}")
    
    print()

def main():
    """Main function."""
    # Find database
    db_path = find_database()
    if not db_path:
        print("❌ Database not found. Checked locations:")
        print("  - data/ai_automation.db")
        print("  - /app/data/ai_automation.db")
        print("  - services/ai-automation-service/data/ai_automation.db")
        sys.exit(1)
    
    print(f"✅ Found database: {db_path}")
    
    # Search for queries
    search_terms = ["blink", "office"]
    all_queries = []
    
    for term in search_terms:
        queries = search_queries(db_path, term, limit=5)
        all_queries.extend(queries)
    
    # Remove duplicates by query_id
    seen_ids = set()
    unique_queries = []
    for q in all_queries:
        if q["query_id"] not in seen_ids:
            seen_ids.add(q["query_id"])
            unique_queries.append(q)
    
    # Sort by created_at
    unique_queries.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    print(f"\n📊 Found {len(unique_queries)} unique queries")
    
    if not unique_queries:
        print("No queries found. Try running a query first.")
        sys.exit(0)
    
    # Analyze each query
    for query in unique_queries[:5]:  # Analyze top 5
        query_id = query["query_id"]
        original_query = query["original_query"]
        suggestions_json = query.get("suggestions")
        
        print("\n" + "=" * 80)
        print(f"QUERY ID: {query_id}")
        print(f"QUERY: {original_query[:100]}...")
        print("=" * 80)
        
        if not suggestions_json:
            print("⚠️  No suggestions found for this query")
            continue
        
        # Parse suggestions
        if isinstance(suggestions_json, str):
            suggestions = json.loads(suggestions_json)
        else:
            suggestions = suggestions_json
        
        if not suggestions:
            print("⚠️  Empty suggestions array")
            continue
        
        print(f"📋 Found {len(suggestions)} suggestion(s)")
        
        # Analyze each suggestion
        for i, suggestion in enumerate(suggestions, 1):
            print(f"\n--- Suggestion {i}/{len(suggestions)} ---")
            analysis = analyze_suggestion(suggestion, query_id)
            print_analysis(analysis)
    
    print("\n" + "=" * 80)
    print("✅ Analysis complete!")
    print("=" * 80)
    print("\nNext steps:")
    print("1. Review the issues above")
    print("2. Test the fix by running a new query")
    print("3. Check the UI to verify only matched devices appear")

if __name__ == "__main__":
    main()

