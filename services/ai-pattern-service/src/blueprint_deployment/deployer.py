"""
BlueprintDeployer - Home Assistant Blueprint Deployment Service (Phase 3)

This service handles:
1. Importing blueprints into Home Assistant
2. Creating automations from blueprints
3. Managing blueprint-based automations

Home Assistant Blueprint API:
- GET /api/config/automation/config/{automation_id} - Get automation config
- POST /api/config/automation/config/{automation_id} - Create/update automation
- DELETE /api/config/automation/config/{automation_id} - Delete automation
- GET /api/services - List available services including blueprint import
- POST /api/services/automation/reload - Reload automations

Blueprint Import:
- POST /api/blueprint/import - Import a blueprint from URL
- GET /api/blueprint/automations - List available blueprints
"""

import logging
import uuid
from datetime import datetime
from typing import Any

import httpx
import yaml

from .schemas import (
    AutomationFromBlueprint,
    BlueprintImportResult,
    DeploymentRequest,
    DeploymentResult,
)

logger = logging.getLogger(__name__)


class BlueprintDeployer:
    """
    Deploys Home Assistant blueprints as automations.
    
    This class integrates with the Home Assistant REST API to:
    1. Import blueprints from the Blueprint Index or community sources
    2. Create automations using the blueprint API
    3. Manage blueprint-based automations lifecycle
    """
    
    def __init__(
        self,
        ha_url: str,
        ha_token: str,
        blueprint_index_url: str | None = None,
    ):
        """
        Initialize the BlueprintDeployer.
        
        Args:
            ha_url: Home Assistant base URL (e.g., http://homeassistant.local:8123)
            ha_token: Long-lived access token for HA API
            blueprint_index_url: Optional Blueprint Index service URL
        """
        self.ha_url = ha_url.rstrip("/")
        self.ha_token = ha_token
        self.blueprint_index_url = blueprint_index_url
        
        self._headers = {
            "Authorization": f"Bearer {ha_token}",
            "Content-Type": "application/json",
        }
    
    async def import_blueprint(
        self,
        blueprint_url: str,
        http_client: httpx.AsyncClient | None = None,
    ) -> BlueprintImportResult:
        """
        Import a blueprint into Home Assistant.
        
        Args:
            blueprint_url: URL to the blueprint YAML file
            http_client: Optional HTTP client (will create one if not provided)
            
        Returns:
            BlueprintImportResult with success status and blueprint path
        """
        client = http_client or httpx.AsyncClient(timeout=30.0)
        close_client = http_client is None
        
        try:
            # Import blueprint via HA API
            response = await client.post(
                f"{self.ha_url}/api/blueprint/import",
                headers=self._headers,
                json={"url": blueprint_url},
            )
            
            if response.status_code == 200:
                data = response.json()
                return BlueprintImportResult(
                    success=True,
                    blueprint_path=data.get("blueprint", {}).get("path"),
                    already_exists=False,
                )
            elif response.status_code == 409:
                # Blueprint already exists
                return BlueprintImportResult(
                    success=True,
                    already_exists=True,
                    error="Blueprint already imported",
                )
            else:
                error_msg = f"Import failed: HTTP {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg = error_data.get("message", error_msg)
                except Exception:
                    pass
                return BlueprintImportResult(success=False, error=error_msg)
                
        except Exception as e:
            logger.error(f"Blueprint import error: {e}", exc_info=True)
            return BlueprintImportResult(success=False, error=str(e))
        finally:
            if close_client:
                await client.aclose()
    
    async def list_available_blueprints(
        self,
        http_client: httpx.AsyncClient | None = None,
    ) -> list[dict[str, Any]]:
        """
        List blueprints available in Home Assistant.
        
        Returns:
            List of blueprint metadata dictionaries
        """
        client = http_client or httpx.AsyncClient(timeout=30.0)
        close_client = http_client is None
        
        try:
            response = await client.get(
                f"{self.ha_url}/api/blueprint/automations",
                headers=self._headers,
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Failed to list blueprints: HTTP {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error listing blueprints: {e}", exc_info=True)
            return []
        finally:
            if close_client:
                await client.aclose()
    
    async def deploy_blueprint(
        self,
        request: DeploymentRequest,
        device_inventory: list[dict[str, Any]] | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> DeploymentResult:
        """
        Deploy a blueprint as a Home Assistant automation.
        
        Args:
            request: Deployment request with blueprint ID and inputs
            device_inventory: Optional device inventory for auto-fill
            http_client: Optional HTTP client
            
        Returns:
            DeploymentResult with automation ID and deployment status
        """
        client = http_client or httpx.AsyncClient(timeout=30.0)
        close_client = http_client is None
        
        warnings: list[str] = []
        auto_filled: list[str] = []
        
        try:
            # 1. Get blueprint details from index (if available)
            blueprint_info = None
            if self.blueprint_index_url:
                try:
                    response = await client.get(
                        f"{self.blueprint_index_url}/api/blueprints/{request.blueprint_id}",
                    )
                    if response.status_code == 200:
                        blueprint_info = response.json()
                except Exception as e:
                    logger.warning(f"Failed to fetch blueprint from index: {e}")
                    warnings.append("Could not fetch blueprint details from index")
            
            # 2. Determine blueprint path
            # Blueprint paths in HA are like: homeassistant/motion_light or custom/my_blueprint
            blueprint_path = self._resolve_blueprint_path(request.blueprint_id, blueprint_info)
            
            if not blueprint_path:
                return DeploymentResult(
                    success=False,
                    error=f"Could not resolve blueprint path for {request.blueprint_id}",
                )
            
            # 3. Prepare input values (with auto-fill if enabled)
            input_values = dict(request.input_values)
            
            if request.use_auto_fill and blueprint_info and device_inventory:
                auto_fill_result = self._auto_fill_inputs(
                    blueprint_info=blueprint_info,
                    provided_inputs=input_values,
                    device_inventory=device_inventory,
                )
                input_values.update(auto_fill_result["values"])
                auto_filled = auto_fill_result["auto_filled"]
                warnings.extend(auto_fill_result.get("warnings", []))
            
            # 4. Generate automation configuration
            automation_config = AutomationFromBlueprint(
                alias=request.automation_name,
                description=request.description,
                use_blueprint={
                    "path": blueprint_path,
                    "input": input_values,
                },
                mode=request.mode,
                max=request.max_runs if request.mode in ("queued", "parallel") else None,
            )
            
            # 5. Generate unique automation ID
            automation_id = f"blueprint_{request.blueprint_id}_{uuid.uuid4().hex[:8]}"
            
            # 6. Create automation via HA API
            config_dict = automation_config.model_dump(exclude_none=True)
            
            # Add entity_id for the automation
            config_dict["id"] = automation_id
            
            response = await client.post(
                f"{self.ha_url}/api/config/automation/config/{automation_id}",
                headers=self._headers,
                json=config_dict,
            )
            
            if response.status_code in (200, 201):
                # 7. Reload automations to activate
                await client.post(
                    f"{self.ha_url}/api/services/automation/reload",
                    headers=self._headers,
                )
                
                # Generate YAML for documentation
                automation_yaml = yaml.dump(
                    config_dict,
                    default_flow_style=False,
                    allow_unicode=True,
                )
                
                return DeploymentResult(
                    success=True,
                    automation_id=f"automation.{automation_id}",
                    automation_yaml=automation_yaml,
                    blueprint_path=blueprint_path,
                    deployed_at=datetime.utcnow(),
                    input_values_used=input_values,
                    auto_filled_inputs=auto_filled,
                    warnings=warnings,
                )
            else:
                error_msg = f"Automation creation failed: HTTP {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg = error_data.get("message", error_msg)
                except Exception:
                    pass
                return DeploymentResult(
                    success=False,
                    error=error_msg,
                    warnings=warnings,
                )
                
        except Exception as e:
            logger.error(f"Blueprint deployment error: {e}", exc_info=True)
            return DeploymentResult(
                success=False,
                error=str(e),
                warnings=warnings,
            )
        finally:
            if close_client:
                await client.aclose()
    
    async def preview_deployment(
        self,
        request: DeploymentRequest,
        device_inventory: list[dict[str, Any]] | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> dict[str, Any]:
        """
        Preview what a blueprint deployment would look like without deploying.
        
        Args:
            request: Deployment request
            device_inventory: Optional device inventory for auto-fill
            http_client: Optional HTTP client
            
        Returns:
            Preview dict with automation YAML and input mapping
        """
        warnings: list[str] = []
        auto_filled: list[str] = []
        
        client = http_client or httpx.AsyncClient(timeout=30.0)
        close_client = http_client is None
        
        try:
            # Get blueprint details
            blueprint_info = None
            if self.blueprint_index_url:
                try:
                    response = await client.get(
                        f"{self.blueprint_index_url}/api/blueprints/{request.blueprint_id}",
                    )
                    if response.status_code == 200:
                        blueprint_info = response.json()
                except Exception as e:
                    logger.warning(f"Failed to fetch blueprint: {e}")
            
            blueprint_path = self._resolve_blueprint_path(request.blueprint_id, blueprint_info)
            
            # Prepare inputs with auto-fill
            input_values = dict(request.input_values)
            auto_fill_suggestions = {}
            missing_required = []
            
            if blueprint_info and device_inventory:
                auto_fill_result = self._auto_fill_inputs(
                    blueprint_info=blueprint_info,
                    provided_inputs=input_values,
                    device_inventory=device_inventory,
                )
                auto_fill_suggestions = auto_fill_result.get("suggestions", {})
                
                if request.use_auto_fill:
                    input_values.update(auto_fill_result["values"])
                    auto_filled = auto_fill_result["auto_filled"]
                
                missing_required = auto_fill_result.get("missing_required", [])
                warnings.extend(auto_fill_result.get("warnings", []))
            
            # Generate automation config
            config = {
                "alias": request.automation_name,
                "description": request.description,
                "use_blueprint": {
                    "path": blueprint_path or f"homeiq/{request.blueprint_id}",
                    "input": input_values,
                },
                "mode": request.mode,
            }
            
            if request.max_runs and request.mode in ("queued", "parallel"):
                config["max"] = request.max_runs
            
            automation_yaml = yaml.dump(
                {k: v for k, v in config.items() if v is not None},
                default_flow_style=False,
                allow_unicode=True,
            )
            
            return {
                "automation_yaml": automation_yaml,
                "automation_config": config,
                "input_mapping": input_values,
                "auto_fill_suggestions": auto_fill_suggestions,
                "missing_required_inputs": missing_required,
                "warnings": warnings,
            }
            
        finally:
            if close_client:
                await client.aclose()
    
    def _resolve_blueprint_path(
        self,
        blueprint_id: str,
        blueprint_info: dict[str, Any] | None = None,
    ) -> str | None:
        """
        Resolve the Home Assistant blueprint path from blueprint ID.
        
        Args:
            blueprint_id: Blueprint ID from the index
            blueprint_info: Optional blueprint details from index
            
        Returns:
            HA blueprint path or None if not found
        """
        # Check if blueprint_info has the path
        if blueprint_info:
            if "ha_path" in blueprint_info:
                return blueprint_info["ha_path"]
            if "source_url" in blueprint_info:
                # Extract path from GitHub URL
                url = blueprint_info["source_url"]
                if "github.com" in url:
                    # Try to derive path from URL
                    # Format: github.com/owner/repo/path/to/blueprint.yaml
                    # HA path might be: owner/blueprint_name
                    parts = url.split("/")
                    if len(parts) >= 5:
                        owner = parts[3]
                        # Get blueprint name from filename
                        filename = parts[-1].replace(".yaml", "").replace(".yml", "")
                        return f"{owner}/{filename}"
        
        # Default: assume it's a HomeIQ blueprint
        return f"homeiq/{blueprint_id}"
    
    def _auto_fill_inputs(
        self,
        blueprint_info: dict[str, Any],
        provided_inputs: dict[str, Any],
        device_inventory: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Auto-fill blueprint inputs from device inventory.
        
        Args:
            blueprint_info: Blueprint details with input definitions
            provided_inputs: Already provided input values
            device_inventory: Available devices
            
        Returns:
            Dict with values, auto_filled list, suggestions, missing_required, warnings
        """
        result = {
            "values": {},
            "auto_filled": [],
            "suggestions": {},
            "missing_required": [],
            "warnings": [],
        }
        
        inputs_schema = blueprint_info.get("inputs", {})
        if not inputs_schema:
            return result
        
        for input_name, input_def in inputs_schema.items():
            # Skip if already provided
            if input_name in provided_inputs:
                continue
            
            # Get input selector type
            selector = input_def.get("selector", {})
            
            # Find matching device from inventory
            match = self._find_device_for_input(
                input_def=input_def,
                selector=selector,
                device_inventory=device_inventory,
            )
            
            if match:
                result["values"][input_name] = match["entity_id"]
                result["auto_filled"].append(input_name)
                result["suggestions"][input_name] = {
                    "entity_id": match["entity_id"],
                    "confidence": match.get("confidence", 0.8),
                    "alternatives": match.get("alternatives", []),
                }
            elif input_def.get("default") is not None:
                result["values"][input_name] = input_def["default"]
            elif not input_def.get("required", True):
                # Optional input without match - skip
                pass
            else:
                # Required input without match
                result["missing_required"].append(input_name)
                result["warnings"].append(
                    f"Required input '{input_name}' could not be auto-filled"
                )
        
        return result
    
    def _find_device_for_input(
        self,
        input_def: dict[str, Any],
        selector: dict[str, Any],
        device_inventory: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        """
        Find a matching device for a blueprint input.
        
        Args:
            input_def: Input definition from blueprint
            selector: Selector configuration
            device_inventory: Available devices
            
        Returns:
            Match dict with entity_id and confidence, or None
        """
        # Handle entity selector
        if "entity" in selector:
            entity_selector = selector["entity"]
            domain = entity_selector.get("domain")
            device_class = entity_selector.get("device_class")
            
            candidates = []
            for device in device_inventory:
                entity_id = device.get("entity_id", "")
                device_domain = entity_id.split(".")[0] if "." in entity_id else ""
                device_class_match = device.get("device_class")
                
                # Check domain match
                if domain:
                    if isinstance(domain, list):
                        if device_domain not in domain:
                            continue
                    elif device_domain != domain:
                        continue
                
                # Check device class match
                if device_class:
                    if isinstance(device_class, list):
                        if device_class_match not in device_class:
                            continue
                    elif device_class_match != device_class:
                        continue
                
                # Calculate confidence
                confidence = 0.7
                if device_class and device_class_match == device_class:
                    confidence = 0.9
                elif domain and device_domain == domain:
                    confidence = 0.8
                
                candidates.append({
                    "entity_id": entity_id,
                    "confidence": confidence,
                })
            
            if candidates:
                # Sort by confidence and return best match
                candidates.sort(key=lambda x: x["confidence"], reverse=True)
                best = candidates[0]
                best["alternatives"] = [c["entity_id"] for c in candidates[1:4]]
                return best
        
        # Handle target selector (device/entity/area)
        elif "target" in selector:
            # For now, find any entity that could work
            # This is a simplified implementation
            for device in device_inventory:
                entity_id = device.get("entity_id", "")
                if entity_id:
                    return {
                        "entity_id": entity_id,
                        "confidence": 0.6,
                    }
        
        return None
    
    async def delete_automation(
        self,
        automation_id: str,
        http_client: httpx.AsyncClient | None = None,
    ) -> bool:
        """
        Delete a blueprint-based automation.
        
        Args:
            automation_id: Automation entity ID (e.g., automation.blueprint_motion_abc123)
            http_client: Optional HTTP client
            
        Returns:
            True if deleted successfully
        """
        client = http_client or httpx.AsyncClient(timeout=30.0)
        close_client = http_client is None
        
        try:
            # Extract config ID from entity ID
            config_id = automation_id.replace("automation.", "")
            
            response = await client.delete(
                f"{self.ha_url}/api/config/automation/config/{config_id}",
                headers=self._headers,
            )
            
            if response.status_code in (200, 204):
                # Reload automations
                await client.post(
                    f"{self.ha_url}/api/services/automation/reload",
                    headers=self._headers,
                )
                return True
            else:
                logger.warning(
                    f"Failed to delete automation {automation_id}: HTTP {response.status_code}"
                )
                return False
                
        except Exception as e:
            logger.error(f"Error deleting automation: {e}", exc_info=True)
            return False
        finally:
            if close_client:
                await client.aclose()
