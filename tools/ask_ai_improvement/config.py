"""
Configuration constants for Ask AI continuous improvement.
"""
import os
from pathlib import Path

BASE_URL = "http://localhost:8024/api/v1/ask-ai"
HEALTH_URL = "http://localhost:8024/health"
MAX_CLARIFICATION_ROUNDS = 10
API_KEY = os.getenv("AI_AUTOMATION_API_KEY", "hs_P3rU9kQ2xZp6vL1fYc7bN4sTqD8mA0wR")

# Output configuration
OUTPUT_DIR = Path("implementation/continuous-improvement")

# Scoring configuration
SCORE_EXCELLENT_THRESHOLD = 85.0
SCORE_WARNING_THRESHOLD = 70.0
YAML_VALIDITY_THRESHOLD = 50.0

# Scoring weights
AUTOMATION_SCORE_WEIGHT = 0.5
YAML_SCORE_WEIGHT = 0.3
CLARIFICATION_SCORE_WEIGHT = 0.2

# Cycle configuration
MAX_CYCLES = 25
DEPLOYMENT_WAIT_TIME = 5.0
CYCLE_WAIT_TIME = 2.0

# Health check configuration
HEALTH_CHECK_RETRIES = 30
HEALTH_CHECK_INTERVAL = 1.0

# Retry configuration
MAX_RETRIES = 3
RETRY_INITIAL_DELAY = 2.0
RETRY_BACKOFF_MULTIPLIER = 2.0

# Timeouts
TIMEOUT = 300.0  # 5 minutes timeout for API calls
HA_API_TIMEOUT = 10.0

