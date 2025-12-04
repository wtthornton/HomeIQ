"""
Policy management router for data-retention service.
"""

from fastapi import APIRouter, HTTPException, Path, Request

from ..models import PolicyListResponse, PolicyCreateRequest, PolicyUpdateRequest, PolicyResponse

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
        raise HTTPException(status_code=500, detail={"error": str(e)})


@router.post("", response_model=PolicyResponse, status_code=201)
async def add_policy(request: Request, policy: PolicyCreateRequest):
    """
    Add a new retention policy.
    
    Creates a new retention policy with the specified configuration.
    """
    try:
        service = request.app.state.service
        service.add_retention_policy(policy.dict())
        return {"message": "Policy added successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail={"error": str(e)})


@router.put("", response_model=PolicyResponse)
async def update_policy(request: Request, policy: PolicyUpdateRequest):
    """
    Update an existing retention policy.
    
    Updates the specified retention policy. Only provided fields will be updated.
    """
    try:
        # Note: The original implementation expects policy name in the request body
        # We'll need to check the actual implementation to see how it handles updates
        service = request.app.state.service
        service.update_retention_policy(policy.dict())
        return {"message": "Policy updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail={"error": str(e)})


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
    except Exception as e:
        raise HTTPException(status_code=400, detail={"error": str(e)})

