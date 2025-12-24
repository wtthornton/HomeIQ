# Story AI1.11: REST API - Home Assistant Integration

**Epic:** Epic-AI-1 - AI Automation Suggestion System  
**Story ID:** AI1.11  
**Priority:** Critical  
**Estimated Effort:** 10-12 hours  
**Dependencies:** Story AI1.10 (Suggestion management API)

---

## User Story

**As a** user  
**I want** to deploy approved automations to Home Assistant  
**so that** they run automatically

---

## Business Value

- Completes the automation deployment workflow
- Leverages HA's proven execution engine
- Enables tracking of deployed automations
- Supports rollback if automations don't work

---

## Acceptance Criteria

1. ✅ Converts suggestion JSON to valid HA automation YAML
2. ✅ Deploys to HA via REST API successfully
3. ✅ Handles HA API errors gracefully (entity not found, invalid YAML)
4. ✅ Tracks deployment status in database (deployed_at, ha_automation_id)
5. ✅ Stores HA automation_id for later removal
6. ✅ Can remove deployed automations via DELETE to HA API
7. ✅ YAML validation catches syntax errors before deployment
8. ✅ Success rate >95% for valid suggestions

---

## Technical Implementation Notes

### Home Assistant API Client

**Create: src/ha_client.py**

```python
import httpx
import yaml
from typing import Dict
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

class HomeAssistantClient:
    """Client for deploying automations to Home Assistant"""
    
    def __init__(self, ha_url: str, ha_token: str):
        self.ha_url = ha_url
        self.headers = {
            "Authorization": f"Bearer {ha_token}",
            "Content-Type": "application/json"
        }
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def get_automations(self) -> List[Dict]:
        """Fetch all current HA automations"""
        try:
            response = await self.client.get(
                f"{self.ha_url}/api/config/automation/config",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch HA automations: {e}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=2, max=10))
    async def deploy_automation(self, automation_dict: Dict) -> str:
        """
        Deploy automation to Home Assistant.
        
        Args:
            automation_dict: Automation in dict format (will be converted from YAML)
        
        Returns:
            automation_id from Home Assistant
        """
        try:
            response = await self.client.post(
                f"{self.ha_url}/api/config/automation/config",
                headers=self.headers,
                json=automation_dict
            )
            response.raise_for_status()
            
            result = response.json()
            automation_id = result.get('automation_id') or automation_dict.get('id')
            
            logger.info(f"Successfully deployed automation: {automation_id}")
            return automation_id
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HA API error deploying automation: {e.response.text}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Home Assistant rejected automation: {e.response.text}"
            )
    
    async def remove_automation(self, automation_id: str) -> bool:
        """Remove automation from Home Assistant"""
        try:
            response = await self.client.delete(
                f"{self.ha_url}/api/config/automation/config/{automation_id}",
                headers=self.headers
            )
            response.raise_for_status()
            
            logger.info(f"Successfully removed automation: {automation_id}")
            return True
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to remove automation {automation_id}: {e}")
            return False
    
    def validate_automation_yaml(self, yaml_str: str) -> Dict:
        """
        Validate automation YAML and convert to dict.
        
        Returns:
            Automation as dict if valid
        
        Raises:
            ValueError if YAML invalid
        """
        try:
            automation = yaml.safe_load(yaml_str)
            
            # Basic validation
            required_fields = ['alias', 'trigger', 'action']
            for field in required_fields:
                if field not in automation:
                    raise ValueError(f"Missing required field: {field}")
            
            return automation
            
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML: {e}")
```

### Deployment API Endpoint

**Create: src/api/deployment.py**

