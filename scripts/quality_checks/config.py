"""
Configuration constants for quality checks.
"""
import os
from pathlib import Path
from typing import Dict

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent

# PostgreSQL connection URL
POSTGRES_URL = os.environ.get("POSTGRES_URL", "postgresql://homeiq:homeiq@localhost:5432/homeiq")

# Database configurations (PostgreSQL schema-per-domain)
DATABASE_CONFIGS: Dict[str, Dict[str, any]] = {
    'ai_automation': {
        'name': 'AI Automation Service',
        'schema': 'automation',
        'service': 'ai-automation-service'
    },
    'metadata': {
        'name': 'Data API (Metadata)',
        'schema': 'core',
        'service': 'data-api'
    },
    'ha_ai_agent': {
        'name': 'HA AI Agent Service',
        'schema': 'agent',
        'service': 'ha-ai-agent-service'
    },
    'proactive_agent': {
        'name': 'Proactive Agent Service',
        'schema': 'automation',
        'service': 'proactive-agent-service'
    },
    'device_intelligence': {
        'name': 'Device Intelligence Service',
        'schema': 'devices',
        'service': 'device-intelligence-service'
    },
    'ha-setup': {
        'name': 'HA Setup Service',
        'schema': 'core',
        'service': 'ha-setup-service'
    },
    'automation_miner': {
        'name': 'Automation Miner',
        'schema': 'automation',
        'service': 'automation-miner'
    },
}

# InfluxDB Configuration
INFLUXDB_DEFAULT_URL = 'http://localhost:8086'
INFLUXDB_DEFAULT_ORG = 'homeiq'
INFLUXDB_DEFAULT_BUCKET = 'home_assistant_events'

# Available check types
PG_CHECKS = [
    'tables',
    'null_values',
    'foreign_keys',
    'indexes',
    'bloat',
    'integrity',
    'orphaned',
    'table_specific',
]

INFLUXDB_CHECKS = [
    'connection',
    'buckets',
    'data_volume',
    'measurements',
    'data_gaps',
    'shards',
    'retention',
    'schema',
]
