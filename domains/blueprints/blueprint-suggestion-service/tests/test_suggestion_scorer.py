"""
Epic 90, Story 90.8: Blueprint suggestion scorer unit tests.

Tests scoring logic, weight normalization, complexity bonus,
fallback scoring, and edge cases.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_blueprint(**overrides) -> dict:
    """Build a minimal blueprint dict with sensible defaults."""
    bp = {
        "id": "bp-001",
        "name": "Test Blueprint",
        "required_domains": ["light"],
        "required_device_classes": [],
        "quality_score": 0.7,
        "community_rating": 0.6,
        "complexity": "simple",
    }
    bp.update(overrides)
    return bp


def _make_device(domain: str = "light", **overrides) -> dict:
    """Build a minimal device dict."""
    dev = {
        "entity_id": f"{domain}.test",
        "domain": domain,
        "device_class": None,
        "area_id": "living_room",
    }
    dev.update(overrides)
    return dev


# ---------------------------------------------------------------------------
# Weight / config tests (no scorer instance needed)
# ---------------------------------------------------------------------------

class TestScorerWeights:
    """Verify weight configuration from Settings."""

    def test_default_weights_sum_to_one(self):
        """All 6 configured weights sum to 1.0."""
        from src.config import settings

        total = (
            settings.device_match_weight
            + settings.blueprint_quality_weight
            + settings.community_rating_weight
            + settings.temporal_relevance_weight
            + settings.user_profile_weight
            + settings.complexity_bonus_weight
        )
        assert abs(total - 1.0) < 0.01, f"Weights should sum to 1.0, got {total}"

    def test_applied_weights_sum_to_080(self):
        """Applied weights (excluding temporal + user_profile) sum to 0.80."""
        from src.config import settings

        applied = (
            settings.device_match_weight
            + settings.blueprint_quality_weight
            + settings.community_rating_weight
            + settings.complexity_bonus_weight
        )
        assert abs(applied - 0.80) < 0.01, f"Applied weights should be 0.80, got {applied}"

    def test_normalization_factor(self):
        """Normalization factor is 1/0.80 = 1.25."""
        from src.config import settings

        applied = (
            settings.device_match_weight
            + settings.blueprint_quality_weight
            + settings.community_rating_weight
            + settings.complexity_bonus_weight
        )
        norm = 1.0 / applied
        assert abs(norm - 1.25) < 0.01, f"Normalization factor should be 1.25, got {norm}"

    def test_device_match_weight_is_050(self):
        """Device match weight defaults to 0.50."""
        from src.config import settings

        assert settings.device_match_weight == 0.50

    def test_complexity_bonus_weight_is_005(self):
        """Complexity bonus weight defaults to 0.05."""
        from src.config import settings

        assert settings.complexity_bonus_weight == 0.05


# ---------------------------------------------------------------------------
# Complexity bonus (internal helper)
# ---------------------------------------------------------------------------

class TestComplexityBonus:
    """Test _calculate_complexity_bonus via SuggestionScorer."""

    @pytest.fixture(autouse=True)
    def setup_scorer(self):
        """Create scorer with DeviceMatcher disabled."""
        with patch("src.services.suggestion_scorer.DEVICE_MATCHER_AVAILABLE", False):
            with patch("src.services.suggestion_scorer.DeviceMatcher", None):
                from src.services.suggestion_scorer import SuggestionScorer
                self.scorer = SuggestionScorer(enable_wyze_scoring=False)

    def test_simple_returns_full_bonus(self):
        assert self.scorer._calculate_complexity_bonus("simple") == 1.0

    def test_medium_returns_partial_bonus(self):
        assert self.scorer._calculate_complexity_bonus("medium") == 0.4

    def test_high_returns_zero_bonus(self):
        assert self.scorer._calculate_complexity_bonus("high") == 0.0

    def test_unknown_complexity_returns_zero(self):
        """Unknown complexity treated as high (no bonus)."""
        assert self.scorer._calculate_complexity_bonus("unknown") == 0.0

    def test_case_insensitive(self):
        assert self.scorer._calculate_complexity_bonus("SIMPLE") == 1.0
        assert self.scorer._calculate_complexity_bonus("Medium") == 0.4


# ---------------------------------------------------------------------------
# Fallback scoring (DeviceMatcher unavailable)
# ---------------------------------------------------------------------------

class TestFallbackScoring:
    """Test _calculate_fallback_score when DeviceMatcher is not available."""

    @pytest.fixture(autouse=True)
    def setup_scorer(self):
        with patch("src.services.suggestion_scorer.DEVICE_MATCHER_AVAILABLE", False):
            with patch("src.services.suggestion_scorer.DeviceMatcher", None):
                from src.services.suggestion_scorer import SuggestionScorer
                self.scorer = SuggestionScorer(enable_wyze_scoring=False)

    def test_fallback_full_domain_match(self):
        """Full domain match gives 50% domain component."""
        bp = _make_blueprint(required_domains=["light"])
        devices = [_make_device("light")]
        score = self.scorer._calculate_fallback_score(bp, devices)
        assert 0.0 <= score <= 1.0

    def test_fallback_no_domain_match(self):
        """No domain match gives 0% domain component."""
        bp = _make_blueprint(required_domains=["climate"])
        devices = [_make_device("light")]
        score_no_match = self.scorer._calculate_fallback_score(bp, devices)

        bp_match = _make_blueprint(required_domains=["light"])
        score_match = self.scorer._calculate_fallback_score(bp_match, devices)

        assert score_no_match < score_match

    def test_fallback_empty_required_domains(self):
        """Empty required_domains gives full domain credit (0.5)."""
        bp = _make_blueprint(required_domains=[])
        devices = [_make_device("light")]
        score = self.scorer._calculate_fallback_score(bp, devices)
        # Should include 0.5 domain + quality + community
        assert score >= 0.5

    def test_fallback_quality_component(self):
        """Higher quality_score produces higher fallback score."""
        devices = [_make_device("light")]
        score_low = self.scorer._calculate_fallback_score(
            _make_blueprint(required_domains=[], quality_score=0.0), devices,
        )
        score_high = self.scorer._calculate_fallback_score(
            _make_blueprint(required_domains=[], quality_score=1.0), devices,
        )
        assert score_high > score_low

    def test_fallback_community_component(self):
        """Higher community_rating produces higher fallback score."""
        devices = [_make_device("light")]
        score_low = self.scorer._calculate_fallback_score(
            _make_blueprint(required_domains=[], community_rating=0.0), devices,
        )
        score_high = self.scorer._calculate_fallback_score(
            _make_blueprint(required_domains=[], community_rating=1.0), devices,
        )
        assert score_high > score_low

    def test_fallback_score_range(self):
        """Fallback score is always in [0.0, 1.0]."""
        test_cases = [
            (_make_blueprint(required_domains=["light"], quality_score=1.0, community_rating=1.0),
             [_make_device("light")]),
            (_make_blueprint(required_domains=["climate"], quality_score=0.0, community_rating=0.0),
             [_make_device("switch")]),
            (_make_blueprint(required_domains=[]),
             []),
        ]
        for bp, devs in test_cases:
            score = self.scorer._calculate_fallback_score(bp, devs)
            assert 0.0 <= score <= 1.0, f"Score out of range: {score}"

    def test_fallback_perfect_score_near_one(self):
        """Perfect inputs produce score near 1.0."""
        bp = _make_blueprint(
            required_domains=["light"],
            quality_score=1.0,
            community_rating=1.0,
        )
        devices = [_make_device("light")]
        score = self.scorer._calculate_fallback_score(bp, devices)
        assert score >= 0.95, f"Perfect fallback should be >= 0.95, got {score}"

    def test_fallback_zero_inputs_low_score(self):
        """Zero quality/community + no domain match produces low score."""
        bp = _make_blueprint(
            required_domains=["climate"],
            quality_score=0.0,
            community_rating=0.0,
        )
        devices = [_make_device("light")]
        score = self.scorer._calculate_fallback_score(bp, devices)
        assert score <= 0.1, f"Zero fallback should be <= 0.1, got {score}"


# ---------------------------------------------------------------------------
# Full scoring (DeviceMatcher mocked)
# ---------------------------------------------------------------------------

class TestFullScoring:
    """Test calculate_suggestion_score with mocked DeviceMatcher."""

    @pytest.fixture(autouse=True)
    def setup_scorer(self):
        with patch("src.services.suggestion_scorer.DEVICE_MATCHER_AVAILABLE", True):
            mock_dm_cls = patch("src.services.suggestion_scorer.DeviceMatcher").start()
            self.mock_device_matcher = mock_dm_cls.return_value
            self.mock_device_matcher.calculate_fit_score.return_value = 0.8

            from src.services.suggestion_scorer import SuggestionScorer
            self.scorer = SuggestionScorer(enable_wyze_scoring=True)
            # Replace with our mock
            self.scorer.device_matcher = self.mock_device_matcher

            yield
        patch.stopall()

    def test_score_in_range(self):
        """Score is always between 0.0 and 1.0."""
        bp = _make_blueprint(quality_score=0.7, community_rating=0.6, complexity="simple")
        devices = [_make_device("light")]
        score = self.scorer.calculate_suggestion_score(bp, devices)
        assert 0.0 <= score <= 1.0

    def test_device_match_dominates(self):
        """High device_match + low others > low device_match + high others."""
        bp = _make_blueprint(quality_score=0.0, community_rating=0.0, complexity="high")
        devices = [_make_device("light")]

        self.mock_device_matcher.calculate_fit_score.return_value = 1.0
        score_high_dm = self.scorer.calculate_suggestion_score(bp, devices)

        self.mock_device_matcher.calculate_fit_score.return_value = 0.0
        bp2 = _make_blueprint(quality_score=1.0, community_rating=1.0, complexity="simple")
        score_high_others = self.scorer.calculate_suggestion_score(bp2, devices)

        assert score_high_dm > score_high_others, (
            f"Device match should dominate: dm={score_high_dm} vs others={score_high_others}"
        )

    def test_simple_scores_higher_than_high(self):
        """Simple complexity scores higher than high complexity (same inputs)."""
        devices = [_make_device("light")]

        bp_simple = _make_blueprint(quality_score=0.7, community_rating=0.6, complexity="simple")
        score_simple = self.scorer.calculate_suggestion_score(bp_simple, devices)

        bp_high = _make_blueprint(quality_score=0.7, community_rating=0.6, complexity="high")
        score_high = self.scorer.calculate_suggestion_score(bp_high, devices)

        assert score_simple > score_high

    def test_medium_between_simple_and_high(self):
        """Medium complexity score falls between simple and high."""
        devices = [_make_device("light")]

        bp_simple = _make_blueprint(complexity="simple")
        bp_medium = _make_blueprint(complexity="medium")
        bp_high = _make_blueprint(complexity="high")

        s_simple = self.scorer.calculate_suggestion_score(bp_simple, devices)
        s_medium = self.scorer.calculate_suggestion_score(bp_medium, devices)
        s_high = self.scorer.calculate_suggestion_score(bp_high, devices)

        assert s_simple > s_medium > s_high

    def test_perfect_inputs_near_one(self):
        """Perfect inputs produce score near 1.0."""
        self.mock_device_matcher.calculate_fit_score.return_value = 1.0
        bp = _make_blueprint(quality_score=1.0, community_rating=1.0, complexity="simple")
        devices = [_make_device("light")]
        score = self.scorer.calculate_suggestion_score(bp, devices)
        assert score >= 0.95, f"Perfect score should be >= 0.95, got {score}"

    def test_zero_inputs_near_zero(self):
        """Zero inputs produce score near 0.0."""
        self.mock_device_matcher.calculate_fit_score.return_value = 0.0
        bp = _make_blueprint(quality_score=0.0, community_rating=0.0, complexity="high")
        devices = [_make_device("light")]
        score = self.scorer.calculate_suggestion_score(bp, devices)
        assert score <= 0.05, f"Zero score should be <= 0.05, got {score}"

    def test_calls_device_matcher(self):
        """Scorer delegates to DeviceMatcher.calculate_fit_score."""
        bp = _make_blueprint()
        devices = [_make_device("light")]
        self.scorer.calculate_suggestion_score(bp, devices)
        self.mock_device_matcher.calculate_fit_score.assert_called_once()

    def test_user_profile_forwarded(self):
        """User profile is forwarded to DeviceMatcher."""
        bp = _make_blueprint()
        devices = [_make_device("light")]
        profile = {"preferred_domains": ["light"], "prefers_simple_automations": True}
        self.scorer.calculate_suggestion_score(bp, devices, user_profile=profile)
        call_kwargs = self.mock_device_matcher.calculate_fit_score.call_args
        assert call_kwargs.kwargs.get("user_profile") is not None or \
               (len(call_kwargs.args) > 4 and call_kwargs.args[4] is not None)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestScorerEdgeCases:
    """Edge-case tests for SuggestionScorer."""

    @pytest.fixture(autouse=True)
    def setup_scorer(self):
        with patch("src.services.suggestion_scorer.DEVICE_MATCHER_AVAILABLE", False):
            with patch("src.services.suggestion_scorer.DeviceMatcher", None):
                from src.services.suggestion_scorer import SuggestionScorer
                self.scorer = SuggestionScorer(enable_wyze_scoring=False)

    def test_empty_devices_list(self):
        """Empty devices list doesn't crash."""
        bp = _make_blueprint(required_domains=["light"])
        score = self.scorer.calculate_suggestion_score(bp, [])
        assert 0.0 <= score <= 1.0

    def test_missing_quality_score_defaults(self):
        """Missing quality_score key uses fallback default."""
        bp = {"id": "bp", "name": "Test", "required_domains": ["light"]}
        devices = [_make_device("light")]
        score = self.scorer.calculate_suggestion_score(bp, devices)
        assert 0.0 <= score <= 1.0

    def test_missing_community_rating_defaults(self):
        """Missing community_rating key uses fallback default (0.0)."""
        bp = _make_blueprint()
        del bp["community_rating"]
        devices = [_make_device("light")]
        score = self.scorer.calculate_suggestion_score(bp, devices)
        assert 0.0 <= score <= 1.0

    def test_multiple_devices(self):
        """Multiple devices with different domains."""
        bp = _make_blueprint(required_domains=["light", "switch"])
        devices = [
            _make_device("light"),
            _make_device("switch"),
            _make_device("climate"),
        ]
        score = self.scorer.calculate_suggestion_score(bp, devices)
        assert 0.0 <= score <= 1.0
