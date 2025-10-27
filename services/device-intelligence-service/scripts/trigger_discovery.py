"""Script to trigger discovery via API."""
import asyncio
import httpx

async def trigger_discovery():
    async with httpx.AsyncClient(timeout=120.0) as client:
        print("Triggering discovery endpoint...")
        try:
            response = await client.post('http://localhost:8019/api/discovery/refresh')
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(trigger_discovery())

