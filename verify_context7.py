#!/usr/bin/env python3
"""
Verify Context7 integration and KB cache status in tapps-agents.

This script checks:
1. Context7 configuration
2. KB cache directory structure
3. Cache contents and statistics
4. Integration health
"""

import asyncio
import sys
from pathlib import Path

# Fix Windows console encoding
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add TappsCodingAgents to path if needed
project_root = Path(__file__).parent
tapps_path = project_root / "TappsCodingAgents"
if tapps_path.exists():
    sys.path.insert(0, str(tapps_path))

try:
    from tapps_agents.context7.commands import Context7Commands
    from tapps_agents.health.checks.context7_cache import Context7CacheHealthCheck
    from tapps_agents.core.config import load_config
except ImportError as e:
    print(f"❌ Error importing tapps_agents: {e}")
    print(f"   Make sure you're running from the project root")
    print(f"   TappsCodingAgents path: {tapps_path}")
    sys.exit(1)


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_status(key: str, value: any, status: str = "info"):
    """Print a status line with formatting."""
    # Use ASCII-safe icons for Windows compatibility
    icons = {
        "success": "[OK]",
        "warning": "[!]",
        "error": "[X]",
        "info": "[i]",
    }
    icon = icons.get(status, "[*]")
    print(f"{icon} {key}: {value}")


async def verify_context7():
    """Main verification function."""
    print_section("Context7 Integration Verification")
    
    # Check configuration
    print_section("1. Configuration Check")
    try:
        config = load_config()
        if not config.context7:
            print_status("Context7 Config", "Not found", "error")
            return False
        
        if not config.context7.enabled:
            print_status("Context7 Enabled", "False", "error")
            print_status("Action", "Enable Context7 in .tapps-agents/config.yaml", "warning")
            return False
        
        print_status("Context7 Enabled", "True", "success")
        print_status("KB Location", config.context7.knowledge_base.location, "info")
        print_status("Max Cache Size", config.context7.knowledge_base.max_cache_size, "info")
        print_status("Refresh Enabled", config.context7.refresh.enabled, "info")
        
    except Exception as e:
        print_status("Config Load", f"Error: {e}", "error")
        return False
    
    # Initialize Context7Commands
    print_section("2. Context7 Commands Initialization")
    try:
        commands = Context7Commands(project_root=project_root)
        
        if not commands.enabled:
            print_status("Commands Enabled", "False", "error")
            return False
        
        print_status("Commands Enabled", "True", "success")
        print_status("Cache Root", str(commands.cache_structure.cache_root), "info")
        
    except Exception as e:
        print_status("Commands Init", f"Error: {e}", "error")
        return False
    
    # Check cache directory
    print_section("3. Cache Directory Structure")
    cache_root = commands.cache_structure.cache_root
    
    if not cache_root.exists():
        print_status("Cache Directory", f"Not found: {cache_root}", "error")
        print_status("Action", "Cache will be created on first use", "info")
    else:
        print_status("Cache Directory", f"Exists: {cache_root}", "success")
        
        # Check subdirectories
        libraries_dir = cache_root / "libraries"
        topics_dir = cache_root / "topics"
        index_file = cache_root / "index.yaml"
        
        print_status("Libraries Dir", f"Exists: {libraries_dir.exists()}", "info")
        print_status("Topics Dir", f"Exists: {topics_dir.exists()}", "info")
        print_status("Index File", f"Exists: {index_file.exists()}", "info")
        
        # Count libraries if directory exists
        if libraries_dir.exists():
            library_dirs = [d for d in libraries_dir.iterdir() if d.is_dir()]
            print_status("Library Count", len(library_dirs), "info")
            if library_dirs:
                print_status("Libraries", ", ".join([d.name for d in library_dirs[:10]]), "info")
                if len(library_dirs) > 10:
                    print_status("", f"... and {len(library_dirs) - 10} more", "info")
    
    # Check KB status
    print_section("4. KB Cache Status")
    try:
        status_result = await commands.cmd_status()
        
        if not status_result.get("success"):
            error = status_result.get("error", "Unknown error")
            print_status("Status Check", f"Failed: {error}", "error")
            return False
        
        metrics = status_result.get("metrics", {})
        
        print_status("Total Entries", metrics.get("total_entries", 0), 
                    "success" if metrics.get("total_entries", 0) > 0 else "warning")
        print_status("Total Libraries", metrics.get("total_libraries", 0), "info")
        print_status("Cache Hits", metrics.get("cache_hits", 0), "info")
        print_status("Cache Misses", metrics.get("cache_misses", 0), "info")
        print_status("API Calls", metrics.get("api_calls", 0), "info")
        
        hit_rate = metrics.get("hit_rate", 0.0)
        hit_rate_status = "success" if hit_rate >= 70.0 else "warning" if hit_rate > 0 else "error"
        print_status("Hit Rate", f"{hit_rate:.1f}%", hit_rate_status)
        
        cache_size_mb = status_result.get("cache_size_mb", 0.0)
        print_status("Cache Size", f"{cache_size_mb:.2f} MB", "info")
        
        avg_response_time = metrics.get("avg_response_time_ms", 0.0)
        response_status = "success" if avg_response_time < 150.0 else "warning"
        print_status("Avg Response Time", f"{avg_response_time:.1f} ms", response_status)
        
        # Check if cache is populated
        if metrics.get("total_entries", 0) == 0:
            print_status("RAG Status", "NOT POPULATED", "warning")
            print_status("Action", "Cache is empty - needs population", "warning")
        else:
            print_status("RAG Status", "POPULATED", "success")
        
    except Exception as e:
        print_status("Status Check", f"Error: {e}", "error")
        import traceback
        traceback.print_exc()
        return False
    
    # Health check
    print_section("5. Health Check")
    try:
        health_check = Context7CacheHealthCheck(project_root=project_root)
        health_result = health_check.run()
        
        print_status("Health Status", health_result.status.upper(), 
                    "success" if health_result.status == "healthy" else 
                    "warning" if health_result.status == "degraded" else "error")
        print_status("Health Score", f"{health_result.score:.1f}/100", "info")
        print_status("Message", health_result.message, "info")
        
        if health_result.details:
            issues = health_result.details.get("issues", [])
            if issues:
                print_status("Issues Found", len(issues), "warning")
                for issue in issues:
                    print(f"   ⚠️  {issue}")
        
        if health_result.remediation:
            print_status("Remediation", "", "info")
            for rem in health_result.remediation:
                print(f"   -> {rem}")
        
    except Exception as e:
        print_status("Health Check", f"Error: {e}", "error")
        import traceback
        traceback.print_exc()
    
    # Summary
    print_section("Verification Summary")
    
    if metrics.get("total_entries", 0) > 0:
        print_status("Overall Status", "Context7 is WORKING and RAG is POPULATED", "success")
        print_status("Cache Entries", metrics.get("total_entries", 0), "success")
        print_status("Hit Rate", f"{hit_rate:.1f}%", "success" if hit_rate >= 70.0 else "warning")
    else:
        print_status("Overall Status", "Context7 is WORKING but RAG is EMPTY", "warning")
        print_status("Action Required", "Populate cache by using Context7 commands", "warning")
        print_status("Example", "*context7-docs fastapi routing", "info")
    
    return True


if __name__ == "__main__":
    try:
        result = asyncio.run(verify_context7())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\n[!] Verification interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n[X] Verification failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

