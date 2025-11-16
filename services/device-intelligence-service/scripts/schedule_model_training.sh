#!/bin/bash
# Scheduled Model Training Script
# 
# This script can be used with cron or systemd timers to automatically
# retrain ML models on a schedule.
#
# Usage:
#   Add to crontab: 0 2 * * 0 /path/to/scripts/schedule_model_training.sh
#   (Runs every Sunday at 2 AM)

set -e

# Configuration
SERVICE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_FILE="${SERVICE_DIR}/training.log"
DAYS_BACK=180
FORCE_RETRAIN=true

# Change to service directory
cd "$SERVICE_DIR"

# Log start
echo "========================================" >> "$LOG_FILE"
echo "Scheduled Model Training Started" >> "$LOG_FILE"
echo "Date: $(date)" >> "$LOG_FILE"
echo "Days Back: $DAYS_BACK" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

# Run training script
python scripts/train_models.py \
    --days-back "$DAYS_BACK" \
    --force \
    --verbose \
    >> "$LOG_FILE" 2>&1

EXIT_CODE=$?

# Log completion
if [ $EXIT_CODE -eq 0 ]; then
    echo "Training completed successfully" >> "$LOG_FILE"
else
    echo "Training failed with exit code: $EXIT_CODE" >> "$LOG_FILE"
fi

echo "========================================" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

exit $EXIT_CODE

