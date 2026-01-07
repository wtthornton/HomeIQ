"""Tests for blueprint search engine."""

import pytest
import pytest_asyncio
from sqlalchemy import select

from src.indexer.blueprint_parser import BlueprintParser
from src.models import IndexedBlueprint
from src.search.search_engine import BlueprintSearchEngine
from src.api.schemas import BlueprintSearchRequest, PatternMatchRequest


class TestBlueprintSearchEngine:
    """Tests for BlueprintSearchEngine class."""
    
    @pytest_asyncio.fixture
    async def search_engine(self, db_session):
        """Create search engine with test database."""
        return BlueprintSearchEngine(db_session)
    
    @pytest_asyncio.fixture
    async def populated_db(self, db_session, sample_blueprint_yaml, sample_security_blueprint_yaml):
        """Populate database with test blueprints."""
        parser = BlueprintParser()
        
        # Create motion light blueprint
        motion_blueprint = parser.parse_blueprint(
            yaml_content=sample_blueprint_yaml,
            source_url="https://example.com/motion-light.yaml",
            source_type="github",
            stars=100,
            author="test_author",
        )
        motion_blueprint.quality_score = 0.8
        motion_blueprint.community_rating = 0.85
        
        # Create security blueprint
        security_blueprint = parser.parse_blueprint(
            yaml_content=sample_security_blueprint_yaml,
            source_url="https://example.com/door-alert.yaml",
            source_type="discourse",
            stars=50,
            author="security_author",
        )
        security_blueprint.quality_score = 0.7
        security_blueprint.community_rating = 0.6
        
        # Add to database
        db_session.add(motion_blueprint)
        db_session.add(security_blueprint)
        await db_session.commit()
        
        return db_session
    
    @pytest.mark.asyncio
    async def test_search_all(self, search_engine, populated_db):
        """Test searching all blueprints."""
        request = BlueprintSearchRequest(
            min_quality_score=0.0,
            min_community_rating=0.0,
            limit=50,
        )
        
        result = await search_engine.search(request)
        
        assert result.total == 2
        assert len(result.blueprints) == 2
    
    @pytest.mark.asyncio
    async def test_search_by_domain(self, search_engine, populated_db):
        """Test searching by required domain."""
        request = BlueprintSearchRequest(
            domains=["light"],
            min_quality_score=0.0,
            min_community_rating=0.0,
        )
        
        result = await search_engine.search(request)
        
        assert result.total >= 1
        for bp in result.blueprints:
            assert "light" in bp.required_domains
    
    @pytest.mark.asyncio
    async def test_search_by_device_class(self, search_engine, populated_db):
        """Test searching by device class."""
        request = BlueprintSearchRequest(
            device_classes=["motion"],
            min_quality_score=0.0,
            min_community_rating=0.0,
        )
        
        result = await search_engine.search(request)
        
        assert result.total >= 1
        for bp in result.blueprints:
            assert "motion" in bp.required_device_classes
    
    @pytest.mark.asyncio
    async def test_search_by_use_case(self, search_engine, populated_db):
        """Test searching by use case."""
        request = BlueprintSearchRequest(
            use_case="security",
            min_quality_score=0.0,
            min_community_rating=0.0,
        )
        
        result = await search_engine.search(request)
        
        for bp in result.blueprints:
            assert bp.use_case == "security"
    
    @pytest.mark.asyncio
    async def test_search_with_quality_filter(self, search_engine, populated_db):
        """Test quality score filtering."""
        request = BlueprintSearchRequest(
            min_quality_score=0.75,
            min_community_rating=0.0,
        )
        
        result = await search_engine.search(request)
        
        for bp in result.blueprints:
            assert bp.quality_score >= 0.75
    
    @pytest.mark.asyncio
    async def test_search_by_text_query(self, search_engine, populated_db):
        """Test text search in name and description."""
        request = BlueprintSearchRequest(
            query="motion",
            min_quality_score=0.0,
            min_community_rating=0.0,
        )
        
        result = await search_engine.search(request)
        
        assert result.total >= 1
    
    @pytest.mark.asyncio
    async def test_search_pagination(self, search_engine, populated_db):
        """Test pagination."""
        request = BlueprintSearchRequest(
            min_quality_score=0.0,
            min_community_rating=0.0,
            limit=1,
            offset=0,
        )
        
        result = await search_engine.search(request)
        
        assert len(result.blueprints) == 1
        assert result.total == 2
        assert result.has_more is True
    
    @pytest.mark.asyncio
    async def test_search_sorting(self, search_engine, populated_db):
        """Test sorting by quality score."""
        request = BlueprintSearchRequest(
            min_quality_score=0.0,
            min_community_rating=0.0,
            sort_by="quality_score",
            sort_order="desc",
        )
        
        result = await search_engine.search(request)
        
        if len(result.blueprints) >= 2:
            assert result.blueprints[0].quality_score >= result.blueprints[1].quality_score
    
    @pytest.mark.asyncio
    async def test_find_by_pattern(self, search_engine, populated_db):
        """Test pattern-based search."""
        request = PatternMatchRequest(
            trigger_domain="binary_sensor",
            action_domain="light",
            min_quality_score=0.0,
        )
        
        result = await search_engine.find_by_pattern(request)
        
        assert result.match_count >= 1
    
    @pytest.mark.asyncio
    async def test_find_by_pattern_with_device_class(self, search_engine, populated_db):
        """Test pattern-based search with device class."""
        request = PatternMatchRequest(
            trigger_domain="binary_sensor",
            action_domain="light",
            trigger_device_class="motion",
            min_quality_score=0.0,
        )
        
        result = await search_engine.find_by_pattern(request)
        
        assert result.match_count >= 1
    
    @pytest.mark.asyncio
    async def test_get_by_id(self, search_engine, populated_db):
        """Test getting blueprint by ID."""
        # First get a blueprint to know its ID
        request = BlueprintSearchRequest(
            min_quality_score=0.0,
            min_community_rating=0.0,
            limit=1,
        )
        search_result = await search_engine.search(request)
        
        if search_result.blueprints:
            blueprint_id = search_result.blueprints[0].id
            result = await search_engine.get_by_id(blueprint_id)
            
            assert result is not None
            assert result.id == blueprint_id
    
    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, search_engine, populated_db):
        """Test getting non-existent blueprint."""
        result = await search_engine.get_by_id("non-existent-id")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_indexing_status(self, search_engine, populated_db):
        """Test getting indexing status."""
        status = await search_engine.get_indexing_status()
        
        assert status.total_blueprints == 2
        assert status.github_blueprints >= 0
        assert status.discourse_blueprints >= 0
