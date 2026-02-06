"""
MQTT and Zigbee configuration management endpoints.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, field_validator

CONFIG_FILE_ENV = "MQTT_ZIGBEE_CONFIG_PATH"


def _determine_default_path() -> Path:
    """Return the first viable path for the shared MQTT/Zigbee config file."""
    env_override = os.getenv(CONFIG_FILE_ENV)
    if env_override:
        return Path(env_override)

    module_path = Path(__file__).resolve()
    candidates = [
        Path("/app/infrastructure/config/mqtt_zigbee_config.json"),
        module_path.parents[2] / "infrastructure" / "config" / "mqtt_zigbee_config.json",
        module_path.parents[1] / "config" / "mqtt_zigbee_config.json",
    ]

    for candidate in candidates:
        try:
            if candidate.parent.exists():
                return candidate
        except IndexError:
            continue

    return candidates[-1]


DEFAULT_CONFIG_PATH = _determine_default_path()


class MqttConfig(BaseModel):
    """Configuration payload for MQTT/Zigbee integrations."""

    broker_url: str = Field(alias="MQTT_BROKER", description="Full MQTT broker URL including scheme and port")
    username: str | None = Field(
        default=None,
        alias="MQTT_USERNAME",
        description="MQTT username (optional when anonymous access is enabled)",
    )
    password: str | None = Field(
        default=None,
        alias="MQTT_PASSWORD",
        description="MQTT password (optional when anonymous access is enabled)",
    )
    base_topic: str = Field(
        default="zigbee2mqtt",
        alias="ZIGBEE2MQTT_BASE_TOPIC",
        description="Base topic used by Zigbee2MQTT",
    )

    model_config = {"populate_by_name": True}

    @field_validator("broker_url")
    @classmethod
    def validate_broker(cls, value: str) -> str:
        """Ensure broker URL uses a supported scheme."""
        if not value:
            raise ValueError("MQTT_BROKER cannot be empty")
        allowed_prefixes = ("mqtt://", "mqtts://", "ws://", "wss://")
        if not value.startswith(allowed_prefixes):
            raise ValueError(
                "MQTT_BROKER must start with one of: mqtt://, mqtts://, ws://, wss://"
            )
        return value

    @field_validator("base_topic")
    @classmethod
    def validate_base_topic(cls, value: str) -> str:
        """Ensure Zigbee base topic is not empty and trimmed."""
        if not value or not value.strip():
            raise ValueError("ZIGBEE2MQTT_BASE_TOPIC cannot be empty")
        return value.strip()


# Create separate routers for public GET and secured PUT
# GET endpoint is public (no auth required) - configuration reading is safe
# PUT endpoint requires authentication - configuration changes must be secured
public_router = APIRouter(prefix="/config/integrations", tags=["Integrations"])
router = APIRouter(prefix="/config/integrations", tags=["Integrations"])


def _config_path() -> Path:
    return DEFAULT_CONFIG_PATH


# Ensure forward references are resolved when module is imported dynamically.
MqttConfig.model_rebuild()


def _load_config_from_disk(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}

    try:
        with path.open("r", encoding="utf-8") as config_file:
            data = json.load(config_file)
            if isinstance(data, dict):
                return data
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Stored MQTT configuration is invalid JSON: {exc}",
        ) from exc

    return {}


def _load_effective_config() -> dict[str, Any]:
    """Merge stored overrides with environment defaults."""
    env_defaults = {
        "MQTT_BROKER": os.getenv("MQTT_BROKER", "mqtt://192.168.1.86:1883"),
        "MQTT_USERNAME": os.getenv("MQTT_USERNAME"),
        "MQTT_PASSWORD": os.getenv("MQTT_PASSWORD"),
        "ZIGBEE2MQTT_BASE_TOPIC": os.getenv("ZIGBEE2MQTT_BASE_TOPIC", "zigbee2mqtt"),
    }

    overrides = _load_config_from_disk(_config_path())
    env_defaults.update({k: v for k, v in overrides.items() if v is not None})
    return env_defaults


def _persist_config(payload: dict[str, Any]) -> None:
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as config_file:
        json.dump(payload, config_file, indent=2, sort_keys=True)


@public_router.get("/mqtt", response_model=MqttConfig)
async def get_mqtt_config() -> MqttConfig:
    """
    Return current MQTT/Zigbee configuration values.
    
    This endpoint is public (no authentication required) to allow the dashboard
    to load existing configuration. Configuration values are not sensitive
    (they're already in environment variables or config files).
    """
    data = _load_effective_config()
    return MqttConfig.model_validate(data, from_attributes=False)


@router.put("/mqtt", response_model=dict[str, Any])
async def update_mqtt_config(config: MqttConfig) -> dict[str, Any]:
    """
    Persist new MQTT/Zigbee configuration values.

    This endpoint requires authentication. Configuration changes must be secured.
    """
    payload = config.model_dump(by_alias=True)

    try:
        _persist_config(payload)
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist configuration: {exc}",
        ) from exc

    return {
        "success": True,
        "message": "MQTT configuration saved. Restart device-intelligence-service to apply changes.",
        "config": payload,
        "config_path": str(_config_path()),
    }

