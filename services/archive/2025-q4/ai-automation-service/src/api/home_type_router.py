"""
Home Type API Router

API endpoints for home type profiling and classification.

Endpoints:
- GET /api/home-type/profile - Get current home type profile
- GET /api/home-type/classify - Classify home type using pre-trained model
- GET /api/home-type/model-info - Get model metadata
"""

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from ..clients.data_api_client import DataAPIClient
from ..config import settings
from ..home_type.production_classifier import ProductionHomeTypeClassifier
from ..home_type.production_profiler import ProductionHomeTypeProfiler

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/home-type",
    tags=["home-type"]
)

# Initialize clients and components
_data_api_client = None
_profiler = None
_classifier = None


def get_data_api_client() -> DataAPIClient:
    """Get or create DataAPIClient."""
    global _data_api_client
    if _data_api_client is None:
        _data_api_client = DataAPIClient(
            base_url=settings.data_api_url,
            influxdb_url=settings.influxdb_url,
            influxdb_token=settings.influxdb_token,
            influxdb_org=settings.influxdb_org,
            influxdb_bucket=settings.influxdb_bucket
        )
    return _data_api_client


def get_profiler() -> ProductionHomeTypeProfiler:
    """Get or create ProductionHomeTypeProfiler."""
    global _profiler
    if _profiler is None:
        _profiler = ProductionHomeTypeProfiler(get_data_api_client())
    return _profiler


def get_classifier() -> ProductionHomeTypeClassifier:
    """Get or create ProductionHomeTypeClassifier."""
    global _classifier
    if _classifier is None:
        # Default model path
        model_path = Path(__file__).parent.parent.parent.parent / "models" / "home_type_classifier.pkl"
        _classifier = ProductionHomeTypeClassifier(model_path)
    return _classifier


@router.get("/profile")
async def get_home_profile(home_id: str = "default"):
    """
    Get current home type profile.
    
    Returns comprehensive home profile including:
    - Device composition
    - Event patterns
    - Spatial layout
    - Behavior patterns
    """
    try:
        profiler = get_profiler()
        profile = await profiler.profile_current_home(home_id=home_id)
        return {
            "status": "success",
            "home_id": home_id,
            "profile": profile
        }
    except Exception as e:
        logger.error(f"Failed to profile home: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/classify")
async def classify_home_type(home_id: str = "default"):
    """
    Classify home type using pre-trained model.
    
    Returns:
    - home_type: Classified home type
    - confidence: Confidence score (0-1)
    - method: Classification method ('ml_model')
    - model_version: Model version used
    """
    try:
        profiler = get_profiler()
        classifier = get_classifier()
        
        # Profile home
        profile = await profiler.profile_current_home(home_id=home_id)
        
        # Classify
        classification = await classifier.classify_home(profile)
        
        return {
            "status": "success",
            "home_id": home_id,
            "classification": classification
        }
    except Exception as e:
        logger.error(f"Failed to classify home: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/model-info")
async def get_model_info():
    """
    Get model metadata.
    
    Returns:
    - is_loaded: Whether model is loaded
    - model_version: Model version
    - training_date: Training date
    - class_names: Available home type classes
    - feature_names: Feature names used
    """
    try:
        classifier = get_classifier()
        info = classifier.get_model_info()
        return {
            "status": "success",
            "model_info": info
        }
    except Exception as e:
        logger.error(f"Failed to get model info: {e}")
        raise HTTPException(status_code=500, detail=str(e))

