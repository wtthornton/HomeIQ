"""
Epic 90, Story 90.8: Rule recommendation ML API tests.

Tests HTTP endpoints for rule-recommendation-ml service.
Mocks the global recommender and feedback store so tests run
without a trained model or database.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure src is importable
_service_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_service_root))

from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_recommender() -> MagicMock:
    """Return a mock RuleRecommender with realistic return values."""
    rec = MagicMock()
    rec._is_fitted = True
    rec.get_model_info.return_value = {
        "is_fitted": True,
        "factors": 64,
        "iterations": 50,
        "num_users": 100,
        "num_patterns": 25,
        "matrix_shape": (100, 25),
        "matrix_nnz": 500,
    }
    rec.recommend.return_value = [
        ("binary_sensor_to_light", 0.95),
        ("switch_to_light", 0.80),
    ]
    rec.get_popular_rules.return_value = [
        ("binary_sensor_to_light", 42.0),
        ("switch_to_light", 35.0),
    ]
    rec.recommend_for_devices.return_value = [
        ("binary_sensor_to_light", 1.5),
    ]
    rec.get_similar_rules.return_value = [
        ("switch_to_light", 0.90),
    ]
    rec.pattern_to_idx = {
        "binary_sensor_to_light": 0,
        "switch_to_light": 1,
        "time_to_climate": 2,
    }
    return rec


def _mock_feedback_store() -> MagicMock:
    """Return a mock FeedbackStore."""
    store = MagicMock()
    store.insert = AsyncMock()
    store.count_since_last_retrain = AsyncMock(return_value=0)
    return store


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def client():
    """Create test client with mocked model and feedback store."""
    mock_rec = _mock_recommender()
    mock_store = _mock_feedback_store()

    # Import app first to ensure src.api.routes is in sys.modules
    # before patch() tries to resolve the dotted path.
    from src.main import app

    with patch("src.api.routes._recommender", mock_rec), \
         patch("src.api.routes._feedback_store", mock_store), \
         patch("src.api.routes._memory_client", None), \
         patch("src.api.routes.init_feedback_store", return_value=mock_store), \
         patch("src.api.routes.init_memory_client", new_callable=AsyncMock), \
         patch("src.api.routes.load_model", return_value=True):

        yield TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class TestHealthEndpoint:

    def test_health_returns_200(self, client):
        response = client.get("/api/v1/health")
        assert response.status_code == 200

    def test_health_has_model_loaded_field(self, client):
        data = client.get("/api/v1/health").json()
        assert "model_loaded" in data

    def test_health_has_status(self, client):
        data = client.get("/api/v1/health").json()
        assert data["status"] == "healthy"


# ---------------------------------------------------------------------------
# Model info
# ---------------------------------------------------------------------------

class TestModelInfoEndpoint:

    def test_model_info_returns_200(self, client):
        response = client.get("/api/v1/model/info")
        assert response.status_code == 200

    def test_model_info_schema(self, client):
        data = client.get("/api/v1/model/info").json()
        assert "is_fitted" in data
        assert "factors" in data
        assert "num_users" in data
        assert "num_patterns" in data


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------

class TestRecommendationsEndpoint:

    def test_popular_recommendations(self, client):
        response = client.get("/api/v1/rule-recommendations?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert "recommendations" in data
        assert data["method"] == "popular"

    def test_recommendations_with_user_id(self, client):
        response = client.get("/api/v1/rule-recommendations?user_id=user_0&limit=5")
        assert response.status_code == 200
        data = response.json()
        assert "recommendations" in data
        assert data["method"] == "collaborative"

    def test_recommendations_with_device_domains(self, client):
        response = client.get(
            "/api/v1/rule-recommendations?device_domains=light&device_domains=switch&limit=5"
        )
        assert response.status_code == 200
        data = response.json()
        assert "recommendations" in data
        assert data["method"] == "device_based"

    def test_recommendations_with_limit(self, client):
        response = client.get("/api/v1/rule-recommendations?limit=3")
        assert response.status_code == 200
        data = response.json()
        assert len(data["recommendations"]) <= 3

    def test_recommendations_response_schema(self, client):
        response = client.get("/api/v1/rule-recommendations?limit=5")
        data = response.json()
        assert "recommendations" in data
        assert "method" in data
        assert "count" in data
        assert isinstance(data["recommendations"], list)
        if data["recommendations"]:
            rec = data["recommendations"][0]
            assert "rule_pattern" in rec
            assert "score" in rec
            assert "trigger_domain" in rec
            assert "action_domain" in rec
            assert "description" in rec

    def test_recommendations_count_matches_list(self, client):
        data = client.get("/api/v1/rule-recommendations?limit=5").json()
        assert data["count"] == len(data["recommendations"])


# ---------------------------------------------------------------------------
# Similar rules
# ---------------------------------------------------------------------------

class TestSimilarRulesEndpoint:

    def test_similar_rules_known_pattern(self, client):
        response = client.get(
            "/api/v1/rule-recommendations/similar?rule_pattern=binary_sensor_to_light&limit=5"
        )
        assert response.status_code == 200

    def test_similar_rules_unknown_pattern(self, client):
        """Unknown pattern returns 404."""
        mock_rec = _mock_recommender()
        mock_rec.get_similar_rules.return_value = []

        with patch("src.api.routes._recommender", mock_rec):
            from src.main import app
            c = TestClient(app, raise_server_exceptions=False)
            response = c.get(
                "/api/v1/rule-recommendations/similar?rule_pattern=nonexistent&limit=5"
            )
            assert response.status_code == 404

    def test_similar_rules_requires_pattern_param(self, client):
        response = client.get("/api/v1/rule-recommendations/similar")
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Popular rules
# ---------------------------------------------------------------------------

class TestPopularEndpoint:

    def test_popular_rules_200(self, client):
        response = client.get("/api/v1/rule-recommendations/popular?limit=5")
        assert response.status_code == 200

    def test_popular_response_schema(self, client):
        data = client.get("/api/v1/rule-recommendations/popular?limit=5").json()
        assert "recommendations" in data
        assert data["method"] == "popular"


# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------

class TestFeedbackEndpoint:

    def test_submit_feedback_accepted(self, client):
        response = client.post(
            "/api/v1/rule-recommendations/feedback",
            json={
                "rule_pattern": "binary_sensor_to_light",
                "feedback_type": "accepted",
                "user_id": "test_user",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "feedback_id" in data

    def test_feedback_requires_rule_pattern(self, client):
        response = client.post(
            "/api/v1/rule-recommendations/feedback",
            json={"feedback_type": "accepted"},
        )
        assert response.status_code == 422

    def test_feedback_requires_feedback_type(self, client):
        response = client.post(
            "/api/v1/rule-recommendations/feedback",
            json={"rule_pattern": "test_pattern"},
        )
        assert response.status_code == 422

    def test_feedback_invalid_type_rejected(self, client):
        response = client.post(
            "/api/v1/rule-recommendations/feedback",
            json={
                "rule_pattern": "test_pattern",
                "feedback_type": "invalid_type",
            },
        )
        assert response.status_code == 422

    def test_all_feedback_types_accepted(self, client):
        for ftype in ("accepted", "rejected", "ignored", "created"):
            response = client.post(
                "/api/v1/rule-recommendations/feedback",
                json={
                    "rule_pattern": "test_pattern",
                    "feedback_type": ftype,
                },
            )
            assert response.status_code == 200, f"Failed for feedback_type={ftype}"

    def test_feedback_with_rating(self, client):
        response = client.post(
            "/api/v1/rule-recommendations/feedback",
            json={
                "rule_pattern": "test_pattern",
                "feedback_type": "accepted",
                "rating": 5,
                "comment": "Works great",
            },
        )
        assert response.status_code == 200

    def test_feedback_rating_out_of_range(self, client):
        response = client.post(
            "/api/v1/rule-recommendations/feedback",
            json={
                "rule_pattern": "test_pattern",
                "feedback_type": "accepted",
                "rating": 10,
            },
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

class TestPatternsEndpoint:

    def test_list_patterns_200(self, client):
        response = client.get("/api/v1/patterns?limit=10")
        assert response.status_code == 200

    def test_list_patterns_schema(self, client):
        data = client.get("/api/v1/patterns?limit=10").json()
        assert "patterns" in data
        assert "total" in data
        assert isinstance(data["patterns"], list)

    def test_list_patterns_pagination(self, client):
        data = client.get("/api/v1/patterns?limit=2&offset=0").json()
        assert len(data["patterns"]) <= 2
