"""
Common utilities for InfluxDB operations.
"""
import os
from typing import Optional

from .config import INFLUXDB_DEFAULT_BUCKET, INFLUXDB_DEFAULT_ORG, INFLUXDB_DEFAULT_URL


def get_influxdb_config() -> dict:
    """Get InfluxDB configuration from environment variables."""
    return {
        'url': os.getenv('INFLUXDB_URL', INFLUXDB_DEFAULT_URL),
        'token': (
            os.getenv('INFLUXDB_TOKEN') or 
            os.getenv('DOCKER_INFLUXDB_INIT_ADMIN_TOKEN') or 
            'homeiq-token'
        ),
        'org': os.getenv('INFLUXDB_ORG', INFLUXDB_DEFAULT_ORG),
        'bucket': os.getenv('INFLUXDB_BUCKET', INFLUXDB_DEFAULT_BUCKET),
    }

