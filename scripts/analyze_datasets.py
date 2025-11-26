#!/usr/bin/env python3
"""Analyze home-assistant-datasets repository"""

import yaml
from pathlib import Path

base = Path("services/tests/datasets/home-assistant-datasets/datasets")

print("=" * 70)
print("HOME ASSISTANT DATASETS - DATA OVERVIEW")
print("=" * 70)

# Check key datasets
datasets_to_check = {
    "assist": "LLM API evaluation",
    "assist-mini": "Mini LLM evaluation",
    "automations": "Automation generation tasks",
    "devices-v2": "Device definitions (v2)",
    "devices-v3": "Device definitions (v3)",
    "device-actions-v2-collect": "Device action examples",
}

for name, desc in datasets_to_check.items():
    dataset_path = base / name
    if not dataset_path.exists():
        continue
    
    card = dataset_path / "dataset_card.yaml"
    count = "N/A"
    if card.exists():
        data = yaml.safe_load(open(card))
        count = data.get("count", "N/A")
    
    # Count files
    files = list(dataset_path.rglob("*"))
    files = [f for f in files if f.is_file()]
    total_size = sum(f.stat().st_size for f in files)
    
    # Count homes if applicable
    homes = list(dataset_path.glob("home*.yaml"))
    homes_count = len(homes) if homes else 0
    
    print(f"\n{name}:")
    print(f"  Description: {desc}")
    print(f"  Count (from card): {count}")
    print(f"  Files: {len(files)}")
    print(f"  Size: {total_size / 1024:.2f} KB")
    if homes_count > 0:
        print(f"  Synthetic Homes: {homes_count}")
        
        # Sample a home to count devices
        if homes:
            try:
                sample = yaml.safe_load(open(homes[0]))
                if "devices" in sample:
                    if isinstance(sample["devices"], dict):
                        devices = sum(
                            len(area_devices) 
                            for area_devices in sample["devices"].values() 
                            if isinstance(area_devices, list)
                        )
                    else:
                        devices = len(sample["devices"])
                    print(f"  Sample home devices: ~{devices}")
                if "areas" in sample:
                    print(f"  Sample home areas: {len(sample['areas'])}")
            except Exception as e:
                pass

print("\n" + "=" * 70)
print("SYNTHETIC EVENT GENERATION CAPACITY")
print("=" * 70)
print("""
From the device definitions, you can generate:
  • Unlimited synthetic events (days/weeks/months of history)
  • Configurable density: 10-1000+ events per day
  • Realistic patterns: time-of-day, co-occurrence, sequences
  • Multiple homes = diverse testing scenarios

Example: 1 home × 30 days × 100 events/day = 3,000 events
        10 homes × 90 days × 50 events/day = 45,000 events
""")

