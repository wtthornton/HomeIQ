"""
Data generation step for production readiness pipeline.
"""
import logging
import subprocess
import sys
from pathlib import Path

from .config import AI_SERVICE_DIR

logger = logging.getLogger(__name__)


async def generate_test_data(count: int = 100, days: int = 90, quick: bool = False, force: bool = False) -> bool:
    """Generate synthetic test data."""
    logger.info("=" * 80)
    logger.info("STEP 4: Generating Test Data")
    logger.info("=" * 80)
    
    output_dir = AI_SERVICE_DIR / "tests" / "datasets" / "synthetic_homes"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if test data already exists
    existing_home_files = list(output_dir.glob("home_*.json"))
    
    if existing_home_files and not force:
        logger.info(f"✅ Test data already exists: {len(existing_home_files)} synthetic home files found")
        logger.info(f"   Location: {output_dir}")
        logger.info("   Skipping data generation (use --force-regenerate to regenerate)")
        return True
    
    if existing_home_files and force:
        logger.info(f"⚠️  Existing test data found: {len(existing_home_files)} files")
        logger.info("   Force regeneration enabled - will regenerate data")
    
    if quick:
        logger.info("Quick mode: Using smaller dataset (10 homes, 7 days)")
        count = 10
        days = 7
    
    cmd = [
        sys.executable,
        str(AI_SERVICE_DIR / "scripts" / "generate_synthetic_homes.py"),
        "--count", str(count),
        "--days", str(days),
        "--output", str(output_dir),
        "--disable-calendar"
    ]
    
    logger.info("Test data generation started - progress will be shown below...")
    logger.info("-" * 80)
    
    process = subprocess.Popen(
        cmd,
        cwd=AI_SERVICE_DIR,
        stdout=sys.stdout,
        stderr=sys.stderr,
        text=True,
        bufsize=0
    )
    
    exit_code = process.wait()
    logger.info("-" * 80)
    
    if exit_code != 0:
        logger.error(f"Test data generation failed (exit code: {exit_code})")
        return False
    
    # Verify output files exist
    home_files = list(output_dir.glob("home_*.json"))
    if not home_files:
        logger.error(f"No synthetic home files generated in {output_dir}")
        return False
    
    logger.info(f"✅ Generated {len(home_files)} synthetic homes")
    return True