```python
from fastapi import APIRouter, HTTPException, Depends
from src.ha_client import HomeAssistantClient
from src.database.crud import get_suggestion_by_id, update_deployment_status
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/deploy", tags=["deployment"])

@router.post("/{suggestion_id}")
async def deploy_automation(
    suggestion_id: int,
    ha_client: HomeAssistantClient = Depends(get_ha_client),
    db: AsyncSession = Depends(get_db)
):
    """
    Deploy approved automation to Home Assistant.
    
    Workflow:
    1. Fetch suggestion from database
    2. Validate YAML
    3. Convert to dict
    4. POST to HA API
    5. Update database with deployment status
    """
    
    # 1. Get suggestion
    suggestion = await get_suggestion_by_id(db, suggestion_id)
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    
    if suggestion.status != 'approved':
        raise HTTPException(status_code=400, detail="Only approved suggestions can be deployed")
    
    # 2. Validate and convert YAML
    try:
        automation_dict = ha_client.validate_automation_yaml(suggestion.automation_yaml)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid automation YAML: {e}")
    
    # 3. Deploy to HA
    try:
        ha_automation_id = await ha_client.deploy_automation(automation_dict)
    except Exception as e:
        logger.error(f"Deployment failed for suggestion {suggestion_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Deployment failed: {e}")
    
    # 4. Update database
    await update_deployment_status(
        db,
        suggestion_id,
        status='deployed',
        ha_automation_id=ha_automation_id,
        deployed_at=datetime.utcnow()
    )
    
    logger.info(f"Suggestion {suggestion_id} deployed as {ha_automation_id}")
    
    return {
        "success": True,
        "suggestion_id": suggestion_id,
        "ha_automation_id": ha_automation_id,
        "deployed_at": datetime.utcnow().isoformat()
    }

@router.delete("/{suggestion_id}")
async def remove_deployed_automation(
    suggestion_id: int,
    ha_client: HomeAssistantClient = Depends(get_ha_client),
    db: AsyncSession = Depends(get_db)
):
    """Remove deployed automation from Home Assistant"""
    
    suggestion = await get_suggestion_by_id(db, suggestion_id)
    
    if not suggestion or suggestion.status != 'deployed':
        raise HTTPException(status_code=400, detail="Only deployed automations can be removed")
    
    # Remove from HA
    success = await ha_client.remove_automation(suggestion.ha_automation_id)
    
    if success:
        # Update database
        await update_deployment_status(db, suggestion_id, status='approved')
        return {"success": True, "message": "Automation removed from Home Assistant"}
    else:
        raise HTTPException(status_code=500, detail="Failed to remove from Home Assistant")
```

---

## Integration Verification

**IV1: Deployed automations appear in HA UI**
- Check HA automation list in UI
- Verify automation details correct
- Automation has "AI Suggested:" prefix

**IV2: Automations execute correctly in HA**
- Trigger automation manually in HA
- Verify actions execute
- Check HA logs for errors

**IV3: HA performance not impacted**
- Monitor HA response times
- Verify automation execution latency unchanged
- Check HA memory/CPU usage

**IV4: Existing HA automations unchanged**
- User-created automations still present
- No modifications to existing automations
- Deployment is additive only

---

## Tasks Breakdown

1. **Create HomeAssistantClient class** (2 hours)
2. **Implement get_automations method** (1 hour)
3. **Implement deploy_automation method** (2 hours)
4. **Implement remove_automation method** (1 hour)
5. **Add YAML validation** (1.5 hours)
6. **Create deployment API endpoints** (2 hours)
7. **Update database with deployment tracking** (1 hour)
8. **Unit tests** (1.5 hours)
9. **Integration test with real HA** (1 hour)

**Total:** 10-12 hours

---

## Definition of Done

- [ ] HomeAssistantClient implemented
- [ ] YAML conversion and validation working
- [ ] Deploy endpoint functional
- [ ] Remove endpoint functional
- [ ] HA API integration tested
- [ ] Deployment status tracking in database
- [ ] Error handling for all HA API errors
- [ ] YAML syntax validation
- [ ] Success rate >95% verified
- [ ] Integration test with real HA passes
- [ ] Code reviewed and approved

---

## Reference Files

**Copy patterns from:**
- Home Assistant REST API: https://developers.home-assistant.io/docs/api/rest/
- Existing HA integrations in project
- YAML library: https://pyyaml.org/

---

## Notes

- HA API requires long-lived access token
- YAML validation critical (invalid YAML crashes HA)
- Store ha_automation_id for later removal
- "AI Suggested:" prefix helps users identify source
- Test with simple automation first (time trigger + light on)

---

**Story Status:** Not Started  
**Assigned To:** TBD  
**Created:** 2025-10-15  
**Updated:** 2025-10-15

