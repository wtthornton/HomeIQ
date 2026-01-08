#!/usr/bin/env python3
"""Test synergy router blueprint import."""

import sys
sys.path.insert(0, '/app')

try:
    from src.api.synergy_router import BLUEPRINT_ENGINE_AVAILABLE, blueprint_router
    print(f"BLUEPRINT_ENGINE_AVAILABLE: {BLUEPRINT_ENGINE_AVAILABLE}")
    print(f"blueprint_router: {blueprint_router}")
    if BLUEPRINT_ENGINE_AVAILABLE:
        print("✓ Blueprint engine is available")
    else:
        print("✗ Blueprint engine is NOT available")
        # Try to import manually to see the error
        try:
            from src.blueprint_opportunity.opportunity_engine import BlueprintOpportunityEngine
            print("  But manual import works - this is strange!")
        except Exception as e:
            print(f"  Manual import also fails: {e}")
            import traceback
            traceback.print_exc()
    sys.exit(0)
except Exception as e:
    import traceback
    print("✗ Import failed:")
    traceback.print_exc()
    sys.exit(1)
