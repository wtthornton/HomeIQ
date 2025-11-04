"""
Diagnostic script to check why nightly suggestions aren't being created or displayed.
This script checks:
1. Scheduler status and next run time
2. Recent suggestions in database
3. Suggestion status distribution
4. Recent job execution history
5. API endpoint availability

Usage:
    python implementation/analysis/diagnose_nightly_suggestions.py
"""

import asyncio
import sys
import requests
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Dict, Any

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    # Try different import paths
    import sys
    from pathlib import Path
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))
    sys.path.insert(0, str(project_root / "services" / "ai-automation-service"))
    
    from src.database.models import get_db_session
    from src.database.crud import get_suggestions
    from sqlalchemy import select
    from src.database.models import Suggestion
    DB_AVAILABLE = True
except ImportError as e:
    print(f"WARNING: Database imports not available: {e}")
    print("   Will skip database checks, but will check API endpoints")
    DB_AVAILABLE = False

# API base URL - Check both ports (8018 internal, 8024 external)
# Try 8024 first (Docker port mapping), fallback to 8018
API_BASE_URL = "http://localhost:8024/api"

def check_api_endpoint(endpoint: str) -> Dict[str, Any]:
    """Check if an API endpoint is available"""
    try:
        url = f"{API_BASE_URL}/{endpoint}"
        response = requests.get(url, timeout=5)
        data = None
        if response.status_code == 200:
            try:
                data = response.json()
            except:
                data = response.text
        return {
            'available': True,
            'status_code': response.status_code,
            'data': data,
            'error': None
        }
    except requests.exceptions.ConnectionError:
        return {
            'available': False,
            'status_code': None,
            'data': None,
            'error': 'Connection refused - service may not be running'
        }
    except requests.exceptions.Timeout:
        return {
            'available': False,
            'status_code': None,
            'data': None,
            'error': 'Request timeout'
        }
    except Exception as e:
        return {
            'available': False,
            'status_code': None,
            'data': None,
            'error': str(e)
        }

def check_scheduler_status():
    """Check scheduler status via API"""
    print("\n" + "=" * 80)
    print("SCHEDULER STATUS")
    print("=" * 80)
    
    result = check_api_endpoint("analysis/schedule")
    
    if not result['available']:
        print(f"ERROR: API endpoint not available: {result['error']}")
        print(f"   URL: {API_BASE_URL}/analysis/schedule")
        print(f"   -> The service may not be running on port 8018")
        return None
    
    if result['status_code'] == 404:
        print(f"ERROR: Endpoint not found (404)")
        print(f"   URL: {API_BASE_URL}/analysis/schedule")
        print(f"   -> The endpoint may have changed or router not registered")
        return None
    
    if result['status_code'] != 200:
        print(f"WARNING: API returned status {result['status_code']}")
        return None
    
    data = result['data']
    if not isinstance(data, dict):
        print(f"WARNING: Unexpected response format: {type(data)}")
        return None
    
    print(f"OK: Scheduler API is accessible")
    print(f"\nSchedule Information:")
    print(f"   - Cron Schedule: {data.get('schedule', 'N/A')}")
    print(f"   - Next Run: {data.get('next_run', 'N/A')}")
    print(f"   - Currently Running: {data.get('is_running', False)}")
    
    recent_jobs = data.get('recent_jobs', [])
    if recent_jobs:
        print(f"\nRecent Job History ({len(recent_jobs)} jobs):")
        for i, job in enumerate(recent_jobs[:5], 1):  # Show last 5
            status = job.get('status', 'unknown')
            start_time = job.get('start_time', 'N/A')
            duration = job.get('duration_seconds', 0)
            suggestions = job.get('suggestions_generated', 0)
            
            status_icon = "[OK]" if status == "success" else "[FAIL]" if status == "failed" else "[WARN]"
            print(f"   {i}. {status_icon} {status.upper()} - {start_time}")
            print(f"      Duration: {duration:.1f}s, Suggestions: {suggestions}")
            
            if status == "failed":
                error = job.get('error', 'Unknown error')
                print(f"      Error: {error}")
    else:
        print(f"\nWARNING: No recent job history found")
        print(f"   -> The scheduler may not have run yet")
    
    return data

