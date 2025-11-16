# Model Training Guide
## Device Intelligence Service

**Last Updated:** 2025-11-16  
**Version:** 1.0

---

## Overview

This guide provides detailed instructions for training, updating, and managing the Machine Learning models used by the Device Intelligence Service for predictive analytics (failure prediction and anomaly detection).

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Training Methods](#training-methods)
3. [Training Data](#training-data)
4. [Model Validation](#model-validation)
5. [Model Versioning](#model-versioning)
6. [Troubleshooting](#troubleshooting)
7. [Best Practices](#best-practices)

---

## Quick Start

### Train Models via API

```bash
# Train with default settings (180 days of historical data)
curl -X POST http://localhost:8028/api/predictions/train \
  -H "Content-Type: application/json" \
  -d '{"force_retrain": false}'
```

### Train Models via Standalone Script

```bash
# From the service directory
cd services/device-intelligence-service

# Train with default settings
python scripts/train_models.py

# Force retrain with custom parameters
python scripts/train_models.py --days-back 90 --force --verbose
```

---

## Training Methods

### Method 1: API Endpoint (Recommended for Production)

**Endpoint:** `POST /api/predictions/train`

**Request Body:**
```json
{
  "force_retrain": false,
  "days_back": 180
}
```

**Parameters:**
- `force_retrain` (boolean, default: `false`): Force retraining even if models already exist
- `days_back` (integer, default: `180`): Number of days of historical data to use for training

**Response:**
```json
{
  "message": "Model training started",
  "status": "training",
  "force_retrain": false,
  "days_back": 180,
  "started_at": "2025-11-16T22:40:51.470818+00:00"
}
```

**Example:**
```bash
# Check model status before training
curl http://localhost:8028/api/predictions/models/status

# Start training
curl -X POST http://localhost:8028/api/predictions/train \
  -H "Content-Type: application/json" \
  -d '{"force_retrain": true, "days_back": 90}'

# Check status after training (wait a few seconds)
curl http://localhost:8028/api/predictions/models/status
```

### Method 2: Standalone Script (Recommended for Scheduled Training)

**Location:** `scripts/train_models.py`

**Usage:**
```bash
python scripts/train_models.py [OPTIONS]
```

**Options:**
- `--days-back N`: Number of days of historical data (default: 180)
- `--force`: Force retrain even if models exist
- `--verbose`: Enable verbose logging

**Examples:**
```bash
# Basic training
python scripts/train_models.py

# Custom time window
python scripts/train_models.py --days-back 90

# Force retrain with verbose output
python scripts/train_models.py --force --verbose

# Full example
python scripts/train_models.py --days-back 120 --force --verbose
```

**Output:**
The script provides detailed training progress and results:
```
================================================================================
ML Model Training Script
================================================================================
Days back: 180
Force retrain: False

📊 Initializing database connection...
✅ Database initialized
🤖 Creating predictive analytics engine...
🚀 Starting model training...

📊 Collecting training data from last 180 days...
✅ Collected 250 training samples from 45 devices
📊 Model performance: Accuracy=0.875, Precision=0.820, Recall=0.780, F1=0.800
✅ Models trained, validated, and saved successfully (version 1.0.2)

================================================================================
✅ Training Complete!
================================================================================
Model Version: 1.0.2
Training Date: 2025-11-16T22:40:51.470818+00:00
Data Source: database
Training Duration: 2.45 seconds

Training Data Stats:
  - Sample Count: 250
  - Unique Devices: 45
  - Days Back: 180

Model Performance:
  - Accuracy: 0.875
  - Precision: 0.820
  - Recall: 0.780
  - F1 Score: 0.800
================================================================================
```

### Method 3: Automatic Training (On Startup)

Models are automatically trained when:
- No pre-trained models exist in the `models/` directory
- Models fail to load during initialization
- Service starts for the first time

This ensures the service always has working models available.

---

## Training Data

### Data Sources

The training process uses data from the following sources (in priority order):

1. **Database (`device_health_metrics` table)** - Primary source
   - Historical device metrics from the last N days
   - Aggregated by device and time window
   - Real production data

2. **Sample Data** - Fallback source
   - Generated synthetic data
   - Used when database has insufficient historical data
   - Ensures training can always proceed

### Data Requirements

**Minimum Requirements:**
- At least 50 training samples (devices)
- At least 100 total data points
- Data spanning multiple days (for time-based features)

**Optimal Requirements:**
- 200+ training samples
- 30+ days of historical data
- Data from 20+ unique devices
- Balanced distribution of device types

### Data Collection Process

1. **Query Database**: Retrieves metrics from `device_health_metrics` table
2. **Filter by Date**: Only includes metrics from the last N days (default: 180)
3. **Aggregate by Device**: Groups metrics by device_id
4. **Extract Features**: Maps metrics to feature columns:
   - `response_time`, `error_rate`, `battery_level`
   - `signal_strength`, `usage_frequency`, `temperature`
   - `humidity`, `uptime_hours`, `restart_count`
   - `connection_drops`, `data_transfer_rate`
5. **Validate Data**: Checks data quality and completeness
6. **Fallback**: Uses sample data if validation fails

### Feature Mapping

The system automatically maps database metrics to training features:

| Feature Column | Possible Metric Names |
|---------------|----------------------|
| `response_time` | response_time, latency, delay |
| `error_rate` | error_rate, errors, error_count |
| `battery_level` | battery, battery_level, battery_percentage |
| `signal_strength` | signal, signal_strength, rssi |
| `usage_frequency` | usage, usage_frequency, activity |
| `temperature` | temperature, temp |
| `humidity` | humidity, hum |
| `restart_count` | restart, restart_count, reboot |
| `connection_drops` | connection_drops, disconnects, drop |
| `data_transfer_rate` | data_rate, transfer_rate, throughput |

If a metric name doesn't match, default values are used.

---

## Model Validation

### Validation Process

Models are automatically validated before saving:

1. **Performance Thresholds:**
   - Accuracy ≥ 50%
   - Precision ≥ 30%
   - Recall ≥ 30%

2. **Functionality Tests:**
   - Prediction test on sample data
   - Anomaly detection test
   - Model loading test

3. **Verification:**
   - Saved models are loaded and tested
   - Predictions verified with dummy data

### Validation Results

Validation results are stored in model metadata:

```json
{
  "validation": {
    "valid": true,
    "reason": "All validation checks passed",
    "checks": {
      "accuracy": {
        "value": 0.875,
        "threshold": 0.5,
        "passed": true
      },
      "precision": {
        "value": 0.820,
        "threshold": 0.3,
        "passed": true
      },
      "recall": {
        "value": 0.780,
        "threshold": 0.3,
        "passed": true
      },
      "prediction_test": {
        "passed": true,
        "sample_predictions": true,
        "sample_proba_shape": true
      },
      "anomaly_test": {
        "passed": true,
        "sample_predictions": true,
        "sample_scores": true
      }
    }
  }
}
```

### Handling Validation Failures

If validation fails:
- Models are **not saved**
- Existing models remain in use
- Error is logged with details
- Training can be retried with different parameters

---

## Model Versioning

### Version Format

Models use semantic versioning: `MAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes (model architecture changes)
- **MINOR**: New features (new model types, significant improvements)
- **PATCH**: Bug fixes, performance improvements

### Version Incrementing

- Versions are automatically incremented on each training
- Patch version is incremented by default
- Version is stored in `model_metadata.json`

### Model Metadata

Each trained model includes comprehensive metadata:

```json
{
  "version": "1.0.2",
  "training_date": "2025-11-16T22:40:51.470818+00:00",
  "training_data_stats": {
    "sample_count": 250,
    "unique_devices": 45,
    "days_back": 180
  },
  "model_performance": {
    "accuracy": 0.875,
    "precision": 0.820,
    "recall": 0.780,
    "f1_score": 0.800
  },
  "scikit_learn_version": "1.7.2",
  "feature_columns": [...],
  "training_parameters": {
    "n_estimators": 100,
    "max_depth": 10,
    "contamination": 0.1
  },
  "data_source": "database",
  "training_duration_seconds": 2.45,
  "validation": {...}
}
```

### Model Backup

Before saving new models:
- Existing models are automatically backed up
- Backup files are timestamped: `model.pkl.backup_YYYYMMDD_HHMMSS`
- Backups allow rollback if needed

---

## Troubleshooting

### Issue: "Insufficient training data"

**Symptoms:**
- Warning: "⚠️ Insufficient training data, using rule-based predictions"
- Models not trained

**Solutions:**
1. **Wait for more data**: Allow the system to collect more historical metrics
2. **Reduce days_back**: Use a shorter time window (e.g., 30 days instead of 180)
3. **Check database**: Verify `device_health_metrics` table has data
4. **Use sample data**: System will automatically fall back to sample data

### Issue: "Model validation failed"

**Symptoms:**
- Training completes but models not saved
- Validation errors in logs

**Solutions:**
1. **Check performance metrics**: Review accuracy, precision, recall values
2. **Increase training data**: More data usually improves performance
3. **Adjust thresholds**: Modify validation thresholds if needed (in code)
4. **Check data quality**: Ensure training data has sufficient variation

### Issue: "Database not initialized"

**Symptoms:**
- Error: "Database not initialized"
- Training falls back to sample data

**Solutions:**
1. **Check database connection**: Verify database is accessible
2. **Check service startup**: Ensure database initialized before training
3. **Review logs**: Check for database initialization errors

### Issue: "Models not loading"

**Symptoms:**
- Service starts but models not available
- Predictions fail

**Solutions:**
1. **Check model files**: Verify `.pkl` files exist in `models/` directory
2. **Check permissions**: Ensure service can read model files
3. **Check version compatibility**: Verify scikit-learn version matches
4. **Retrain models**: Force retrain to regenerate models

### Issue: "Training takes too long"

**Symptoms:**
- Training exceeds expected duration
- Timeout errors

**Solutions:**
1. **Reduce days_back**: Use shorter time window
2. **Limit sample count**: Reduce number of training samples
3. **Check database performance**: Optimize database queries
4. **Monitor resources**: Check CPU and memory usage

---

## Best Practices

### Training Frequency

**Recommended Schedule:**
- **Weekly**: For active systems with frequent data collection
- **Monthly**: For stable systems with consistent data
- **After major changes**: When device types or metrics change significantly

**Automated Training:**
```bash
# Add to crontab for weekly training (Sundays at 2 AM)
0 2 * * 0 cd /path/to/service && python scripts/train_models.py --force
```

### Data Quality

1. **Ensure sufficient data**: Aim for 200+ samples from 20+ devices
2. **Monitor data collection**: Verify metrics are being stored regularly
3. **Check data freshness**: Use recent data (last 180 days)
4. **Validate metrics**: Ensure metric names match expected patterns

### Model Monitoring

1. **Track performance**: Monitor accuracy, precision, recall over time
2. **Compare versions**: Track performance changes between versions
3. **Set alerts**: Alert if performance degrades significantly
4. **Review predictions**: Periodically review prediction quality

### Backup Strategy

1. **Automatic backups**: System creates backups automatically
2. **Manual backups**: Copy `models/` directory before major updates
3. **Version control**: Consider committing model metadata to git
4. **Retention**: Keep backups for at least 30 days

### Performance Optimization

1. **Training time**: Typically 1-5 seconds for 200 samples
2. **Prediction latency**: <10ms per prediction
3. **Memory usage**: ~50-100MB for loaded models
4. **Disk space**: ~5-10MB per model set

---

## Advanced Topics

### Custom Training Parameters

To modify training parameters, edit `src/core/predictive_analytics.py`:

```python
training_params = {
    "n_estimators": 100,      # Number of trees (increase for better accuracy)
    "max_depth": 10,          # Max tree depth (increase for complex patterns)
    "contamination": 0.1,     # Anomaly detection threshold
    "test_size": 0.2,         # Test set size (20%)
    "random_state": 42        # Reproducibility
}
```

### Custom Validation Thresholds

Modify validation thresholds in `_validate_models()`:

```python
min_accuracy = 0.5   # Minimum accuracy (50%)
min_precision = 0.3  # Minimum precision (30%)
min_recall = 0.3     # Minimum recall (30%)
```

### Training with Custom Data

To train with custom data:

```python
from src.core.predictive_analytics import PredictiveAnalyticsEngine

engine = PredictiveAnalyticsEngine()
custom_data = [...]  # Your custom training data
await engine.train_models(historical_data=custom_data)
```

---

## API Reference

### Get Model Status

```bash
GET /api/predictions/models/status
```

Returns current model status, version, and performance metrics.

### Train Models

```bash
POST /api/predictions/train
Content-Type: application/json

{
  "force_retrain": false,
  "days_back": 180
}
```

Starts model training in the background.

---

## Support

For issues or questions:
1. Check logs: `docker compose logs device-intelligence-service`
2. Review model metadata: `GET /api/predictions/models/status`
3. Check training script output: Review `training.log` file
4. Consult service documentation: See main README.md

---

**Document Version:** 1.0  
**Last Updated:** 2025-11-16

