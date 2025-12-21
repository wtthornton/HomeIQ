"""
Configuration constants for quality checks.
"""
from pathlib import Path
from typing import Dict, List

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Database configurations (2025)
DATABASE_CONFIGS: Dict[str, Dict[str, any]] = {
    'ai_automation': {
        'name': 'AI Automation Service',
        'paths': [
            '/app/data/ai_automation.db',
            'services/ai-automation-service/data/ai_automation.db',
            'data/ai_automation.db',
        ],
        'service': 'ai-automation-service'
    },
    'metadata': {
        'name': 'Data API (Metadata)',
        'paths': [
            '/app/data/metadata.db',
            'services/data-api/data/metadata.db',
            'data/metadata.db',
        ],
        'service': 'data-api'
    },
    'ha_ai_agent': {
        'name': 'HA AI Agent Service',
        'paths': [
            '/app/data/ha_ai_agent.db',
            'services/ha-ai-agent-service/data/ha_ai_agent.db',
            'data/ha_ai_agent.db',
        ],
        'service': 'ha-ai-agent-service'
    },
    'proactive_agent': {
        'name': 'Proactive Agent Service',
        'paths': [
            '/app/data/proactive_agent.db',
            'services/proactive-agent-service/data/proactive_agent.db',
            'data/proactive_agent.db',
        ],
        'service': 'proactive-agent-service'
    },
    'device_intelligence': {
        'name': 'Device Intelligence Service',
        'paths': [
            '/app/data/device_intelligence.db',
            'services/device-intelligence-service/data/device_intelligence.db',
            'data/device_intelligence.db',
        ],
        'service': 'device-intelligence-service'
    },
    'ha-setup': {
        'name': 'HA Setup Service',
        'paths': [
            '/app/data/ha-setup.db',
            'services/ha-setup-service/data/ha-setup.db',
            'data/ha-setup.db',
        ],
        'service': 'ha-setup-service'
    },
    'automation_miner': {
        'name': 'Automation Miner',
        'paths': [
            '/app/data/automation_miner.db',
            'services/automation-miner/data/automation_miner.db',
            'data/automation_miner.db',
        ],
        'service': 'automation-miner'
    },
}

# InfluxDB Configuration
INFLUXDB_DEFAULT_URL = 'http://localhost:8086'
INFLUXDB_DEFAULT_ORG = 'homeiq'
INFLUXDB_DEFAULT_BUCKET = 'home_assistant_events'

# Available check types
SQLITE_CHECKS = [
    'tables',
    'null_values',
    'foreign_keys',
    'indexes',
    'vacuum',
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

