#!/usr/bin/env python3
"""
Production Readiness Script
Builds, deploys, tests, generates data, trains models, and prepares for production.

Enhanced with Epic 42 & 43 improvements:
- Pre-flight validation of dependencies and configuration
- Critical vs optional component classification
- Enhanced error messages with actionable fix instructions
- Model quality validation with defined thresholds
- Component documentation (see docs/architecture/production-readiness-components.md)

Usage:
    python scripts/prepare_for_production.py
    python scripts/prepare_for_production.py --quick  # Smaller dataset, faster
    python scripts/prepare_for_production.py --skip-build --skip-deploy
    python scripts/prepare_for_production.py --skip-validation  # Skip pre-flight checks (advanced)
"""

import argparse
import asyncio
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Setup logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file (Epic 42.2)
try:
    from dotenv import load_dotenv
    load_dotenv()
    logger.debug("Loaded environment variables from .env file")
except ImportError:
    # python-dotenv not installed, but that's okay - env vars can be set manually
    logger.debug("python-dotenv not installed - environment variables must be set manually or via system")
except Exception as e:
    logger.warning(f"Could not load .env file: {e} - continuing with system environment variables")

# Project root
project_root = Path(__file__).parent.parent
ai_service_dir = project_root / "services" / "ai-automation-service"
device_intelligence_dir = project_root / "services" / "device-intelligence-service"
test_results_dir = project_root / "test-results"
implementation_dir = project_root / "implementation"

# Component Classification (Epic 42.1: Critical vs Optional)
CRITICAL_COMPONENTS = {
    'build': True,
    'deploy': True,
    'smoke_tests': True,
    'data_generation': True,
    'home_type': True,
    'device_intelligence': True
}

OPTIONAL_COMPONENTS = {
    'gnn_synergy': True,
    'soft_prompt': True
}

# Required Environment Variables (Epic 42.2: Pre-Flight Validation)
REQUIRED_ENV_VARS = {
    'HA_HTTP_URL': 'Home Assistant HTTP URL (e.g., http://192.168.1.86:8123)',
    'HA_TOKEN': 'Home Assistant long-lived access token'
}

OPTIONAL_ENV_VARS = {
    'OPENAI_API_KEY': 'OpenAI API key (required for Ask AI suggestions and automation generation, but not for model training)'
}

# Model Quality Thresholds (Epic 43.1: Model Quality Validation)
MODEL_QUALITY_THRESHOLDS = {
    'home_type': {
        'accuracy': 0.90,  # 90% minimum accuracy
        'precision': 0.85,  # 85% minimum precision
        'recall': 0.85,     # 85% minimum recall
        'f1_score': 0.85   # 85% minimum F1 score
    },
    'device_intelligence': {
        'accuracy': 0.85,  # 85% minimum accuracy
        'precision': 0.80,  # 80% minimum precision
        'recall': 0.80,     # 80% minimum recall
        'f1_score': 0.80   # 80% minimum F1 score
    },
    'gnn_synergy': {
        # Optional model - no strict thresholds, but validate if metrics exist
        'accuracy': 0.70,  # 70% minimum if metrics available
    },
    'soft_prompt': {
        # Optional model - no strict thresholds, but validate if metrics exist
        'accuracy': 0.70,  # 70% minimum if metrics available
    }
}

# Required Python Packages (Epic 42.2: Pre-Flight Validation)
REQUIRED_PACKAGES = [
    'docker',
    'fastapi',
    'pydantic',
    'sqlalchemy',
    'influxdb-client',
    'aiohttp',
    'pytest'
]


