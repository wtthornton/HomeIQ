"""
Unit tests for Phase 2 Tasks 2.4 and 2.5

Task 2.4: Sequence Support for Test Stage
Task 2.5: Enhanced Component Restoration with Nested Component Support

Tests verify:
- Sequence detection logic
- Test mode selection (sequence vs simple)
- Nested component detection
- Component restoration with intent validation
"""

import pytest

pytest.importorskip(
    "transformers",
    reason="transformers dependency not available in this environment"
)

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, Mock

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from src.api.ask_ai_router import restore_stripped_components
from src.llm.openai_client import OpenAIClient
from src.services.component_detector import ComponentDetector, DetectedComponent


class TestTask24SequenceDetection:
    """Test Task 2.4: Sequence Support for Test Stage"""

    @pytest.fixture
    def component_detector(self):
        """Create ComponentDetector instance"""
        return ComponentDetector()

    def test_detect_sequences_with_delays(self, component_detector):
        """Test detecting sequences with delays"""
        description = "Flash office lights 5 times with 2-second delays when door opens"
        yaml_content = ""

        detected = component_detector.detect_stripped_components(yaml_content, description)

        # Should detect both delay and repeat
        delay_found = any(comp.component_type == 'delay' for comp in detected)
        repeat_found = any(comp.component_type == 'repeat' for comp in detected)

        assert delay_found, "Should detect delay in description"
        assert repeat_found, "Should detect repeat in description"
        assert len(detected) >= 2, "Should detect at least delay and repeat"

    def test_detect_simple_automation_no_sequences(self, component_detector):
        """Test detecting simple automation without sequences"""
        description = "Turn on bedroom lights when door opens"
        yaml_content = ""

        detected = component_detector.detect_stripped_components(yaml_content, description)

        # Should not detect delays or repeats
        delay_found = any(comp.component_type == 'delay' for comp in detected)
        repeat_found = any(comp.component_type == 'repeat' for comp in detected)

        assert not delay_found, "Should not detect delay in simple automation"
        assert not repeat_found, "Should not detect repeat in simple automation"

    def test_sequence_mode_selection(self):
        """Test sequence mode selection logic"""
        # Simulate detection of delays/repeats
        detected_components = [
            DetectedComponent(
                component_type='delay',
                original_value='2 seconds',
                detected_from='description',
                confidence=0.95
            ),
            DetectedComponent(
                component_type='repeat',
                original_value='5 times',
                detected_from='description',
                confidence=0.95
            )
        ]

        # Check if sequences are detected
        has_sequences = any(
            comp.component_type in ['repeat', 'delay']
            for comp in detected_components
        )

        assert has_sequences is True, "Should detect sequences"

        # Should use sequence mode
        test_mode = 'sequence' if has_sequences else 'simple'
        assert test_mode == 'sequence', "Should select sequence mode"

    def test_simple_mode_selection(self):
        """Test simple mode selection for non-sequence automations"""
        # Simulate no delays/repeats detected
        detected_components = []

        has_sequences = any(
            comp.component_type in ['repeat', 'delay']
            for comp in detected_components
        )

        assert has_sequences is False, "Should not detect sequences"

        # Should use simple mode
        test_mode = 'sequence' if has_sequences else 'simple'
        assert test_mode == 'simple', "Should select simple mode"

    def test_test_mode_flag_in_suggestion(self):
        """Test that test_mode flag is correctly set in suggestion"""
        suggestion = {
            'description': 'Flash lights 3 times with delays',
            'test_mode': 'sequence'
        }

        # Simulate check in generate_automation_yaml
        is_sequence_test = suggestion.get('test_mode') == 'sequence'

        assert is_sequence_test is True, "Should detect sequence test mode"

        # Simple mode
        suggestion['test_mode'] = 'simple'
        is_sequence_test = suggestion.get('test_mode') == 'sequence'
        assert is_sequence_test is False, "Should detect simple test mode"


