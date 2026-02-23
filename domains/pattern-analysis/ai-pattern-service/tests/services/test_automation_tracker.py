"""
Unit tests for AutomationTracker service

Tests automation execution tracking and confidence adjustment.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from typing import Any
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from src.services.automation_tracker import AutomationTracker


class TestAutomationTracker:
    """Test suite for AutomationTracker class."""
    
    @pytest.fixture
    async def test_db(self) -> AsyncSession:
        """Create test database session."""
        from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
        from sqlalchemy.pool import StaticPool
        
        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
            echo=False,
        )
        
        async_session = async_sessionmaker(engine, expire_on_commit=False)
        
        # Create tables
        async with engine.begin() as conn:
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS automation_executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    automation_id TEXT NOT NULL,
                    synergy_id TEXT NOT NULL,
                    success BOOLEAN NOT NULL,
                    error TEXT,
                    execution_time_ms INTEGER,
                    triggered_count INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS synergy_opportunities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    synergy_id TEXT UNIQUE NOT NULL,
                    confidence REAL NOT NULL,
                    impact_score REAL NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
        
        async with async_session() as session:
            yield session
    
    @pytest.fixture
    def tracker(self, test_db: AsyncSession) -> AutomationTracker:
        """Create AutomationTracker instance for testing."""
        return AutomationTracker(db=test_db)
    
    @pytest.fixture
    def sample_execution_result(self) -> dict[str, Any]:
        """Sample execution result for testing."""
        return {
            'success': True,
            'error': None,
            'execution_time_ms': 150,
            'triggered_count': 5
        }
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.requires_db
    async def test_init(self, test_db: AsyncSession):
        """Test AutomationTracker initialization."""
        tracker = AutomationTracker(db=test_db)
        assert tracker.db is not None
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.requires_db
    async def test_track_automation_execution_success(
        self,
        tracker: AutomationTracker,
        test_db: AsyncSession,
        sample_execution_result: dict[str, Any]
    ):
        """Test tracking successful automation execution."""
        automation_id = "automation.test_automation"
        synergy_id = "test-synergy-123"
        
        # First, create a synergy in the database
        await test_db.execute(
            text("""
                INSERT INTO synergy_opportunities (synergy_id, confidence, impact_score)
                VALUES (:synergy_id, :confidence, :impact_score)
            """),
            {
                "synergy_id": synergy_id,
                "confidence": 0.7,
                "impact_score": 0.5
            }
        )
        await test_db.commit()
        
        # Execute
        await tracker.track_automation_execution(
            automation_id,
            synergy_id,
            sample_execution_result,
            db=test_db
        )
        
        # Verify execution record was created
        result = await test_db.execute(
            text("""
                SELECT * FROM automation_executions
                WHERE synergy_id = :synergy_id
            """),
            {"synergy_id": synergy_id}
        )
        row = result.fetchone()
        assert row is not None
        assert row[2] == synergy_id  # synergy_id column
        assert row[3] == 1  # success = True (stored as 1)
        assert row[6] == 5  # triggered_count
        
        # Verify confidence was updated
        result = await test_db.execute(
            text("""
                SELECT confidence, impact_score FROM synergy_opportunities
                WHERE synergy_id = :synergy_id
            """),
            {"synergy_id": synergy_id}
        )
        row = result.fetchone()
        assert row is not None
        # Confidence should have increased (0.7 + 0.05 = 0.75)
        assert row[0] > 0.7
        # Impact should have increased (0.5 + 0.03 = 0.53)
        assert row[1] > 0.5
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.requires_db
    async def test_track_automation_execution_failure(
        self,
        tracker: AutomationTracker,
        test_db: AsyncSession
    ):
        """Test tracking failed automation execution."""
        automation_id = "automation.test_automation"
        synergy_id = "test-synergy-456"
        
        execution_result = {
            'success': False,
            'error': 'Entity not found',
            'execution_time_ms': 50,
            'triggered_count': 0
        }
        
        # First, create a synergy in the database
        await test_db.execute(
            text("""
                INSERT INTO synergy_opportunities (synergy_id, confidence, impact_score)
                VALUES (:synergy_id, :confidence, :impact_score)
            """),
            {
                "synergy_id": synergy_id,
                "confidence": 0.8,
                "impact_score": 0.7
            }
        )
        await test_db.commit()
        
        # Execute
        await tracker.track_automation_execution(
            automation_id,
            synergy_id,
            execution_result,
            db=test_db
        )
        
        # Verify execution record was created
        result = await test_db.execute(
            text("""
                SELECT * FROM automation_executions
                WHERE synergy_id = :synergy_id
            """),
            {"synergy_id": synergy_id}
        )
        row = result.fetchone()
        assert row is not None
        assert row[3] == 0  # success = False (stored as 0)
        assert row[4] == 'Entity not found'  # error message
        
        # Verify confidence was decreased
        result = await test_db.execute(
            text("""
                SELECT confidence, impact_score FROM synergy_opportunities
                WHERE synergy_id = :synergy_id
            """),
            {"synergy_id": synergy_id}
        )
        row = result.fetchone()
        assert row is not None
        # Confidence should have decreased (0.8 - 0.1 = 0.7)
        assert row[0] < 0.8
        # Impact should have decreased (0.7 - 0.05 = 0.65)
        assert row[1] < 0.7
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.requires_db
    async def test_get_execution_stats(
        self,
        tracker: AutomationTracker,
        test_db: AsyncSession
    ):
        """Test getting execution statistics."""
        synergy_id = "test-synergy-789"
        
        # Create synergy
        await test_db.execute(
            text("""
                INSERT INTO synergy_opportunities (synergy_id, confidence, impact_score)
                VALUES (:synergy_id, :confidence, :impact_score)
            """),
            {
                "synergy_id": synergy_id,
                "confidence": 0.7,
                "impact_score": 0.5
            }
        )
        
        # Create execution records
        await test_db.execute(
            text("""
                INSERT INTO automation_executions 
                (automation_id, synergy_id, success, error, execution_time_ms, triggered_count)
                VALUES 
                ('automation.test1', :synergy_id, 1, NULL, 100, 3),
                ('automation.test1', :synergy_id, 1, NULL, 150, 5),
                ('automation.test1', :synergy_id, 0, 'Error', 50, 0)
            """),
            {"synergy_id": synergy_id}
        )
        await test_db.commit()
        
        # Execute
        stats = await tracker.get_execution_stats(synergy_id, db=test_db)
        
        # Verify
        assert stats['total_executions'] == 3
        assert stats['successful_executions'] == 2
        assert stats['failed_executions'] == 1
        assert stats['total_triggered'] == 8
        assert stats['success_rate'] == pytest.approx(2.0 / 3.0, rel=0.01)
        assert stats['avg_execution_time_ms'] == pytest.approx(100.0, rel=0.01)
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.requires_db
    async def test_get_execution_stats_no_data(
        self,
        tracker: AutomationTracker,
        test_db: AsyncSession
    ):
        """Test getting execution statistics when no data exists."""
        synergy_id = "test-synergy-nonexistent"
        
        # Execute
        stats = await tracker.get_execution_stats(synergy_id, db=test_db)
        
        # Verify
        assert stats['total_executions'] == 0
        assert stats['successful_executions'] == 0
        assert stats['failed_executions'] == 0
        assert stats['total_triggered'] == 0
        assert stats['success_rate'] == 0.0
        assert stats['avg_execution_time_ms'] == 0.0
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_track_automation_execution_no_db(self):
        """Test tracking execution when no database session is available."""
        tracker = AutomationTracker(db=None)
        
        # Should not raise exception, just log warning
        await tracker.track_automation_execution(
            "automation.test",
            "synergy-123",
            {'success': True, 'triggered_count': 1},
            db=None
        )
        
        # No assertions needed - just verifying no exception is raised
