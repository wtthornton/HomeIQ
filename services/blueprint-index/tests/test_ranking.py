"""Tests for blueprint ranking algorithms."""

import pytest
from src.search.ranking import BlueprintRanker
from src.models import IndexedBlueprint


class TestBlueprintRanker:
    """Tests for BlueprintRanker class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.ranker = BlueprintRanker()
    
    def _create_blueprint(
        self,
        required_domains=None,
        required_device_classes=None,
        action_services=None,
        quality_score=0.5,
        community_rating=0.5,
    ) -> IndexedBlueprint:
        """Helper to create test blueprint."""
        bp = IndexedBlueprint(
            id="test-id",
            source_url="https://example.com/test.yaml",
            source_type="test",
            name="Test Blueprint",
            required_domains=required_domains or [],
            required_device_classes=required_device_classes or [],
            action_services=action_services or [],
            quality_score=quality_score,
            community_rating=community_rating,
        )
        return bp
    
    def test_calculate_pattern_score_perfect_match(self):
        """Test pattern score for perfect match."""
        blueprint = self._create_blueprint(
            required_domains=["binary_sensor", "light"],
            required_device_classes=["motion"],
            action_services=["light.turn_on"],
            quality_score=0.9,
            community_rating=0.8,
        )
        
        score = self.ranker._calculate_pattern_score(
            blueprint,
            trigger_domain="binary_sensor",
            action_domain="light",
            trigger_device_class="motion",
        )
        
        assert score > 0.8  # High score for good match
    
    def test_calculate_pattern_score_partial_match(self):
        """Test pattern score for partial match."""
        blueprint = self._create_blueprint(
            required_domains=["binary_sensor"],  # Missing light
            required_device_classes=["motion"],
            quality_score=0.5,
            community_rating=0.5,
        )
        
        score = self.ranker._calculate_pattern_score(
            blueprint,
            trigger_domain="binary_sensor",
            action_domain="light",
            trigger_device_class="motion",
        )
        
        assert 0.3 < score < 0.8  # Moderate score for partial match
    
    def test_calculate_pattern_score_no_match(self):
        """Test pattern score for no match."""
        blueprint = self._create_blueprint(
            required_domains=["climate"],
            required_device_classes=["temperature"],
            quality_score=0.5,
            community_rating=0.5,
        )
        
        score = self.ranker._calculate_pattern_score(
            blueprint,
            trigger_domain="binary_sensor",
            action_domain="light",
            trigger_device_class="motion",
        )
        
        assert score < 0.5  # Low score for poor match
    
    def test_calculate_fit_score_all_requirements_met(self):
        """Test fit score when all requirements are met."""
        blueprint = self._create_blueprint(
            required_domains=["binary_sensor", "light"],
            required_device_classes=["motion"],
            quality_score=0.8,
            community_rating=0.9,
        )
        
        score = self.ranker.calculate_fit_score(
            blueprint,
            user_domains=["binary_sensor", "light", "switch"],
            user_device_classes=["motion", "door"],
            same_area=True,
        )
        
        assert score > 0.9  # Very high score
    
    def test_calculate_fit_score_partial_requirements(self):
        """Test fit score when only some requirements are met."""
        blueprint = self._create_blueprint(
            required_domains=["binary_sensor", "light", "climate"],
            required_device_classes=["motion", "temperature"],
            quality_score=0.8,
            community_rating=0.7,
        )
        
        score = self.ranker.calculate_fit_score(
            blueprint,
            user_domains=["binary_sensor", "light"],  # Missing climate
            user_device_classes=["motion"],  # Missing temperature
            same_area=False,
        )
        
        assert 0.3 < score < 0.8  # Moderate score
    
    def test_calculate_fit_score_no_requirements(self):
        """Test fit score when blueprint has no requirements."""
        blueprint = self._create_blueprint(
            required_domains=[],
            required_device_classes=[],
            quality_score=0.7,
            community_rating=0.8,
        )
        
        score = self.ranker.calculate_fit_score(
            blueprint,
            user_domains=["binary_sensor"],
            user_device_classes=["motion"],
            same_area=True,
        )
        
        assert score > 0.9  # High score since no requirements
    
    def test_rank_for_pattern(self):
        """Test ranking blueprints for a pattern."""
        blueprints = [
            self._create_blueprint(
                required_domains=["binary_sensor"],
                quality_score=0.5,
                community_rating=0.3,
            ),
            self._create_blueprint(
                required_domains=["binary_sensor", "light"],
                required_device_classes=["motion"],
                action_services=["light.turn_on"],
                quality_score=0.9,
                community_rating=0.9,
            ),
            self._create_blueprint(
                required_domains=["climate"],
                quality_score=0.7,
                community_rating=0.7,
            ),
        ]
        blueprints[0].id = "bp1"
        blueprints[1].id = "bp2"
        blueprints[2].id = "bp3"
        
        ranked = self.ranker.rank_for_pattern(
            blueprints,
            trigger_domain="binary_sensor",
            action_domain="light",
            trigger_device_class="motion",
        )
        
        assert len(ranked) == 3
        # Best match should be first
        assert ranked[0].id == "bp2"
    
    def test_rank_by_fit(self):
        """Test ranking blueprints by fit score."""
        blueprints = [
            self._create_blueprint(
                required_domains=["climate"],
                quality_score=0.9,
                community_rating=0.9,
            ),
            self._create_blueprint(
                required_domains=["binary_sensor", "light"],
                required_device_classes=["motion"],
                quality_score=0.8,
                community_rating=0.8,
            ),
        ]
        blueprints[0].id = "bp1"
        blueprints[1].id = "bp2"
        
        ranked = self.ranker.rank_by_fit(
            blueprints,
            user_domains=["binary_sensor", "light"],
            user_device_classes=["motion"],
            same_area=True,
            min_fit_score=0.3,
        )
        
        assert len(ranked) >= 1
        # Best fit should be first
        if len(ranked) >= 2:
            assert ranked[0][1] >= ranked[1][1]  # Score of first >= second
    
    def test_rank_by_fit_filters_low_scores(self):
        """Test that rank_by_fit filters out low scores."""
        blueprints = [
            self._create_blueprint(
                required_domains=["climate", "vacuum", "cover"],  # No match
                required_device_classes=["temperature"],
                quality_score=0.9,
            ),
        ]
        blueprints[0].id = "bp1"
        
        ranked = self.ranker.rank_by_fit(
            blueprints,
            user_domains=["binary_sensor", "light"],
            user_device_classes=["motion"],
            same_area=True,
            min_fit_score=0.9,  # High threshold
        )
        
        # Should be filtered out due to low fit
        assert len(ranked) == 0 or ranked[0][1] >= 0.9