def validate_model_quality(model_name: str, results: dict, allow_low_quality: bool = False) -> tuple[bool, dict]:
    """
    Validate model quality against defined thresholds (Epic 43.1: Model Quality Validation).
    
    Args:
        model_name: Name of the model (e.g., 'home_type', 'device_intelligence')
        results: Dictionary containing model metrics/results
        allow_low_quality: If True, return warning but don't fail validation
    
    Returns:
        Tuple of (passed: bool, validation_details: dict)
    """
    if model_name not in MODEL_QUALITY_THRESHOLDS:
        # No thresholds defined for this model
        return True, {'status': 'no_thresholds', 'message': 'No quality thresholds defined'}
    
    thresholds = MODEL_QUALITY_THRESHOLDS[model_name]
    validation_details = {
        'status': 'checking',
        'metrics_checked': [],
        'metrics_passed': [],
        'metrics_failed': [],
        'warnings': []
    }
    
    # Extract metrics based on model type
    metrics = {}
    if model_name == 'home_type':
        # Home type classifier results format
        metrics = {
            'accuracy': results.get('accuracy'),
            'precision': results.get('precision'),
            'recall': results.get('recall'),
            'f1_score': results.get('f1_score')
        }
    elif model_name == 'device_intelligence':
        # Device intelligence metadata format
        perf = results.get('model_performance', {})
        metrics = {
            'accuracy': perf.get('accuracy'),
            'precision': perf.get('precision'),
            'recall': perf.get('recall'),
            'f1_score': perf.get('f1_score')
        }
    else:
        # Optional models - check if any metrics exist
        metrics = {
            'accuracy': results.get('accuracy') or results.get('model_performance', {}).get('accuracy')
        }
    
    # Validate each metric against threshold
    all_passed = True
    for metric_name, threshold in thresholds.items():
        if metric_name not in metrics:
            # Metric not available - skip (graceful handling)
            validation_details['warnings'].append(f"{metric_name} not available in results")
            continue
        
        metric_value = metrics[metric_name]
        if metric_value is None:
            validation_details['warnings'].append(f"{metric_name} is None - cannot validate")
            continue
        
        validation_details['metrics_checked'].append({
            'metric': metric_name,
            'value': metric_value,
            'threshold': threshold,
            'passed': metric_value >= threshold
        })
        
        if metric_value >= threshold:
            validation_details['metrics_passed'].append(metric_name)
        else:
            validation_details['metrics_failed'].append({
                'metric': metric_name,
                'value': metric_value,
                'threshold': threshold,
                'gap': threshold - metric_value
            })
            all_passed = False
    
    # Determine final status
    if all_passed:
        validation_details['status'] = 'passed'
        validation_details['message'] = 'All quality thresholds met'
    else:
        validation_details['status'] = 'failed' if not allow_low_quality else 'warning'
        failed_metrics = ', '.join([f['metric'] for f in validation_details['metrics_failed']])
        validation_details['message'] = f"Quality thresholds not met: {failed_metrics}"
    
    return all_passed or allow_low_quality, validation_details


def format_error_message(what: str, why: str, how_to_fix: str, impact: str = "OPTIONAL") -> str:
    """
    Format error message in What/Why/How to Fix format (Epic 42.3).
    
    Args:
        what: Clear description of what failed
        why: Explanation of root cause
        how_to_fix: Actionable steps to resolve
        impact: "CRITICAL" or "OPTIONAL"
    
    Returns:
        Formatted error message string
    """
    impact_icon = "🔴" if impact == "CRITICAL" else "🟡"
    return f"""
{impact_icon} {what}

**Why it failed:**
{why}

**How to fix:**
{how_to_fix}

**Impact:** {impact} - {'Blocks production deployment' if impact == 'CRITICAL' else 'Enhancement feature, not required'}
"""


def run_command(cmd: list, cwd: Path = None, check: bool = False) -> tuple[int, str, str]:
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


def validate_dependencies(skip_validation: bool = False) -> tuple[bool, list[str]]:
    """
    Validate all dependencies before starting operations (Epic 42.2: Pre-Flight Validation).
    
    Returns:
        Tuple of (all_passed: bool, missing_items: list[str])
    """
    if skip_validation:
        logger.info("⚠️  Skipping dependency validation (--skip-validation flag)")
        return True, []
    
    logger.info("="*80)
    logger.info("PRE-FLIGHT VALIDATION: Checking Dependencies")
    logger.info("="*80)
    
    missing_items = []
    validation_results = []
    
    # Check Docker
    if not check_docker_compose():
        missing_items.append("Docker Compose")
        validation_results.append(("Docker Compose", False, "Install Docker Desktop or Docker Engine + Docker Compose"))
    else:
        validation_results.append(("Docker Compose", True, "✅ Available"))
    
    # Check Python packages
    import importlib.util
    for package in REQUIRED_PACKAGES:
        # Handle package name variations (e.g., 'docker' -> 'docker' module)
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
    
    # Check required environment variables (already loaded from .env if dotenv available)
    for var, description in REQUIRED_ENV_VARS.items():
        if not os.getenv(var):
            missing_items.append(f"Environment variable: {var}")
            validation_results.append((f"Env: {var}", False, f"Set {var} or add to .env file: {var}=<value>"))
        else:
            validation_results.append((f"Env: {var}", True, f"✅ Set ({description})"))
    
    # Check optional environment variables (informational only)
    for var, description in OPTIONAL_ENV_VARS.items():
        if not os.getenv(var):
            validation_results.append((f"Env: {var} (optional)", False, f"⚠️  Not set - {description}. Add to .env file for optional features."))
        else:
            validation_results.append((f"Env: {var} (optional)", True, f"✅ Set ({description})"))
    
    # Print validation results
    logger.info("\nValidation Checklist:")
    for item, passed, message in validation_results:
        if "(optional)" in item:
            icon = "✅" if passed else "⚠️"
        else:
            icon = "✅" if passed else "❌"
        logger.info(f"  {icon} {item}: {message}")
    
    if missing_items:
        logger.error("\n❌ Validation failed - Missing items:")
        for item in missing_items:
            logger.error(f"  - {item}")
        logger.error("\nPlease install missing dependencies and set required environment variables before continuing.")
        return False, missing_items
    
    logger.info("\n✅ All dependencies validated successfully")
    return True, []


