#!/usr/bin/env python3
"""
HACS Diagnostic Script

Checks if HACS and Team Tracker are installed in Home Assistant.
Provides installation guidance if not installed.

Note: HACS cannot be installed via HA API - it requires manual installation.

Usage:
    python scripts/check-hacs-status.py

Environment Variables:
    HA_HTTP_URL: Home Assistant URL (default: http://192.168.1.86:8123)
    HA_TOKEN: Long-lived access token from Home Assistant
"""

import asyncio
import os
import sys
from datetime import datetime

# Fix Unicode support for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

try:
    import aiohttp
except ImportError:
    print("ERROR: aiohttp not installed. Run: pip install aiohttp")
    sys.exit(1)


class HACSDiagnostic:
    """Diagnostic tool for checking HACS and Team Tracker status"""

    def __init__(self):
        self.ha_url = os.getenv("HA_HTTP_URL", "http://192.168.1.86:8123")
        self.ha_token = os.getenv("HA_TOKEN", "")
        self.timeout = aiohttp.ClientTimeout(total=10)

    async def check_hacs(self) -> dict:
        """
        Check if HACS is installed

        Returns:
            Dict with status information
        """
        if not self.ha_token:
            return {
                "installed": False,
                "error": "HA_TOKEN not configured",
                "recommendation": "Set HA_TOKEN environment variable",
            }

        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.ha_token}",
                    "Content-Type": "application/json",
                }

                # Check config entries
                async with session.get(
                    f"{self.ha_url}/api/config/config_entries",
                    headers=headers,
                    timeout=self.timeout,
                ) as response:
                    if response.status != 200:
                        return {
                            "installed": False,
                            "error": f"Cannot access HA API: HTTP {response.status}",
                            "recommendation": "Check HA connectivity and token permissions",
                        }

                    config_entries = await response.json()
                    hacs_entry = None
                    for entry in config_entries:
                        entry_domain = entry.get("domain", "").lower()
                        if entry_domain == "hacs":
                            hacs_entry = entry
                            break

                # Check for HACS entities
                async with session.get(
                    f"{self.ha_url}/api/states",
                    headers=headers,
                    timeout=self.timeout,
                ) as response:
                    hacs_entities = []
                    if response.status == 200:
                        states = await response.json()
                        hacs_entities = [
                            s for s in states
                            if s["entity_id"].startswith(("sensor.hacs", "binary_sensor.hacs"))
                        ]

                is_installed = hacs_entry is not None or len(hacs_entities) > 0

                return {
                    "installed": is_installed,
                    "hacs_entry": hacs_entry,
                    "hacs_entities_count": len(hacs_entities),
                    "hacs_entities": [e["entity_id"] for e in hacs_entities[:5]],  # Show first 5
                    "installed_via": "config_entry" if hacs_entry else ("entities" if hacs_entities else "neither"),
                }

        except Exception as e:
            return {
                "installed": False,
                "error": str(e),
                "error_type": type(e).__name__,
            }

    async def check_team_tracker(self) -> dict:
        """Check if Team Tracker is installed"""
        if not self.ha_token:
            return {"installed": False, "error": "HA_TOKEN not configured"}

        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.ha_token}",
                    "Content-Type": "application/json",
                }

                # Check config entries
                async with session.get(
                    f"{self.ha_url}/api/config/config_entries",
                    headers=headers,
                    timeout=self.timeout,
                ) as response:
                    if response.status != 200:
                        return {"installed": False, "error": f"Cannot access HA API: HTTP {response.status}"}

                    config_entries = await response.json()
                    tt_entry = None
                    for entry in config_entries:
                        if "team_tracker" in entry.get("domain", "").lower():
                            tt_entry = entry
                            break

                # Check for Team Tracker sensors
                async with session.get(
                    f"{self.ha_url}/api/states",
                    headers=headers,
                    timeout=self.timeout,
                ) as response:
                    tt_sensors = []
                    if response.status == 200:
                        states = await response.json()
                        tt_sensors = [
                            s for s in states
                            if "team_tracker" in s["entity_id"].lower()
                        ]

                is_installed = tt_entry is not None or len(tt_sensors) > 0

                return {
                    "installed": is_installed,
                    "config_entry": tt_entry,
                    "sensors_count": len(tt_sensors),
                    "sensor_examples": [s["entity_id"] for s in tt_sensors[:5]] if tt_sensors else [],
                }

        except Exception as e:
            return {
                "installed": False,
                "error": str(e),
                "error_type": type(e).__name__,
            }

    def print_installation_guide(self):
        """Print HACS installation instructions"""
        print("\n" + "="*80)
        print("HACS INSTALLATION GUIDE")
        print("="*80)
        print("\nHACS cannot be installed via API. Follow these manual steps:\n")

        print("STEP 1: Access Home Assistant Terminal")
        print("  - Install 'Terminal & SSH' add-on in Home Assistant")
        print("  - Or use SSH to access your HA instance\n")

        print("STEP 2: Download and Install HACS")
        print("  cd /config")
        print("  wget -O - https://get.hacs.xyz | bash -\n")

        print("STEP 3: Restart Home Assistant")
        print("  Settings > System > Restart Home Assistant\n")

        print("STEP 4: Configure HACS")
        print("  Settings > Devices & Services > Add Integration > Search 'HACS'\n")

        print("STEP 5: Install Team Tracker")
        print("  1. Open HACS in Home Assistant sidebar")
        print("  2. Click 'Integrations'")
        print("  3. Click '+ Explore & Download Repositories'")
        print("  4. Search 'Team Tracker'")
        print("  5. Click 'Download'")
        print("  6. Restart Home Assistant")
        print("  7. Add Team Tracker integration and configure your teams\n")

        print("Official Documentation:")
        print("  HACS: https://hacs.xyz/docs/setup/download")
        print("  Team Tracker: https://github.com/vasquatch2/team_tracker")
        print("\n" + "="*80)

    async def run(self):
        """Run diagnostics"""
        print("\n" + "="*80)
        print("HACS DIAGNOSTIC CHECK")
        print("="*80)
        print(f"\nChecking Home Assistant at: {self.ha_url}")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        if not self.ha_token:
            print("\n⚠️  WARNING: HA_TOKEN not set in environment")
            print("Set it with: export HA_TOKEN='your_long_lived_token'")
            self.print_installation_guide()
            return

        print(f"Token: {'*' * (len(self.ha_token) - 4)}{self.ha_token[-4:]}")

        # Check HACS
        print("\n" + "-"*80)
        print("Checking HACS Installation...")
        print("-"*80)

        hacs_result = await self.check_hacs()

        if hacs_result.get("error"):
            print(f"❌ ERROR: {hacs_result['error']}")
        elif hacs_result["installed"]:
            print("✅ HACS is installed")
            if hacs_result.get("hacs_entry"):
                print("   Found in config entries")
            if hacs_result.get("hacs_entities_count", 0) > 0:
                print(f"   Found {hacs_result['hacs_entities_count']} primary entities")
                print(f"   Examples: {', '.join(hacs_result['hacs_entities'][:3])}")
            print(f"   Detection method: {hacs_result.get('installed_via', 'unknown')}")
        else:
            print("❌ HACS is NOT installed")
            self.print_installation_guide()

        # Check Team Tracker
        print("\n" + "-"*80)
        print("Checking Team Tracker Installation...")
        print("-"*80)

        tt_result = await self.check_team_tracker()

        if tt_result.get("error"):
            print(f"❌ ERROR: {tt_result['error']}")
        elif tt_result["installed"]:
            print("✅ Team Tracker is installed")
            if tt_result.get("config_entry"):
                print("   Found in config entries")
            if tt_result.get("sensors_count", 0) > 0:
                print(f"   Found {tt_result['sensors_count']} Team Tracker sensors")
                print(f"   Examples: {', '.join(tt_result['sensor_examples'][:3])}")
        else:
            print("❌ Team Tracker is NOT installed")
            if hacs_result.get("installed"):
                print("\n💡 To install Team Tracker:")
                print("  1. Open HACS in Home Assistant")
                print("  2. Click 'Integrations' > '+' > Search 'Team Tracker'")
                print("  3. Download and restart HA")
            else:
                print("\n⚠️  Install HACS first (see guide above)")

        # Summary
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)

        status = "✅ READY" if (hacs_result.get("installed") and tt_result.get("installed")) else "⚠️  ACTION REQUIRED"
        print(f"\nStatus: {status}")

        if hacs_result.get("installed") and tt_result.get("installed"):
            print("\n✨ Your HomeIQ sports feature is ready to use!")
            print("   - HACS: Installed")
            print("   - Team Tracker: Installed")
            print("\nYou can now use the Sports tab in your HomeIQ dashboard.")
        elif hacs_result.get("installed"):
            print("\n📋 Next Steps:")
            print("   - ✅ HACS: Installed")
            print("   - ❌ Team Tracker: Needs installation")
            print("\nInstall Team Tracker via HACS (instructions above)")
        else:
            print("\n📋 Installation Required:")
            print("   - ❌ HACS: Not installed")
            print("   - ❌ Team Tracker: Not installed")
            print("\nFollow the HACS installation guide above")

        print("\n" + "="*80)


async def main():
    """Main entry point"""
    diagnostic = HACSDiagnostic()
    await diagnostic.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        sys.exit(1)

