#!/usr/bin/env python3
"""
Verify Synergies Fix and Execute Next Steps

This script:
1. Checks current synergy count in database
2. Verifies API endpoint is working
3. Provides instructions to trigger detection if needed
"""

import asyncio
import sys
import sqlite3
from pathlib import Path
from typing import Optional

# Try to find database
def find_database() -> Optional[Path]:
    """Find the ai_automation.db database file."""
    possible_paths = [
        Path(__file__).parent.parent / "services" / "ai-automation-service" / "data" / "ai_automation.db",
        Path(__file__).parent.parent / "data" / "ai_automation.db",
        Path("/app/data/ai_automation.db"),  # Docker path
        Path("./ai_automation.db"),
    ]
    
    for path in possible_paths:
        if path.exists():
            return path
    return None

def check_database_synergies(db_path: Path) -> dict:
    """Check synergy count and stats from database."""
    print("\n" + "=" * 70)
    print("STEP 1: Checking Database")
    print("=" * 70)
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='synergy_opportunities'")
        if not cursor.fetchone():
            print("❌ synergy_opportunities table does not exist!")
            print("   Run database migrations: alembic upgrade head")
            conn.close()
            return {"exists": False, "count": 0}
        
        # Get total count
        cursor.execute("SELECT COUNT(*) FROM synergy_opportunities")
        total = cursor.fetchone()[0]
        
        # Get stats
        cursor.execute("SELECT synergy_type, COUNT(*) FROM synergy_opportunities GROUP BY synergy_type")
        by_type = dict(cursor.fetchall())
        
        cursor.execute("SELECT complexity, COUNT(*) FROM synergy_opportunities GROUP BY complexity")
        by_complexity = dict(cursor.fetchall())
        
        cursor.execute("SELECT AVG(impact_score) FROM synergy_opportunities")
        avg_impact = cursor.fetchone()[0] or 0.0
        
        cursor.execute("SELECT COUNT(*) FROM synergy_opportunities WHERE validated_by_patterns = 1")
        validated = cursor.fetchone()[0]
        
        conn.close()
        
        print(f"✅ Database found: {db_path}")
        print(f"✅ Total Synergies: {total}")
        print(f"   - By Type: {by_type}")
        print(f"   - By Complexity: {by_complexity}")
        print(f"   - Avg Impact: {avg_impact:.2%}" if avg_impact else "   - Avg Impact: 0%")
        print(f"   - Pattern Validated: {validated}")
        
        return {
            "exists": True,
            "count": total,
            "by_type": by_type,
            "by_complexity": by_complexity,
            "avg_impact": avg_impact,
            "validated": validated
        }
        
    except Exception as e:
        print(f"❌ Error checking database: {e}")
        import traceback
        traceback.print_exc()
        return {"exists": False, "count": 0, "error": str(e)}

