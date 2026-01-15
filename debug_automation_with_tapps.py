"""
Debug automation error using TappsCodingAgents debugger
"""

import json
import sys
import os

# Fix Windows encoding
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

# Read automation data (handle BOM)
with open('automation_from_ha.json', 'r', encoding='utf-8-sig') as f:
    automation = json.load(f)

# Find scene.create and scene.turn_on actions
print("[ANALYSIS] Analyzing automation scene entities...")
print()

scene_create_action = None
scene_turn_on_action = None

for action in automation.get('actions', []):
    if action.get('action') == 'scene.create':
        scene_create_action = action
        print(f"[FOUND] scene.create action:")
        print(f"  scene_id: {action.get('data', {}).get('scene_id')}")
        print(f"  snapshot_entities: {action.get('data', {}).get('snapshot_entities')}")
    elif action.get('action') == 'scene.turn_on':
        scene_turn_on_action = action
        print(f"[FOUND] scene.turn_on action:")
        print(f"  entity_id: {action.get('target', {}).get('entity_id')}")

print()

# Analyze the issue
if scene_create_action and scene_turn_on_action:
    scene_id = scene_create_action.get('data', {}).get('scene_id')
    entity_id = scene_turn_on_action.get('target', {}).get('entity_id')
    
    print("[ROOT CAUSE ANALYSIS]")
    print(f"Scene created with scene_id: '{scene_id}'")
    print(f"Scene activated with entity_id: '{entity_id}'")
    print()
    
    # Check if they match
    expected_entity_id = f"scene.{scene_id}"
    if entity_id == expected_entity_id:
        print("[OK] Scene ID matches entity ID format")
        print(f"   scene.create uses: {scene_id}")
        print(f"   scene.turn_on uses: {entity_id} (correct format)")
        print()
        print("[ISSUE] The scene entity doesn't exist until the automation runs!")
        print()
        print("[EXPLANATION]")
        print("  - scene.create creates a scene dynamically when the automation runs")
        print("  - The scene entity 'scene.{scene_id}' doesn't exist until scene.create executes")
        print("  - Home Assistant UI validates entities when you open the editor")
        print("  - Since the scene doesn't exist yet, it shows 'Unknown entity'")
        print()
        print("[WHY NO ERROR DURING CREATION]")
        print("  Home Assistant API doesn't validate scene entities during automation creation")
        print("  because scenes can be created dynamically. Validation only happens at runtime.")
        print()
        print("[SOLUTION]")
        print("  1. The automation is actually correct - the scene will exist at runtime")
        print("  2. To fix the UI error, either:")
        print("     a. Create the scene manually before the automation runs")
        print("     b. Use a different pattern that doesn't require dynamic scene creation")
        print("     c. Ignore the UI warning (it's a false positive)")
    else:
        print(f"[ERROR] Scene ID mismatch!")
        print(f"   Expected entity_id: scene.{scene_id}")
        print(f"   Actual entity_id: {entity_id}")
        print()
        print("[ROOT CAUSE] This is the actual bug - the scene entity ID doesn't match!")
elif scene_create_action:
    print("[WARNING] Found scene.create but no scene.turn_on action")
elif scene_turn_on_action:
    print("[ERROR] Found scene.turn_on but no scene.create action!")
    print("  The scene entity is referenced but never created.")
else:
    print("[INFO] No scene actions found in automation")
