"""
Model saving and management for production readiness pipeline.
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Tuple

from .config import AI_SERVICE_DIR, DEVICE_INTELLIGENCE_DIR

logger = logging.getLogger(__name__)


def save_models(output_dir: Path) -> Tuple[bool, dict]:
    """Save and verify all trained models."""
    logger.info("=" * 80)
    logger.info("STEP 6: Saving Models")
    logger.info("=" * 80)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    manifest = {
        'timestamp': datetime.now().isoformat(),
        'models': {}
    }
    
    # Home Type Classifier
    model_path = AI_SERVICE_DIR / "models" / "home_type_classifier.pkl"
    metadata_path = AI_SERVICE_DIR / "models" / "home_type_classifier_metadata.json"
    results_path = AI_SERVICE_DIR / "models" / "home_type_classifier_results.json"
    
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
    di_models_dir = DEVICE_INTELLIGENCE_DIR / "models"
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
    gnn_model = AI_SERVICE_DIR / "models" / "gnn_synergy.pth"
    gnn_metadata = AI_SERVICE_DIR / "models" / "gnn_synergy_metadata.json"
    
    if gnn_model.exists():
        manifest['models']['gnn_synergy'] = {
            'model': str(gnn_model),
            'metadata': str(gnn_metadata) if gnn_metadata.exists() else None,
            'size_bytes': gnn_model.stat().st_size
        }
        logger.info(f"✅ GNN synergy: {gnn_model}")
    
    # Soft Prompt
    soft_prompt_dir = AI_SERVICE_DIR / "models" / "soft_prompts"
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

