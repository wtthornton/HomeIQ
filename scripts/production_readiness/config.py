"""
Configuration constants for production readiness pipeline.
"""
from pathlib import Path
from typing import Dict, List

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
AI_SERVICE_DIR = PROJECT_ROOT / "services" / "ai-automation-service"
DEVICE_INTELLIGENCE_DIR = PROJECT_ROOT / "services" / "device-intelligence-service"
TEST_RESULTS_DIR = PROJECT_ROOT / "test-results"
IMPLEMENTATION_DIR = PROJECT_ROOT / "implementation"

# Component Classification (Epic 42.1: Critical vs Optional)
CRITICAL_COMPONENTS: Dict[str, bool] = {
    'build': True,
    'deploy': True,
    'smoke_tests': True,
    'data_generation': True,
    'home_type': True,
    'device_intelligence': True
}

OPTIONAL_COMPONENTS: Dict[str, bool] = {
    'gnn_synergy': True,
    'soft_prompt': True
}

# Required Environment Variables (Epic 42.2: Pre-Flight Validation)
REQUIRED_ENV_VARS: Dict[str, str] = {
    'HA_HTTP_URL': 'Home Assistant HTTP URL (e.g., http://192.168.1.86:8123)',
    'HA_TOKEN': 'Home Assistant long-lived access token'
}

OPTIONAL_ENV_VARS: Dict[str, str] = {
    'OPENAI_API_KEY': 'OpenAI API key (required for Ask AI suggestions and automation generation, but not for model training)'
}

# Model Quality Thresholds (Epic 43.1: Model Quality Validation)
MODEL_QUALITY_THRESHOLDS: Dict[str, Dict[str, float]] = {
    'home_type': {
        'accuracy': 0.90,  # 90% minimum accuracy
        'precision': 0.85,  # 85% minimum precision
        'recall': 0.85,     # 85% minimum recall
        'f1_score': 0.85   # 85% minimum F1 score
    },
    'device_intelligence': {
        'accuracy': 0.85,  # 85% minimum accuracy
        'precision': 0.80,  # 80% minimum precision
        'recall': 0.80,     # 80% minimum recall
        'f1_score': 0.80   # 80% minimum F1 score
    },
    'gnn_synergy': {
        # Optional model - no strict thresholds, but validate if metrics exist
        'accuracy': 0.70,  # 70% minimum if metrics available
    },
    'soft_prompt': {
        # Optional model - no strict thresholds, but validate if metrics exist
        'accuracy': 0.70,  # 70% minimum if metrics available
    }
}

# Required Python Packages (Epic 42.2: Pre-Flight Validation)
REQUIRED_PACKAGES: List[str] = [
    'docker',
    'fastapi',
    'pydantic',
    'sqlalchemy',
    'influxdb-client',
    'aiohttp',
    'pytest'
]

