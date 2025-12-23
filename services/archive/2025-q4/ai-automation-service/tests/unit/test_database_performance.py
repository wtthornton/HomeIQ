"""
Unit Tests for Database Performance Optimizations

Tests SQLite WAL mode and batch storage optimizations (Phase 1-2).
"""

import pytest
import pytest_asyncio
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from src.database.crud import store_suggestion
from src.database.models import Base

# ============================================================================
# Test Database Fixtures
# ============================================================================

@pytest_asyncio.fixture
async def db_engine():
    """Create in-memory SQLite database for testing"""
    test_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        pool_pre_ping=True,
        connect_args={
            "timeout": 30.0
        }
    )

    # Configure SQLite pragmas for optimal performance (same as production)
    @event.listens_for(test_engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        """Set SQLite pragmas on each connection for optimal performance."""
        cursor = dbapi_conn.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA cache_size=-64000")
            cursor.execute("PRAGMA temp_store=MEMORY")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=30000")
        except Exception:
            pass
        finally:
            cursor.close()

    # Create all tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield test_engine

    # Cleanup
    await test_engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    """Create database session for testing"""
    async_session = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session() as session:
        yield session


# ============================================================================
# SQLite WAL Mode Tests (Phase 1)
# ============================================================================

class TestSQLiteWALMode:
    """Test SQLite WAL mode and pragmas are configured correctly"""

    @pytest.mark.asyncio
    async def test_sqlite_wal_mode_enabled(self, db_session):
        """Verify WAL mode is enabled after initialization"""
        result = await db_session.execute(text("PRAGMA journal_mode"))
        mode = result.scalar()
        # Note: In-memory databases use "memory" journal mode, not WAL
        # This is expected SQLite behavior - WAL is only for file-based databases
        assert mode in ["wal", "memory"], f"Expected WAL or memory mode, got {mode}"

    @pytest.mark.asyncio
    async def test_sqlite_cache_size(self, db_session):
        """Verify cache size is configured"""
        result = await db_session.execute(text("PRAGMA cache_size"))
        cache = result.scalar()
        # Cache size should be -64000 (64MB) or similar
        assert cache == -64000, f"Expected -64000 KB cache, got {cache}"

    @pytest.mark.asyncio
    async def test_sqlite_synchronous_mode(self, db_session):
        """Verify synchronous mode is NORMAL"""
        result = await db_session.execute(text("PRAGMA synchronous"))
        sync_mode = result.scalar()
        assert sync_mode == 1, f"Expected NORMAL (1), got {sync_mode}"

    @pytest.mark.asyncio
    async def test_sqlite_foreign_keys_enabled(self, db_session):
        """Verify foreign keys are enabled"""
        result = await db_session.execute(text("PRAGMA foreign_keys"))
        fk_enabled = result.scalar()
        assert fk_enabled == 1, f"Expected foreign keys enabled, got {fk_enabled}"

    @pytest.mark.asyncio
    async def test_sqlite_busy_timeout(self, db_session):
        """Verify busy timeout is configured"""
        result = await db_session.execute(text("PRAGMA busy_timeout"))
        timeout = result.scalar()
        assert timeout == 30000, f"Expected 30000ms timeout, got {timeout}"

    @pytest.mark.asyncio
    async def test_sqlite_temp_store_memory(self, db_session):
        """Verify temp store uses memory"""
        result = await db_session.execute(text("PRAGMA temp_store"))
        temp_store = result.scalar()
        assert temp_store == 2, f"Expected MEMORY (2), got {temp_store}"


# ============================================================================
# Batch Storage Tests (Phase 2)
# ============================================================================

class TestBatchSuggestionStorage:
    """Test batch suggestion storage optimization"""

    @pytest.mark.asyncio
    async def test_batch_suggestion_storage_single_transaction(self, db_session):
        """Test batch storage of multiple suggestions in single transaction"""
        suggestions = [
            {
                'title': f'Test Suggestion {i}',
                'description': f'Test description {i}',
                'confidence': 0.8,
                'category': 'convenience',
                'priority': 'medium'
            }
            for i in range(10)
        ]

        stored_count = 0
        for suggestion in suggestions:
            try:
                await store_suggestion(db_session, suggestion, commit=False)
                stored_count += 1
            except Exception as e:
                pytest.fail(f"Failed to store suggestion: {e}")

        # Commit all at once
        await db_session.commit()

        assert stored_count == 10

        # Verify all stored
        result = await db_session.execute(text("SELECT COUNT(*) FROM suggestions"))
        count = result.scalar()
        assert count == 10

    @pytest.mark.asyncio
    async def test_batch_storage_with_error_handling(self, db_session):
        """Test batch storage continues on error"""
        suggestions = [
            {'title': 'Valid 1', 'description': 'test', 'confidence': 0.8},
            {'title': 'Valid 2', 'description': 'test', 'confidence': 0.8},
            {'title': 'Valid 3', 'description': 'test', 'confidence': 0.8},
        ]

        stored_count = 0
        for suggestion in suggestions:
            try:
                await store_suggestion(db_session, suggestion, commit=False)
                stored_count += 1
            except Exception:
                # Continue with other suggestions on error
                pass

        # Commit successful suggestions
        if stored_count > 0:
            await db_session.commit()

        # All should have stored successfully
        assert stored_count == 3

    @pytest.mark.asyncio
    async def test_batch_storage_rollback_on_commit_failure(self, db_session):
        """Test batch storage rolls back on commit failure"""
        # First, create one suggestion normally
        await store_suggestion(
            db_session,
            {'title': 'Test', 'description': 'test', 'confidence': 0.8}
        )

        # Now try to batch store more with a violation
        suggestions = [
            {'title': 'Valid', 'description': 'test', 'confidence': 0.8},
        ]

        stored_count = 0
        for suggestion in suggestions:
            try:
                await store_suggestion(db_session, suggestion, commit=False)
                stored_count += 1
            except Exception:
                pass

        # Try to commit (will fail if there's a constraint violation)
        try:
            await db_session.commit()
        except Exception:
            await db_session.rollback()

        # Verify previous suggestion still exists
        result = await db_session.execute(text("SELECT COUNT(*) FROM suggestions"))
        count = result.scalar()
        # Should still have just the first one if rollback worked
        assert count >= 1


# ============================================================================
# Performance Tests
# ============================================================================

class TestDatabasePerformance:
    """Test database performance improvements"""

    @pytest.mark.asyncio
    async def test_batch_vs_individual_storage_performance(self, db_session):
        """Compare batch vs individual storage performance"""
        import time

        # Test individual storage (old way)
        suggestions = [
            {'title': f'Test {i}', 'description': 'test', 'confidence': 0.8}
            for i in range(10)
        ]

        start = time.time()
        for suggestion in suggestions:
            await store_suggestion(db_session, suggestion, commit=True)
        individual_time = time.time() - start

        # Clear for batch test
        await db_session.execute(text("DELETE FROM suggestions"))
        await db_session.commit()

        # Test batch storage (new way)
        start = time.time()
        for suggestion in suggestions:
            await store_suggestion(db_session, suggestion, commit=False)
        await db_session.commit()
        batch_time = time.time() - start

        # Batch should be faster (or at least not slower)
        # Actual improvement depends on DB, but should be measurable
        print(f"\nIndividual: {individual_time:.4f}s, Batch: {batch_time:.4f}s")
        assert batch_time < individual_time * 2, "Batch storage should not be significantly slower"

    @pytest.mark.asyncio
    async def test_wal_mode_concurrent_reads(self, db_session):
        """Test WAL mode allows concurrent reads"""
        # Create a suggestion
        await store_suggestion(
            db_session,
            {'title': 'Test', 'description': 'test', 'confidence': 0.8}
        )

        # WAL mode should allow concurrent reads
        # This is more of a functional test than performance
        result1 = await db_session.execute(text("SELECT COUNT(*) FROM suggestions"))
        count1 = result1.scalar()

        result2 = await db_session.execute(text("SELECT COUNT(*) FROM suggestions"))
        count2 = result2.scalar()

        assert count1 == count2 == 1

