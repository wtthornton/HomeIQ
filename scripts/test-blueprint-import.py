#!/usr/bin/env python3
"""Test blueprint opportunity engine import."""

import sys
sys.path.insert(0, '/app')

try:
    from src.blueprint_opportunity.opportunity_engine import BlueprintOpportunityEngine
    print("✓ Import successful")
    sys.exit(0)
except Exception as e:
    import traceback
    print("✗ Import failed:")
    traceback.print_exc()
    sys.exit(1)
