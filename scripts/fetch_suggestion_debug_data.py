#!/usr/bin/env python3
"""
Fetch debug panel data for a specific suggestion ID and generate a markdown file.

This script uses the same API endpoints that the frontend uses to fetch suggestion data.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

# Add the services directory to the path so we can import from the service
sys.path.insert(0, str(Path(__file__).parent.parent / "services" / "ai-automation-service" / "src"))

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8018/api")
API_KEY = os.getenv("API_KEY", "hs_P3rU9kQ2xZp6vL1fYc7bN4sTqD8mA0wR")

def fetch_json(url: str, method: str = "GET", body: dict | None = None) -> dict[str, Any]:
    """Fetch JSON from API with authentication."""
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "X-HomeIQ-API-Key": API_KEY,
        "Content-Type": "application/json",
    }

    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=30)
        else:
            response = requests.post(url, headers=headers, json=body, timeout=30)

        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {url}: {e}")
        if hasattr(e, "response") and e.response is not None:
            try:
                error_detail = e.response.json()
                print(f"Error details: {error_detail}")
            except:
                print(f"Response text: {e.response.text}")
        raise

def find_suggestion_in_database(suggestion_id: str) -> tuple[str, dict[str, Any]] | None:
    """Search through database to find the suggestion with the given ID. Returns (query_id, suggestion)."""
    try:
        import os

        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import sessionmaker

        # Get database URL from environment or use default
        script_dir = Path(__file__).parent.parent
        default_db = script_dir / "data" / "ai_automation.db"

        db_path = os.getenv("DATABASE_URL", f"sqlite:///{default_db}")
        if not db_path.startswith("sqlite:///"):
            # If it's a relative path, make it absolute
            if not os.path.isabs(db_path.replace("sqlite:///", "")):
                db_path = f"sqlite:///{os.path.join(script_dir, db_path.replace('sqlite:///', ''))}"

        engine = create_engine(db_path, echo=False)
        Session = sessionmaker(bind=engine)
        session = Session()

        try:
            # Query to find suggestion in JSON field
            # SQLite JSON functions: json_extract, json_each
            query = text("""
                SELECT query_id, suggestions
                FROM ask_ai_queries
                WHERE suggestions IS NOT NULL
            """)

            result = session.execute(query)
            rows = result.fetchall()

            for row in rows:
                query_id = row[0]
                suggestions_json = row[1]

                if suggestions_json:
                    try:
                        suggestions = json.loads(suggestions_json) if isinstance(suggestions_json, str) else suggestions_json
                        if isinstance(suggestions, list):
                            for suggestion in suggestions:
                                # Try multiple ID formats
                                sid = suggestion.get("suggestion_id", "")
                                # Match exact ID, or ID with # prefix, or numeric part
                                if (sid == suggestion_id or
                                    sid == suggestion_id.replace("#", "") or
                                    sid == f"ask-ai-{suggestion_id.replace('#', '')}" or
                                    suggestion_id.replace("#", "") in sid):
                                    print(f"Found suggestion {suggestion_id} (matched {sid}) in query {query_id}")
                                    return (query_id, suggestion)
                    except json.JSONDecodeError:
                        continue

            print(f"Suggestion {suggestion_id} not found in database")
            return None
        finally:
            session.close()
    except ImportError:
        print("SQLAlchemy not available. Cannot query database directly.")
        return None
    except Exception as e:
        print(f"Error querying database: {e}")
        return None

def get_suggestion_from_query(query_id: str, suggestion_id: str) -> dict[str, Any] | None:
    """Get a specific suggestion from a query."""
    url = f"{API_BASE_URL}/v1/ask-ai/query/{query_id}/suggestions"

    try:
        data = fetch_json(url)
        suggestions = data.get("suggestions", [])

        for suggestion in suggestions:
            sid = suggestion.get("suggestion_id", "")
            # Try multiple ID formats
            if (sid == suggestion_id or
                sid == suggestion_id.replace("#", "") or
                sid == f"ask-ai-{suggestion_id.replace('#', '')}" or
                suggestion_id.replace("#", "") in sid):
                return suggestion

        print(f"Suggestion {suggestion_id} not found in query {query_id}")
        print(f"Available suggestion IDs in this query: {[s.get('suggestion_id') for s in suggestions]}")
        return None
    except Exception as e:
        print(f"Error fetching suggestions from query {query_id}: {e}")
        return None

def format_markdown(suggestion: dict[str, Any], query_id: str | None = None) -> str:
    """Format suggestion debug data as markdown."""

    suggestion_id = suggestion.get("suggestion_id", "Unknown")
    created_at = suggestion.get("created_at", "")

    # Try to format the date
    try:
        if created_at:
            dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            formatted_date = dt.strftime("%m/%d/%Y, %I:%M:%S %p")
        else:
            formatted_date = "Unknown"
    except:
        formatted_date = created_at

    original_query = suggestion.get("original_query", suggestion.get("query", "Unknown query"))

    md = f"""# Suggestion ID #{suggestion_id} - Debug Panel Information