def check_suggestions_api():
    """Check suggestions API endpoint"""
    print("\n" + "=" * 80)
    print("SUGGESTIONS API")
    print("=" * 80)
    
    result = check_api_endpoint("suggestions/list?limit=100")
    
    if not result['available']:
        print(f"ERROR: API endpoint not available: {result['error']}")
        return None
    
    if result['status_code'] != 200:
        print(f"WARNING: API returned status {result['status_code']}")
        if result['data']:
            print(f"   Error: {result['data']}")
        return None
    
    data = result['data']
    if not isinstance(data, dict):
        print(f"WARNING: Unexpected response format: {type(data)}")
        print(f"   Response: {data}")
        return None
    
    suggestions = data.get('data', {}).get('suggestions', [])
    count = data.get('data', {}).get('count', len(suggestions))
    
    print(f"OK: Suggestions API is accessible")
    print(f"   Total suggestions returned: {count}")
    
    if suggestions:
        # Group by status
        status_counts = {}
        for s in suggestions:
            status = s.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print(f"\nStatus Distribution:")
        for status, count in sorted(status_counts.items()):
            print(f"   - {status}: {count}")
        
        # Show recent suggestions
        print(f"\nMost Recent Suggestions:")
        for s in suggestions[:5]:
            created = s.get('created_at', 'N/A')
            status = s.get('status', 'N/A')
            title = s.get('title', 'N/A')[:60]
            print(f"   - [{status}] {title}...")
            print(f"     Created: {created}")
    else:
        print(f"\nWARNING: No suggestions found in API response")
    
    return suggestions

async def check_database_suggestions():
    """Check suggestions directly in database"""
    if not DB_AVAILABLE:
        print("\nWARNING: Skipping database checks (imports not available)")
        return
    
    print("\n" + "=" * 80)
    print("DATABASE SUGGESTIONS")
    print("=" * 80)
    
    try:
        async with get_db_session() as db:
            # Get all suggestions
            all_suggestions = await get_suggestions(db, status=None, limit=100)
            print(f"OK: Database connection successful")
            print(f"   Total suggestions in database: {len(all_suggestions)}")
            
            if not all_suggestions:
                print(f"\nWARNING: No suggestions found in database")
                print(f"   -> This suggests the nightly job has never run successfully")
                return
            
            # Group by status
            status_counts = {}
            for s in all_suggestions:
                status = s.status or 'null'
                status_counts[status] = status_counts.get(status, 0) + 1
            
            print(f"\nStatus Breakdown:")
            for status, count in sorted(status_counts.items()):
                print(f"   - {status}: {count}")
            
            # Get recent suggestions (last 7 days)
            seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
            recent_query = select(Suggestion).where(
                Suggestion.created_at >= seven_days_ago
            ).order_by(Suggestion.created_at.desc())
            
            from sqlalchemy.ext.asyncio import AsyncSession
            result = await db.execute(recent_query)
            recent_suggestions = result.scalars().all()
            
            print(f"\nRecent Suggestions (Last 7 Days): {len(recent_suggestions)}")
            
            if recent_suggestions:
                print(f"\nRecent Suggestion Details:")
                for s in recent_suggestions[:10]:
                    print(f"   - ID: {s.id}, Status: {s.status}, Created: {s.created_at}")
                    print(f"     Title: {s.title[:60]}...")
                    print(f"     Confidence: {s.confidence:.2f}")
                    if s.pattern_id:
                        print(f"     Pattern ID: {s.pattern_id} (from nightly job)")
            else:
                print(f"\nWARNING: No suggestions created in the last 7 days!")
                print(f"   -> The nightly job may not be running or not creating suggestions")
            
            # Check suggestions created today
            today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            today_query = select(Suggestion).where(
                Suggestion.created_at >= today_start
            ).order_by(Suggestion.created_at.desc())
            
            result = await db.execute(today_query)
            today_suggestions = result.scalars().all()
            
            print(f"\nSuggestions Created Today: {len(today_suggestions)}")
            
            if today_suggestions:
                print(f"\nToday's Suggestions:")
                for s in today_suggestions:
                    print(f"   - ID: {s.id}, Status: {s.status}, Created: {s.created_at}")
                    print(f"     Title: {s.title[:60]}...")
            else:
                print(f"\nWARNING: No suggestions created today!")
                print(f"   -> The nightly job may not have run today")
            
            # Check for suggestions with pattern_id (from nightly job)
            pattern_query = select(Suggestion).where(
                Suggestion.pattern_id.isnot(None)
            ).order_by(Suggestion.created_at.desc())
            
            result = await db.execute(pattern_query)
            pattern_suggestions = result.scalars().all()
            
            print(f"\nSuggestions with pattern_id (from nightly job): {len(pattern_suggestions)}")
            
            if pattern_suggestions:
                print(f"\nPattern-Based Suggestions:")
                for s in pattern_suggestions[:5]:
                    print(f"   - ID: {s.id}, Pattern ID: {s.pattern_id}, Status: {s.status}")
                    print(f"     Created: {s.created_at}")
                    print(f"     Title: {s.title[:60]}...")
            else:
                print(f"\nWARNING: No pattern-based suggestions found!")
                print(f"   -> The nightly job may not be creating suggestions from patterns")
            
            # Check draft suggestions specifically
            draft_query = select(Suggestion).where(
                Suggestion.status == 'draft'
            ).order_by(Suggestion.created_at.desc())
            
            result = await db.execute(draft_query)
            draft_suggestions = result.scalars().all()
            
            print(f"\nDraft Suggestions (what frontend shows): {len(draft_suggestions)}")
            
            if draft_suggestions:
                recent_drafts = [s for s in draft_suggestions if s.created_at >= seven_days_ago]
                print(f"   Recent drafts (last 7 days): {len(recent_drafts)}")
                
                if recent_drafts:
                    print(f"\nRecent Draft Suggestions:")
                    for s in recent_drafts[:5]:
                        print(f"   - ID: {s.id}, Created: {s.created_at}")
                        print(f"     Title: {s.title[:60]}...")
                        print(f"     Pattern ID: {s.pattern_id or 'None (manual)'}")
            
    except Exception as e:
        print(f"ERROR: Database check failed: {e}")
        import traceback
        traceback.print_exc()

