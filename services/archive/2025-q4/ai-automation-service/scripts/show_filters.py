"""Show what pattern filters are filtering out"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.pattern_detection.pattern_filters import (
    ACTIONABLE_DOMAINS,
    EXCLUDED_DOMAINS,
    EXCLUDED_PREFIXES,
    MIN_CONFIDENCE,
    MIN_OCCURRENCES,
    is_actionable_device,
)

print("=" * 60)
print("PATTERN FILTERING CONFIGURATION")
print("=" * 60)

print("\n=== EXCLUDED DOMAINS (completely filtered) ===")
for domain in EXCLUDED_DOMAINS:
    print(f"  ❌ {domain}")

print("\n=== EXCLUDED PREFIXES (specific patterns filtered) ===")
for prefix in EXCLUDED_PREFIXES:
    print(f"  ❌ {prefix}")

print("\n=== ACTIONABLE DOMAINS (always allowed) ===")
for domain in ACTIONABLE_DOMAINS:
    print(f"  ✅ {domain}")

print("\n=== MINIMUM REQUIREMENTS ===")
print(f"  Minimum occurrences: {MIN_OCCURRENCES}")
print(f"  Minimum confidence: {MIN_CONFIDENCE}")

print("\n=== TEST EXAMPLES ===")
test_devices = [
    'light.bedroom',
    'switch.living_room',
    'media_player.tv',
    'sensor.battery',
    'sensor.dal_team_tracker',
    'sensor.home_assistant_cpu',
    'sensor.slzb_coordinator_temp',
    'image.roborock_map_0',
    'event.backup_automatic',
    'device_tracker.phone',
    'person.bill',
    'binary_sensor.motion',
    'climate.thermostat',
    'fan.ceiling_fan',
]

for device in test_devices:
    result = is_actionable_device(device)
    status = "✅ ALLOWED" if result else "❌ FILTERED"
    print(f"  {device:40} {status}")

print("\n=== CO-OCCURRENCE PATTERN VALIDATION ===")
print("For co-occurrence patterns, BOTH devices must be actionable.")
print("Examples:")
test_co_occurrence = [
    ('light.bedroom', 'switch.living_room', True),
    ('light.bedroom', 'sensor.battery', False),
    ('media_player.tv', 'sensor.dal_team_tracker', False),
    ('light.living_room', 'media_player.tv', True),
]

for device1, device2, expected in test_co_occurrence:
    both_valid = is_actionable_device(device1) and is_actionable_device(device2)
    status = "✅ VALID" if both_valid == expected else "⚠️  UNEXPECTED"
    print(f"  {device1} + {device2}")
    print(f"    → {status} (both actionable: {both_valid})")

