#!/usr/bin/env python3
"""Quick test to check HA API from container"""
import asyncio
import os

import aiohttp


async def test():
    ha_url = os.getenv("HA_URL", "http://192.168.1.86:8123").rstrip("/")
    ha_token = os.getenv("HA_TOKEN", "")

    print(f"HA URL: {ha_url}")
    print(f"HA Token: {'SET' if ha_token else 'NOT SET'}")

    async with aiohttp.ClientSession() as session:
        headers = {"Authorization": f"Bearer {ha_token}"}
        async with session.get(f"{ha_url}/api/config", headers=headers) as response:
            print(f"Status: {response.status}")
            if response.status == 200:
                data = await response.json()
                print(f"Version: {data.get('version', 'unknown')}")
            else:
                text = await response.text()
                print(f"Error: {text[:200]}")

if __name__ == "__main__":
    asyncio.run(test())

