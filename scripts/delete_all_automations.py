#!/usr/bin/env python3
"""
Delete all automations in Home Assistant via API.

DISCOVERY (Oct 2025): There IS an API endpoint to delete automations!
Use the 'id' from automation attributes, NOT the entity_id.

Correct: DELETE /api/config/automation/config/{id-from-attributes}
Wrong:   DELETE /api/config/automation/config/{entity_id}
"""
import asyncio

import aiohttp


async def main():
    # Load config
    env_vars = {}
    with open(".env", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                env_vars[key] = value

    url = env_vars.get("HA_HTTP_URL")
    token = env_vars.get("HA_TOKEN")

    print(f"Connecting to {url}...")
    print()

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    async with aiohttp.ClientSession() as session:
        # Get all automations
        async with session.get(f"{url}/api/states", headers=headers) as resp:
            states = await resp.json()
            automations = [s for s in states if s.get("entity_id", "").startswith("automation.")]

        print(f"Found {len(automations)} automations")
        print()

        if not automations:
            print("No automations to delete.")
            return

        # Display what will be deleted
        print("Automations to delete:")
        for auto in automations[:10]:  # Show first 10
            entity_id = auto.get("entity_id")
            attrs = auto.get("attributes", {})
            friendly_name = attrs.get("friendly_name", entity_id)
            auto_id = attrs.get("id")
            print(f"  - {entity_id}: {friendly_name} (id: {auto_id})")
        if len(automations) > 10:
            print(f"  ... and {len(automations) - 10} more")
        print()

        # Confirmation
        confirm = input(f"Type 'DELETE ALL' to delete {len(automations)} automations: ")

        if confirm != "DELETE ALL":
            print("Cancelled.")
            return

        print()
        print("Deleting automations...")
        print()

        # Delete each automation using the 'id' from attributes
        success = 0
        failed = 0

        for auto in automations:
            entity_id = auto.get("entity_id")
            attrs = auto.get("attributes", {})
            friendly_name = attrs.get("friendly_name", entity_id)
            auto_id = attrs.get("id")

            if not auto_id:
                print(f"SKIPPED - {entity_id}: No ID found in attributes")
                failed += 1
                continue

            # Use the ID from attributes
            async with session.delete(f"{url}/api/config/automation/config/{auto_id}",
                                    headers=headers) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    if result.get("result") == "ok":
                        success += 1
                        print(f"OK - Deleted {entity_id}: {friendly_name}")
                    else:
                        failed += 1
                        print(f"FAILED - {entity_id}: Unexpected response")
                else:
                    failed += 1
                    text = await resp.text()
                    print(f"FAILED - {entity_id}: HTTP {resp.status} - {text[:100]}")

        print()
        print("=" * 60)
        print(f"Completed: {success} deleted, {failed} failed out of {len(automations)} total")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