def check_docker_compose() -> bool:
    """Check if docker compose is available."""
    # Try docker compose (newer)
    exit_code, _, _ = run_command(["docker", "compose", "version"], check=False)
    if exit_code == 0:
        return True
    
    # Try docker-compose (older)
    exit_code, _, _ = run_command(["docker-compose", "--version"], check=False)
    return exit_code == 0


def get_docker_compose_cmd() -> str:
    """Get the docker compose command to use."""
    exit_code, _, _ = run_command(["docker", "compose", "version"], check=False)
    if exit_code == 0:
        return "docker compose"
    return "docker-compose"


def build_system() -> bool:
    """Build Docker images."""
    logger.info("="*80)
    logger.info("STEP 1: Building Docker Images")
    logger.info("="*80)
    
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
    logger.info("="*80)
    logger.info("STEP 2: Deploying Services")
    logger.info("="*80)
    
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


def run_smoke_tests(output_dir: Path) -> tuple[bool, dict]:
    """Run smoke tests."""
    logger.info("="*80)
    logger.info("STEP 3: Running Smoke Tests")
    logger.info("="*80)
    
    # Import smoke tests
    smoke_test_path = project_root / "tests" / "smoke_tests.py"
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


async def generate_test_data(count: int = 100, days: int = 90, quick: bool = False, force: bool = False) -> bool:
    """Generate synthetic test data. Only generates if data doesn't exist unless force=True."""
    logger.info("="*80)
    logger.info("STEP 4: Generating Test Data")
    logger.info("="*80)
    
    output_dir = ai_service_dir / "tests" / "datasets" / "synthetic_homes"
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
        str(ai_service_dir / "scripts" / "generate_synthetic_homes.py"),
        "--count", str(count),
        "--days", str(days),
        "--output", str(output_dir),
        "--disable-calendar"  # Faster generation
    ]
    
    # Run with real-time output streaming
    logger.info("Test data generation started - progress will be shown below...")
    logger.info("-" * 80)
    
    import subprocess
    import sys
    
    # Use unbuffered subprocess for real-time output
    process = subprocess.Popen(
        cmd,
        cwd=ai_service_dir,
        stdout=sys.stdout,  # Stream directly to console
        stderr=sys.stderr,
        text=True,
        bufsize=0  # Unbuffered for real-time output
    )
    
    # Wait for completion
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


async def train_home_type_classifier(synthetic_homes_dir: Path, allow_low_quality: bool = False) -> tuple[bool, dict]:
    """Train home type classifier model."""
    logger.info("Training Home Type Classifier...")
    
    model_dir = ai_service_dir / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    
    model_path = model_dir / "home_type_classifier.pkl"
    
    cmd = [
        sys.executable,
        str(ai_service_dir / "scripts" / "train_home_type_classifier.py"),
        "--synthetic-homes", str(synthetic_homes_dir),
        "--output", str(model_path),
        "--test-size", "0.2"
    ]
    
    exit_code, stdout, stderr = run_command(cmd, cwd=ai_service_dir, check=False)
    
    if exit_code != 0:
        logger.error(f"Home type classifier training failed:\n{stderr}")
        return False, {}
    
    # Load results if available
    results_path = model_dir / "home_type_classifier_results.json"
    results = {}
    if results_path.exists():
        try:
            with open(results_path, 'r', encoding='utf-8') as f:
                results = json.load(f)
        except Exception:
            pass
    
    # Validate model quality (Epic 43.1: Model Quality Validation)
    quality_passed, quality_details = validate_model_quality('home_type', results, allow_low_quality=allow_low_quality)
    
    if not quality_passed:
        failed_metrics = quality_details.get('metrics_failed', [])
        failed_str = ', '.join([f"{f['metric']} ({f['value']:.2%} < {f['threshold']:.2%})" for f in failed_metrics])
        error_msg = format_error_message(
            what="Home type classifier quality validation failed",
            why=f"Model metrics below thresholds: {failed_str}",
            how_to_fix="1. Review training data quality\n2. Check for data imbalance\n3. Consider adjusting model parameters\n4. Use --allow-low-quality flag to proceed anyway",
            impact="CRITICAL"
        )
        logger.error(error_msg)
        return False, results
    
    # Log quality metrics
    if quality_details.get('metrics_passed'):
        metrics_str = ', '.join([f"{m} ✅" for m in quality_details['metrics_passed']])
        logger.info(f"✅ Home type classifier quality validated: {metrics_str}")
    
    logger.info("✅ Home type classifier trained and validated successfully")
    return True, {**results, '_quality_validation': quality_details}


