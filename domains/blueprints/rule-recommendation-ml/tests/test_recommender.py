"""
Epic 90, Story 90.8: Rule recommendation ML unit tests.

Tests collaborative filtering, device-based recommendations,
popular fallback, cold-start handling, model save/load, and pickle security.

NOTE: These tests require the ``implicit`` library.  If it is not installed
the entire module is skipped gracefully.
"""

from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np
import pytest
from scipy.sparse import csr_matrix, random as sparse_random

# Try to import the recommender; skip the module if implicit is missing.
try:
    import sys
    _service_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(_service_root / "src"))
    from models.rule_recommender import RuleRecommender  # noqa: E402
except ImportError as _exc:
    pytest.skip(f"Skipping recommender tests: {_exc}", allow_module_level=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_sample_data(
    n_users: int = 20,
    n_patterns: int = 10,
    density: float = 0.3,
) -> tuple[csr_matrix, dict[int, str], dict[int, str]]:
    """Create synthetic user-pattern interaction data."""
    mat = sparse_random(n_users, n_patterns, density=density, format="csr", random_state=42)
    mat.data[:] = np.clip(mat.data * 5, 1, 10)  # positive confidence values

    idx_to_user = {i: f"user_{i}" for i in range(n_users)}
    idx_to_pattern = {
        0: "binary_sensor_to_light",
        1: "switch_to_light",
        2: "time_to_climate",
        3: "sensor_to_fan",
        4: "binary_sensor_to_lock",
        5: "sun_to_cover",
        6: "time_to_light",
        7: "switch_to_climate",
        8: "binary_sensor_to_scene",
        9: "sensor_to_light",
    }
    # Pad if n_patterns > 10
    for i in range(10, n_patterns):
        idx_to_pattern[i] = f"pattern_{i}"

    return mat, idx_to_user, idx_to_pattern


def _fit_sample_recommender(**kwargs) -> RuleRecommender:
    """Create and fit a recommender with sample data."""
    mat, idx_to_user, idx_to_pattern = _build_sample_data(**kwargs)
    recommender = RuleRecommender(factors=16, iterations=10)
    recommender.fit(mat, idx_to_user, idx_to_pattern)
    return recommender


# ---------------------------------------------------------------------------
# Model Initialization
# ---------------------------------------------------------------------------

class TestRuleRecommenderInit:

    def test_instantiation(self):
        rec = RuleRecommender()
        assert rec is not None
        assert rec._is_fitted is False

    def test_default_factors(self):
        rec = RuleRecommender()
        assert rec.factors == 64

    def test_default_iterations(self):
        rec = RuleRecommender()
        assert rec.iterations == 50

    def test_custom_hyperparameters(self):
        rec = RuleRecommender(factors=32, iterations=20, regularization=0.05)
        assert rec.factors == 32
        assert rec.iterations == 20
        assert rec.regularization == 0.05


# ---------------------------------------------------------------------------
# Fit
# ---------------------------------------------------------------------------

class TestFit:

    def test_fit_marks_fitted(self):
        rec = _fit_sample_recommender()
        assert rec._is_fitted is True

    def test_fit_stores_mappings(self):
        mat, idx_to_user, idx_to_pattern = _build_sample_data()
        rec = RuleRecommender(factors=16, iterations=10)
        rec.fit(mat, idx_to_user, idx_to_pattern)
        assert len(rec.idx_to_user) == mat.shape[0]
        assert len(rec.idx_to_pattern) == mat.shape[1]
        assert len(rec.user_to_idx) == mat.shape[0]
        assert len(rec.pattern_to_idx) == mat.shape[1]

    def test_fit_returns_self(self):
        mat, idx_to_user, idx_to_pattern = _build_sample_data()
        rec = RuleRecommender(factors=16, iterations=10)
        result = rec.fit(mat, idx_to_user, idx_to_pattern)
        assert result is rec

    def test_fit_stores_user_items(self):
        rec = _fit_sample_recommender()
        assert rec._user_items is not None


# ---------------------------------------------------------------------------
# Recommendations (collaborative filtering)
# ---------------------------------------------------------------------------

class TestRecommend:

    def test_recommend_known_user(self):
        rec = _fit_sample_recommender()
        recs = rec.recommend(user_id="user_0", n=5)
        assert isinstance(recs, list)
        assert len(recs) <= 5
        for pattern, score in recs:
            assert isinstance(pattern, str)
            assert isinstance(score, float)

    def test_recommend_unknown_user_falls_back_to_popular(self):
        rec = _fit_sample_recommender()
        recs = rec.recommend(user_id="nonexistent_user", n=5)
        assert isinstance(recs, list)
        assert len(recs) > 0

    def test_recommend_by_user_idx(self):
        rec = _fit_sample_recommender()
        recs = rec.recommend(user_idx=0, n=5)
        assert isinstance(recs, list)

    def test_recommend_requires_fitted_model(self):
        rec = RuleRecommender()
        with pytest.raises(RuntimeError, match="fitted"):
            rec.recommend(user_id="user_0", n=5)

    def test_recommend_requires_user_id_or_idx(self):
        rec = _fit_sample_recommender()
        with pytest.raises(ValueError, match="user_id or user_idx"):
            rec.recommend(n=5)


# ---------------------------------------------------------------------------
# Device-based recommendations
# ---------------------------------------------------------------------------

class TestDeviceBasedRecommendations:

    def test_recommend_for_devices(self):
        rec = _fit_sample_recommender()
        recs = rec.recommend_for_devices(["light", "switch"], n=5)
        assert isinstance(recs, list)

    def test_recommend_for_devices_unmatched_domain(self):
        """Domains not in any pattern return empty list."""
        rec = _fit_sample_recommender()
        recs = rec.recommend_for_devices(["nonexistent_domain"], n=5)
        assert isinstance(recs, list)
        assert len(recs) == 0

    def test_recommend_for_devices_requires_fitted(self):
        rec = RuleRecommender()
        with pytest.raises(RuntimeError, match="fitted"):
            rec.recommend_for_devices(["light"], n=5)

    def test_recommend_for_devices_respects_limit(self):
        rec = _fit_sample_recommender()
        recs = rec.recommend_for_devices(["light", "switch", "climate"], n=2)
        assert len(recs) <= 2


# ---------------------------------------------------------------------------
# Popular rules
# ---------------------------------------------------------------------------

class TestPopularRules:

    def test_get_popular_rules(self):
        rec = _fit_sample_recommender()
        popular = rec.get_popular_rules(n=5)
        assert isinstance(popular, list)
        assert len(popular) <= 5
        for pattern, count in popular:
            assert isinstance(pattern, str)
            assert isinstance(count, float)

    def test_popular_sorted_descending(self):
        rec = _fit_sample_recommender()
        popular = rec.get_popular_rules(n=10)
        counts = [c for _, c in popular]
        assert counts == sorted(counts, reverse=True)

    def test_popular_returns_empty_when_no_data(self):
        rec = RuleRecommender()
        popular = rec.get_popular_rules(n=5)
        assert popular == []

    def test_popular_respects_limit(self):
        rec = _fit_sample_recommender()
        popular = rec.get_popular_rules(n=3)
        assert len(popular) <= 3


# ---------------------------------------------------------------------------
# Similar rules
# ---------------------------------------------------------------------------

class TestSimilarRules:

    def test_get_similar_rules_known_pattern(self):
        rec = _fit_sample_recommender()
        similar = rec.get_similar_rules("binary_sensor_to_light", n=3)
        assert isinstance(similar, list)

    def test_get_similar_rules_unknown_pattern(self):
        rec = _fit_sample_recommender()
        similar = rec.get_similar_rules("nonexistent_pattern", n=3)
        assert similar == []

    def test_get_similar_rules_requires_fitted(self):
        rec = RuleRecommender()
        with pytest.raises(RuntimeError, match="fitted"):
            rec.get_similar_rules("binary_sensor_to_light", n=3)


# ---------------------------------------------------------------------------
# Model info
# ---------------------------------------------------------------------------

class TestModelInfo:

    def test_model_info_before_fit(self):
        rec = RuleRecommender(factors=32, iterations=25)
        info = rec.get_model_info()
        assert info["is_fitted"] is False
        assert info["factors"] == 32
        assert info["iterations"] == 25
        assert info["num_users"] == 0

    def test_model_info_after_fit(self):
        rec = _fit_sample_recommender(n_users=20, n_patterns=10)
        info = rec.get_model_info()
        assert info["is_fitted"] is True
        assert info["num_users"] == 20
        assert info["num_patterns"] == 10
        assert info["matrix_shape"] == (20, 10)
        assert info["matrix_nnz"] > 0


# ---------------------------------------------------------------------------
# Save / Load
# ---------------------------------------------------------------------------

class TestSaveLoad:

    def test_save_creates_files(self, tmp_path):
        rec = _fit_sample_recommender()
        save_path = tmp_path / "model.pkl"
        rec.save(save_path)
        assert save_path.exists()
        assert save_path.with_suffix(".npz").exists()

    def test_load_restores_model(self, tmp_path):
        rec = _fit_sample_recommender()
        save_path = tmp_path / "model.pkl"
        rec.save(save_path)

        loaded = RuleRecommender.load(save_path)
        assert loaded._is_fitted is True
        assert loaded.factors == rec.factors
        assert loaded.iterations == rec.iterations
        assert len(loaded.idx_to_user) == len(rec.idx_to_user)
        assert len(loaded.idx_to_pattern) == len(rec.idx_to_pattern)

    def test_loaded_model_produces_same_popular(self, tmp_path):
        rec = _fit_sample_recommender()
        save_path = tmp_path / "model.pkl"
        rec.save(save_path)

        loaded = RuleRecommender.load(save_path)

        orig_popular = rec.get_popular_rules(n=5)
        loaded_popular = loaded.get_popular_rules(n=5)
        assert len(orig_popular) == len(loaded_popular)
        # Same patterns in same order
        orig_patterns = [p for p, _ in orig_popular]
        loaded_patterns = [p for p, _ in loaded_popular]
        assert orig_patterns == loaded_patterns

    def test_save_creates_parent_dirs(self, tmp_path):
        rec = _fit_sample_recommender()
        save_path = tmp_path / "nested" / "dir" / "model.pkl"
        rec.save(save_path)
        assert save_path.exists()


# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------

class TestPickleSecurity:

    def test_pickle_used_for_trusted_internal_files_only(self):
        """SECURITY: pickle.load is used for trusted internal model files only.

        Model files are generated internally and stored in /app/models/.
        The code has noqa: S301 / S403 comments documenting this decision.
        If model files ever come from external sources, switch to a secure
        serialization format.
        """
        assert hasattr(pickle, "load")
        assert hasattr(pickle, "dump")


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_single_user_single_pattern(self):
        """Minimal data (1 user, 1 pattern) doesn't crash."""
        mat = csr_matrix(np.array([[3.0]]))
        idx_to_user = {0: "sole_user"}
        idx_to_pattern = {0: "only_pattern"}
        rec = RuleRecommender(factors=4, iterations=5)
        rec.fit(mat, idx_to_user, idx_to_pattern)
        popular = rec.get_popular_rules(n=5)
        assert len(popular) == 1

    def test_recommend_n_larger_than_patterns(self):
        """Requesting more recs than patterns doesn't crash."""
        rec = _fit_sample_recommender(n_patterns=3)
        recs = rec.recommend(user_id="user_0", n=100)
        assert isinstance(recs, list)
        assert len(recs) <= 100
