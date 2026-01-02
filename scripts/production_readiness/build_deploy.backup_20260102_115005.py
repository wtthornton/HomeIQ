"""
Build and deployment steps for production readiness pipeline.
"""
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Tuple

from .config import PROJECT_ROOT, TEST_RESULTS_DIR
from .helpers import check_docker_compose, get_docker_compose_cmd, run_command

logger = logging.getLogger(__name__)


def build_system() -> bool:
    """Build Docker images."""
    logger.info("=" * 80)
    logger.info("STEP 1: Building Docker Images")
    logger.info("=" * 80)
    
    if not check_docker_compose():
        logger.error("Docker Compose not found. Please install Docker and Docker Compose.")
        return False
    
    compose_cmd = get_docker_compose_cmd()
    cmd = compose_cmd.split() + ["build", "--no-cache"]
    exit_code, stdout, stderr = run_command(cmd, check=False)
    
    if exit_code != 0:
        logger.error(f"Build failed:\n{stderr}")
        return False
    
    logger.info("✅ Docker images built successfully")
    return True


def deploy_system() -> bool:
    """Deploy services with Docker Compose."""
    logger.info("=" * 80)
    logger.info("STEP 2: Deploying Services")
    logger.info("=" * 80)
    
    compose_cmd = get_docker_compose_cmd()
    
    # Stop existing services
    logger.info("Stopping existing services...")
    cmd = compose_cmd.split() + ["down", "--timeout", "30"]
    run_command(cmd, check=False)
    
    # Start services
    logger.info("Starting services...")
    cmd = compose_cmd.split() + ["up", "-d"]
    exit_code, stdout, stderr = run_command(cmd, check=False)
    
    if exit_code != 0:
        logger.error(f"Deployment failed:\n{stderr}")
        return False
    
    # Wait for services to be healthy
    logger.info("Waiting for services to be healthy (60 seconds)...")
    time.sleep(60)
    
    logger.info("✅ Services deployed successfully")
    return True


def run_smoke_tests(output_dir: Path) -> Tuple[bool, dict]:
    """Run smoke tests."""
    logger.info("=" * 80)
    logger.info("STEP 3: Running Smoke Tests")
    logger.info("=" * 80)
    
    smoke_test_path = PROJECT_ROOT / "tests" / "smoke_tests.py"
    if not smoke_test_path.exists():
        logger.error(f"Smoke test script not found: {smoke_test_path}")
        return False, {}
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"smoke_test_results_{timestamp}.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    cmd = [
        sys.executable,
        str(smoke_test_path),
        "--output", "json",
        "--output-file", str(output_file)
    ]
    
    exit_code, stdout, stderr = run_command(cmd, check=False)
    
    if exit_code != 0:
        logger.error(f"Smoke tests failed:\n{stderr}")
        return False, {}
    
    # Load results
    try:
        with open(output_file, 'r') as f:
            results = json.load(f)
        
        if results.get('overall_status') == 'pass':
            logger.info("✅ All smoke tests passed")
            return True, results
        else:
            logger.warning("⚠️  Some smoke tests failed (check results)")
            return False, results
    except Exception as e:
        logger.error(f"Failed to load smoke test results: {e}")
        return False, {}

