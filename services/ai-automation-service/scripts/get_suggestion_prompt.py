#!/usr/bin/env python3
"""
Utility script to retrieve and display OpenAI prompts for a specific automation suggestion.

Usage:
    python scripts/get_suggestion_prompt.py <query_id> [suggestion_id]
    python scripts/get_suggestion_prompt.py --search "flash lights"  # Search by query text
    python scripts/get_suggestion_prompt.py --latest  # Get latest suggestion
"""

import json
import sqlite3
import sys
from pathlib import Path

# Database path - try multiple locations
script_dir = Path(__file__).parent
service_dir = script_dir.parent
possible_db_paths = [
    service_dir / "data" / "ai_automation.db",
    service_dir / "src" / "data" / "ai_automation.db",
    Path("/app/data/ai_automation.db"),  # Docker path
]

db_path = None
for path in possible_db_paths:
    if path.exists():
        db_path = path
        break

if not db_path:
    print("Error: Database not found. Checked:")
    for path in possible_db_paths:
        print(f"  - {path}")
    sys.exit(1)

# Suppress database path message unless verbose
if "--verbose" in sys.argv:
    print(f"Using database: {db_path}")


def get_query_by_id(query_id: str) -> dict | None:
    """Get query by ID."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM ask_ai_queries WHERE query_id = ?",
        (query_id,),
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def search_queries_by_text(search_text: str, limit: int = 10) -> list[dict]:
    """Search queries by text in original_query."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM ask_ai_queries WHERE original_query LIKE ? ORDER BY created_at DESC LIMIT ?",
        (f"%{search_text}%", limit),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_latest_query() -> dict | None:
    """Get the most recent query."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM ask_ai_queries ORDER BY created_at DESC LIMIT 1",
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def find_suggestion_by_id(suggestions: list[dict], suggestion_id: str) -> dict | None:
    """Find suggestion by ID (supports both full ID and partial match)."""
    if not suggestions:
        return None

    # Try exact match first
    for suggestion in suggestions:
        if suggestion.get("suggestion_id") == suggestion_id:
            return suggestion

    # Try partial match (e.g., "71481" matches "ask-ai-71481...")
    suggestion_id_lower = suggestion_id.lower()
    for suggestion in suggestions:
        sid = suggestion.get("suggestion_id", "").lower()
        if suggestion_id_lower in sid or sid in suggestion_id_lower:
            return suggestion

    return None


def format_prompt_display(query: dict, suggestion: dict) -> str:
    """Format the prompt for display."""
    debug = suggestion.get("debug", {})

    output = []
    output.append("=" * 80)
    output.append("OPENAI PROMPT FOR AUTOMATION SUGGESTION")
    output.append("=" * 80)
    output.append("")

    # Query Information
    output.append("QUERY INFORMATION:")
    output.append(f"  Query ID: {query.get('query_id', 'N/A')}")
    output.append(f"  Original Query: {query.get('original_query', 'N/A')}")
    output.append(f"  Created: {query.get('created_at', 'N/A')}")
    output.append(f"  Confidence: {query.get('confidence', 'N/A')}")
    output.append("")

    # Suggestion Information
    output.append("SUGGESTION INFORMATION:")
    output.append(f"  Suggestion ID: {suggestion.get('suggestion_id', 'N/A')}")
    output.append(f"  Description: {suggestion.get('description', 'N/A')}")
    output.append(f"  Trigger: {suggestion.get('trigger_summary', 'N/A')}")
    output.append(f"  Action: {suggestion.get('action_summary', 'N/A')}")
    output.append(f"  Devices Involved: {', '.join(suggestion.get('devices_involved', []))}")
    output.append(f"  Validated Entities: {json.dumps(suggestion.get('validated_entities', {}), indent=2)}")
    output.append(f"  Confidence: {suggestion.get('confidence', 'N/A')}")
    output.append("")

    # System Prompt
    output.append("=" * 80)
    output.append("SYSTEM PROMPT")
    output.append("=" * 80)
    system_prompt = debug.get("system_prompt", "N/A")
    output.append(system_prompt)
    output.append("")

    # User Prompt (Full)
    output.append("=" * 80)
    output.append("USER PROMPT (FULL - SENT TO OPENAI)")
    output.append("=" * 80)
    user_prompt = debug.get("user_prompt", "N/A")
    output.append(user_prompt)
    output.append("")

    # Filtered User Prompt (if different)
    filtered_prompt = debug.get("filtered_user_prompt")
    if filtered_prompt and filtered_prompt != user_prompt:
        output.append("=" * 80)
        output.append("USER PROMPT (FILTERED - ENTITIES ONLY)")
        output.append("=" * 80)
        output.append(filtered_prompt)
        output.append("")

    # Clarification Context
    clarification_context = debug.get("clarification_context")
    if clarification_context:
        output.append("=" * 80)
        output.append("CLARIFICATION CONTEXT (Q&A)")
        output.append("=" * 80)
        output.append(json.dumps(clarification_context, indent=2))
        output.append("")

    # OpenAI Response
    openai_response = debug.get("openai_response")
    if openai_response:
        output.append("=" * 80)
        output.append("OPENAI RESPONSE")
        output.append("=" * 80)
        if isinstance(openai_response, list):
            # Find the matching suggestion in the response
            for resp in openai_response:
                if resp.get("description") == suggestion.get("description"):
                    output.append(json.dumps(resp, indent=2))
                    break
            else:
                output.append(json.dumps(openai_response, indent=2))
        else:
            output.append(json.dumps(openai_response, indent=2))
        output.append("")

    # Token Usage
    token_usage = debug.get("token_usage")
    if token_usage:
        output.append("=" * 80)
        output.append("TOKEN USAGE")
        output.append("=" * 80)
        output.append(json.dumps(token_usage, indent=2))
        output.append("")

    # Device Selection Debug
    device_debug = debug.get("device_selection")
    if device_debug:
        output.append("=" * 80)
        output.append("DEVICE SELECTION DEBUG")
        output.append("=" * 80)
        output.append(json.dumps(device_debug, indent=2))
        output.append("")

    # Entity Context Stats
    entity_context_stats = debug.get("entity_context_stats")
    if entity_context_stats:
        output.append("=" * 80)
        output.append("ENTITY CONTEXT STATISTICS")
        output.append("=" * 80)
        output.append(json.dumps(entity_context_stats, indent=2))
        output.append("")

    output.append("=" * 80)
    output.append("END OF PROMPT")
    output.append("=" * 80)

    return "\n".join(output)


def main():
    """Main function."""
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    query = None
    suggestion_id = None

    # Parse arguments
    if sys.argv[1] == "--latest":
        query = get_latest_query()
        if len(sys.argv) > 2:
            suggestion_id = sys.argv[2]
    elif sys.argv[1] == "--search":
        if len(sys.argv) < 3:
            print("Error: --search requires search text")
            sys.exit(1)
        search_text = sys.argv[2]
        queries = search_queries_by_text(search_text)
        if not queries:
            print(f"No queries found matching: {search_text}")
            sys.exit(1)
        print(f"Found {len(queries)} queries matching '{search_text}':")
        for i, q in enumerate(queries, 1):
            suggestions = json.loads(q.get("suggestions", "[]") or "[]")
            print(f"  {i}. [{q.get('query_id')}] {q.get('original_query', '')[:80]}... ({len(suggestions)} suggestions)")
        if len(queries) == 1:
            query = queries[0]
            if len(sys.argv) > 3:
                suggestion_id = sys.argv[3]
        else:
            print("\nPlease specify query_id: python scripts/get_suggestion_prompt.py <query_id> [suggestion_id]")
            sys.exit(0)
    else:
        query_id = sys.argv[1]
        query = get_query_by_id(query_id)
        if len(sys.argv) > 2:
            suggestion_id = sys.argv[2]

    if not query:
        print("Query not found")
        sys.exit(1)

    # Parse suggestions JSON
    suggestions_json = query.get("suggestions")
    if suggestions_json:
        suggestions = json.loads(suggestions_json) if isinstance(suggestions_json, str) else suggestions_json
    else:
        suggestions = []

    if not suggestions:
        print(f"Query {query.get('query_id')} has no suggestions")
        sys.exit(1)

    # Find suggestion
    if suggestion_id:
        suggestion = find_suggestion_by_id(suggestions, suggestion_id)
        if not suggestion:
            print(f"Suggestion {suggestion_id} not found in query {query.get('query_id')}")
            print(f"Available suggestions: {[s.get('suggestion_id') for s in suggestions]}")
            sys.exit(1)
    else:
        # Use first suggestion
        suggestion = suggestions[0]
        print(f"No suggestion_id provided, using first suggestion: {suggestion.get('suggestion_id')}")
        if len(suggestions) > 1:
            print(f"Available suggestions: {[s.get('suggestion_id') for s in suggestions]}")

    # Display prompt
    output = format_prompt_display(query, suggestion)
    print(output)

    # Optionally save to file
    if "--save" in sys.argv:
        filename = f"prompt_{query.get('query_id')}_{suggestion.get('suggestion_id', 'unknown')}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"\nPrompt saved to: {filename}")


if __name__ == "__main__":
    main()

