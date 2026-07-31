"""
Unit tests for Query Processor Service

Epic 39, Story 39.12: Query & Automation Service Testing
"""

from unittest.mock import AsyncMock, create_autospec

import pytest
from src.services.clarification.service import ClarificationService
from src.services.query.processor import QueryProcessor


class TestQueryProcessor:
    """Test suite for query processor service."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_process_query_validation(self):
        """Test query validation."""
        processor = QueryProcessor()

        # Test empty query
        with pytest.raises(ValueError, match="Query is required"):
            await processor.process_query("")

        # Test None query
        with pytest.raises(ValueError, match="Query is required"):
            await processor.process_query(None)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_process_query_with_entities(self, sample_entities):
        """Test query processing with mock entity extractor."""
        entity_extractor = AsyncMock()
        entity_extractor.extract = AsyncMock(return_value=sample_entities)

        processor = QueryProcessor(entity_extractor=entity_extractor)

        result = await processor.process_query(
            query="Turn on office lights",
            user_id="test_user"
        )

        assert "query_id" in result
        assert result["original_query"] == "Turn on office lights"
        assert len(result["extracted_entities"]) > 0
        assert "confidence" in result
        assert "processing_time_ms" in result

    @pytest.mark.unit
    def test_calculate_confidence_no_entities(self):
        """Test confidence calculation with no entities."""
        processor = QueryProcessor()
        confidence = processor._calculate_confidence([], [], None)
        assert confidence == 0.5  # Base confidence

    @pytest.mark.unit
    def test_calculate_confidence_with_entities(self, sample_entities):
        """Test confidence calculation with entities."""
        processor = QueryProcessor()
        confidence = processor._calculate_confidence(sample_entities, [], None)
        assert confidence > 0.5
        assert confidence <= 0.95

    @pytest.mark.unit
    def test_calculate_confidence_with_suggestions(self, sample_entities):
        """Test confidence calculation with suggestions."""
        processor = QueryProcessor()
        suggestions = [{"confidence": 0.8}]
        confidence = processor._calculate_confidence(sample_entities, suggestions, None)
        assert confidence > 0.5

    @pytest.mark.unit
    def test_build_message_no_suggestions(self):
        """Test message building with no suggestions."""
        processor = QueryProcessor()
        message = processor._build_message([], [], None)
        assert "couldn't generate" in message.lower() or "provide more details" in message.lower()

    @pytest.mark.unit
    def test_build_message_with_suggestions(self, sample_entities):
        """Test message building with suggestions."""
        processor = QueryProcessor()
        suggestions = [{"description": "Test automation"}]
        message = processor._build_message(sample_entities, suggestions, None)
        assert "suggestion" in message.lower() or "automation" in message.lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_clarification_called_with_signature_the_real_service_accepts(self):
        """Regression: the clarification call must bind against the real signature.

        query_router builds QueryProcessor with a real ClarificationService, so
        every request reaches this call. A keyword the signature does not accept
        raises TypeError and fails the whole request.

        The other tests in this file inject a bare AsyncMock, which accepts any
        keyword and therefore cannot catch signature drift — this test uses the
        real collaborator on purpose.
        """
        processor = QueryProcessor(clarification_service=ClarificationService())

        result = await processor.process_query("Turn on office lights")

        assert result["query_id"]

    @pytest.mark.unit
    def test_only_autospec_catches_signature_drift(self):
        """Only create_autospec enforces signatures — spec= does not.

        Documents why the bug above survived the existing suite, so the next
        person does not "simplify" the test above back to a bare AsyncMock.
        Both AsyncMock() and AsyncMock(spec=ClarificationService) accept any
        keyword; only create_autospec binds against the real signature.
        """
        for permissive in (AsyncMock(), AsyncMock(spec=ClarificationService)):
            permissive.detect_clarification_needs(query="q", entities=[], db=None)

        autospecced = create_autospec(ClarificationService, instance=True)
        with pytest.raises(TypeError, match="unexpected keyword argument 'db'"):
            autospecced.detect_clarification_needs(query="q", entities=[], db=None)