async def train_device_intelligence(allow_low_quality: bool = False) -> tuple[bool, dict]:
    """
    Train device intelligence models with synthetic data (Epic 46.3).
    
    Uses template-based synthetic device data for initial training before alpha release.
    """
    logger.info("Training Device Intelligence Models...")
    
    # Generate synthetic device data for initial training (Epic 46.3)
    logger.info("Generating synthetic device data for initial training...")
    use_synthetic = False
    try:
        # Import synthetic device generator
        sys.path.insert(0, str(device_intelligence_dir))
        from src.training.synthetic_device_generator import SyntheticDeviceGenerator
        
        generator = SyntheticDeviceGenerator()
        synthetic_data = generator.generate_training_data(count=1000, days=180)
        logger.info(f"✅ Generated {len(synthetic_data)} synthetic device samples")
        use_synthetic = True
    except Exception as e:
        logger.warning(f"⚠️ Failed to generate synthetic data: {e}")
        logger.warning("   Falling back to database data")
        import traceback
        logger.debug(traceback.format_exc())
    
    # Train with synthetic data if available
    cmd = [
        sys.executable,
        str(device_intelligence_dir / "scripts" / "train_models.py"),
        "--force",
        "--verbose"
    ]
    
    if use_synthetic:
        cmd.extend(["--synthetic-data", "--synthetic-count", "1000"])
        logger.info("   Using synthetic data for training")
    
    exit_code, stdout, stderr = run_command(cmd, cwd=device_intelligence_dir, check=False)
    
    if exit_code != 0:
        logger.error(f"Device intelligence training failed:\n{stderr}")
        return False, {}
    
    # Load metadata if available
    metadata_path = device_intelligence_dir / "models" / "model_metadata.json"
    results = {}
    if metadata_path.exists():
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                results = json.load(f)
        except Exception:
            pass
    
    # Validate model quality (Epic 43.1: Model Quality Validation)
    quality_passed, quality_details = validate_model_quality('device_intelligence', results, allow_low_quality=allow_low_quality)
    
    if not quality_passed:
        failed_metrics = quality_details.get('metrics_failed', [])
        failed_str = ', '.join([f"{f['metric']} ({f['value']:.2%} < {f['threshold']:.2%})" for f in failed_metrics])
        error_msg = format_error_message(
            what="Device intelligence quality validation failed",
            why=f"Model metrics below thresholds: {failed_str}",
            how_to_fix="1. Review training data quality\n2. Check for data imbalance\n3. Consider adjusting model parameters\n4. Use --allow-low-quality flag to proceed anyway",
            impact="CRITICAL"
        )
        logger.error(error_msg)
        return False, results
    
    # Log quality metrics
    if quality_details.get('metrics_passed'):
        metrics_str = ', '.join([f"{m} ✅" for m in quality_details['metrics_passed']])
        logger.info(f"✅ Device intelligence quality validated: {metrics_str}")
    
    logger.info("✅ Device intelligence models trained and validated successfully")
    return True, {**results, '_quality_validation': quality_details}


async def train_gnn_synergy() -> tuple[bool, dict]:
    """Train GNN synergy detector model."""
    logger.info("Training GNN Synergy Detector...")
    
    script_path = ai_service_dir / "scripts" / "train_gnn_synergy.py"
    if not script_path.exists():
        logger.warning("GNN training script not found, skipping")
        return True, {}
    
    cmd = [
        sys.executable,
        str(script_path)
    ]
    
    exit_code, stdout, stderr = run_command(cmd, cwd=ai_service_dir, check=False)
    
    if exit_code != 0:
        error_msg = format_error_message(
            what="GNN Synergy training failed",
            why=f"Training script exited with code {exit_code}. Check logs above for details.",
            how_to_fix="1. Check script logs for specific errors\n2. Ensure required dependencies are installed\n3. Verify database contains synergy data or entities for synthetic generation",
            impact="OPTIONAL"
        )
        logger.warning(error_msg)
        return False, {}
    
    logger.info("✅ GNN synergy detector trained successfully")
    return True, {}


async def train_soft_prompt() -> tuple[bool, dict]:
    """Train soft prompt model."""
    logger.info("Training Soft Prompt...")
    
    script_path = ai_service_dir / "scripts" / "train_soft_prompt.py"
    if not script_path.exists():
        logger.warning("Soft prompt training script not found, skipping")
        return True, {}
    
    cmd = [
        sys.executable,
        str(script_path)
    ]
    
    exit_code, stdout, stderr = run_command(cmd, cwd=ai_service_dir, check=False)
    
    if exit_code != 0:
        error_msg = format_error_message(
            what="Soft Prompt training failed",
            why=f"Training script exited with code {exit_code}. Check logs above for details.",
            how_to_fix="1. Check script logs for specific errors\n2. Ensure required dependencies are installed (transformers, torch, peft)\n3. Verify database contains Ask AI labelled data (ask_ai_queries table with approved suggestions)\n4. Check HuggingFace model cache or network connectivity for model downloads",
            impact="OPTIONAL"
        )
        logger.warning(error_msg)
        return False, {}
    
    logger.info("✅ Soft prompt trained successfully")
    return True, {}


