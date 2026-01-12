#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backfill Quality Scores for Synergies

Executes quality score backfill for synergies in Docker database.
"""

import subprocess
import sys
from pathlib import Path

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    import os
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

def main():
    """Run backfill script in Docker container."""
    script_path = Path(__file__).parent.parent / "services" / "ai-pattern-service" / "scripts" / "backfill_quality_scores.py"
    
    if not script_path.exists():
        print(f"ERROR: Script not found: {script_path}")
        sys.exit(1)
    
    # Copy script to container and run it
    print("Copying script to container...")
    copy_cmd = [
        "docker", "cp",
        str(script_path),
        "ai-pattern-service:/tmp/backfill_quality_scores.py"
    ]
    result = subprocess.run(copy_cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR copying script: {result.stderr}")
        sys.exit(1)
    
    # Run script in container
    print("\nRunning backfill script...")
    run_cmd = [
        "docker", "exec", "ai-pattern-service",
        "python", "/tmp/backfill_quality_scores.py",
        "--db-path", "/app/data/ai_automation.db"
    ]
    
    # Add --dry-run if requested
    if "--dry-run" in sys.argv:
        run_cmd.append("--dry-run")
    elif "--execute" not in sys.argv:
        # Default to dry-run for safety
        print("⚠️  Running in DRY-RUN mode by default. Use --execute to apply changes.")
        run_cmd.append("--dry-run")
    
    result = subprocess.run(run_cmd, text=True, encoding='utf-8', errors='replace')
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()
