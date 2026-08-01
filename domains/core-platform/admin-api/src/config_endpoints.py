"""
Configuration Management Endpoints
"""

import logging
import os
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .config_manager import config_manager

logger = logging.getLogger(__name__)

# Backup, restore, and history have no backing store: ConfigManager persists the
# current .env.<service> only, with no archive and no change log. They previously
# returned fabricated empty payloads, so an operator "backing up" or "rolling
# back" configuration got a 200 and no state change. 501 until a store exists.
_NO_BACKING_STORE = (
    "Not implemented: no configuration {feature} store exists. "
    "ConfigManager persists only the current .env.<service>."
)


class ConfigItem(BaseModel):
    """Configuration item model"""
    key: str
    value: Any
    description: str
    type: str
    required: bool = False
    default: Any = None
    validation_rules: dict[str, Any] = {}


class ConfigUpdate(BaseModel):
    """Configuration update model"""
    key: str
    value: Any
    reason: str | None = None


class ConfigValidation(BaseModel):
    """Configuration validation model"""
    is_valid: bool
    errors: list[str] = []
    warnings: list[str] = []


class ConfigEndpoints:
    """Configuration management endpoints"""

    def __init__(self):
        """Initialize config endpoints"""
        self.router = APIRouter()
        self.service_urls = {
            "websocket-ingestion": os.getenv("WEBSOCKET_INGESTION_URL", "http://localhost:8001")
        }

        self._add_routes()

    def _add_routes(self):
        """Add configuration routes"""

        @self.router.get("/config", response_model=dict[str, Any])
        async def get_configuration(
            service: str | None = Query(None, description="Specific service to get config for"),
            include_sensitive: bool = Query(False, description="Include sensitive configuration values")
        ):
            """Get configuration for services"""
            try:
                if include_sensitive:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Sensitive configuration values cannot be retrieved via API.",
                    )

                if service and service in self.service_urls:
                    # Get config for specific service
                    config = await self._get_service_config(service, include_sensitive)
                    if not config["available"]:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"No configuration file for service {service}",
                        )
                    return {service: config}
                else:
                    # Get config for all services
                    all_config = {}
                    for service_name in self.service_urls:
                        config = await self._get_service_config(service_name, include_sensitive)
                        all_config[service_name] = config
                    return all_config

            except HTTPException:
                # Deliberate status (e.g. the 403 above) must not be masked as a 500
                raise
            except Exception as e:
                logger.error(f"Error getting configuration: {e}")
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={"detail": "Failed to get configuration"},
                )

        @self.router.get("/config/schema", response_model=dict[str, list[ConfigItem]])
        async def get_config_schema():
            """Get configuration schema for all services"""
            try:
                schema = await self._get_config_schema()
                return schema

            except Exception as e:
                logger.error(f"Error getting configuration schema: {e}")
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={"detail": "Failed to get configuration schema"},
                )

        @self.router.put("/config/{service}", response_model=dict[str, Any])
        async def update_configuration(
            service: str,
            updates: list[ConfigUpdate] = Body(..., description="Configuration updates")
        ):
            """Update configuration for a specific service"""
            try:
                if service not in self.service_urls:
                    return JSONResponse(
                        status_code=status.HTTP_404_NOT_FOUND,
                        content={"detail": f"Service {service} not found"},
                    )

                # Validate updates
                validation = await self._validate_config_updates(service, updates)
                if not validation.is_valid:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Configuration validation failed: {', '.join(validation.errors)}"
                    )

                # Apply updates
                result = await self._apply_config_updates(service, updates)

                return {
                    "service": service,
                    "updated": len(updates),
                    "timestamp": datetime.now().isoformat(),
                    "result": result
                }

            except HTTPException:
                raise
            except PermissionError as exc:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=str(exc),
                ) from exc
            except Exception as e:
                logger.error(f"Error updating configuration: {e}")
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={"detail": "Failed to update configuration"},
                )

        @self.router.post("/config/{service}/validate", response_model=ConfigValidation)
        async def validate_configuration(
            service: str,
            config: dict[str, Any] = Body(..., description="Configuration to validate")
        ):
            """Validate configuration for a service"""
            try:
                if service not in self.service_urls:
                    return JSONResponse(
                        status_code=status.HTTP_404_NOT_FOUND,
                        content={"detail": f"Service {service} not found"},
                    )

                validation = await self._validate_service_config(service, config)
                return validation

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error validating configuration: {e}")
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={"detail": "Failed to validate configuration"},
                )

        @self.router.get("/config/{service}/backup", response_model=dict[str, Any])
        async def backup_configuration(service: str):
            """Backup current configuration for a service"""
            try:
                if service not in self.service_urls:
                    return JSONResponse(
                        status_code=status.HTTP_404_NOT_FOUND,
                        content={"detail": f"Service {service} not found"},
                    )

                backup = await self._backup_service_config(service)
                return backup

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error backing up configuration: {e}")
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={"detail": "Failed to backup configuration"},
                )

        @self.router.post("/config/{service}/restore", response_model=dict[str, Any])
        async def restore_configuration(
            service: str,
            backup_data: dict[str, Any] = Body(..., description="Backup data to restore")
        ):
            """Restore configuration from backup"""
            try:
                if service not in self.service_urls:
                    return JSONResponse(
                        status_code=status.HTTP_404_NOT_FOUND,
                        content={"detail": f"Service {service} not found"},
                    )

                result = await self._restore_service_config(service, backup_data)
                return result

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error restoring configuration: {e}")
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={"detail": "Failed to restore configuration"},
                )

        @self.router.get("/config/{service}/history", response_model=list[dict[str, Any]])
        async def get_config_history(
            service: str,
            limit: int = Query(10, description="Maximum number of history entries")
        ):
            """Get configuration change history for a service"""
            try:
                if service not in self.service_urls:
                    return JSONResponse(
                        status_code=status.HTTP_404_NOT_FOUND,
                        content={"detail": f"Service {service} not found"},
                    )

                history = await self._get_config_history(service, limit)
                return history

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error getting configuration history: {e}")
                return JSONResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content={"detail": "Failed to get configuration history"},
                )

    async def _get_service_config(self, service: str, include_sensitive: bool) -> dict[str, Any]:
        """Get configuration for a specific service.

        Reads the real .env.<service> via ConfigManager. Sensitive values are
        always masked -- the route rejects include_sensitive=true with a 403, so
        the flag only ever arrives false and is echoed back for the caller.

        A missing file yields ``available: False`` rather than raising, so the
        all-services listing is not failed by one unconfigured service. The
        single-service route turns that into a 404.
        """
        try:
            config = config_manager.read_config(service)
        except FileNotFoundError:
            return {
                "service": service,
                "include_sensitive": include_sensitive,
                "available": False,
                "configuration": {},
            }

        return {
            "service": service,
            "include_sensitive": include_sensitive,
            "available": True,
            "configuration": config_manager.sanitize_config(config),
        }

    async def _get_config_schema(self) -> dict[str, list[ConfigItem]]:
        """Get configuration schema for all services"""
        schema = {}
        for service_name in self.service_urls:
            template = config_manager.get_config_template(service_name)
            schema[service_name] = [
                ConfigItem(
                    key=key,
                    value=field.get("default", ""),
                    description=field.get("description", ""),
                    type=field.get("type", "text"),
                    required=bool(field.get("required", False)),
                    default=field.get("default"),
                )
                for key, field in template.items()
            ]
        return schema

    async def _validate_config_updates(self, service: str, updates: list[ConfigUpdate]) -> ConfigValidation:
        """Validate configuration updates"""
        errors = []
        warnings = []

        # Get current schema
        schema = await self._get_config_schema()
        service_schema = schema.get(service, [])

        # Create schema lookup
        schema_lookup = {item.key: item for item in service_schema}

        for update in updates:
            if update.key not in schema_lookup:
                warnings.append(f"Unknown configuration key: {update.key}")
                continue

            schema_item = schema_lookup[update.key]

            # Check required fields
            if schema_item.required and update.value is None:
                errors.append(f"Required field {update.key} cannot be null")

            # Type validation
            if not self._validate_type(update.value, schema_item.type):
                errors.append(f"Invalid type for {update.key}: expected {schema_item.type}")

            # Custom validation rules
            if schema_item.validation_rules:
                validation_result = self._validate_rules(update.value, schema_item.validation_rules)
                if validation_result["errors"]:
                    errors.extend(validation_result["errors"])
                if validation_result["warnings"]:
                    warnings.extend(validation_result["warnings"])

        return ConfigValidation(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    async def _apply_config_updates(self, service: str, updates: list[ConfigUpdate]) -> dict[str, Any]:
        """Apply configuration updates to a service.

        Writes through ConfigManager. PermissionError (a sensitive key with
        ADMIN_API_ALLOW_SECRET_WRITES unset) propagates -- the route maps it to
        403 rather than reporting a write that never happened.
        """
        try:
            written = config_manager.write_config(
                service,
                {update.key: str(update.value) for update in updates},
            )
        except FileNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No configuration file for service {service}",
            ) from None

        return {
            "status": "applied",
            "applied": len(updates),
            "keys": sorted(update.key for update in updates),
            "configuration": config_manager.sanitize_config(written),
        }

    async def _validate_service_config(self, service: str, config: dict[str, Any]) -> ConfigValidation:
        """Validate complete service configuration"""
        # Convert config dict to ConfigUpdate list
        updates = [ConfigUpdate(key=k, value=v) for k, v in config.items()]
        return await self._validate_config_updates(service, updates)

    async def _backup_service_config(self, _service: str) -> dict[str, Any]:
        """Backup service configuration -- unimplemented, see _NO_BACKING_STORE."""
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=_NO_BACKING_STORE.format(feature="backup"),
        )

    async def _restore_service_config(self, _service: str, _backup_data: dict[str, Any]) -> dict[str, Any]:
        """Restore service configuration from backup -- unimplemented."""
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=_NO_BACKING_STORE.format(feature="backup"),
        )

    async def _get_config_history(self, _service: str, _limit: int) -> list[dict[str, Any]]:
        """Get configuration change history -- unimplemented."""
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=_NO_BACKING_STORE.format(feature="change-history"),
        )

    def _validate_type(self, value: Any, expected_type: str) -> bool:
        """Validate value type"""
        if expected_type == "string":
            return isinstance(value, str)
        elif expected_type == "integer":
            return isinstance(value, int)
        elif expected_type == "float":
            return isinstance(value, (int, float))
        elif expected_type == "boolean":
            return isinstance(value, bool)
        elif expected_type == "array":
            return isinstance(value, list)
        elif expected_type == "object":
            return isinstance(value, dict)
        else:
            return True  # Unknown type, assume valid

    def _validate_rules(self, value: Any, rules: dict[str, Any]) -> dict[str, list[str]]:
        """Validate value against custom rules"""
        errors = []
        warnings = []

        # Min/Max validation
        if "min" in rules and value < rules["min"]:
            errors.append(f"Value {value} is below minimum {rules['min']}")

        if "max" in rules and value > rules["max"]:
            errors.append(f"Value {value} is above maximum {rules['max']}")

        # String length validation
        if isinstance(value, str):
            if "min_length" in rules and len(value) < rules["min_length"]:
                errors.append(f"String length {len(value)} is below minimum {rules['min_length']}")

            if "max_length" in rules and len(value) > rules["max_length"]:
                errors.append(f"String length {len(value)} is above maximum {rules['max_length']}")

        # Pattern validation
        if "pattern" in rules and isinstance(value, str):
            import re
            if not re.match(rules["pattern"], value):
                errors.append(f"Value {value} does not match pattern {rules['pattern']}")

        # Enum validation
        if "enum" in rules and value not in rules["enum"]:
            errors.append(f"Value {value} is not in allowed values {rules['enum']}")

        return {"errors": errors, "warnings": warnings}
