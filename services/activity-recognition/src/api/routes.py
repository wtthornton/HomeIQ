"""
API Routes for Activity Recognition Service

Provides REST API endpoints for:
- Activity prediction from sensor sequences
- Current activity status
- Activity history
"""

import logging
from pathlib import Path
from typing import Any

import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["activity"])


# ============================================================================
# Pydantic Models
# ============================================================================

class SensorReading(BaseModel):
    """Single sensor reading."""
    
    motion: float = Field(0.0, description="Motion sensor value (0 or 1)")
    door: float = Field(0.0, description="Door sensor value (0 or 1)")
    temperature: float = Field(20.0, description="Temperature in Celsius")
    humidity: float = Field(50.0, description="Humidity percentage")
    power: float = Field(0.0, description="Power consumption in Watts")


class SensorSequence(BaseModel):
    """Sequence of sensor readings for prediction."""
    
    readings: list[SensorReading] = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Sequence of sensor readings"
    )


class ActivityPrediction(BaseModel):
    """Activity prediction result."""
    
    activity: str = Field(..., description="Predicted activity name")
    activity_id: int = Field(..., description="Activity class ID")
    confidence: float = Field(..., description="Prediction confidence (0-1)")
    probabilities: dict[str, float] = Field(
        ..., description="Probabilities for all activities"
    )


class CurrentActivityResponse(BaseModel):
    """Current activity status."""
    
    activity: str
    activity_id: int
    confidence: float
    last_updated: str
    sensor_summary: dict[str, float]


class HealthResponse(BaseModel):
    """Health check response."""
    
    status: str
    service: str
    version: str
    model_loaded: bool


# ============================================================================
# Global Model Instance
# ============================================================================

_onnx_session = None
_model_path = Path("./models/activity_lstm.onnx")

# Activity labels
ACTIVITIES = {
    0: "sleeping",
    1: "waking",
    2: "leaving",
    3: "arriving",
    4: "cooking",
    5: "eating",
    6: "working",
    7: "watching_tv",
    8: "relaxing",
    9: "other",
}


def get_model():
    """Get the loaded ONNX model session."""
    global _onnx_session
    if _onnx_session is None:
        raise HTTPException(
            status_code=503,
            detail="Model not loaded. Please ensure the ONNX model is available."
        )
    return _onnx_session


def load_model(path: Path | str | None = None) -> bool:
    """Load the ONNX model."""
    global _onnx_session, _model_path
    
    try:
        import onnxruntime as ort
    except ImportError:
        logger.error("onnxruntime not installed")
        return False
    
    if path is not None:
        _model_path = Path(path)
    
    if not _model_path.exists():
        logger.warning(f"Model file not found at {_model_path}")
        return False
    
    try:
        _onnx_session = ort.InferenceSession(
            str(_model_path),
            providers=["CPUExecutionProvider"],
        )
        logger.info(f"Loaded ONNX model from {_model_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        return False


# ============================================================================
# Helper Functions
# ============================================================================

def readings_to_array(readings: list[SensorReading]) -> np.ndarray:
    """Convert sensor readings to numpy array."""
    features = []
    for r in readings:
        features.append([
            r.motion,
            r.door,
            r.temperature,
            r.humidity,
            r.power,
        ])
    return np.array(features, dtype=np.float32)


def predict_activity(sensor_array: np.ndarray) -> tuple[int, np.ndarray]:
    """
    Run activity prediction.
    
    Args:
        sensor_array: Shape (seq_len, n_features)
        
    Returns:
        Tuple of (predicted_class, probabilities)
    """
    session = get_model()
    
    # Add batch dimension
    input_array = sensor_array[np.newaxis, :, :]
    
    # Run inference
    input_name = session.get_inputs()[0].name
    output_name = session.get_outputs()[0].name
    
    logits = session.run([output_name], {input_name: input_array})[0]
    
    # Convert to probabilities using numerically stable softmax
    # Subtract max for numerical stability (prevents overflow)
    if logits.ndim == 1:
        logits_stable = logits - np.max(logits)
        exp_logits = np.exp(logits_stable)
        probs = exp_logits / np.sum(exp_logits)
        predicted_class = int(np.argmax(logits))
    else:
        logits_stable = logits - np.max(logits, axis=1, keepdims=True)
        exp_logits = np.exp(logits_stable)
        probs = exp_logits / np.sum(exp_logits, axis=1, keepdims=True)
        predicted_class = int(np.argmax(logits, axis=1)[0])
        probs = probs[0]
    
    return predicted_class, probs[0]


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        service="activity-recognition",
        version="1.0.0",
        model_loaded=_onnx_session is not None,
    )


@router.post("/predict", response_model=ActivityPrediction)
async def predict(sequence: SensorSequence):
    """
    Predict activity from sensor sequence.
    
    Requires a sequence of sensor readings (minimum 10, recommended 30).
    """
    if len(sequence.readings) < 10:
        raise HTTPException(
            status_code=400,
            detail="Sequence must have at least 10 readings"
        )
    
    # Convert to array
    sensor_array = readings_to_array(sequence.readings)
    
    # Predict
    predicted_class, probs = predict_activity(sensor_array)
    
    # Build response
    activity_name = ACTIVITIES.get(predicted_class, "unknown")
    confidence = float(probs[predicted_class])
    
    probabilities = {
        ACTIVITIES[i]: float(probs[i])
        for i in range(len(probs))
        if i in ACTIVITIES
    }
    
    return ActivityPrediction(
        activity=activity_name,
        activity_id=predicted_class,
        confidence=confidence,
        probabilities=probabilities,
    )


@router.get("/activities", response_model=dict[int, str])
async def list_activities():
    """List all supported activity classes."""
    return ACTIVITIES


@router.get("/model/info")
async def get_model_info() -> dict[str, Any]:
    """Get information about the loaded model."""
    if _onnx_session is None:
        return {
            "loaded": False,
            "model_path": str(_model_path),
        }
    
    inputs = _onnx_session.get_inputs()
    outputs = _onnx_session.get_outputs()
    
    return {
        "loaded": True,
        "model_path": str(_model_path),
        "inputs": [
            {
                "name": inp.name,
                "shape": inp.shape,
                "type": inp.type,
            }
            for inp in inputs
        ],
        "outputs": [
            {
                "name": out.name,
                "shape": out.shape,
                "type": out.type,
            }
            for out in outputs
        ],
    }