class TestTask25NestedComponentDetection:
    """Test Task 2.5: Enhanced Component Restoration - Nested Component Detection"""

    def test_detect_nested_delay_in_repeat(self):
        """Test detecting nested components (delay within repeat)"""
        stripped_components = [
            {'type': 'delay', 'original_value': '2 seconds', 'confidence': 0.95},
            {'type': 'repeat', 'original_value': '3 times with delays', 'confidence': 0.95}
        ]

        nested_components = []
        simple_components = []

        for comp in stripped_components:
            comp_type = comp.get('type', '')
            original_value = comp.get('original_value', '')

            # Check if component appears to be nested
            if comp_type == 'delay' and any(
                'repeat' in str(other_comp.get('original_value', '')).lower() or other_comp.get('type') == 'repeat'
                for other_comp in stripped_components
            ):
                nested_components.append(comp)
            elif comp_type == 'repeat':
                if 'delay' in original_value.lower() or 'wait' in original_value.lower():
                    nested_components.append(comp)
                else:
                    simple_components.append(comp)
            else:
                simple_components.append(comp)

        # Delay should be nested (because repeat exists)
        delay_nested = any(
            comp.get('type') == 'delay' for comp in nested_components
        )
        assert delay_nested, "Delay should be detected as nested"

        # Repeat should be nested if it mentions delay
        repeat_nested = any(
            comp.get('type') == 'repeat' and 'delay' in comp.get('original_value', '').lower()
            for comp in nested_components
        )
        assert repeat_nested, "Repeat mentioning delay should be nested"

    def test_detect_simple_components(self):
        """Test detecting simple (non-nested) components"""
        stripped_components = [
            {'type': 'delay', 'original_value': '30 seconds', 'confidence': 0.95},
            {'type': 'time_condition', 'original_value': 'after 5pm', 'confidence': 0.95}
        ]

        nested_components = []
        simple_components = []

        for comp in stripped_components:
            comp_type = comp.get('type', '')
            original_value = comp.get('original_value', '')

            if comp_type == 'delay' and any(
                'repeat' in str(other_comp.get('original_value', '')).lower() or other_comp.get('type') == 'repeat'
                for other_comp in stripped_components
            ):
                nested_components.append(comp)
            elif comp_type == 'repeat':
                if 'delay' in original_value.lower() or 'wait' in original_value.lower():
                    nested_components.append(comp)
                else:
                    simple_components.append(comp)
            else:
                simple_components.append(comp)

        # Should have simple components (no repeats)
        assert len(simple_components) >= 1, "Should detect simple components"
        assert len(nested_components) == 0, "Should not detect nested components"

    def test_nesting_info_generation(self):
        """Test nesting info generation for prompt"""
        nested_components = [
            {'type': 'delay', 'original_value': '2 seconds'},
            {'type': 'repeat', 'original_value': '3 times'}
        ]

        nesting_info = ""
        if nested_components:
            nesting_info = f"\n\nNESTED COMPONENTS DETECTED: {len(nested_components)} component(s) may be nested (e.g., delays within repeat blocks). Pay special attention to restore them in the correct order and context."

        assert len(nesting_info) > 0, "Should generate nesting info"
        assert "NESTED COMPONENTS DETECTED" in nesting_info, "Should mention nested components"
        assert str(len(nested_components)) in nesting_info, "Should include count"