**Created:** {formatted_date}
**Query ID:** {query_id or "Unknown"}
**Query:** "{original_query}"

---

## 1. Device Selection

### Selected Devices

"""

    # Device Info
    device_info = suggestion.get("device_info", [])
    if device_info:
        md += "| Friendly Name | Entity ID | Domain | Status |\n"
        md += "|--------------|-----------|--------|--------|\n"
        for device in device_info:
            friendly_name = device.get("friendly_name", "Unknown")
            entity_id = device.get("entity_id", "Unknown")
            domain = device.get("domain", "N/A")
            selected = "Selected" if device.get("selected", True) else "Excluded"
            md += f"| {friendly_name} | `{entity_id}` | {domain} | {selected} |\n"
    else:
        md += "*No device info available*\n"

    md += "\n### Device Selection Reasoning\n\n"

    # Debug device selection
    debug = suggestion.get("debug", {})
    device_selection = debug.get("device_selection", [])

    if device_selection:
        for idx, device in enumerate(device_selection, 1):
            device_name = device.get("device_name", f"Device {idx}")
            entity_id = device.get("entity_id")
            entity_type = device.get("entity_type", "individual")
            selection_reason = device.get("selection_reason", "No reason provided")

            md += f"#### {device_name}\n"
            md += f"- **Entity ID:** `{entity_id or 'N/A'}`\n"
            md += f"- **Entity Type:** {entity_type}\n"
            md += f"- **Why Selected:** {selection_reason}\n\n"

            # Entities
            entities = device.get("entities", [])
            if entities:
                md += "**Entities:**\n"
                for entity in entities:
                    eid = entity.get("entity_id", "Unknown")
                    fname = entity.get("friendly_name", "Unknown")
                    md += f"- `{eid}` - {fname}\n"
                md += "\n"

            # Capabilities
            capabilities = device.get("capabilities", [])
            if capabilities:
                md += "**Capabilities:**\n"
                for cap in capabilities:
                    md += f"- {cap}\n"
                md += "\n"

            # Actions Suggested
            actions = device.get("actions_suggested", [])
            if actions:
                md += "**Actions Suggested:**\n"
                for action in actions:
                    md += f"- {action}\n"
                md += "\n"

            md += "---\n\n"
    else:
        md += "*No device selection reasoning available*\n\n"

    md += "## 2. OpenAI Prompts\n\n"

    # Entity Context Statistics
    entity_context_stats = debug.get("entity_context_stats", {})
    if entity_context_stats:
        md += "### Entity Context Statistics\n\n"
        total = entity_context_stats.get("total_entities_available", 0)
        used = entity_context_stats.get("entities_used_in_suggestion", 0)
        md += f"- **Total Entities Available:** {total}\n"
        md += f"- **Entities Used in Suggestion:** {used}\n"
        if total > 0 and used > 0:
            md += f"- **Note:** Filtered prompt shows only {used} of {total} available entities to reduce token usage\n"
        md += "\n"

    # System Prompt
    system_prompt = debug.get("system_prompt")
    if system_prompt:
        md += "### System Prompt\n\n"
        md += "```\n"
        md += system_prompt
        md += "\n```\n\n"

    # User Prompt
    user_prompt = debug.get("user_prompt")
    filtered_user_prompt = debug.get("filtered_user_prompt")

    if user_prompt or filtered_user_prompt:
        md += "### User Prompt\n\n"

        if filtered_user_prompt:
            md += "#### Filtered Prompt (Only Entities Used in Suggestion)\n"
            md += "```\n"
            md += filtered_user_prompt
            md += "\n```\n\n"

        if user_prompt:
            md += "#### Full Prompt (All Entities Available During Generation)\n"
            md += "```\n"
            md += user_prompt
            md += "\n```\n\n"

    # OpenAI Response
    openai_response = debug.get("openai_response")
    if openai_response:
        md += "### OpenAI Response\n\n"
        md += "```json\n"
        md += json.dumps(openai_response, indent=2)
        md += "\n```\n\n"

    # Token Usage
    token_usage = debug.get("token_usage", {})
    if token_usage:
        md += "### Token Usage\n\n"
        md += f"- **Prompt Tokens:** {token_usage.get('prompt_tokens', 0)}\n"
        md += f"- **Completion Tokens:** {token_usage.get('completion_tokens', 0)}\n"
        md += f"- **Total Tokens:** {token_usage.get('total_tokens', 0)}\n\n"

    md += "## 3. Technical Prompt\n\n"

    technical_prompt = suggestion.get("technical_prompt", {})
    if technical_prompt:
        md += "### Technical Prompt (Full JSON)\n\n"
        md += "```json\n"
        md += json.dumps(technical_prompt, indent=2)
        md += "\n```\n\n"

        # Trigger Entities
        trigger = technical_prompt.get("trigger", {})
        trigger_entities = trigger.get("entities", [])
        if trigger_entities:
            md += "### Trigger Entities\n\n"
            for entity in trigger_entities:
                md += f"#### {entity.get('friendly_name', 'Unknown')}\n"
                md += f"- **Entity ID:** `{entity.get('entity_id', 'Unknown')}`\n"
                md += f"- **Domain:** {entity.get('domain', 'N/A')}\n"
                md += f"- **Platform:** {entity.get('platform', 'N/A')}\n"
                if entity.get("to"):
                    from_state = entity.get("from", "any")
                    to_state = entity.get("to")
                    md += f"- **State Transition:** {from_state} → {to_state}\n"
                md += "\n"

        # Action Entities
        action = technical_prompt.get("action", {})
        action_entities = action.get("entities", [])
        if action_entities:
            md += "### Action Entities\n\n"
            for entity in action_entities:
                md += f"#### {entity.get('friendly_name', 'Unknown')}\n"
                md += f"- **Entity ID:** `{entity.get('entity_id', 'Unknown')}`\n"
                md += f"- **Domain:** {entity.get('domain', 'N/A')}\n"

                service_calls = entity.get("service_calls", [])
                if service_calls:
                    md += "\n**Service Calls:**\n"
                    for sc in service_calls:
                        service = sc.get("service", "Unknown")
                        md += f"- **Service:** `{service}`\n"
                        parameters = sc.get("parameters", {})
                        if parameters:
                            md += "  ```json\n"
                            md += json.dumps(parameters, indent=2)
                            md += "\n  ```\n"
                md += "\n"
    else:
        md += "*No technical prompt available*\n\n"

    md += "## 4. YAML Response\n\n"

    automation_yaml = suggestion.get("automation_yaml")
    if automation_yaml:
        md += "```yaml\n"
        md += automation_yaml
        md += "\n```\n\n"
    else:
        md += "*No YAML response available*\n\n"

    md += "---\n\n"
    md += "## Notes\n\n"
    md += "- This file contains all debug information displayed in the Debug Panel for this suggestion\n"
    md += "- Information is organized in the same order as it appears in the Debug Panel tabs\n"

    return md

def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("Usage: python fetch_suggestion_debug_data.py <suggestion_id> [query_id]")
        print("Example: python fetch_suggestion_debug_data.py ask-ai-abc123")
        print("Or: python fetch_suggestion_debug_data.py ask-ai-abc123 query-xyz789")
        sys.exit(1)

    suggestion_id = sys.argv[1]
    query_id = sys.argv[2] if len(sys.argv) > 2 else None

    print(f"Fetching debug data for suggestion: {suggestion_id}")
    print(f"API Base URL: {API_BASE_URL}")

    suggestion = None
    found_query_id = query_id

    if query_id:
        # Direct lookup if query_id is provided
        print(f"Fetching from query: {query_id}")
        suggestion = get_suggestion_from_query(query_id, suggestion_id)
    else:
        # Try to find in database
        print("Query ID not provided. Searching database...")
        result = find_suggestion_in_database(suggestion_id)
        if result:
            found_query_id, suggestion = result
        else:
            # Try API approach - search through recent queries
            print("Not found in database. Trying API search...")
            print("Note: For suggestion #2060, you may need to provide the query_id.")
            print("You can find it by:")
            print("1. Checking the browser's network tab when viewing the suggestion")
            print("2. Looking at the URL when viewing the suggestion in the UI")
            print("3. Querying the database directly")
            sys.exit(1)

    if not suggestion:
        print(f"Could not find suggestion {suggestion_id}")
        sys.exit(1)

    # Generate markdown
    markdown = format_markdown(suggestion, found_query_id)

    # Write to file
    output_file = Path(__file__).parent.parent / "docs" / "suggestions" / f"suggestion-{suggestion_id.replace('ask-ai-', '').replace('#', '')}-debug-info.md"
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(markdown)

    print("\n✅ Successfully generated debug data file:")
    print(f"   {output_file}")
    print(f"\nSuggestion ID: {suggestion_id}")
    print(f"Query ID: {found_query_id}")

if __name__ == "__main__":
    main()

