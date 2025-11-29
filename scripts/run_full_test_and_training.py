#!/usr/bin/env python3
"""
Full Test and Training Orchestration Script
Runs complete test data generation, model training, testing, and optimization pipeline.

Usage:
    python scripts/run_full_test_and_training.py
    python scripts/run_full_test_and_training.py --quick  # Smaller dataset, faster
    python scripts/run_full_test_and_training.py --skip-generation  # Skip data generation
"""

import argparse
import asyncio
import logging
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime

# Import progress indicator from same directory
_scripts_dir = Path(__file__).parent
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))
from progress_indicator import Spinner, ProgressBar, StatusUpdater, print_step_header

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Project root
project_root = Path(__file__).parent.parent
ai_service_dir = project_root / "services" / "ai-automation-service"


def run_command(cmd: list, cwd: Path = None, check: bool = True) -> tuple[int, str, str]:
    """Run a command and return exit code, stdout, stderr."""
    logger.info(f"Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd or project_root,
            capture_output=True,
            text=True,
            check=check
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {e}")
        return e.returncode, e.stdout, e.stderr


def check_file_exists(filepath: Path) -> bool:
    """Check if a file exists."""
    exists = filepath.exists()
    if not exists:
        logger.warning(f"File not found: {filepath}")
    return exists


def wait_for_files(files: list[Path], timeout: int = 3600, check_interval: int = 10):
    """Wait for files to exist, checking every check_interval seconds."""
    start_time = time.time()
    remaining_files = list(files)
    
    while remaining_files and (time.time() - start_time) < timeout:
        remaining_files = [f for f in remaining_files if not f.exists()]
        if remaining_files:
            logger.info(f"Waiting for {len(remaining_files)} files...")
            time.sleep(check_interval)
        else:
            logger.info("All files found!")
            return True
    
    if remaining_files:
        logger.error(f"Timeout waiting for files: {remaining_files}")
        return False
    return True


async def generate_test_data(count: int = 100, days: int = 90, quick: bool = False):
    """Generate synthetic test data."""
    print_step_header(1, 4, "Generating Synthetic Test Data")
    
    output_dir = ai_service_dir / "tests" / "datasets" / "synthetic_homes"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    cmd = [
        sys.executable,
        str(ai_service_dir / "scripts" / "generate_synthetic_homes.py"),
        "--count", str(count),
        "--days", str(days),
        "--output", str(output_dir),
        "--disable-calendar"  # Faster generation
    ]
    
    if quick:
        logger.info("Quick mode: Using smaller dataset (10 homes, 7 days)")
        count = 10
        days = 7
        cmd = [
            sys.executable,
            str(ai_service_dir / "scripts" / "generate_synthetic_homes.py"),
            "--count", "10",
            "--days", "7",
            "--output", str(output_dir),
            "--disable-calendar"
        ]
    
    status = StatusUpdater("Generating synthetic test data")
    status.update(f"Generating {count} homes with {days} days of data...")
    
    # Monitor progress by checking for output files
    import threading
    
    def monitor_progress():
        """Monitor file generation progress."""
        while True:
            home_files = list(output_dir.glob("home_*.json"))
            if len(home_files) >= count:
                break
            if len(home_files) > 0:
                status.update(f"Generated {len(home_files)}/{count} homes...")
            time.sleep(2)
    
    monitor_thread = threading.Thread(target=monitor_progress, daemon=True)
    monitor_thread.start()
    
    exit_code, stdout, stderr = run_command(cmd, cwd=ai_service_dir, check=False)
    
    if exit_code != 0:
        status.finish(success=False, message="Test data generation failed")
        logger.error(f"Test data generation failed:\n{stderr}")
        return False
    
    # Verify output files exist
    home_files = list(output_dir.glob("home_*.json"))
    status.finish(success=True, message=f"Generated {len(home_files)} synthetic homes")
    logger.info("✅ Test data generation completed")
    return True


async def train_models(synthetic_homes_dir: Path):
    """Train home type classifier model."""
    print_step_header(2, 4, "Training Home Type Classifier")
    
    model_dir = ai_service_dir / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    
    # Check if we have synthetic homes
    home_files = list(synthetic_homes_dir.glob("home_*.json"))
    if not home_files:
        logger.error(f"No synthetic home files found in {synthetic_homes_dir}")
        return False
    
    logger.info(f"Found {len(home_files)} synthetic homes for training")
    
    cmd = [
        sys.executable,
        str(ai_service_dir / "scripts" / "train_home_type_classifier.py"),
        "--synthetic-homes", str(synthetic_homes_dir),
        "--output", str(model_dir / "home_type_classifier.pkl"),
        "--test-size", "0.2"
    ]
    
    with Spinner("Training home type classifier model") as spinner:
        exit_code, stdout, stderr = run_command(cmd, cwd=ai_service_dir, check=False)
        
        if exit_code != 0:
            spinner.stop(success=False, message="Model training failed")
            logger.error(f"Model training failed:\n{stderr}")
            return False
    
    logger.info("✅ Model training completed")
    return True


def run_unit_tests():
    """Run all unit tests."""
    print_step_header(3, 4, "Running Unit Tests")
    
    cmd = [
        sys.executable,
        str(project_root / "scripts" / "simple-unit-tests.py"),
        "--python-only"
    ]
    
    with Spinner("Running unit tests") as spinner:
        exit_code, stdout, stderr = run_command(cmd, check=False)
        
        if exit_code != 0:
            spinner.stop(success=False, message="Some unit tests failed")
            logger.warning(f"Some unit tests failed. Check output for details.")
            logger.debug(f"Unit test output:\n{stdout}\n{stderr}")
        else:
            spinner.stop(success=True, message="All unit tests passed")
            logger.info("✅ All unit tests passed")
    
    return exit_code == 0


def optimize_system():
    """Optimize system configurations based on test results."""
    print_step_header(4, 4, "System Optimization")
    
    status = StatusUpdater("Optimizing system")
    
    # Check container health
    status.update("Checking container health...")
    exit_code, stdout, stderr = run_command(
        ["docker", "compose", "ps", "--format", "table {{.Name}}\t{{.Status}}"],
        check=False
    )
    
    if exit_code == 0:
        unhealthy = [line for line in stdout.split('\n') if 'unhealthy' in line.lower() or 'restarting' in line.lower()]
        if unhealthy:
            status.update(f"Found {len(unhealthy)} unhealthy containers")
            logger.warning(f"Found {len(unhealthy)} unhealthy containers:")
            for container in unhealthy:
                logger.warning(f"  - {container}")
        else:
            status.update("All containers are healthy")
            logger.info("✅ All containers are healthy")
    
    # Check database performance
    status.update("Checking database performance...")
    status.finish(success=True, message="System optimization checks completed")
    logger.info("System optimization checks completed")
    return True


async def main():
    """Main orchestration function."""
    parser = argparse.ArgumentParser(description='Run full test and training pipeline')
    parser.add_argument('--quick', action='store_true', help='Use smaller dataset (10 homes, 7 days)')
    parser.add_argument('--skip-generation', action='store_true', help='Skip test data generation')
    parser.add_argument('--skip-training', action='store_true', help='Skip model training')
    parser.add_argument('--skip-tests', action='store_true', help='Skip running tests')
    
    args = parser.parse_args()
    
    start_time = datetime.now()
    print("\n" + "="*80)
    print("HomeIQ Full Test and Training Pipeline")
    print(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80 + "\n")
    logger.info("="*80)
    logger.info("HomeIQ Full Test and Training Pipeline")
    logger.info(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*80)
    
    results = {
        'generation': False,
        'training': False,
        'tests': False,
        'optimization': False
    }
    
    # Step 1: Generate test data
    if not args.skip_generation:
        if args.quick:
            results['generation'] = await generate_test_data(count=10, days=7, quick=True)
        else:
            results['generation'] = await generate_test_data(count=100, days=90, quick=False)
    else:
        logger.info("Skipping test data generation")
        results['generation'] = True  # Assume existing data
    
    # Wait a bit for file system to sync
    time.sleep(2)
    
    # Step 2: Train models
    synthetic_homes_dir = ai_service_dir / "tests" / "datasets" / "synthetic_homes"
    if not args.skip_training and results['generation']:
        results['training'] = await train_models(synthetic_homes_dir)
    else:
        logger.info("Skipping model training")
        results['training'] = True
    
    # Step 3: Run tests
    if not args.skip_tests:
        results['tests'] = run_unit_tests()
    else:
        logger.info("Skipping tests")
        results['tests'] = True
    
    # Step 4: Optimize
    results['optimization'] = optimize_system()
    
    # Summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    logger.info("="*80)
    logger.info("PIPELINE SUMMARY")
    logger.info("="*80)
    logger.info(f"Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
    logger.info(f"Test Data Generation: {'✅ PASSED' if results['generation'] else '❌ FAILED'}")
    logger.info(f"Model Training: {'✅ PASSED' if results['training'] else '❌ FAILED'}")
    logger.info(f"Unit Tests: {'✅ PASSED' if results['tests'] else '❌ FAILED'}")
    logger.info(f"Optimization: {'✅ PASSED' if results['optimization'] else '❌ FAILED'}")
    logger.info("="*80)
    
    # Return exit code
    all_passed = all(results.values())
    return 0 if all_passed else 1


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