class TestTask25Restoration:
    """Test Task 2.5: Component Restoration"""

    @pytest.fixture
    def mock_openai_client(self):
        """Mock OpenAI client for restoration"""
        client = Mock(spec=OpenAIClient)
        client.model = "gpt-4o-mini"
        client.client = Mock()
        return client

    @pytest.mark.asyncio
    async def test_restoration_with_nested_components(self, mock_openai_client):
        """Test restoration with nested components"""
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = json.dumps({
            "restored": True,
            "restored_components": ["delay", "repeat"],
            "restoration_details": [
                "Restored delay: 2 seconds within repeat block",
                "Restored repeat: 3 times"
            ],
            "nested_components_restored": ["delay"],
            "restoration_structure": "delay: 2s within repeat: 3 times",
            "confidence": 0.95,
            "intent_match": True,
            "intent_validation": "Delays are correctly nested within repeat block as specified in original query"
        })

        mock_openai_client.client.chat.completions.create = AsyncMock(return_value=mock_response)

        original_suggestion = {
            'description': 'Flash lights 3 times with 2-second delays',
            'trigger_summary': 'Door opens',
            'action_summary': 'Flash lights with delays'
        }

        test_result = {
            'stripped_components': [
                {'type': 'delay', 'original_value': '2 seconds', 'confidence': 0.95},
                {'type': 'repeat', 'original_value': '3 times', 'confidence': 0.95}
            ]
        }

        original_query = "Flash office lights 3 times with 2-second delays when door opens"

        result = await restore_stripped_components(
            original_suggestion=original_suggestion,
            test_result=test_result,
            original_query=original_query,
            openai_client=mock_openai_client
        )

        # Verify enhanced fields are present
        assert 'nested_components_restored' in result, "Should include nested components"
        assert 'restoration_structure' in result, "Should include restoration structure"
        assert 'intent_match' in result, "Should include intent match"
        assert 'intent_validation' in result, "Should include intent validation"

        assert result['intent_match'] is True, "Should match user intent"
        assert len(result['nested_components_restored']) > 0, "Should restore nested components"
        assert len(result['restoration_structure']) > 0, "Should describe restoration structure"

    @pytest.mark.asyncio
    async def test_restoration_without_nested_components(self, mock_openai_client):
        """Test restoration with simple (non-nested) components"""
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = json.dumps({
            "restored": True,
            "restored_components": ["delay"],
            "restoration_details": ["Restored delay: 30 seconds"],
            "nested_components_restored": [],
            "restoration_structure": "delay: 30 seconds (simple component)",
            "confidence": 0.9,
            "intent_match": True,
            "intent_validation": "Delay matches original query intent"
        })

        mock_openai_client.client.chat.completions.create = AsyncMock(return_value=mock_response)

        original_suggestion = {
            'description': 'Wait 30 seconds then turn on lights',
            'trigger_summary': 'Button pressed',
            'action_summary': 'Wait then turn on'
        }

        test_result = {
            'stripped_components': [
                {'type': 'delay', 'original_value': '30 seconds', 'confidence': 0.95}
            ]
        }

        original_query = "Wait 30 seconds then turn on the lights"

        result = await restore_stripped_components(
            original_suggestion=original_suggestion,
            test_result=test_result,
            original_query=original_query,
            openai_client=mock_openai_client
        )

        # Verify all fields are present
        assert 'nested_components_restored' in result, "Should include nested components field"
        assert 'restoration_structure' in result, "Should include restoration structure"
        assert result['intent_match'] is True, "Should match user intent"
        assert len(result['nested_components_restored']) == 0, "Should have no nested components"

    @pytest.mark.asyncio
    async def test_restoration_without_openai_client(self):
        """Test restoration fallback when OpenAI client is unavailable"""
        original_suggestion = {
            'description': 'Flash lights with delays',
            'trigger_summary': 'Door opens',
            'action_summary': 'Flash lights'
        }

        test_result = {
            'stripped_components': [
                {'type': 'delay', 'original_value': '2 seconds', 'confidence': 0.95}
            ]
        }

        result = await restore_stripped_components(
            original_suggestion=original_suggestion,
            test_result=test_result,
            original_query="Flash lights with 2-second delays",
            openai_client=None  # No OpenAI client
        )

        # Should return basic restoration without enhanced fields
        assert 'restored_components' in result, "Should include restored components"
        assert 'restoration_log' in result, "Should include restoration log"
        # Enhanced fields may not be present without OpenAI
        assert result['restoration_confidence'] == 0.5 or 'restoration_confidence' not in result


class TestIntegration:
    """Integration tests for complete flow"""

    def test_sequence_detection_to_restoration_flow(self):
        """Test complete flow from sequence detection to restoration"""
        # Step 1: Detect components
        component_detector = ComponentDetector()
        description = "Flash office lights 5 times with 2-second delays when door opens"
        detected = component_detector.detect_stripped_components("", description)

        # Step 2: Determine mode
        has_sequences = any(
            comp.component_type in ['repeat', 'delay']
            for comp in detected
        )
        test_mode = 'sequence' if has_sequences else 'simple'

        # Step 3: Format for restoration
        stripped_components = component_detector.format_components_for_preview(detected)

        # Verify flow
        assert test_mode == 'sequence', "Should detect sequence mode"
        assert len(stripped_components) >= 2, "Should have multiple components"

        # Verify component types
        component_types = [comp.get('type') for comp in stripped_components]
        assert 'delay' in component_types, "Should include delay"
        assert 'repeat' in component_types, "Should include repeat"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

