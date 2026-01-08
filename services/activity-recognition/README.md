# Activity Recognition Service

ML-powered activity recognition from smart home sensor data for HomeIQ.

## Overview

This service recognizes household activities from sensor sequences using an LSTM neural network:
- **Input**: Sequences of sensor readings (motion, door, temperature, humidity, power)
- **Output**: Activity classification with confidence scores

## Supported Activities

| ID | Activity | Description |
|----|----------|-------------|
| 0 | sleeping | Nighttime sleep |
| 1 | waking | Morning routine |
| 2 | leaving | Leaving home |
| 3 | arriving | Coming home |
| 4 | cooking | Meal preparation |
| 5 | eating | Mealtime |
| 6 | working | Work/study |
| 7 | watching_tv | Entertainment |
| 8 | relaxing | Leisure time |
| 9 | other | Unclassified |

## Port

- **Internal**: 8036
- **External**: 8036

## API Endpoints

### Health & Info

- `GET /api/v1/health` - Health check
- `GET /api/v1/model/info` - Model information
- `GET /api/v1/activities` - List supported activities

### Prediction

- `POST /api/v1/predict` - Predict activity from sensor sequence

## Usage

### Predict Activity

```python
import httpx

# Prepare sensor sequence (minimum 10 readings)
readings = [
    {"motion": 1, "door": 0, "temperature": 21.5, "humidity": 45, "power": 150}
    for _ in range(30)
]

response = httpx.post(
    "http://localhost:8036/api/v1/predict",
    json={"readings": readings}
)

result = response.json()
print(f"Activity: {result['activity']}")
print(f"Confidence: {result['confidence']:.2%}")
```

## Training

```python
from src.data.sensor_loader import SensorDataLoader
from src.models.activity_classifier import ActivityLSTM, ActivityTrainer, export_to_onnx

# Load data
loader = SensorDataLoader()
df = loader.load_smart_star()

# Create sequences
X, y = loader.create_sequences(df)

# Train model
model = ActivityLSTM(input_size=5, hidden_size=64, num_classes=10)
trainer = ActivityTrainer(model)
trainer.train(train_loader, val_loader, num_epochs=50)

# Export to ONNX
export_to_onnx(model, "models/activity_lstm.onnx")
```

## Docker

```bash
# Build
docker build -t homeiq-activity-recognition .

# Run
docker run -p 8036:8036 -v ./models:/app/models homeiq-activity-recognition
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8036` | Service port |
| `HOST` | `0.0.0.0` | Bind address |
| `MODEL_PATH` | `./models/activity_lstm.onnx` | Path to ONNX model |
| `DEBUG` | `false` | Enable debug mode |
| `OMP_NUM_THREADS` | `4` | ONNX Runtime threads |

## Integration with HomeIQ

This service integrates with:
- **ai-pattern-service**: Activity-based synergy detection
- **websocket-ingestion**: Real-time sensor data processing
- **health-dashboard**: Activity status display
