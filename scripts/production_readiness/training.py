"""
Model training steps for production readiness pipeline.
"""
import json
import logging
import sys
from pathlib import Path
from typing import Tuple

from .config import AI_SERVICE_DIR, DEVICE_INTELLIGENCE_DIR
from .helpers import format_error_message, run_command, validate_model_quality

logger = logging.getLogger(__name__)


async def train_home_type_classifier(synthetic_homes_dir: Path, allow_low_quality: bool = False) -> Tuple[bool, dict]:
    """Train home type classifier model."""
    logger.info("Training Home Type Classifier...")
    
    model_dir = AI_SERVICE_DIR / "models"
    model_dir.mkdir(parents=True, exist_ok=True)
    model_path = model_dir / "home_type_classifier.pkl"
    
    cmd = [
        sys.executable,
        str(AI_SERVICE_DIR / "scripts" / "train_home_type_classifier.py"),
        "--synthetic-homes", str(synthetic_homes_dir),
        "--output", str(model_path),
        "--test-size", "0.2"
    ]
    
    exit_code, stdout, stderr = run_command(cmd, cwd=AI_SERVICE_DIR, check=False)
    
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
    
    # Validate model quality
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


async def train_device_intelligence(allow_low_quality: bool = False) -> Tuple[bool, dict]:
    """Train device intelligence models with synthetic data."""
    logger.info("Training Device Intelligence Models...")
    
    logger.info("Generating synthetic device data for initial training...")
    use_synthetic = False
    try:
        sys.path.insert(0, str(DEVICE_INTELLIGENCE_DIR))
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
        str(DEVICE_INTELLIGENCE_DIR / "scripts" / "train_models.py"),
        "--force",
        "--verbose"
    ]
    
    if use_synthetic:
        cmd.extend(["--synthetic-data", "--synthetic-count", "1000"])
        logger.info("   Using synthetic data for training")
    
    exit_code, stdout, stderr = run_command(cmd, cwd=DEVICE_INTELLIGENCE_DIR, check=False)
    
    if exit_code != 0:
        logger.error(f"Device intelligence training failed:\n{stderr}")
        return False, {}
    
    # Load metadata if available
    metadata_path = DEVICE_INTELLIGENCE_DIR / "models" / "model_metadata.json"
    results = {}
    if metadata_path.exists():
        try:
            with open(metadata_path, 'r', encoding='utf-8') as f:
                results = json.load(f)
        except Exception:
            pass
    
    # Validate model quality
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


async def train_gnn_synergy() -> Tuple[bool, dict]:
    """Train GNN synergy detector model."""
    logger.info("Training GNN Synergy Detector...")
    
    script_path = AI_SERVICE_DIR / "scripts" / "train_gnn_synergy.py"
    if not script_path.exists():
        logger.warning("GNN training script not found, skipping")
        return True, {}
    
    cmd = [sys.executable, str(script_path)]
    exit_code, stdout, stderr = run_command(cmd, cwd=AI_SERVICE_DIR, check=False)
    
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


async def train_soft_prompt() -> Tuple[bool, dict]:
    """Train soft prompt model."""
    logger.info("Training Soft Prompt...")
    
    script_path = AI_SERVICE_DIR / "scripts" / "train_soft_prompt.py"
    if not script_path.exists():
        logger.warning("Soft prompt training script not found, skipping")
        return True, {}
    
    cmd = [sys.executable, str(script_path)]
    exit_code, stdout, stderr = run_command(cmd, cwd=AI_SERVICE_DIR, check=False)
    
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
    logger.info("=" * 80)
    logger.info("STEP 5: Training All Models")
    logger.info("=" * 80)
    
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