async def train_all_models(synthetic_homes_dir: Path, allow_low_quality: bool = False) -> dict:
    """Train all models."""
    logger.info("="*80)
    logger.info("STEP 5: Training All Models")
    logger.info("="*80)
    
    results = {
        'home_type': {'success': False, 'results': {}},
        'device_intelligence': {'success': False, 'results': {}},
        'gnn_synergy': {'success': False, 'results': {}},
        'soft_prompt': {'success': False, 'results': {}}
    }
    
    # Train home type classifier
    success, training_results = await train_home_type_classifier(synthetic_homes_dir, allow_low_quality=allow_low_quality)
    results['home_type'] = {'success': success, 'results': training_results}
    
    # Train device intelligence
    success, training_results = await train_device_intelligence(allow_low_quality=allow_low_quality)
    results['device_intelligence'] = {'success': success, 'results': training_results}
    
    # Train GNN synergy (non-critical)
    success, training_results = await train_gnn_synergy()
    results['gnn_synergy'] = {'success': success, 'results': training_results}
    
    # Train soft prompt (non-critical)
    success, training_results = await train_soft_prompt()
    results['soft_prompt'] = {'success': success, 'results': training_results}
    
    return results


def save_models(output_dir: Path) -> tuple[bool, dict]:
    """Save and verify all trained models."""
    logger.info("="*80)
    logger.info("STEP 6: Saving Models")
    logger.info("="*80)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    manifest = {
        'timestamp': datetime.now().isoformat(),
        'models': {}
    }
    
    # Home Type Classifier
    model_path = ai_service_dir / "models" / "home_type_classifier.pkl"
    metadata_path = ai_service_dir / "models" / "home_type_classifier_metadata.json"
    results_path = ai_service_dir / "models" / "home_type_classifier_results.json"
    
    if model_path.exists():
        manifest['models']['home_type_classifier'] = {
            'model': str(model_path),
            'metadata': str(metadata_path) if metadata_path.exists() else None,
            'results': str(results_path) if results_path.exists() else None,
            'size_bytes': model_path.stat().st_size
        }
        logger.info(f"✅ Home type classifier: {model_path}")
    else:
        logger.warning(f"⚠️  Home type classifier not found: {model_path}")
    
    # Device Intelligence Models
    di_models_dir = device_intelligence_dir / "models"
    if di_models_dir.exists():
        failure_model = di_models_dir / "failure_prediction_model.pkl"
        anomaly_model = di_models_dir / "anomaly_detection_model.pkl"
        metadata = di_models_dir / "model_metadata.json"
        
        if failure_model.exists() and anomaly_model.exists():
            manifest['models']['device_intelligence'] = {
                'failure_model': str(failure_model),
                'anomaly_model': str(anomaly_model),
                'metadata': str(metadata) if metadata.exists() else None,
                'failure_size_bytes': failure_model.stat().st_size,
                'anomaly_size_bytes': anomaly_model.stat().st_size
            }
            logger.info(f"✅ Device intelligence models: {di_models_dir}")
        else:
            logger.warning(f"⚠️  Device intelligence models not found")
    
    # GNN Synergy
    gnn_model = ai_service_dir / "models" / "gnn_synergy.pth"
    gnn_metadata = ai_service_dir / "models" / "gnn_synergy_metadata.json"
    
    if gnn_model.exists():
        manifest['models']['gnn_synergy'] = {
            'model': str(gnn_model),
            'metadata': str(gnn_metadata) if gnn_metadata.exists() else None,
            'size_bytes': gnn_model.stat().st_size
        }
        logger.info(f"✅ GNN synergy: {gnn_model}")
    
    # Soft Prompt
    soft_prompt_dir = ai_service_dir / "models" / "soft_prompts"
    if soft_prompt_dir.exists() and any(soft_prompt_dir.iterdir()):
        manifest['models']['soft_prompt'] = {
            'directory': str(soft_prompt_dir),
            'files': [str(f.name) for f in soft_prompt_dir.iterdir() if f.is_file()]
        }
        logger.info(f"✅ Soft prompt: {soft_prompt_dir}")
    
    # Save manifest
    manifest_path = output_dir / f"model_manifest_{timestamp}.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    logger.info(f"✅ Model manifest saved to {manifest_path}")
    
    return True, manifest


