"""First-version rollback removes the automation from HA (_rollback_by_removal).

Compiled-flow deployments write only a Deployment row; rollback of version 1
must mean removal, not 'No previous version found'.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.services.deployment_service import DeploymentError, DeploymentService


def make_service(deployment):
    svc = DeploymentService.__new__(DeploymentService)
    svc.ha_client = AsyncMock()
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = deployment
    db.execute.return_value = result
    svc.db = db
    return svc


@pytest.mark.asyncio
async def test_removal_deletes_from_ha_and_marks_rolled_back():
    deployment = MagicMock(deployment_id="d_abc", status="deployed")
    svc = make_service(deployment)

    out = await svc._rollback_by_removal("office_presence_lighting")

    svc.ha_client.delete_automation.assert_awaited_once_with("office_presence_lighting")
    assert deployment.status == "rolled_back"
    svc.db.commit.assert_awaited_once()
    assert out == {
        "automation_id": "office_presence_lighting",
        "status": "rolled_back",
        "action": "removed",
        "deployment_id": "d_abc",
    }


@pytest.mark.asyncio
async def test_removal_without_deployment_raises():
    svc = make_service(None)
    with pytest.raises(DeploymentError):
        await svc._rollback_by_removal("ghost_automation")
    svc.ha_client.delete_automation.assert_not_awaited()
