"""
Spec Management Router

CRUD endpoints for automation specs
"""

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Body

from shared.homeiq_automation.spec_validator import SpecValidator

from ..registry.spec_registry import SpecRegistry
from ..config import settings

router = APIRouter(prefix="/api/specs", tags=["specs"])

# Initialize registry and validator
spec_registry = SpecRegistry(settings.database_url)
spec_validator = SpecValidator()


@router.post("")
async def create_spec(spec: dict, home_id: str = settings.home_id):
    """Create/update automation spec"""
    try:
        # Validate spec before storing
        is_valid, errors = spec_validator.validate(spec)
        if not is_valid:
            error_messages = [e.get("message", str(e)) for e in errors]
            raise HTTPException(
                status_code=400,
                detail={"errors": error_messages, "validation_failed": True}
            )
        
        result = spec_registry.store_spec(spec, home_id, deploy=False)
        return {"success": True, "spec": result}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{spec_id}")
async def get_spec(spec_id: str, home_id: str = settings.home_id, version: Optional[str] = None):
    """Get automation spec"""
    spec = spec_registry.get_spec(spec_id, home_id, version)
    if not spec:
        raise HTTPException(status_code=404, detail="Spec not found")
    return {"success": True, "spec": spec}


@router.get("/{spec_id}/history")
async def get_spec_history(spec_id: str, home_id: str = settings.home_id):
    """Get spec version history"""
    history = spec_registry.get_spec_history(spec_id, home_id)
    return {"success": True, "history": history}


@router.post("/{spec_id}/deploy")
async def deploy_spec(
    spec_id: str,
    request_data: dict = Body(default={}),
    home_id: str = settings.home_id
):
    """Deploy spec version"""
    version = request_data.get("version")
    if not version:
        raise HTTPException(status_code=400, detail="version is required in request body")
    
    success = spec_registry.deploy_spec(spec_id, home_id, version)
    if not success:
        raise HTTPException(status_code=404, detail="Spec version not found")
    return {"success": True, "spec_id": spec_id, "version": version}


@router.get("")
async def list_specs(home_id: str = settings.home_id):
    """List all active specs for home"""
    specs = spec_registry.get_active_specs(home_id)
    return {"success": True, "specs": specs}
