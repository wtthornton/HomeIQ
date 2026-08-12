"""Deploy create/update and rollback semantics (TAP-5992).

Reproduces the 2026-08-12 incident: deploying a new artifact with
ha_automation_id omitted matched an unrelated same-area deployment,
overwrote it as v2, and the rollback then removed that automation from
HA entirely. Omitted id must ALWAYS create; rollback of version N>1 must
restore version N-1; removal only ever applies to a version-1 chain.
"""

import uuid
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from src.database.models import CompiledArtifact, Deployment, Plan


def unique(prefix: str) -> str:
    """The shared test DB persists rows across runs; scope every id."""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


async def deployments_for(db, compiled_ids):
    rows = (
        (
            await db.execute(
                select(Deployment)
                .where(Deployment.compiled_id.in_(compiled_ids))
                .order_by(Deployment.version, Deployment.deployed_at)
            )
        )
        .scalars()
        .all()
    )
    return rows

BENIGN_YAML_A = """\
alias: Office presence lighting
triggers:
  - trigger: state
    entity_id: binary_sensor.office_presence_group
    to: "on"
actions:
  - action: light.turn_on
    target:
      entity_id: light.office
"""

BENIGN_YAML_B = """\
alias: Office fan comfort
triggers:
  - trigger: state
    entity_id: binary_sensor.office_presence_group
    to: "on"
actions:
  - action: fan.turn_on
    target:
      entity_id: fan.office
"""


@pytest.fixture
def mock_ha(monkeypatch):
    """Deploy handler calls get_ha_client() directly; hand it a counter mock."""
    from src.api import dependencies

    ha = AsyncMock()
    counter = {"n": 0}
    run_id = uuid.uuid4().hex[:8]  # HA ids must not repeat across tests

    async def deploy_automation(_yaml: str):
        counter["n"] += 1
        return {"automation_id": f"automation.created_{run_id}_{counter['n']}"}

    ha.deploy_automation = AsyncMock(side_effect=deploy_automation)
    monkeypatch.setattr(dependencies, "get_ha_client", lambda: ha)
    return ha


async def seed_artifact(db, compiled_id: str, yaml_text: str, area: str = "office"):
    db.add(
        Plan(
            plan_id=f"plan_{compiled_id}",
            template_id="presence_template",
            template_version=1,
            parameters={},
            confidence=0.9,
            safety_class="low",
        )
    )
    await db.commit()
    db.add(
        CompiledArtifact(
            compiled_id=compiled_id,
            plan_id=f"plan_{compiled_id}",
            template_id="presence_template",
            area_id=area,
            yaml=yaml_text,
            human_summary=f"summary for {compiled_id}",
        )
    )
    await db.commit()


async def deploy(client, compiled_id: str, ha_automation_id: str | None = None):
    body = {"compiled_id": compiled_id}
    if ha_automation_id:
        body["ha_automation_id"] = ha_automation_id
    response = await client.post("/api/deploy/automation/deploy", json=body)
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.asyncio
async def test_omitted_id_never_updates_a_same_area_deployment(client, db_session, mock_ha):
    """The incident sequence: deploy A, deploy B without id — A stays intact."""
    light, fan = unique("c_light"), unique("c_fan")
    await seed_artifact(db_session, light, BENIGN_YAML_A)
    await seed_artifact(db_session, fan, BENIGN_YAML_B)  # same template + area

    first = await deploy(client, light)
    second = await deploy(client, fan)  # id omitted — must CREATE

    assert first["ha_automation_id"] != second["ha_automation_id"]

    rows = await deployments_for(db_session, [light, fan])
    assert len(rows) == 2
    assert all(r.status == "deployed" for r in rows), "no superseded row for an unrelated artifact"
    assert all(r.version == 1 for r in rows)


@pytest.mark.asyncio
async def test_explicit_id_updates_and_chains_versions(client, db_session, mock_ha):
    v1, v2 = unique("c_v1"), unique("c_v2")
    await seed_artifact(db_session, v1, BENIGN_YAML_A)
    await seed_artifact(db_session, v2, BENIGN_YAML_A)

    first = await deploy(client, v1)
    target = first["ha_automation_id"]
    second = await deploy(client, v2, ha_automation_id=target)

    assert second["ha_automation_id"] == target
    rows = await deployments_for(db_session, [v1, v2])
    assert [r.version for r in rows] == [1, 2]
    assert rows[0].status == "superseded"
    assert rows[1].status == "deployed"


@pytest.mark.asyncio
async def test_rollback_of_v2_restores_v1_not_removal(client, db_session, mock_ha):
    from src.services.deployment_service import DeploymentService

    v1, v2 = unique("c_v1"), unique("c_v2")
    await seed_artifact(db_session, v1, BENIGN_YAML_A)
    await seed_artifact(db_session, v2, BENIGN_YAML_A)
    first = await deploy(client, v1)
    target = first["ha_automation_id"]
    await deploy(client, v2, ha_automation_id=target)

    service = DeploymentService(db=db_session, ha_client=mock_ha, yaml_service=AsyncMock())
    result = await service.rollback_automation(target)

    assert result["success"] is True
    assert result["restored_version"] == 1
    # v1's YAML was redeployed, not removed
    redeployed = mock_ha.deploy_automation.await_args.args[0]
    assert "Office presence lighting" in redeployed
    assert f"id: {target}" in redeployed

    rows = await deployments_for(db_session, [v1, v2])
    assert rows[0].status == "deployed"  # v1 active again
    assert rows[1].status == "rolled_back"


@pytest.mark.asyncio
async def test_rollback_of_v1_removes(client, db_session, mock_ha):
    from src.services.deployment_service import DeploymentService

    only = unique("c_only")
    await seed_artifact(db_session, only, BENIGN_YAML_A)
    first = await deploy(client, only)
    target = first["ha_automation_id"]

    service = DeploymentService(db=db_session, ha_client=mock_ha, yaml_service=AsyncMock())
    service._rollback_by_removal = AsyncMock(
        return_value={"success": True, "message": "removed", "automation_id": target}
    )
    result = await service.rollback_automation(target)

    assert result["message"] == "removed"
    service._rollback_by_removal.assert_awaited_once_with(target)
    rows = await deployments_for(db_session, [only])
    assert rows[0].status == "rolled_back"
