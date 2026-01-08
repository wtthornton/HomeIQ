"""Blueprint Opportunity Engine - Discovers automation opportunities."""

import logging
import time
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

import httpx

from .device_matcher import DeviceMatcher
from .input_autofill import InputAutofill
from .schemas import (
    AutofilledInput,
    BlueprintDeploymentPreview,
    BlueprintOpportunity,
    BlueprintSummary,
    DeviceSignature,
    OpportunityDiscoveryRequest,
    OpportunityDiscoveryResponse,
)

logger = logging.getLogger(__name__)


class BlueprintOpportunityEngine:
    """
    Discovers automation opportunities by matching device inventory to blueprints.
    
    This engine:
    1. Fetches user's device inventory from data-api
    2. Queries blueprint-index for matching blueprints
    3. Calculates fit scores
    4. Auto-fills inputs where possible
    5. Returns ranked opportunities
    """
    
    def __init__(
        self,
        blueprint_index_url: str = "http://blueprint-index:8031",
        data_api_url: str = "http://data-api:8006",
        api_key: Optional[str] = None,
    ):
        """
        Initialize opportunity engine.
        
        Args:
            blueprint_index_url: URL of the blueprint-index service
            data_api_url: URL of the data-api service
            api_key: API key for authentication
        """
        self.blueprint_index_url = blueprint_index_url.rstrip("/")
        self.data_api_url = data_api_url.rstrip("/")
        self.api_key = api_key
        
        self.device_matcher = DeviceMatcher()
        self.input_autofill = InputAutofill()
        
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        
        self._client = httpx.AsyncClient(
            headers=headers,
            timeout=httpx.Timeout(30.0),
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
    
    async def discover_opportunities(
        self,
        request: Optional[OpportunityDiscoveryRequest] = None,
    ) -> OpportunityDiscoveryResponse:
        """
        Main entry point for opportunity discovery.
        
        Args:
            request: Discovery parameters
            
        Returns:
            Discovery response with ranked opportunities
        """
        start_time = time.time()
        
        if request is None:
            request = OpportunityDiscoveryRequest()
        
        # 1. Fetch device inventory
        devices = await self._fetch_device_inventory()
        logger.info(f"Fetched {len(devices)} devices")
        
        if not devices:
            return OpportunityDiscoveryResponse(
                opportunities=[],
                total_found=0,
                device_count=0,
                area_count=0,
                discovery_time_ms=(time.time() - start_time) * 1000,
            )
        
        # Count unique areas
        areas = {d.area_id for d in devices if d.area_id}
        
        # 2. Extract device signatures
        user_domains = list({d.domain for d in devices})
        user_device_classes = list({d.device_class for d in devices if d.device_class})
        
        # 3. Query blueprint index for matching blueprints
        blueprints = await self._search_blueprints(
            domains=user_domains,
            device_classes=user_device_classes,
            use_cases=request.use_cases,
            min_quality_score=0.5,
            limit=100,  # Get more than needed for filtering
        )
        
        logger.info(f"Found {len(blueprints)} candidate blueprints")
        
        # 4. Calculate fit scores and rank
        ranked = self.device_matcher.rank_blueprints(
            blueprints, devices, request.min_fit_score
        )
        
        # 5. Build opportunities with autofill
        opportunities = []
        for blueprint, fit_score, matched_devices, same_area in ranked:
            if blueprint.id in request.exclude_blueprint_ids:
                continue
            
            # Get full blueprint details for autofill
            full_blueprint = await self._get_blueprint_details(blueprint.id)
            
            if full_blueprint:
                inputs = full_blueprint.get("inputs", {})
                
                # Determine area preference
                area_id, area_name = None, None
                if same_area and matched_devices:
                    area_id = matched_devices[0].area_id
                    area_name = matched_devices[0].area_name
                
                # Auto-fill inputs
                autofilled, unfilled = self.input_autofill.autofill_inputs(
                    inputs, matched_devices, area_id
                )
                
                autofill_complete = len(unfilled) == 0
                one_click_deploy = fit_score >= 0.95 and autofill_complete
            else:
                autofilled = []
                unfilled = []
                autofill_complete = False
                one_click_deploy = False
                area_id, area_name = None, None
            
            opportunity = BlueprintOpportunity(
                id=str(uuid4()),
                blueprint=blueprint,
                fit_score=fit_score,
                matched_devices=matched_devices,
                matching_domains=self.device_matcher.get_matching_domains(blueprint, matched_devices),
                matching_device_classes=self.device_matcher.get_matching_device_classes(blueprint, matched_devices),
                area_id=area_id,
                area_name=area_name,
                same_area=same_area,
                autofilled_inputs=autofilled,
                unfilled_inputs=unfilled,
                autofill_complete=autofill_complete,
                one_click_deploy=one_click_deploy,
                deployment_method="blueprint",
                discovered_at=datetime.now(timezone.utc),
                reason=self._generate_reason(blueprint, fit_score, same_area),
            )
            
            opportunities.append(opportunity)
            
            if len(opportunities) >= request.limit:
                break
        
        elapsed_ms = (time.time() - start_time) * 1000
        logger.info(f"Discovered {len(opportunities)} opportunities in {elapsed_ms:.1f}ms")
        
        return OpportunityDiscoveryResponse(
            opportunities=opportunities,
            total_found=len(ranked),
            device_count=len(devices),
            area_count=len(areas),
            discovery_time_ms=elapsed_ms,
        )
    
    async def preview_deployment(
        self,
        blueprint_id: str,
        area_id: Optional[str] = None,
    ) -> Optional[BlueprintDeploymentPreview]:
        """
        Preview what a blueprint deployment would look like.
        
        Args:
            blueprint_id: Blueprint to preview
            area_id: Optional area to target
            
        Returns:
            Deployment preview or None if not possible
        """
        # Fetch blueprint details
        blueprint = await self._get_blueprint_details(blueprint_id)
        if not blueprint:
            return None
        
        # Fetch devices
        devices = await self._fetch_device_inventory()
        
        # Filter by area if specified
        if area_id:
            devices = [d for d in devices if d.area_id == area_id]
        
        # Auto-fill inputs
        inputs = blueprint.get("inputs", {})
        autofilled, unfilled = self.input_autofill.autofill_inputs(
            inputs, devices, area_id
        )
        
        # Extract target entities
        target_entities = [a.entity_id for a in autofilled if a.entity_id]
        
        # Generate automation name
        automation_name = f"HomeIQ: {blueprint.get('name', 'Automation')}"
        
        issues = []
        if unfilled:
            issues.append(f"Missing required inputs: {', '.join(unfilled)}")
        
        return BlueprintDeploymentPreview(
            blueprint_id=blueprint_id,
            blueprint_name=blueprint.get("name", ""),
            automation_name=automation_name,
            inputs=self.input_autofill.generate_input_dict(autofilled),
            autofilled_inputs=autofilled,
            manual_inputs_required=unfilled,
            target_entities=target_entities,
            estimated_complexity=blueprint.get("complexity", "medium"),
            ready_to_deploy=len(unfilled) == 0,
            deployment_issues=issues,
            yaml_preview=blueprint.get("yaml_content"),
        )
    
    async def _fetch_device_inventory(self) -> list[DeviceSignature]:
        """Fetch device inventory from data-api."""
        devices = []
        
        try:
            if not self._client:
                raise RuntimeError("Client not initialized")
            
            # Fetch entities
            response = await self._client.get(
                f"{self.data_api_url}/api/entities"
            )
            
            if response.status_code == 200:
                entities_data = response.json()
                
                # Handle both list and dict with 'entities' key
                if isinstance(entities_data, dict):
                    entities = entities_data.get("entities", [])
                else:
                    entities = entities_data
                
                for entity in entities:
                    entity_id = entity.get("entity_id", "")
                    if not entity_id:
                        continue
                    
                    # Extract domain from entity_id
                    parts = entity_id.split(".", 1)
                    domain = parts[0] if len(parts) > 0 else ""
                    
                    device = DeviceSignature(
                        entity_id=entity_id,
                        domain=domain,
                        device_class=entity.get("device_class"),
                        area_id=entity.get("area_id"),
                        area_name=entity.get("area_name"),
                        device_id=entity.get("device_id"),
                        friendly_name=entity.get("friendly_name"),
                        manufacturer=entity.get("manufacturer"),
                        model=entity.get("model"),
                        integration=entity.get("integration"),
                    )
                    devices.append(device)
            else:
                logger.warning(f"Failed to fetch entities: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error fetching device inventory: {e}", exc_info=True)
        
        return devices
    
    async def _search_blueprints(
        self,
        domains: Optional[list[str]] = None,
        device_classes: Optional[list[str]] = None,
        use_cases: Optional[list[str]] = None,
        min_quality_score: float = 0.5,
        limit: int = 50,
    ) -> list[BlueprintSummary]:
        """Search blueprints from blueprint-index service."""
        blueprints = []
        
        try:
            if not self._client:
                raise RuntimeError("Client not initialized")
            
            params = {
                "min_quality_score": min_quality_score,
                "limit": limit,
            }
            
            if domains:
                params["domains"] = ",".join(domains)
            if device_classes:
                params["device_classes"] = ",".join(device_classes)
            if use_cases:
                params["use_case"] = use_cases[0]  # First use case
            
            response = await self._client.get(
                f"{self.blueprint_index_url}/api/blueprints/search",
                params=params,
            )
            
            if response.status_code == 200:
                data = response.json()
                
                for bp in data.get("blueprints", []):
                    blueprint = BlueprintSummary(
                        id=bp.get("id", ""),
                        name=bp.get("name", ""),
                        description=bp.get("description"),
                        source_url=bp.get("source_url", ""),
                        source_type=bp.get("source_type", ""),
                        domain=bp.get("domain", "automation"),
                        use_case=bp.get("use_case"),
                        required_domains=bp.get("required_domains", []),
                        required_device_classes=bp.get("required_device_classes", []),
                        community_rating=bp.get("community_rating", 0.0),
                        quality_score=bp.get("quality_score", 0.5),
                        stars=bp.get("stars", 0),
                        complexity=bp.get("complexity", "medium"),
                        author=bp.get("author"),
                    )
                    blueprints.append(blueprint)
            else:
                logger.warning(f"Failed to search blueprints: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error searching blueprints: {e}", exc_info=True)
        
        return blueprints
    
    async def _get_blueprint_details(
        self,
        blueprint_id: str,
    ) -> Optional[dict[str, Any]]:
        """Get full blueprint details from blueprint-index service."""
        try:
            if not self._client:
                raise RuntimeError("Client not initialized")
            
            response = await self._client.get(
                f"{self.blueprint_index_url}/api/blueprints/{blueprint_id}"
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Failed to get blueprint {blueprint_id}: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting blueprint details: {e}", exc_info=True)
            return None
    
    def _generate_reason(
        self,
        blueprint: BlueprintSummary,
        fit_score: float,
        same_area: bool,
    ) -> str:
        """Generate human-readable reason for recommendation."""
        reasons = []
        
        if fit_score >= 0.95:
            reasons.append("Perfect match for your devices")
        elif fit_score >= 0.8:
            reasons.append("Great match for your devices")
        else:
            reasons.append("Matches some of your devices")
        
        if same_area:
            reasons.append("all devices are in the same area")
        
        if blueprint.community_rating >= 0.8:
            reasons.append(f"highly rated by community ({int(blueprint.community_rating * 100)}%)")
        
        if blueprint.stars >= 100:
            reasons.append(f"popular ({blueprint.stars} stars)")
        
        return " - ".join(reasons)
