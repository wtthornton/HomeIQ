"""Naming rubric contract tests (TAP-6230).

This service owns the only naming/area scoring rubric in HomeIQ. The dashboard
used to carry a second copy in TypeScript and the two had already drifted apart,
so `contracts/naming-rubric/golden-vectors.json` now pins the rubric's output and
both sides assert against it.

Two failure modes are covered:
  * the rubric changes but the vectors were not regenerated, and
  * the rubric holds but the HTTP layer stops serializing it faithfully.

If a rubric change is intentional, regenerate the vectors:
    .venv/bin/python contracts/naming-rubric/generate_vectors.py
and the dashboard's vitest parity suite will pick up the new expectations.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.api.naming_router import router
from src.services.naming_convention.score_engine import ScoreEngine

REPO_ROOT = Path(__file__).resolve().parents[4]
VECTORS_PATH = REPO_ROOT / "contracts/naming-rubric/golden-vectors.json"


def _load_vectors() -> list[dict]:
    return json.loads(VECTORS_PATH.read_text())["vectors"]


VECTORS = _load_vectors()


@pytest.fixture(scope="module")
def client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_vectors_file_is_present_and_populated():
    assert VECTORS, f"no golden vectors found at {VECTORS_PATH}"


@pytest.mark.parametrize("vector", VECTORS, ids=lambda v: v["name"])
def test_engine_reproduces_golden_vector(vector):
    """The rubric still produces the score the contract promises."""
    score = ScoreEngine().score_entity(dict(vector["entity"]))
    assert score.total_score == vector["expected"]["total_score"], vector["why"]


@pytest.mark.parametrize("vector", VECTORS, ids=lambda v: v["name"])
def test_engine_reproduces_per_rule_breakdown(vector):
    """Per-rule points match too, so an offsetting pair of changes cannot hide."""
    score = ScoreEngine().score_entity(dict(vector["entity"]))
    actual = {r.rule_name: r.earned_points for r in score.rule_results}
    expected = {r["rule"]: r["earned"] for r in vector["expected"]["rules"]}
    assert actual == expected, vector["why"]


def test_stateless_endpoint_scores_every_vector_identically(client):
    """POST /score is the path the dashboard uses; it must not re-interpret anything."""
    response = client.post(
        "/api/naming/score",
        json={"entities": [v["entity"] for v in VECTORS]},
    )
    assert response.status_code == 200

    scored = response.json()["entities"]
    assert len(scored) == len(VECTORS)
    for actual, vector in zip(scored, VECTORS, strict=True):
        assert actual["entity_id"] == vector["entity"]["entity_id"]
        assert actual["total_score"] == vector["expected"]["total_score"], vector["why"]
        assert actual["max_score"] == vector["expected"]["max_score"]


def test_stateless_endpoint_reads_nothing_from_the_database(client):
    """An entity absent from the registry still scores, which is why this path exists."""
    response = client.post(
        "/api/naming/score",
        json={
            "entities": [
                {
                    "entity_id": "light.never_synced",
                    "domain": "light",
                    "area_id": "office",
                    "friendly_name": "Office Lamp",
                    "device_class": "light",
                    "aliases": ["lamp", "office lamp"],
                    "labels": ["ai:automatable"],
                }
            ]
        },
    )
    assert response.status_code == 200
    assert response.json()["entities"][0]["total_score"] == 100


def test_stateless_endpoint_rejects_an_empty_batch(client):
    response = client.post("/api/naming/score", json={"entities": []})
    assert response.status_code == 422
