# Production Operations Guide
## Device Intelligence Service - ML Model Management

**Last Updated:** 2025-11-16  
**Version:** 1.0

---

## Overview

This guide covers production operations for managing ML models in the Device Intelligence Service, including scheduled retraining, monitoring, and maintenance.

---

## Scheduled Model Retraining

### Option 1: Linux/Unix (Cron)

**Weekly Training (Sundays at 2 AM):**

```bash
# Edit crontab
crontab -e

# Add this line:
0 2 * * 0 cd /path/to/services/device-intelligence-service && python scripts/train_models.py --force --days-back 180 >> training.log 2>&1
```

**Monthly Training (1st of month at 2 AM):**

```bash
0 2 1 * * cd /path/to/services/device-intelligence-service && python scripts/train_models.py --force --days-back 180 >> training.log 2>&1
```

**Using the provided script:**

```bash
# Make script executable
chmod +x scripts/schedule_model_training.sh

# Add to crontab
0 2 * * 0 /path/to/services/device-intelligence-service/scripts/schedule_model_training.sh
```

### Option 2: Windows (Task Scheduler)

1. Open Task Scheduler
2. Create Basic Task
3. Set trigger (e.g., Weekly on Sunday at 2 AM)
4. Set action: Start a program
5. Program: `powershell.exe`
6. Arguments: `-File "C:\path\to\services\device-intelligence-service\scripts\schedule_model_training.ps1"`

### Option 3: Docker Container (Cron)

Add to Dockerfile or docker-compose.yml:

```yaml
services:
  device-intelligence-service:
    # ... existing config ...
    volumes:
      - ./scripts:/app/scripts
    # Install cron in container and add cron job
```

Or use a separate cron container that calls the API:

```yaml
  model-trainer:
    image: curlimages/curl:latest
    command: >
      sh -c "
      while true; do
        sleep 604800
        curl -X POST http://device-intelligence-service:8019/api/predictions/train
          -H 'Content-Type: application/json'
          -d '{\"force_retrain\": true, \"days_back\": 180}'
      done
      "
    depends_on:
      - device-intelligence-service
```

### Option 4: Kubernetes CronJob

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: model-training
spec:
  schedule: "0 2 * * 0"  # Every Sunday at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: train-models
            image: homeiq-device-intelligence-service:latest
            command:
            - python
            - scripts/train_models.py
            - --force
            - --days-back
            - "180"
          restartPolicy: OnFailure
```

---

## Monitoring Model Performance

### Check Model Status

```bash
# Get current model status
curl http://localhost:8028/api/predictions/models/status | jq

# Compare with previous version
curl http://localhost:8028/api/predictions/models/compare | jq
```

### Monitor Training Logs

```bash
# View training logs
docker compose logs device-intelligence-service | grep -i "training\|model\|validation"

# View training script logs
tail -f services/device-intelligence-service/training.log
```

### Set Up Alerts

**Example: Alert if model performance degrades**

```bash
#!/bin/bash
# check_model_performance.sh

THRESHOLD=0.7
CURRENT_ACCURACY=$(curl -s http://localhost:8028/api/predictions/models/status | jq -r '.model_metadata.model_performance.accuracy')

if (( $(echo "$CURRENT_ACCURACY < $THRESHOLD" | bc -l) )); then
    echo "ALERT: Model accuracy ($CURRENT_ACCURACY) below threshold ($THRESHOLD)"
    # Send alert (email, Slack, etc.)
fi
```

---

## Model Maintenance

### Backup Models

**Manual Backup:**

```bash
# Backup entire models directory
tar -czf models_backup_$(date +%Y%m%d).tar.gz models/

# Or copy to backup location
cp -r models/ backups/models_$(date +%Y%m%d)/
```

**Automatic Backups:**

Models are automatically backed up before retraining. Backups are stored in the `models/` directory with timestamps:
- `failure_prediction_model.pkl.backup_YYYYMMDD_HHMMSS`
- `model_metadata.json.backup_YYYYMMDD_HHMMSS`

### Restore Models

```bash
# Restore from automatic backup
cd services/device-intelligence-service/models
cp failure_prediction_model.pkl.backup_20251116_020000 failure_prediction_model.pkl
cp model_metadata.json.backup_20251116_020000 model_metadata.json

# Restart service
docker compose restart device-intelligence-service
```

### Clean Up Old Backups

```bash
# Keep only last 10 backups
cd services/device-intelligence-service/models
ls -t *.backup_* | tail -n +11 | xargs rm -f
```

---

## Performance Monitoring

### Key Metrics to Monitor

1. **Model Performance:**
   - Accuracy (should be > 0.7)
   - Precision (should be > 0.5)
   - Recall (should be > 0.5)
   - F1 Score (should be > 0.6)

2. **Training Metrics:**
   - Training duration (typically 1-5 seconds)
   - Training data sample count (should be > 100)
   - Data source (database vs sample)

3. **Prediction Metrics:**
   - Prediction latency (< 10ms per prediction)
   - Prediction accuracy (monitor over time)

### Monitoring Script

```bash
#!/bin/bash
# monitor_models.sh

STATUS=$(curl -s http://localhost:8028/api/predictions/models/status)
ACCURACY=$(echo $STATUS | jq -r '.model_metadata.model_performance.accuracy')
VERSION=$(echo $STATUS | jq -r '.model_metadata.version')
TRAINING_DATE=$(echo $STATUS | jq -r '.model_metadata.training_date')

echo "Model Version: $VERSION"
echo "Training Date: $TRAINING_DATE"
echo "Accuracy: $ACCURACY"

if (( $(echo "$ACCURACY < 0.7" | bc -l) )); then
    echo "WARNING: Model accuracy below recommended threshold"
fi
```

---

## Troubleshooting

### Models Not Training

**Check:**
1. Database has sufficient data
2. Service has write permissions to `models/` directory
3. Training logs for errors
4. Model validation is passing

**Solution:**
```bash
# Force retrain with verbose logging
python scripts/train_models.py --force --verbose
```

### Performance Degradation

**Symptoms:**
- Model accuracy decreasing over time
- Predictions becoming less accurate

**Solutions:**
1. Retrain with more recent data
2. Increase training data window
3. Review training data quality
4. Check for data drift

### Disk Space Issues

**Symptoms:**
- Models directory growing large
- Backup files accumulating

**Solutions:**
```bash
# Clean up old backups (keep last 10)
cd models/
ls -t *.backup_* | tail -n +11 | xargs rm -f
```

---

## Best Practices

1. **Regular Retraining:**
   - Weekly for active systems
   - Monthly for stable systems
   - After major data changes

2. **Monitor Performance:**
   - Track accuracy trends
   - Alert on degradation
   - Review predictions periodically

3. **Backup Strategy:**
   - Keep backups for 30+ days
   - Test restore procedures
   - Document backup locations

4. **Documentation:**
   - Document model versions
   - Track performance changes
   - Note any manual interventions

---

**Document Version:** 1.0  
**Last Updated:** 2025-11-16

