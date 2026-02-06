"""
Policy management router for data-retention service.
"""

import logging

from fastapi import APIRouter, HTTPException, Path, Request

from ..models import PolicyListResponse, PolicyCreateRequest, PolicyUpdateRequest, PolicyResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/policies", tags=["policies"])


@router.get("", response_model=PolicyListResponse)
async def get_policies(request: Request):
    """
    Get all retention policies.

    Returns a list of all configured retention policies.
    """
    try:
        service = request.app.state.service
        policies = service.get_retention_policies()
        return {"policies": policies}
    except Exception as e:
        logger.error(f"Get policies failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": "Internal server error"})


@router.post("", response_model=PolicyResponse, status_code=201)
async def add_policy(request: Request, policy: PolicyCreateRequest):
    """
    Add a new retention policy.

    Creates a new retention policy with the specified configuration.
    """
    try:
        service = request.app.state.service
        service.add_retention_policy(policy.model_dump())
        return {"message": "Policy added successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": str(e)})
    except Exception as e:
        logger.error(f"Add policy failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": "Internal server error"})


@router.put("", response_model=PolicyResponse)
async def update_policy(request: Request, policy: PolicyUpdateRequest):
    """
    Update an existing retention policy.

    Updates the specified retention policy. Only provided fields will be updated.
    """
    try:
        service = request.app.state.service
        service.update_retention_policy(policy.model_dump())
        return {"message": "Policy updated successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": str(e)})
    except Exception as e:
        logger.error(f"Update policy failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": "Internal server error"})


@router.delete("/{policy_name}", response_model=PolicyResponse)
async def delete_policy(request: Request, policy_name: str = Path(..., description="Name of the policy to delete")):
    """
    Delete a retention policy.

    Removes the specified retention policy.
    """
    try:
        service = request.app.state.service
        service.remove_retention_policy(policy_name)
        return {"message": "Policy deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": str(e)})
    except Exception as e:
        logger.error(f"Delete policy failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail={"error": "Internal server error"})

