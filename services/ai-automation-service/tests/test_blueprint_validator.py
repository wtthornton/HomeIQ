"""
Unit tests for BlueprintValidator service.

Epic AI-6 Story AI6.2: Blueprint Validation Service for Patterns
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.blueprint_discovery.blueprint_validator import (
    BlueprintValidationConfig,
    BlueprintValidator,
)
from src.utils.miner_integration import MinerIntegration


@pytest.fixture
def mock_miner():
    """Create a mock MinerIntegration instance."""
    miner = MagicMock(spec=MinerIntegration)
    miner.is_available = AsyncMock(return_value=True)
    miner.search_blueprints = AsyncMock(return_value=[])
    return miner


@pytest.fixture
def sample_blueprint():
    """Sample blueprint data."""
    return {
        "id": "blueprint1",
        "title": "Motion-Activated Light",
        "description": "Turn on lights when motion detected",
        "use_case": "comfort",
        "quality_score": 0.85,
        "metadata": {
            "_blueprint_metadata": {
                "name": "Motion-Activated Light",
                "description": "Turn on lights when motion detected"
            },
            "_blueprint_variables": {
                "motion_sensor": {
                    "domain": "binary_sensor",
                    "device_class": "motion"
                },
                "target_light": {
                    "domain": "light"
                }
            },
            "_blueprint_devices": ["binary_sensor", "light"]
        }
    }


@pytest.fixture
def sample_time_of_day_pattern():
    """Sample time-of-day pattern."""
    return {
        "pattern_type": "time_of_day",
        "device_id": "light.office",
        "hour": 7,
        "minute": 0,
        "confidence": 0.75,
        "occurrences": 25,
        "total_events": 30
    }


@pytest.fixture
def sample_co_occurrence_pattern():
    """Sample co-occurrence pattern."""
    return {
        "pattern_type": "co_occurrence",
        "device1": "binary_sensor.office_motion",
        "device2": "light.office",
        "confidence": 0.68,
        "support": 15
    }


@pytest.fixture
def sample_anomaly_pattern():
    """Sample anomaly pattern."""
    return {
        "pattern_type": "anomaly",
        "device_id": "light.bedroom",
        "expected_state": "off",
        "actual_state": "on",
        "confidence": 0.70
    }


@pytest.fixture
def blueprint_validator(mock_miner):
    """Create a BlueprintValidator instance."""
    return BlueprintValidator(mock_miner)


class TestBlueprintValidationConfig:
    """Test BlueprintValidationConfig constants."""

    def test_config_constants(self):
        """Test that config constants are properly defined."""
        assert BlueprintValidationConfig.DEVICE_OVERLAP_WEIGHT == 0.50
        assert BlueprintValidationConfig.USE_CASE_ALIGNMENT_WEIGHT == 0.30
        assert BlueprintValidationConfig.PATTERN_SIMILARITY_WEIGHT == 0.20
        assert BlueprintValidationConfig.BASE_BOOST == 0.1
        assert BlueprintValidationConfig.MAX_BOOST == 0.3
        assert BlueprintValidationConfig.MIN_MATCH_SCORE == 0.7

    def test_weights_sum_to_one(self):
        """Test that match score weights sum to 1.0."""
        total = (
            BlueprintValidationConfig.DEVICE_OVERLAP_WEIGHT +
            BlueprintValidationConfig.USE_CASE_ALIGNMENT_WEIGHT +
            BlueprintValidationConfig.PATTERN_SIMILARITY_WEIGHT
        )
        assert abs(total - 1.0) < 0.001  # Allow floating point precision


class TestBlueprintValidator:
    """Test BlueprintValidator service."""

    @pytest.mark.asyncio
    async def test_init(self, mock_miner):
        """Test service initialization."""
        validator = BlueprintValidator(mock_miner)
        assert validator.miner == mock_miner

    @pytest.mark.asyncio
    async def test_validate_pattern_miner_unavailable(
        self,
        blueprint_validator,
        mock_miner,
        sample_time_of_day_pattern
    ):
        """Test validation when miner is unavailable."""
        mock_miner.is_available.return_value = False

        result = await blueprint_validator.validate_pattern(
            sample_time_of_day_pattern,
            "time_of_day"
        )

        assert result['validated'] is False
        assert result['confidence_boost'] == 0.0
        mock_miner.search_blueprints.assert_not_called()

    @pytest.mark.asyncio
    async def test_validate_pattern_no_device_types(
        self,
        blueprint_validator,
        mock_miner
    ):
        """Test validation with pattern that has no device types."""
        pattern = {"pattern_type": "time_of_day", "confidence": 0.75}

        result = await blueprint_validator.validate_pattern(pattern, "time_of_day")

        assert result['validated'] is False
        assert result['confidence_boost'] == 0.0

    @pytest.mark.asyncio
    async def test_validate_pattern_no_blueprints(
        self,
        blueprint_validator,
        mock_miner,
        sample_time_of_day_pattern
    ):
        """Test validation when no blueprints found."""
        mock_miner.search_blueprints.return_value = []

        result = await blueprint_validator.validate_pattern(
            sample_time_of_day_pattern,
            "time_of_day"
        )

        assert result['validated'] is False
        assert result['confidence_boost'] == 0.0

    @pytest.mark.asyncio
    async def test_validate_pattern_success(
        self,
        blueprint_validator,
        mock_miner,
        sample_time_of_day_pattern,
        sample_blueprint
    ):
        """Test successful pattern validation."""
        mock_miner.search_blueprints.return_value = [sample_blueprint]

        result = await blueprint_validator.validate_pattern(
            sample_time_of_day_pattern,
            "time_of_day"
        )

        assert result['validated'] is True
        assert result['match_score'] >= BlueprintValidationConfig.MIN_MATCH_SCORE
        assert 0.1 <= result['confidence_boost'] <= 0.3
        assert result['blueprint_match'] is not None

    @pytest.mark.asyncio
    async def test_validate_pattern_low_match_score(
        self,
        blueprint_validator,
        mock_miner,
        sample_time_of_day_pattern
    ):
        """Test validation with blueprint that has low match score."""
        # Blueprint with mismatched devices
        low_match_blueprint = {
            "id": "bp1",
            "quality_score": 0.8,
            "metadata": {
                "_blueprint_devices": ["switch"],  # No match with light
                "_blueprint_metadata": {"description": "Switch automation"}
            }
        }
        mock_miner.search_blueprints.return_value = [low_match_blueprint]

        result = await blueprint_validator.validate_pattern(
            sample_time_of_day_pattern,
            "time_of_day"
        )

        # Should fail validation due to low match score
        assert result['validated'] is False or result['match_score'] < BlueprintValidationConfig.MIN_MATCH_SCORE

    def test_extract_device_types_time_of_day(
        self,
        blueprint_validator,
        sample_time_of_day_pattern
    ):
        """Test device type extraction from time-of-day pattern."""
        device_types = blueprint_validator._extract_device_types(
            sample_time_of_day_pattern,
            "time_of_day"
        )

        assert "light" in device_types

    def test_extract_device_types_co_occurrence(
        self,
        blueprint_validator,
        sample_co_occurrence_pattern
    ):
        """Test device type extraction from co-occurrence pattern."""
        device_types = blueprint_validator._extract_device_types(
            sample_co_occurrence_pattern,
            "co_occurrence"
        )

        assert "binary_sensor" in device_types
        assert "light" in device_types

    def test_extract_device_types_anomaly(
        self,
        blueprint_validator,
        sample_anomaly_pattern
    ):
        """Test device type extraction from anomaly pattern."""
        device_types = blueprint_validator._extract_device_types(
            sample_anomaly_pattern,
            "anomaly"
        )

        assert "light" in device_types

    @pytest.mark.asyncio
    async def test_search_blueprints_deduplication(
        self,
        blueprint_validator,
        mock_miner,
        sample_blueprint
    ):
        """Test blueprint search deduplication."""
        # Same blueprint returned for multiple device types
        mock_miner.search_blueprints.return_value = [sample_blueprint]

        blueprints = await blueprint_validator._search_blueprints(
            ["light", "binary_sensor"]
        )

        # Should deduplicate (only called once per device type, but same blueprint returned)
        assert len(blueprints) <= 2  # At most one per device type
        assert mock_miner.search_blueprints.call_count == 2

    def test_find_best_match(
        self,
        blueprint_validator,
        sample_time_of_day_pattern,
        sample_blueprint
    ):
        """Test finding best matching blueprint."""
        best_match = blueprint_validator._find_best_match(
            sample_time_of_day_pattern,
            "time_of_day",
            [sample_blueprint]
        )

        assert best_match is not None
        assert best_match['match_score'] >= 0.0
        assert best_match['blueprint'] == sample_blueprint

    def test_find_best_match_low_score(
        self,
        blueprint_validator,
        sample_time_of_day_pattern
    ):
        """Test finding best match with low score."""
        # Blueprint with no matching devices
        low_match_blueprint = {
            "id": "bp1",
            "metadata": {
                "_blueprint_devices": ["switch"],
                "_blueprint_metadata": {"description": "Switch automation"}
            }
        }

        best_match = blueprint_validator._find_best_match(
            sample_time_of_day_pattern,
            "time_of_day",
            [low_match_blueprint]
        )

        # Should return None if match score < MIN_MATCH_SCORE
        if best_match:
            assert best_match['match_score'] < BlueprintValidationConfig.MIN_MATCH_SCORE
        else:
            assert best_match is None

    def test_calculate_match_score(
        self,
        blueprint_validator,
        sample_co_occurrence_pattern,
        sample_blueprint
    ):
        """Test match score calculation."""
        score = blueprint_validator._calculate_match_score(
            sample_co_occurrence_pattern,
            "co_occurrence",
            sample_blueprint
        )

        assert 0.0 <= score <= 1.0
        # Should have decent score for matching devices
        assert score >= 0.3

    def test_calculate_use_case_alignment(
        self,
        blueprint_validator,
        sample_time_of_day_pattern,
        sample_blueprint
    ):
        """Test use case alignment calculation."""
        score = blueprint_validator._calculate_use_case_alignment(
            sample_time_of_day_pattern,
            sample_blueprint
        )

        assert 0.0 <= score <= 1.0

    def test_calculate_pattern_similarity_time_of_day(
        self,
        blueprint_validator,
        sample_time_of_day_pattern
    ):
        """Test pattern similarity for time-of-day patterns."""
        blueprint = {
            "metadata": {
                "_blueprint_metadata": {
                    "description": "Turn on lights at scheduled time daily"
                }
            }
        }

        score = blueprint_validator._calculate_pattern_similarity(
            sample_time_of_day_pattern,
            "time_of_day",
            blueprint
        )

        assert 0.0 <= score <= 1.0
        # Should have high score for time-related blueprints
        assert score >= 0.5

    def test_calculate_pattern_similarity_co_occurrence(
        self,
        blueprint_validator,
        sample_co_occurrence_pattern
    ):
        """Test pattern similarity for co-occurrence patterns."""
        blueprint = {
            "metadata": {
                "_blueprint_metadata": {
                    "description": "When motion detected, turn on light"
                }
            }
        }

        score = blueprint_validator._calculate_pattern_similarity(
            sample_co_occurrence_pattern,
            "co_occurrence",
            blueprint
        )

        assert 0.0 <= score <= 1.0
        # Should have high score for trigger-action blueprints
        assert score >= 0.5

    def test_calculate_confidence_boost_base(
        self,
        blueprint_validator
    ):
        """Test confidence boost calculation - base boost."""
        boost = blueprint_validator._calculate_confidence_boost(
            match_score=0.75,
            blueprint_quality=0.8
        )

        assert BlueprintValidationConfig.BASE_BOOST <= boost <= BlueprintValidationConfig.MAX_BOOST

    def test_calculate_confidence_boost_maximum(
        self,
        blueprint_validator
    ):
        """Test confidence boost calculation - maximum boost."""
        boost = blueprint_validator._calculate_confidence_boost(
            match_score=1.0,  # Perfect match
            blueprint_quality=1.0  # Perfect quality
        )

        assert boost == BlueprintValidationConfig.MAX_BOOST

    def test_calculate_confidence_boost_minimum_match(
        self,
        blueprint_validator
    ):
        """Test confidence boost calculation - minimum match score."""
        boost = blueprint_validator._calculate_confidence_boost(
            match_score=BlueprintValidationConfig.MIN_MATCH_SCORE,
            blueprint_quality=0.7
        )

        assert boost >= BlueprintValidationConfig.BASE_BOOST

    def test_apply_confidence_boost(
        self,
        blueprint_validator,
        sample_time_of_day_pattern,
        sample_blueprint
    ):
        """Test applying confidence boost to pattern."""
        validation_result = {
            'validated': True,
            'match_score': 0.8,
            'blueprint_match': sample_blueprint,
            'confidence_boost': 0.15
        }

        boosted_pattern = blueprint_validator.apply_confidence_boost(
            sample_time_of_day_pattern,
            validation_result
        )

        assert boosted_pattern['confidence'] > sample_time_of_day_pattern['confidence']
        assert boosted_pattern['confidence'] <= 1.0
        assert 'blueprint_validation' in boosted_pattern.get('metadata', {})

    def test_apply_confidence_boost_not_validated(
        self,
        blueprint_validator,
        sample_time_of_day_pattern
    ):
        """Test applying boost when pattern not validated."""
        validation_result = {
            'validated': False,
            'confidence_boost': 0.0
        }

        boosted_pattern = blueprint_validator.apply_confidence_boost(
            sample_time_of_day_pattern,
            validation_result
        )

        assert boosted_pattern['confidence'] == sample_time_of_day_pattern['confidence']

    def test_apply_confidence_boost_clamps_to_one(
        self,
        blueprint_validator
    ):
        """Test that boosted confidence is clamped to 1.0."""
        pattern = {"confidence": 0.95}
        validation_result = {
            'validated': True,
            'confidence_boost': 0.2  # Would push over 1.0
        }

        boosted_pattern = blueprint_validator.apply_confidence_boost(
            pattern,
            validation_result
        )

        assert boosted_pattern['confidence'] == 1.0

    @pytest.mark.asyncio
    async def test_validate_time_of_day_pattern(
        self,
        blueprint_validator,
        mock_miner,
        sample_time_of_day_pattern,
        sample_blueprint
    ):
        """Test validation of time-of-day pattern."""
        mock_miner.search_blueprints.return_value = [sample_blueprint]

        result = await blueprint_validator.validate_pattern(
            sample_time_of_day_pattern,
            "time_of_day"
        )

        assert isinstance(result, dict)
        assert 'validated' in result
        assert 'match_score' in result
        assert 'confidence_boost' in result

    @pytest.mark.asyncio
    async def test_validate_co_occurrence_pattern(
        self,
        blueprint_validator,
        mock_miner,
        sample_co_occurrence_pattern,
        sample_blueprint
    ):
        """Test validation of co-occurrence pattern."""
        mock_miner.search_blueprints.return_value = [sample_blueprint]

        result = await blueprint_validator.validate_pattern(
            sample_co_occurrence_pattern,
            "co_occurrence"
        )

        assert isinstance(result, dict)
        assert 'validated' in result

    @pytest.mark.asyncio
    async def test_validate_anomaly_pattern(
        self,
        blueprint_validator,
        mock_miner,
        sample_anomaly_pattern,
        sample_blueprint
    ):
        """Test validation of anomaly pattern."""
        mock_miner.search_blueprints.return_value = [sample_blueprint]

        result = await blueprint_validator.validate_pattern(
            sample_anomaly_pattern,
            "anomaly"
        )

        assert isinstance(result, dict)
        assert 'validated' in result

    @pytest.mark.asyncio
    async def test_validation_error_handling(
        self,
        blueprint_validator,
        mock_miner,
        sample_time_of_day_pattern
    ):
        """Test error handling during validation."""
        mock_miner.is_available.side_effect = Exception("Service error")

        result = await blueprint_validator.validate_pattern(
            sample_time_of_day_pattern,
            "time_of_day"
        )

        # Should return no boost, not raise exception
        assert result['validated'] is False
        assert result['confidence_boost'] == 0.0