async def check_api_endpoint(base_url: str = "http://localhost:8005") -> dict:
    """Check if API endpoint is accessible."""
    print("\n" + "=" * 70)
    print("STEP 2: Checking API Endpoint")
    print("=" * 70)
    
    try:
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            # Check stats endpoint
            stats_url = f"{base_url}/api/synergies/stats"
            print(f"📡 Checking: {stats_url}")
            
            try:
                async with session.get(stats_url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        data = await response.json()
                        stats = data.get("data", data)
                        
                        print(f"✅ API is accessible")
                        print(f"   - Total Synergies: {stats.get('total_synergies', 0)}")
                        print(f"   - By Type: {stats.get('by_type', {})}")
                        print(f"   - Avg Impact: {stats.get('avg_impact_score', 0):.2%}" if stats.get('avg_impact_score') else "   - Avg Impact: 0%")
                        
                        return {
                            "accessible": True,
                            "stats": stats,
                            "status": response.status
                        }
                    else:
                        print(f"⚠️  API returned status {response.status}")
                        text = await response.text()
                        print(f"   Response: {text[:200]}")
                        return {"accessible": False, "status": response.status, "error": text[:200]}
                        
            except asyncio.TimeoutError:
                print(f"❌ API request timed out")
                print(f"   Is the service running at {base_url}?")
                return {"accessible": False, "error": "timeout"}
            except aiohttp.ClientError as e:
                print(f"❌ API connection error: {e}")
                print(f"   Is the service running at {base_url}?")
                return {"accessible": False, "error": str(e)}
                
    except ImportError:
        print("⚠️  aiohttp not available, skipping API check")
        print("   Install with: pip install aiohttp")
        return {"accessible": None, "error": "aiohttp not installed"}
    except Exception as e:
        print(f"❌ Error checking API: {e}")
        import traceback
        traceback.print_exc()
        return {"accessible": False, "error": str(e)}

def print_next_steps(db_result: dict, api_result: dict):
    """Print next steps based on results."""
    print("\n" + "=" * 70)
    print("NEXT STEPS")
    print("=" * 70)
    
    db_count = db_result.get("count", 0)
    api_accessible = api_result.get("accessible")
    
    if db_count == 0:
        print("\n🔍 ISSUE: No synergies found in database")
        print("\nTo populate synergies, you have two options:")
        print("\n1. Run Daily Analysis (Automatic):")
        print("   - The daily analysis scheduler should run automatically")
        print("   - Check logs: docker logs ai-automation-service")
        print("   - Or trigger manually via API (requires admin auth)")
        
        print("\n2. Trigger Detection via API (Manual):")
        print("   POST http://localhost:8005/api/synergies/detect")
        print("   Requires: Admin authentication")
        print("   Example:")
        print("   curl -X POST 'http://localhost:8005/api/synergies/detect?use_patterns=true' \\")
        print("        -H 'Authorization: Bearer YOUR_TOKEN'")
        
        print("\n3. Check Service Status:")
        print("   - Ensure ai-automation-service is running")
        print("   - Check: docker ps | grep ai-automation")
        print("   - Check logs: docker logs ai-automation-service")
        
    elif db_count > 0 and api_accessible is False:
        print("\n⚠️  ISSUE: Database has synergies but API is not accessible")
        print(f"   - Database has {db_count} synergies")
        print(f"   - But API endpoint is not responding")
        print("\nActions:")
        print("   1. Restart ai-automation-service:")
        print("      docker restart ai-automation-service")
        print("   2. Check service logs:")
        print("      docker logs ai-automation-service")
        print("   3. Verify service is running:")
        print("      docker ps | grep ai-automation")
        
    elif db_count > 0 and api_accessible is True:
        api_count = api_result.get("stats", {}).get("total_synergies", 0)
        if api_count == db_count:
            print("\n✅ SUCCESS: Everything is working correctly!")
            print(f"   - Database: {db_count} synergies")
            print(f"   - API: {api_count} synergies")
            print("\nThe frontend fix should now display the correct count.")
            print("Refresh the Synergies page to see the updated total.")
        else:
            print("\n⚠️  MISMATCH: Database and API counts don't match")
            print(f"   - Database: {db_count} synergies")
            print(f"   - API: {api_count} synergies")
            print("\nActions:")
            print("   1. Restart ai-automation-service to refresh API cache")
            print("      docker restart ai-automation-service")
    
    print("\n" + "=" * 70)
    print("VERIFICATION COMPLETE")
    print("=" * 70)

async def main():
    """Main execution."""
    print("=" * 70)
    print("SYNERGIES FIX VERIFICATION")
    print("=" * 70)
    print("\nThis script verifies:")
    print("  1. Database has synergies")
    print("  2. API endpoint is accessible")
    print("  3. Provides next steps if issues found")
    
    # Step 1: Check database
    db_path = find_database()
    if not db_path:
        print("\n❌ Could not find ai_automation.db database")
        print("   Searched in:")
        print("   - services/ai-automation-service/data/")
        print("   - data/")
        print("   - /app/data/ (Docker)")
        print("   - ./ (current directory)")
        print("\nIf using Docker, run this script inside the container:")
        print("   docker exec -it ai-automation-service python scripts/verify_synergies_fix.py")
        sys.exit(1)
    
    db_result = check_database_synergies(db_path)
    
    # Step 2: Check API
    api_result = await check_api_endpoint()
    
    # Step 3: Print next steps
    print_next_steps(db_result, api_result)

if __name__ == "__main__":
    asyncio.run(main())

