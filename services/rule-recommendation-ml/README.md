# Rule Recommendation ML Service

ML-powered rule recommendation service for HomeIQ based on the Wyze Rule Recommendation dataset.

## Overview

This service provides personalized automation rule recommendations using:
- **Wyze Rule Recommendation Dataset**: 1M+ real automation rules from 300K+ users
- **Collaborative Filtering**: ALS (Alternating Least Squares) algorithm
- **Device Matching**: Maps Wyze devices to Home Assistant domains

## Features

- **Personalized Recommendations**: Based on user's existing automations
- **Device-Based Recommendations**: Based on user's device inventory
- **Similar Rules**: Find rules similar to a given pattern
- **Popular Rules**: Fallback to most popular patterns
- **Feedback Loop**: Collect user feedback for model improvement

## Port

- **Internal**: 8035
- **External**: 8035

## API Endpoints

### Health & Info

- `GET /api/v1/health` - Health check
- `GET /api/v1/model/info` - Model information and statistics

### Recommendations

- `GET /api/v1/rule-recommendations` - Get personalized recommendations
  - `?user_id=<id>` - For personalized recommendations
  - `?device_domains=light,switch` - For device-based recommendations
  - `?limit=10` - Number of recommendations

- `GET /api/v1/rule-recommendations/similar` - Get similar rules
  - `?rule_pattern=binary_sensor_to_light` - Pattern to find similar rules for

- `GET /api/v1/rule-recommendations/popular` - Get popular rules

### Feedback

- `POST /api/v1/rule-recommendations/feedback` - Submit feedback

## Training the Model

```python
from src.data.wyze_loader import WyzeDataLoader
from src.models.rule_recommender import RuleRecommender

# Load and preprocess data
loader = WyzeDataLoader()
df = loader.load()

# Create user-rule matrix
matrix, idx_to_user, idx_to_pattern = loader.get_user_rule_matrix(df)

# Train model
recommender = RuleRecommender(factors=64, iterations=50)
recommender.fit(matrix, idx_to_user, idx_to_pattern)

# Save model
recommender.save("models/rule_recommender.pkl")
```

## Docker

```bash
# Build
docker build -t homeiq-rule-recommendation-ml .

# Run
docker run -p 8035:8035 homeiq-rule-recommendation-ml
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8035` | Service port |
| `HOST` | `0.0.0.0` | Bind address |
| `MODEL_PATH` | `./models/rule_recommender.pkl` | Path to trained model |
| `DEBUG` | `false` | Enable debug mode |
| `CORS_ORIGINS` | `*` | Allowed CORS origins |

## Dependencies

- `polars>=1.0.0` - Fast data processing
- `datasets>=3.0.0` - Hugging Face datasets
- `implicit>=0.7.0` - Collaborative filtering
- `fastapi>=0.115.0` - API framework
- `uvicorn>=0.30.0` - ASGI server

## Integration with HomeIQ

This service integrates with:
- **ai-pattern-service**: Enhances blueprint opportunity scoring
- **health-dashboard**: Displays recommendations in Synergies tab
- **ai-automation-service**: Provides recommendations during automation creation
