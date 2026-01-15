"""
Observability Router

Endpoints for metrics and explainability
"""

from fastapi import APIRouter, HTTPException

from ..observability.explainer import Explainer
from ..rollout.kill_switch import KillSwitch

router = APIRouter(prefix="/api/observability", tags=["observability"])

explainer = Explainer()
kill_switch = KillSwitch()


@router.get("/explain/{correlation_id}")
async def explain_execution(correlation_id: str):
    """Get explanation for execution"""
    explanation = explainer.generate_user_explanation(correlation_id)
    if not explanation:
        raise HTTPException(status_code=404, detail="Explanation not found")
    return {"success": True, "explanation": explanation}


@router.get("/kill-switch/status")
async def get_kill_switch_status():
    """Get kill switch status"""
    return {"success": True, "status": kill_switch.get_status()}


@router.post("/kill-switch/pause")
async def pause_kill_switch(global_pause: bool = False, home_id: str = None, spec_id: str = None):
    """Pause automations via kill switch"""
    if global_pause:
        kill_switch.pause_global()
    elif home_id:
        kill_switch.pause_home(home_id)
    elif spec_id:
        kill_switch.pause_spec(spec_id)
    else:
        raise HTTPException(status_code=400, detail="Must specify global_pause, home_id, or spec_id")
    return {"success": True}


@router.post("/kill-switch/resume")
async def resume_kill_switch(global_resume: bool = False, home_id: str = None, spec_id: str = None):
    """Resume automations via kill switch"""
    if global_resume:
        kill_switch.resume_global()
    elif home_id:
        kill_switch.resume_home(home_id)
    elif spec_id:
        kill_switch.resume_spec(spec_id)
    else:
        raise HTTPException(status_code=400, detail="Must specify global_resume, home_id, or spec_id")
    return {"success": True}
