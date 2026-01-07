"""
Integration tests for ChainDetector module.

Tests the chain detection functionality including:
- 3-device chain detection
- 4-device chain detection
- Quality-based pair selection
- Cross-area chain validation
"""

import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock

import sys
from pathlib import Path

# Add src/synergy_detection to path directly (avoid __init__.py import issues)
src_path = Path(__file__).parent.parent.parent / "src" / "synergy_detection"
sys.path.insert(0, str(src_path))

from chain_detection import ChainDetector, TOP_PAIRS_FOR_CHAINS


class TestChainDetector:
    """Test ChainDetector class."""

    @pytest.fixture
    def detector(self):
        """Create a ChainDetector instance."""
        return ChainDetector()

    @pytest.fixture
    def mock_cache(self):
        """Create a mock synergy cache."""
        cache = MagicMock()
        cache.get_chain_result = AsyncMock(return_value=None)
        cache.set_chain_result = AsyncMock()
        return cache

    @pytest.fixture
    def detector_with_cache(self, mock_cache):
        """Create a ChainDetector with mock cache."""
        return ChainDetector(synergy_cache=mock_cache)

    @pytest.fixture
    def sample_pairwise_synergies(self):
        """Create sample pairwise synergies for testing."""
        return [
            {
                'synergy_id': str(uuid.uuid4()),
                'trigger_entity': 'binary_sensor.motion_hallway',
                'action_entity': 'light.hallway',
                'area': 'hallway',
                'impact_score': 0.8,
                'confidence': 0.9,
                'rationale': 'Motion activates hallway light'
            },
            {
                'synergy_id': str(uuid.uuid4()),
                'trigger_entity': 'light.hallway',
                'action_entity': 'light.living_room',
                'area': 'hallway',
                'impact_score': 0.7,
                'confidence': 0.85,
                'rationale': 'Hallway light triggers living room light'
            },
            {
                'synergy_id': str(uuid.uuid4()),
                'trigger_entity': 'light.living_room',
                'action_entity': 'switch.fan',
                'area': 'living_room',
                'impact_score': 0.6,
                'confidence': 0.8,
                'rationale': 'Living room light triggers fan'
            },
        ]

    def test_build_action_lookup(self, detector, sample_pairwise_synergies):
        """Test building action lookup dictionary."""
        lookup = detector.build_action_lookup(sample_pairwise_synergies)
        
        assert 'light.hallway' in lookup
        assert 'light.living_room' in lookup
        assert 'switch.fan' in lookup
        assert len(lookup['light.hallway']) == 1
        assert lookup['light.hallway'][0]['trigger_entity'] == 'binary_sensor.motion_hallway'

    def test_calculate_quality_score(self, detector):
        """Test quality score calculation."""
        synergy = {'confidence': 0.9, 'impact_score': 0.8}
        score = detector._calculate_quality_score(synergy)
        
        # 0.9 * 0.6 + 0.8 * 0.4 = 0.54 + 0.32 = 0.86
        assert abs(score - 0.86) < 0.001

    def test_calculate_quality_score_missing_values(self, detector):
        """Test quality score with missing values."""
        synergy = {}
        score = detector._calculate_quality_score(synergy)
        assert score == 0.0

    def test_get_top_pairs_by_quality(self, detector, sample_pairwise_synergies):
        """Test getting top pairs by quality."""
        # With small list, should return all
        top_pairs = detector._get_top_pairs_by_quality(sample_pairwise_synergies, limit=10)
        assert len(top_pairs) == 3
        
        # With limit, should return limited
        top_pairs = detector._get_top_pairs_by_quality(sample_pairwise_synergies, limit=2)
        assert len(top_pairs) == 2
        
        # Should be sorted by quality
        assert top_pairs[0]['confidence'] >= top_pairs[1]['confidence']

    def test_should_skip_3_chain_same_device(self, detector):
        """Test skipping chain when same device appears twice."""
        should_skip = detector._should_skip_3_chain(
            trigger_entity='light.a',
            next_action='light.a',  # Same as trigger
            synergy={'area': 'room1'},
            next_synergy={'area': 'room1'}
        )
        assert should_skip is True

    def test_should_skip_3_chain_different_area(self, detector):
        """Test chain with different areas (no validation function)."""
        should_skip = detector._should_skip_3_chain(
            trigger_entity='light.a',
            next_action='light.c',
            synergy={'area': 'room1'},
            next_synergy={'area': 'room2'}  # Different area
        )
        # Without validation function, different areas are allowed
        assert should_skip is False

    def test_should_skip_3_chain_valid(self, detector):
        """Test valid chain that should not be skipped."""
        should_skip = detector._should_skip_3_chain(
            trigger_entity='light.a',
            next_action='light.c',
            synergy={'area': 'room1'},
            next_synergy={'area': 'room1'}
        )
        assert should_skip is False

    def test_create_3_device_chain(self, detector):
        """Test creating a 3-device chain."""
        synergy = {
            'impact_score': 0.8,
            'confidence': 0.9,
            'area': 'hallway',
            'rationale': 'First step'
        }
        next_synergy = {
            'impact_score': 0.7,
            'confidence': 0.85,
            'rationale': 'Second step'
        }
        
        chain = detector._create_3_device_chain(
            trigger_entity='motion.a',
            action_entity='light.b',
            next_action='light.c',
            synergy=synergy,
            next_synergy=next_synergy
        )
        
        assert chain['synergy_type'] == 'device_chain'
        assert chain['synergy_depth'] == 3
        assert len(chain['devices']) == 3
        assert chain['devices'] == ['motion.a', 'light.b', 'light.c']
        assert chain['trigger_entity'] == 'motion.a'
        assert chain['action_entity'] == 'light.c'
        assert chain['area'] == 'hallway'
        assert chain['impact_score'] == 0.75  # Average of 0.8 and 0.7
        assert chain['confidence'] == 0.85  # Min of 0.9 and 0.85
        assert '→' in chain['chain_path']

    @pytest.mark.asyncio
    async def test_detect_3_device_chains(self, detector, sample_pairwise_synergies):
        """Test detecting 3-device chains."""
        chains = await detector.detect_3_device_chains(sample_pairwise_synergies)
        
        # Should find at least one chain: motion → hallway → living_room
        assert len(chains) >= 1
        
        # Check chain structure
        chain = chains[0]
        assert chain['synergy_type'] == 'device_chain'
        assert chain['synergy_depth'] == 3
        assert len(chain['devices']) == 3

    @pytest.mark.asyncio
    async def test_detect_3_device_chains_with_cache(self, detector_with_cache, sample_pairwise_synergies, mock_cache):
        """Test 3-device chain detection with caching."""
        chains = await detector_with_cache.detect_3_device_chains(sample_pairwise_synergies)
        
        # Cache should have been checked and set
        assert mock_cache.get_chain_result.called
        assert mock_cache.set_chain_result.called

    @pytest.mark.asyncio
    async def test_detect_3_device_chains_cache_hit(self, detector_with_cache, sample_pairwise_synergies, mock_cache):
        """Test 3-device chain detection with cache hit."""
        cached_chain = {
            'synergy_id': 'cached-id',
            'synergy_type': 'device_chain',
            'synergy_depth': 3,
            'devices': ['a', 'b', 'c']
        }
        mock_cache.get_chain_result = AsyncMock(return_value=cached_chain)
        
        chains = await detector_with_cache.detect_3_device_chains(sample_pairwise_synergies)
        
        # Should return cached chain
        assert any(c.get('synergy_id') == 'cached-id' for c in chains)

    def test_should_skip_4_chain_device_in_chain(self, detector):
        """Test skipping 4-chain when device already in chain."""
        should_skip = detector._should_skip_4_chain(
            d='light.b',  # Already in chain
            a='light.a',
            chain_devices=['light.a', 'light.b', 'light.c'],
            three_chain={'area': 'room1'},
            next_synergy={'area': 'room1'}
        )
        assert should_skip is True

    def test_should_skip_4_chain_circular(self, detector):
        """Test skipping circular 4-chain."""
        should_skip = detector._should_skip_4_chain(
            d='light.a',  # Same as first device
            a='light.a',
            chain_devices=['light.a', 'light.b', 'light.c'],
            three_chain={'area': 'room1'},
            next_synergy={'area': 'room1'}
        )
        assert should_skip is True

    def test_create_4_device_chain(self, detector):
        """Test creating a 4-device chain."""
        three_chain = {
            'impact_score': 0.75,
            'confidence': 0.85,
            'area': 'hallway',
            'rationale': '3-chain rationale'
        }
        next_synergy = {
            'impact_score': 0.65,
            'confidence': 0.8,
            'rationale': 'Fourth step'
        }
        
        chain = detector._create_4_device_chain(
            a='motion.a',
            b='light.b',
            c='light.c',
            d='switch.d',
            three_chain=three_chain,
            next_synergy=next_synergy
        )
        
        assert chain['synergy_type'] == 'device_chain'
        assert chain['synergy_depth'] == 4
        assert len(chain['devices']) == 4
        assert chain['devices'] == ['motion.a', 'light.b', 'light.c', 'switch.d']
        assert chain['trigger_entity'] == 'motion.a'
        assert chain['action_entity'] == 'switch.d'
        assert chain['impact_score'] == 0.7  # Average of 0.75 and 0.65
        assert chain['confidence'] == 0.8  # Min of 0.85 and 0.8

    @pytest.mark.asyncio
    async def test_detect_4_device_chains(self, detector, sample_pairwise_synergies):
        """Test detecting 4-device chains."""
        # First get 3-device chains
        three_chains = await detector.detect_3_device_chains(sample_pairwise_synergies)
        
        # Then detect 4-device chains
        four_chains = await detector.detect_4_device_chains(
            three_chains, sample_pairwise_synergies
        )
        
        # May or may not find 4-chains depending on data
        # Just verify structure if found
        for chain in four_chains:
            assert chain['synergy_type'] == 'device_chain'
            assert chain['synergy_depth'] == 4
            assert len(chain['devices']) == 4

    @pytest.mark.asyncio
    async def test_detect_4_device_chains_empty_input(self, detector):
        """Test 4-device chain detection with empty 3-chains."""
        four_chains = await detector.detect_4_device_chains([], [])
        assert four_chains == []


class TestChainDetectorConstants:
    """Test configuration constants."""

    def test_top_pairs_constant(self):
        """Test TOP_PAIRS_FOR_CHAINS constant."""
        assert TOP_PAIRS_FOR_CHAINS == 1000

    def test_max_chains_reasonable(self):
        """Test that max chain limits are reasonable."""
        from chain_detection import MAX_3_DEVICE_CHAINS, MAX_4_DEVICE_CHAINS
        
        assert MAX_3_DEVICE_CHAINS == 200
        assert MAX_4_DEVICE_CHAINS == 100
        assert MAX_4_DEVICE_CHAINS < MAX_3_DEVICE_CHAINS