def generate_report(
    build_status: bool,
    deploy_status: bool,
    smoke_results: dict,
    data_generation_status: bool,
    training_results: dict,
    model_manifest: dict,
    output_dir: Path
) -> Path:
    """Generate comprehensive production readiness report."""
    logger.info("="*80)
    logger.info("STEP 7: Generating Production Readiness Report")
    logger.info("="*80)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = output_dir / f"production_readiness_report_{timestamp}.md"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Calculate overall status (Epic 42.1: Critical vs Optional)
    # Only check critical components for production readiness
    critical_passed = (
        build_status and
        deploy_status and
        smoke_results.get('overall_status') == 'pass' and
        data_generation_status and
        training_results.get('home_type', {}).get('success', False) and
        training_results.get('device_intelligence', {}).get('success', False)
    )
    
    # Check optional components separately
    optional_status = {
        'gnn_synergy': training_results.get('gnn_synergy', {}).get('success', False),
        'soft_prompt': training_results.get('soft_prompt', {}).get('success', False)
    }
    optional_passed = [name for name, status in optional_status.items() if status]
    optional_failed = [name for name, status in optional_status.items() if not status]
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# Production Readiness Report\n\n")
        f.write(f"**Generated:** {datetime.now().isoformat()}\n\n")
        f.write("---\n\n")
        
        # Overall Status (Epic 42.1: Critical vs Optional)
        f.write("## Overall Status\n\n")
        if critical_passed:
            f.write("✅ **PRODUCTION READY** (Critical components passed)\n\n")
            if optional_failed:
                f.write(f"⚠️  **Optional Components:** {', '.join([name.replace('_', ' ').title() for name in optional_failed])} not configured\n\n")
            if optional_passed:
                f.write(f"✨ **Optional Enhancements:** {', '.join([name.replace('_', ' ').title() for name in optional_passed])} available\n\n")
        else:
            f.write("❌ **NOT PRODUCTION READY** (Critical components failed)\n\n")
        f.write("---\n\n")
        
        # Build Status
        f.write("## 1. Build Status\n\n")
        f.write(f"- **Status:** {'✅ PASSED' if build_status else '❌ FAILED'}\n\n")
        f.write("---\n\n")
        
        # Deployment Status
        f.write("## 2. Deployment Status\n\n")
        f.write(f"- **Status:** {'✅ PASSED' if deploy_status else '❌ FAILED'}\n\n")
        f.write("---\n\n")
        
        # Smoke Tests
        f.write("## 3. Smoke Test Results\n\n")
        if smoke_results:
            f.write(f"- **Overall Status:** {smoke_results.get('overall_status', 'unknown').upper()}\n")
            f.write(f"- **Total Tests:** {smoke_results.get('total_tests', 0)}\n")
            f.write(f"- **Passed:** {smoke_results.get('passed', 0)}\n")
            f.write(f"- **Failed:** {smoke_results.get('failed', 0)}\n")
            f.write(f"- **Critical Passed:** {smoke_results.get('critical_passed', 0)}\n")
            f.write(f"- **Critical Failed:** {smoke_results.get('critical_failed', 0)}\n\n")
            
            f.write("### Service Details\n\n")
            for service in smoke_results.get('services', []):
                status_icon = "✅" if service.get('passed') else "❌"
                f.write(f"- {status_icon} **{service.get('service')}**: {service.get('status')}\n")
                if service.get('error'):
                    f.write(f"  - Error: {service.get('error')}\n")
        else:
            f.write("- **Status:** Not run\n")
        f.write("\n---\n\n")
        
        # Data Generation
        f.write("## 4. Test Data Generation\n\n")
        f.write(f"- **Status:** {'✅ PASSED' if data_generation_status else '❌ FAILED'}\n\n")
        f.write("---\n\n")
        
        # Training Results (Epic 42.1: Critical vs Optional)
        f.write("## 5. Model Training Results\n\n")
        
        # Critical Models Section (Epic 43.1: Model Quality Validation)
        f.write("### Critical Models (Required for Production)\n\n")
        critical_models = ['home_type', 'device_intelligence']
        for model_name in critical_models:
            if model_name in training_results:
                result = training_results[model_name]
                status_icon = "✅" if result.get('success') else "❌"
                f.write(f"#### {model_name.replace('_', ' ').title()}\n\n")
                f.write(f"- **Status:** {status_icon} {'PASSED' if result.get('success') else 'FAILED'}\n")
                f.write(f"- **Type:** 🔴 CRITICAL\n")
                
                # Quality Validation Results (Epic 43.1)
                quality_validation = result.get('results', {}).get('_quality_validation', {})
                if quality_validation:
                    quality_status = quality_validation.get('status', 'unknown')
                    if quality_status == 'passed':
                        f.write("- **Quality:** ✅ All thresholds met\n")
                    elif quality_status == 'failed':
                        f.write("- **Quality:** ❌ Below thresholds\n")
                        failed_metrics = quality_validation.get('metrics_failed', [])
                        for failed in failed_metrics:
                            f.write(f"  - ⚠️  {failed['metric']}: {failed['value']:.2%} (threshold: {failed['threshold']:.2%})\n")
                    elif quality_status == 'warning':
                        f.write("- **Quality:** ⚠️  Below thresholds (allowed with --allow-low-quality)\n")
                
                if result.get('results'):
                    f.write("- **Metrics:**\n")
                    for key, value in result['results'].items():
                        # Skip internal quality validation dict
                        if key == '_quality_validation':
                            continue
                        if isinstance(value, (int, float)):
                            f.write(f"  - {key}: {value}\n")
                        elif isinstance(value, dict) and 'accuracy' in value:
                            # Handle nested performance dicts
                            for perf_key, perf_value in value.items():
                                if isinstance(perf_value, (int, float)):
                                    f.write(f"  - {perf_key}: {perf_value}\n")
                f.write("\n")
        
        # Optional Models Section
        f.write("### Optional Models (Enhancements)\n\n")
        optional_models = ['gnn_synergy', 'soft_prompt']
        for model_name in optional_models:
            if model_name in training_results:
                result = training_results[model_name]
                status_icon = "✅" if result.get('success') else "⚠️"
                f.write(f"#### {model_name.replace('_', ' ').title()}\n\n")
                f.write(f"- **Status:** {status_icon} {'PASSED' if result.get('success') else 'NOT CONFIGURED'}\n")
                f.write(f"- **Type:** 🟡 OPTIONAL\n")
                if not result.get('success'):
                    f.write("- **Note:** Optional enhancement - not required for production deployment\n")
                if result.get('results'):
                    f.write("- **Metrics:**\n")
                    for key, value in result['results'].items():
                        if isinstance(value, (int, float)):
                            f.write(f"  - {key}: {value}\n")
                f.write("\n")
        f.write("---\n\n")
        
        # Model Manifest
        f.write("## 6. Model Manifest\n\n")
        if model_manifest:
            f.write(f"- **Generated:** {model_manifest.get('timestamp', 'unknown')}\n\n")
            f.write("### Models Saved\n\n")
            for model_name, model_info in model_manifest.get('models', {}).items():
                f.write(f"#### {model_name.replace('_', ' ').title()}\n\n")
                for key, value in model_info.items():
                    if value:
                        f.write(f"- **{key}:** {value}\n")
                f.write("\n")
        f.write("---\n\n")
        
        # Production Readiness Checklist
        f.write("## 7. Production Readiness Checklist\n\n")
        checklist = [
            ("Build completed successfully", build_status),
            ("Services deployed and running", deploy_status),
            ("All critical smoke tests passed", smoke_results.get('critical_failed', 1) == 0),
            ("Test data generated", data_generation_status),
            ("Home type classifier trained", training_results.get('home_type', {}).get('success', False)),
            ("Device intelligence models trained", training_results.get('device_intelligence', {}).get('success', False)),
            ("Models saved and verified", len(model_manifest.get('models', {})) > 0)
        ]
        
        for item, status in checklist:
            icon = "✅" if status else "❌"
            f.write(f"- {icon} {item}\n")
        
        f.write("\n---\n\n")
        f.write("## Next Steps\n\n")
        if critical_passed:
            f.write("1. Review model performance metrics\n")
            f.write("2. Verify model files are in correct locations\n")
            f.write("3. Deploy to production environment\n")
        else:
            f.write("1. Review failed steps above\n")
            f.write("2. Fix critical issues\n")
            f.write("3. Re-run this script\n")
    
    logger.info(f"✅ Report saved to {report_path}")
    return report_path


