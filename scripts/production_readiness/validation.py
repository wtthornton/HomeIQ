"""
Validation step for production readiness pipeline.
"""
import importlib.util
import logging
import os
from typing import Tuple

from .config import OPTIONAL_ENV_VARS, REQUIRED_ENV_VARS, REQUIRED_PACKAGES
from .helpers import check_docker_compose

logger = logging.getLogger(__name__)


def validate_dependencies(skip_validation: bool = False) -> Tuple[bool, list[str]]:
    """Validate all dependencies before starting operations."""
    if skip_validation:
        logger.info("⚠️  Skipping dependency validation (--skip-validation flag)")
        return True, []
    
    logger.info("=" * 80)
    logger.info("PRE-FLIGHT VALIDATION: Checking Dependencies")
    logger.info("=" * 80)
    
    missing_items = []
    validation_results = []
    
    # Check Docker
    if not check_docker_compose():
        missing_items.append("Docker Compose")
        validation_results.append(("Docker Compose", False, "Install Docker Desktop or Docker Engine + Docker Compose"))
    else:
        validation_results.append(("Docker Compose", True, "✅ Available"))
    
    # Check Python packages
    for package in REQUIRED_PACKAGES:
        package_import = package.replace('-', '_')
        if package == 'docker':
            package_import = 'docker'
        elif package == 'influxdb-client':
            package_import = 'influxdb_client'
        
        spec = importlib.util.find_spec(package_import)
        if spec is None:
            missing_items.append(f"Python package: {package}")
            validation_results.append((f"Python: {package}", False, f"Install with: pip install {package}"))
        else:
            validation_results.append((f"Python: {package}", True, "✅ Installed"))
    
    # Check required environment variables
    for var, description in REQUIRED_ENV_VARS.items():
        if not os.getenv(var):
            missing_items.append(f"Environment variable: {var}")
            validation_results.append((f"Env: {var}", False, f"Set {var} or add to .env file: {var}=<value>"))
        else:
            validation_results.append((f"Env: {var}", True, f"✅ Set ({description})"))
    
    # Check optional environment variables
    for var, description in OPTIONAL_ENV_VARS.items():
        if not os.getenv(var):
            validation_results.append((f"Env: {var} (optional)", False, f"⚠️  Not set - {description}. Add to .env file for optional features."))
        else:
            validation_results.append((f"Env: {var} (optional)", True, f"✅ Set ({description})"))
    
    # Print validation results
    logger.info("\nValidation Checklist:")
    for item, passed, message in validation_results:
        icon = "✅" if passed else ("⚠️" if "(optional)" in item else "❌")
        logger.info(f"  {icon} {item}: {message}")
    
    if missing_items:
        logger.error("\n❌ Validation failed - Missing items:")
        for item in missing_items:
            logger.error(f"  - {item}")
        logger.error("\nPlease install missing dependencies and set required environment variables before continuing.")
        return False, missing_items
    
    logger.info("\n✅ All dependencies validated successfully")
    return True, []

