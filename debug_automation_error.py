"""
Debug script for automation error using TappsCodingAgents
Analyzes the "Unknown entity" error for Scene: Activate action
"""

import json
import re
import sys
import os
from pathlib import Path

# Fix Windows encoding
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# Read conversation data (handle BOM)
def read_conversation_data(file_path: str) -> dict:
    """Read conversation data, handling UTF-8 BOM"""
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        return json.load(f)

# Extract automation YAML from conversation
def extract_automation_yaml(conversation_data: dict) -> str | None:
    """Extract automation YAML from conversation history"""
    history = conversation_data.get('conversation_history', [])
    
    # Look for assistant messages with tool calls that contain automation_yaml
    for msg in reversed(history):  # Start from most recent
        if msg.get('role') == 'assistant':
            content = msg.get('content', '')
            
            # Check if message contains YAML (look for automation structure)
            if 'alias:' in content.lower() and 'trigger:' in content.lower():
                # Extract YAML block
                yaml_match = re.search(r'```yaml\n(.*?)\n```', content, re.DOTALL)
                if yaml_match:
                    return yaml_match.group(1)
    
    # Also check full_assembled_messages
    full_messages = conversation_data.get('full_assembled_messages', [])
    for msg in reversed(full_messages):
        if isinstance(msg, dict):
            # Check tool calls
            tool_calls = msg.get('tool_calls', [])
            for tool_call in tool_calls:
                if tool_call.get('function', {}).get('name') == 'create_automation_from_prompt':
                    arguments = tool_call.get('function', {}).get('arguments', {})
                    if isinstance(arguments, str):
                        arguments = json.loads(arguments)
                    automation_yaml = arguments.get('automation_yaml')
                    if automation_yaml:
                        return automation_yaml
    
    return None

# Extract scene entities from YAML
def extract_scene_entities(yaml_content: str) -> dict:
    """Extract scene entities from automation YAML"""
    scenes = {
        'created': [],  # scene.create calls
        'activated': [],  # scene.turn_on calls
        'entities': []  # scene.* entity IDs referenced
    }
    
    # Extract scene.create calls
    scene_create_pattern = r'scene\.create[:\s]+[\w\s]*?scene_id:\s*["\']?([\w_]+)["\']?'
    created_scenes = re.findall(scene_create_pattern, yaml_content, re.IGNORECASE)
    scenes['created'] = [s.strip() for s in created_scenes]
    
    # Extract scene.turn_on calls
    scene_turn_on_pattern = r'scene\.turn_on[:\s]+[\w\s]*?entity_id:\s*["\']?scene\.([\w_]+)["\']?'
    activated_scenes = re.findall(scene_turn_on_pattern, yaml_content, re.IGNORECASE)
    scenes['activated'] = [s.strip() for s in activated_scenes]
    
    # Also check for scene.* in entity_id fields
    scene_entity_pattern = r'entity_id:\s*["\']?scene\.([\w_]+)["\']?'
    scene_entities = re.findall(scene_entity_pattern, yaml_content, re.IGNORECASE)
    scenes['entities'] = list(set(scene_entities))
    
    return scenes

def main():
    """Main debug function"""
    print("🔍 Debugging automation error...")
    print(f"📁 Reading conversation data...")
    
    # Read conversation data
    try:
        conversation_data = read_conversation_data('conversation_data.json')
        print(f"✅ Loaded conversation data")
    except Exception as e:
        print(f"❌ Error reading conversation data: {e}")
        return 1
    
    # Extract automation YAML
    print(f"📝 Extracting automation YAML...")
    automation_yaml = extract_automation_yaml(conversation_data)
    
    if not automation_yaml:
        print("❌ Could not find automation YAML in conversation")
        print("💡 Checking pending_preview...")
        # Try pending_preview
        # This would need to be retrieved from the conversation service
        return 1
    
    print(f"✅ Found automation YAML ({len(automation_yaml)} chars)")
    
    # Extract scene entities
    print(f"🎬 Analyzing scene entities...")
    scenes = extract_scene_entities(automation_yaml)
    
    print(f"\n📊 Scene Analysis:")
    print(f"   Created scenes (scene.create): {scenes['created']}")
    print(f"   Activated scenes (scene.turn_on): {scenes['activated']}")
    print(f"   Scene entities referenced: {scenes['entities']}")
    
    # Find mismatches
    print(f"\n🔍 Checking for mismatches...")
    created_scene_ids = set(scenes['created'])
    activated_scene_ids = set([s.replace('scene.', '') for s in scenes['activated']])
    
    missing_scenes = activated_scene_ids - created_scene_ids
    unused_scenes = created_scene_ids - activated_scene_ids
    
    if missing_scenes:
        print(f"❌ ERROR: Scene entities activated but not created:")
        for scene_id in missing_scenes:
            print(f"   - scene.{scene_id} is referenced in scene.turn_on but not created via scene.create")
        print(f"\n💡 This is the root cause of the 'Unknown entity' error!")
    
    if unused_scenes:
        print(f"⚠️  WARNING: Scenes created but not activated:")
        for scene_id in unused_scenes:
            print(f"   - {scene_id} is created but never used")
    
    if not missing_scenes and not unused_scenes:
        print(f"✅ All scenes are properly created and activated")
    
    # Save YAML for further analysis
    with open('automation_yaml_extracted.yaml', 'w', encoding='utf-8') as f:
        f.write(automation_yaml)
    print(f"\n💾 Saved automation YAML to automation_yaml_extracted.yaml")
    
    return 0 if not missing_scenes else 1

if __name__ == '__main__':
    sys.exit(main())