def print_recommendations():
    """Print recommendations based on findings"""
    print("\n" + "=" * 80)
    print("RECOMMENDATIONS")
    print("=" * 80)
    
    print("\n1. If scheduler is not running:")
    print("   - Check service logs for startup errors")
    print("   - Verify the service is running: docker ps | grep ai-automation-service")
    print("   - Check if scheduler started: Look for 'Scheduler started' in logs")
    
    print("\n2. If scheduler is running but no suggestions:")
    print("   - Check if patterns are being detected (Phase 3 logs)")
    print("   - Verify event data is available (Phase 2)")
    print("   - Check for OpenAI API errors (Phase 5)")
    print("   - Manually trigger job: POST http://localhost:8018/api/analysis/trigger")
    
    print("\n3. If suggestions exist but not showing in frontend:")
    print("   - Check frontend API connection (browser console)")
    print("   - Verify status filter (should include 'draft')")
    print("   - Check API response format matches frontend expectations")
    
    print("\n4. To manually trigger the nightly job:")
    print("   curl -X POST http://localhost:8018/api/analysis/trigger")
    print("   or use the API docs at: http://localhost:8018/docs")
    
    print("\n5. To check service logs:")
    print("   docker logs ai-automation-service --tail 100")
    print("   or check local logs if running directly")

async def main():
    """Run all diagnostic checks"""
    print("=" * 80)
    print("NIGHTLY JOB SUGGESTIONS DIAGNOSTIC")
    print("=" * 80)
    print(f"API Base URL: {API_BASE_URL}")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    
    # Check scheduler status
    scheduler_data = check_scheduler_status()
    
    # Check suggestions API
    api_suggestions = check_suggestions_api()
    
    # Check database
    await check_database_suggestions()
    
    # Print recommendations
    print_recommendations()
    
    print("\n" + "=" * 80)
    print("Diagnostic complete!")
    print("=" * 80)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nWARNING: Diagnostic interrupted by user")
    except Exception as e:
        print(f"\n\nERROR: Diagnostic failed: {e}")
        import traceback
        traceback.print_exc()