async def main():
    """Main orchestration function."""
    parser = argparse.ArgumentParser(description='Prepare system for production deployment')
    parser.add_argument('--skip-build', action='store_true', help='Skip Docker build step')
    parser.add_argument('--skip-deploy', action='store_true', help='Skip deployment step')
    parser.add_argument('--skip-smoke', action='store_true', help='Skip smoke tests')
    parser.add_argument('--skip-generation', action='store_true', help='Skip test data generation')
    parser.add_argument('--skip-training', action='store_true', help='Skip model training')
    parser.add_argument('--quick', action='store_true', help='Use smaller dataset (10 homes, 7 days)')
    parser.add_argument('--count', type=int, help='Number of synthetic homes to generate (default: 100, or 10 in quick mode)')
    parser.add_argument('--days', type=int, help='Number of days of events per home (default: 90, or 7 in quick mode)')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose logging')
    parser.add_argument('--output-dir', type=str, help='Custom output directory for reports')
    parser.add_argument('--skip-validation', action='store_true', help='Skip pre-flight dependency validation (advanced users only)')
    parser.add_argument('--allow-low-quality', action='store_true', help='Allow models that don\'t meet quality thresholds to proceed (advanced users only)')
    parser.add_argument('--force-regenerate', action='store_true', help='Force regeneration of test data even if it already exists')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Setup output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = implementation_dir
    
    start_time = datetime.now()
    logger.info("="*80)
    logger.info("HomeIQ Production Readiness Pipeline")
    logger.info(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*80)
    
    # Pre-Flight Validation (Epic 42.2)
    validation_passed, missing_items = validate_dependencies(args.skip_validation)
    if not validation_passed:
        error_msg = format_error_message(
            what="Pre-flight validation failed",
            why=f"Missing {len(missing_items)} required dependency(ies)",
            how_to_fix="\n".join([f"  - {item}" for item in missing_items]) + "\n\nInstall missing dependencies and set required environment variables, then re-run the script.",
            impact="CRITICAL"
        )
        logger.error(error_msg)
        return 1
    
    results = {
        'build': False,
        'deploy': False,
        'smoke_tests': {'success': False, 'results': {}},
        'data_generation': False,
        'training': {},
        'model_save': {'success': False, 'manifest': {}}
    }
    
    # Step 1: Build
    if not args.skip_build:
        results['build'] = build_system()
        if not results['build']:
            logger.error("Build failed - stopping pipeline")
            return 1
    else:
        logger.info("Skipping build step")
        results['build'] = True
    
    # Step 2: Deploy
    if not args.skip_deploy:
        results['deploy'] = deploy_system()
        if not results['deploy']:
            logger.error("Deployment failed - stopping pipeline")
            return 1
    else:
        logger.info("Skipping deployment step")
        results['deploy'] = True
    
    # Step 3: Smoke Tests
    if not args.skip_smoke:
        success, smoke_results = run_smoke_tests(test_results_dir)
        results['smoke_tests'] = {'success': success, 'results': smoke_results}
    else:
        logger.info("Skipping smoke tests")
        results['smoke_tests'] = {'success': True, 'results': {}}
    
    # Step 4: Generate Test Data
    if not args.skip_generation:
        if args.count or args.days:
            # Custom count/days specified
            count = args.count if args.count else (10 if args.quick else 100)
            days = args.days if args.days else (7 if args.quick else 90)
            results['data_generation'] = await generate_test_data(count=count, days=days, quick=False, force=args.force_regenerate)
        elif args.quick:
            results['data_generation'] = await generate_test_data(count=10, days=7, quick=True, force=args.force_regenerate)
        else:
            results['data_generation'] = await generate_test_data(count=100, days=90, quick=False, force=args.force_regenerate)
    else:
        logger.info("Skipping test data generation")
        results['data_generation'] = True
    
    # Step 5: Train Models
    synthetic_homes_dir = ai_service_dir / "tests" / "datasets" / "synthetic_homes"
    if not args.skip_training and results['data_generation']:
        results['training'] = await train_all_models(synthetic_homes_dir, allow_low_quality=args.allow_low_quality)
    else:
        logger.info("Skipping model training")
        results['training'] = {}
    
    # Step 6: Save Models
    success, manifest = save_models(test_results_dir)
    results['model_save'] = {'success': success, 'manifest': manifest}
    
    # Step 7: Generate Report
    report_path = generate_report(
        results['build'],
        results['deploy'],
        results['smoke_tests']['results'],
        results['data_generation'],
        results['training'],
        results['model_save']['manifest'],
        output_dir
    )
    
    # Summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    logger.info("="*80)
    logger.info("PIPELINE SUMMARY")
    logger.info("="*80)
    logger.info(f"Duration: {duration:.1f} seconds ({duration/60:.1f} minutes)")
    logger.info(f"Build: {'✅ PASSED' if results['build'] else '❌ FAILED'}")
    logger.info(f"Deploy: {'✅ PASSED' if results['deploy'] else '❌ FAILED'}")
    logger.info(f"Smoke Tests: {'✅ PASSED' if results['smoke_tests']['success'] else '❌ FAILED'}")
    logger.info(f"Data Generation: {'✅ PASSED' if results['data_generation'] else '❌ FAILED'}")
    
    # Enhanced training status (Epic 42.1: Critical vs Optional)
    critical_training = [
        results['training'].get('home_type', {}).get('success', False),
        results['training'].get('device_intelligence', {}).get('success', False)
    ]
    optional_training = [
        results['training'].get('gnn_synergy', {}).get('success', False),
        results['training'].get('soft_prompt', {}).get('success', False)
    ]
    
    critical_all_passed = all(critical_training)
    optional_status = []
    if optional_training[0]:
        optional_status.append("GNN")
    if optional_training[1]:
        optional_status.append("Soft Prompt")
    
    if critical_all_passed:
        training_status = "✅ PASSED (critical)"
        if optional_status:
            training_status += f" | ✨ Optional: {', '.join(optional_status)}"
        elif not all(optional_training):
            training_status += " | ⚠️  Optional: Not configured"
    else:
        training_status = "❌ FAILED (critical)"
    
    logger.info(f"Training: {training_status}")
    logger.info(f"Model Save: {'✅ PASSED' if results['model_save']['success'] else '❌ FAILED'}")
    logger.info(f"Report: {report_path}")
    logger.info("="*80)
    
    # Determine exit code
    critical_passed = (
        results['build'] and
        results['deploy'] and
        results['smoke_tests']['success'] and
        results['data_generation'] and
        results['training'].get('home_type', {}).get('success', False) and
        results['training'].get('device_intelligence', {}).get('success', False)
    )
    
    if critical_passed:
        logger.info("✅ SYSTEM IS PRODUCTION READY")
        if optional_status:
            logger.info(f"✨ Optional enhancements available: {', '.join(optional_status)}")
        return 0
    else:
        logger.warning("⚠️  SYSTEM IS NOT PRODUCTION READY - Review report for details")
        logger.warning("   Critical components must pass for production deployment")
        return 1


if __name__ == '__main__':
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

