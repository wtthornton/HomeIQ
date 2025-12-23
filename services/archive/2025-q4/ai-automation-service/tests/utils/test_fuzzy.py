"""
Unit tests for fuzzy matching utilities.

Tests rapidfuzz-based fuzzy matching functions with various inputs:
- Typo handling
- Abbreviation matching
- Word order independence
- Threshold application
- Fallback behavior
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from utils.fuzzy import (
    RAPIDFUZZ_AVAILABLE,
    fuzzy_match_best,
    fuzzy_match_with_context,
    fuzzy_score,
)


class TestFuzzyScore:
    """Test fuzzy_score() function"""

    @pytest.mark.skipif(not RAPIDFUZZ_AVAILABLE, reason="rapidfuzz not available")
    def test_exact_match(self):
        """Test exact match returns 1.0"""
        score = fuzzy_score("office light", "office light")
        assert score == 1.0

    @pytest.mark.skipif(not RAPIDFUZZ_AVAILABLE, reason="rapidfuzz not available")
    def test_typo_handling(self):
        """Test typo handling (office lite -> office light)"""
        score = fuzzy_score("office lite", "office light", threshold=0.0)
        assert score > 0.8  # Should be high despite typo

    @pytest.mark.skipif(not RAPIDFUZZ_AVAILABLE, reason="rapidfuzz not available")
    def test_abbreviation_handling(self):
        """Test abbreviation handling (LR light -> Living Room Light)"""
        score = fuzzy_score("LR light", "Living Room Light", threshold=0.0)
        assert score > 0.7  # Should match despite abbreviation

    @pytest.mark.skipif(not RAPIDFUZZ_AVAILABLE, reason="rapidfuzz not available")
    def test_word_order_independence(self):
        """Test word order independence"""
        score1 = fuzzy_score("light living room", "living room light", threshold=0.0)
        score2 = fuzzy_score("living room light", "light living room", threshold=0.0)
        assert score1 > 0.9  # Should match regardless of order
        assert score2 > 0.9
        assert abs(score1 - score2) < 0.1  # Should be symmetric

    @pytest.mark.skipif(not RAPIDFUZZ_AVAILABLE, reason="rapidfuzz not available")
    def test_partial_match(self):
        """Test partial match (kitchen -> Kitchen Light)"""
        score = fuzzy_score("kitchen", "Kitchen Light", threshold=0.0)
        assert score > 0.6  # Should match partial

    @pytest.mark.skipif(not RAPIDFUZZ_AVAILABLE, reason="rapidfuzz not available")
    def test_threshold_application(self):
        """Test threshold filtering"""
        # Low similarity should return 0.0 with default threshold
        score = fuzzy_score("office", "bathroom", threshold=0.7)
        assert score == 0.0

        # Same strings with lower threshold should return score
        score = fuzzy_score("office", "bathroom", threshold=0.0)
        assert score < 0.5  # Low similarity

    @pytest.mark.skipif(not RAPIDFUZZ_AVAILABLE, reason="rapidfuzz not available")
    def test_empty_candidate(self):
        """Test empty candidate returns 0.0"""
        score = fuzzy_score("office light", "")
        assert score == 0.0

    def test_fallback_when_rapidfuzz_unavailable(self):
        """Test fallback behavior when rapidfuzz unavailable"""
        with patch('utils.fuzzy.RAPIDFUZZ_AVAILABLE', False):
            # Exact match should still work
            score = fuzzy_score("office light", "office light")
            assert score == 1.0

            # Substring match should work
            score = fuzzy_score("office", "office light")
            assert score == 0.7

            # No match should return 0.0
            score = fuzzy_score("office", "bathroom")
            assert score == 0.0


class TestFuzzyMatchBest:
    """Test fuzzy_match_best() function"""

    @pytest.mark.skipif(not RAPIDFUZZ_AVAILABLE, reason="rapidfuzz not available")
    def test_exact_match_in_list(self):
        """Test finding exact match in candidate list"""
        candidates = ["office light", "office lamp", "kitchen light"]
        results = fuzzy_match_best("office light", candidates, threshold=0.0)
        assert len(results) == 1
        assert results[0][0] == "office light"
        assert results[0][1] == 1.0

    @pytest.mark.skipif(not RAPIDFUZZ_AVAILABLE, reason="rapidfuzz not available")
    def test_typo_handling_in_list(self):
        """Test finding match with typo in list"""
        candidates = ["office light", "office lamp", "kitchen light"]
        results = fuzzy_match_best("office lite", candidates, threshold=0.0)
        assert len(results) > 0
        assert results[0][0] == "office light"  # Should match despite typo
        assert results[0][1] > 0.8

    @pytest.mark.skipif(not RAPIDFUZZ_AVAILABLE, reason="rapidfuzz not available")
    def test_multiple_results(self):
        """Test returning multiple results"""
        candidates = ["office light", "office lamp", "kitchen light", "bathroom light"]
        results = fuzzy_match_best("office light", candidates, threshold=0.0, limit=3)
        assert len(results) <= 3
        assert all(score > 0.0 for _, score in results)

    @pytest.mark.skipif(not RAPIDFUZZ_AVAILABLE, reason="rapidfuzz not available")
    def test_threshold_filtering(self):
        """Test threshold filtering in batch matching"""
        candidates = ["office light", "office lamp", "kitchen light", "bathroom"]
        results = fuzzy_match_best("office light", candidates, threshold=0.7)
        # Should only return matches above threshold
        assert all(score >= 0.7 for _, score in results)

    @pytest.mark.skipif(not RAPIDFUZZ_AVAILABLE, reason="rapidfuzz not available")
    def test_empty_candidates(self):
        """Test empty candidate list"""
        results = fuzzy_match_best("office light", [])
        assert results == []

    @pytest.mark.skipif(not RAPIDFUZZ_AVAILABLE, reason="rapidfuzz not available")
    def test_large_candidate_list(self):
        """Test performance with large candidate list"""
        candidates = [f"light_{i}" for i in range(1000)]
        candidates.append("office light")
        results = fuzzy_match_best("office light", candidates, threshold=0.0, limit=5)
        assert len(results) <= 5
        # Should find the best match
        assert any("office light" in candidate for candidate, _ in results)

    def test_fallback_when_rapidfuzz_unavailable(self):
        """Test fallback behavior when rapidfuzz unavailable"""
        with patch('utils.fuzzy.RAPIDFUZZ_AVAILABLE', False):
            candidates = ["office light", "office lamp", "kitchen light"]
            results = fuzzy_match_best("office light", candidates, limit=2)
            assert len(results) > 0
            assert results[0][0] == "office light"
            assert results[0][1] == 1.0


class TestFuzzyMatchWithContext:
    """Test fuzzy_match_with_context() function"""

    @pytest.mark.skipif(not RAPIDFUZZ_AVAILABLE, reason="rapidfuzz not available")
    def test_base_score_only(self):
        """Test without context bonuses"""
        score = fuzzy_match_with_context("office light", "office light")
        assert score == 1.0

    @pytest.mark.skipif(not RAPIDFUZZ_AVAILABLE, reason="rapidfuzz not available")
    def test_with_location_bonus(self):
        """Test with location context bonus"""
        context_bonuses = {'location': 0.2}
        score = fuzzy_match_with_context("light", "office light", context_bonuses)
        base_score = fuzzy_score("light", "office light", threshold=0.0)
        expected = min(base_score + 0.2, 1.0)
        assert abs(score - expected) < 0.01

    @pytest.mark.skipif(not RAPIDFUZZ_AVAILABLE, reason="rapidfuzz not available")
    def test_score_capping(self):
        """Test that enhanced score is capped at 1.0"""
        context_bonuses = {'location': 0.5, 'device_type': 0.5}
        score = fuzzy_match_with_context("office light", "office light", context_bonuses)
        assert score == 1.0  # Should be capped at 1.0

    @pytest.mark.skipif(not RAPIDFUZZ_AVAILABLE, reason="rapidfuzz not available")
    def test_multiple_bonuses(self):
        """Test with multiple context bonuses"""
        context_bonuses = {'location': 0.1, 'device_type': 0.1}
        score = fuzzy_match_with_context("light", "office light", context_bonuses)
        base_score = fuzzy_score("light", "office light", threshold=0.0)
        expected = min(base_score + 0.2, 1.0)
        assert abs(score - expected) < 0.01

    @pytest.mark.skipif(not RAPIDFUZZ_AVAILABLE, reason="rapidfuzz not available")
    def test_low_base_score_with_bonus(self):
        """Test that bonuses can boost low base scores"""
        context_bonuses = {'location': 0.3}
        score = fuzzy_match_with_context("light", "office lamp", context_bonuses)
        base_score = fuzzy_score("light", "office lamp", threshold=0.0)
        # Bonus should increase score
        assert score > base_score
        assert score <= 1.0


class TestScoreNormalization:
    """Test that all scores are normalized to 0.0-1.0 range"""

    @pytest.mark.skipif(not RAPIDFUZZ_AVAILABLE, reason="rapidfuzz not available")
    def test_fuzzy_score_range(self):
        """Test fuzzy_score returns values in 0.0-1.0 range"""
        test_cases = [
            ("office light", "office light"),
            ("office lite", "office light"),
            ("LR light", "Living Room Light"),
            ("office", "bathroom"),
        ]
        for query, candidate in test_cases:
            score = fuzzy_score(query, candidate, threshold=0.0)
            assert 0.0 <= score <= 1.0

    @pytest.mark.skipif(not RAPIDFUZZ_AVAILABLE, reason="rapidfuzz not available")
    def test_fuzzy_match_best_range(self):
        """Test fuzzy_match_best returns scores in 0.0-1.0 range"""
        candidates = ["office light", "office lamp", "kitchen light"]
        results = fuzzy_match_best("office light", candidates, threshold=0.0)
        for candidate, score in results:
            assert 0.0 <= score <= 1.0

    @pytest.mark.skipif(not RAPIDFUZZ_AVAILABLE, reason="rapidfuzz not available")
    def test_fuzzy_match_with_context_range(self):
        """Test fuzzy_match_with_context returns scores in 0.0-1.0 range"""
        context_bonuses = {'location': 0.5}
        score = fuzzy_match_with_context("light", "office light", context_bonuses)
        assert 0.0 <= score <= 1.0

