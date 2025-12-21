#!/usr/bin/env python3
"""
Store Context7 API key in encrypted storage.

This script stores the API key securely in encrypted storage
so it's automatically available to all agents.
"""

import sys
from pathlib import Path

# Add TappsCodingAgents to path
project_root = Path(__file__).parent
tapps_path = project_root / "TappsCodingAgents"
if tapps_path.exists():
    sys.path.insert(0, str(tapps_path))

try:
    from tapps_agents.context7.security import APIKeyManager
except ImportError as e:
    print(f"Error importing APIKeyManager: {e}")
    print("Trying alternative import...")
    try:
        # Try alternative location
        sys.path.insert(0, str(tapps_path / "tapps_agents"))
        from context7.security import APIKeyManager
    except ImportError:
        print("Could not import APIKeyManager")
        print("API key will need to be set as environment variable")
        sys.exit(1)


def store_api_key():
    """Store Context7 API key in encrypted storage."""
    api_key = "ctx7sk-a2043cb5-8c75-46cc-8ee1-0d137fdc56cc"
    
    print("=" * 70)
    print("  Context7 API Key Storage")
    print("=" * 70)
    print()
    
    try:
        key_manager = APIKeyManager()
        
        # Store encrypted API key
        key_manager.store_api_key("context7", api_key, encrypt=True)
        
        print("[OK] API key stored in encrypted storage")
        print(f"[i] Location: .tapps-agents/api-keys.encrypted")
        print()
        print("[i] The key will be automatically loaded by agents")
        print("[i] No need to set environment variable")
        print()
        
        # Verify it was stored
        loaded_key = key_manager.load_api_key("context7")
        if loaded_key == api_key:
            print("[OK] Verification: Key loaded successfully")
            return True
        else:
            print("[!] Warning: Key verification failed")
            return False
            
    except Exception as e:
        print(f"[X] Error storing API key: {e}")
        print()
        print("[!] Alternative: Set as environment variable")
        print("   PowerShell: $env:CONTEXT7_API_KEY='ctx7sk-a2043cb5-8c75-46cc-8ee1-0d137fdc56cc'")
        return False


if __name__ == "__main__":
    result = store_api_key()
    sys.exit(0 if result else 1)

