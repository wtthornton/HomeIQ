"""Unit tests for DeviceRecommenderService — Story 85.2

Tests the pure logic in find_similar_devices() and wrapper methods.
"""

import pytest
from unittest.mock import MagicMock, patch

from src.services.device_recommender import (
    DeviceRecommenderService,
    get_recommender_service,
)


class TestFindSimilarDevices:
    """Test find_similar_devices — pure in-memory similarity scoring."""

    def setup_method(self):
        self.svc = DeviceRecommenderService()

    def _make_device(self, device_id, device_type=None, manufacturer=None, device_category=None):
        return {
            "device_id": device_id,
            "device_type": device_type,
            "manufacturer": manufacturer,
            "device_category": device_category,
        }

    def test_empty_device_list(self):
        result = self.svc.find_similar_devices("d1", [])
        assert result == []

    def test_reference_device_not_found(self):
        devices = [self._make_device("d2", "light", "Philips", "lighting")]
        result = self.svc.find_similar_devices("d1", devices)
        assert result == []

    def test_identical_type_scores_high(self):
        devices = [
            self._make_device("d1", "light", "Philips", "lighting"),
            self._make_device("d2", "light", "IKEA", "lighting"),
        ]
        result = self.svc.find_similar_devices("d1", devices)
        assert len(result) == 1
        assert result[0]["device_id"] == "d2"
        # type(0.5) + category(0.2) = 0.7
        assert result[0]["similarity_score"] == pytest.approx(0.7)

    def test_same_manufacturer_scores(self):
        devices = [
            self._make_device("d1", "light", "Philips", "lighting"),
            self._make_device("d2", "sensor", "Philips", "sensor"),
        ]
        result = self.svc.find_similar_devices("d1", devices)
        # Only manufacturer matches (0.3) — not above 0.3 threshold
        # score must be > 0.3 to be included
        assert len(result) == 0

    def test_same_type_and_manufacturer(self):
        devices = [
            self._make_device("d1", "light", "Philips", "lighting"),
            self._make_device("d2", "light", "Philips", "lighting"),
        ]
        result = self.svc.find_similar_devices("d1", devices)
        assert len(result) == 1
        # type(0.5) + manufacturer(0.3) + category(0.2) = 1.0
        assert result[0]["similarity_score"] == pytest.approx(1.0)

    def test_excludes_reference_device(self):
        devices = [
            self._make_device("d1", "light", "Philips", "lighting"),
        ]
        result = self.svc.find_similar_devices("d1", devices)
        assert len(result) == 0

    def test_excludes_low_score_devices(self):
        """Devices with score <= 0.3 are excluded."""
        devices = [
            self._make_device("d1", "light", "Philips", "lighting"),
            self._make_device("d2", "sensor", "IKEA", "sensor"),
        ]
        result = self.svc.find_similar_devices("d1", devices)
        assert len(result) == 0

    def test_results_sorted_by_similarity_descending(self):
        devices = [
            self._make_device("d1", "light", "Philips", "lighting"),
            self._make_device("d2", "light", "IKEA", "lighting"),      # 0.7
            self._make_device("d3", "light", "Philips", "lighting"),   # 1.0
        ]
        result = self.svc.find_similar_devices("d1", devices)
        assert result[0]["device_id"] == "d3"
        assert result[1]["device_id"] == "d2"

    def test_max_10_results(self):
        ref = self._make_device("d1", "light", "Philips", "lighting")
        others = [
            self._make_device(f"d{i}", "light", "Philips", "lighting")
            for i in range(2, 20)
        ]
        result = self.svc.find_similar_devices("d1", [ref] + others)
        assert len(result) == 10

    def test_none_fields_dont_crash(self):
        devices = [
            self._make_device("d1", None, None, None),
            self._make_device("d2", None, None, None),
        ]
        result = self.svc.find_similar_devices("d1", devices)
        # None == None is True for all 3 fields: 0.5+0.3+0.2 = 1.0
        assert len(result) == 1


class TestCompareDevices:

    def setup_method(self):
        self.svc = DeviceRecommenderService()

    def test_no_engine_returns_unavailable(self):
        result = self.svc.compare_devices(["d1", "d2"], [])
        assert "not available" in result["message"]
        assert result["devices"] == []

    def test_with_engine_delegates(self):
        mock_engine = MagicMock()
        mock_engine.compare_devices.return_value = {"winner": "d1", "devices": []}
        self.svc._comparison_engine = mock_engine

        result = self.svc.compare_devices(["d1", "d2"], [{"id": "d1"}, {"id": "d2"}])
        assert result["winner"] == "d1"
        mock_engine.compare_devices.assert_called_once()

    def test_engine_exception_returns_error(self):
        mock_engine = MagicMock()
        mock_engine.compare_devices.side_effect = Exception("comparison failed")
        self.svc._comparison_engine = mock_engine

        result = self.svc.compare_devices(["d1"], [])
        assert "failed" in result["message"]
        assert result["devices"] == []


class TestRecommendDevices:

    def setup_method(self):
        self.svc = DeviceRecommenderService()

    @pytest.mark.asyncio
    async def test_no_recommender_returns_empty(self):
        result = await self.svc.recommend_devices("light")
        assert result == []

    @pytest.mark.asyncio
    async def test_recommender_exception_returns_empty(self):
        mock_rec = MagicMock()
        mock_rec.recommend_devices = MagicMock(side_effect=Exception("fail"))
        self.svc._recommender = mock_rec
        result = await self.svc.recommend_devices("light")
        assert result == []


class TestSingleton:

    def test_returns_same_instance(self):
        import src.services.device_recommender as mod
        mod._recommender_service = None
        assert get_recommender_service() is get_recommender_service()
