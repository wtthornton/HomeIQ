"""Tests for FeedbackStore's DB URL contract and insert path (TAP-7312).

`FeedbackStore` was constructed with a `PosixPath` (from `feedback_db_path`,
a leftover sqlite-style local path) instead of a DB URL string, so
`create_async_engine` blew up with `ArgumentError: Expected string or URL
object, got PosixPath(...)` on the first real operation -- reported upstream
as a bare 500 on the first feedback insert.
"""

from pathlib import Path

import pytest

from src.data.feedback_store import FeedbackStore


class TestFeedbackStoreConstructorContract:
    def test_rejects_path_object(self):
        with pytest.raises(TypeError, match="DB URL string"):
            FeedbackStore(Path("/data/feedback.db"))

    def test_accepts_string_url(self):
        store = FeedbackStore("sqlite+aiosqlite:///:memory:")
        assert store._db_url == "sqlite+aiosqlite:///:memory:"

    def test_none_falls_back_to_default(self):
        store = FeedbackStore(None)
        assert isinstance(store._db_url, str)


class TestFeedbackStoreInsertEndToEnd:
    async def test_insert_then_total_count(self):
        store = FeedbackStore("sqlite+aiosqlite:///:memory:")

        await store.insert(
            feedback_id="fb-1",
            rule_pattern="binary_sensor_to_light",
            user_id="user-1",
            feedback_type="accepted",
            rating=5,
            comment="works great",
            automation_id=None,
        )

        assert await store.total_count() == 1

    async def test_insert_is_readable_back(self):
        store = FeedbackStore("sqlite+aiosqlite:///:memory:")

        await store.insert(
            feedback_id="fb-2",
            rule_pattern="switch_to_light",
            user_id=None,
            feedback_type="created",
            rating=None,
            comment=None,
            automation_id="automation.foo",
        )

        rows = await store.get_all_feedback()
        assert len(rows) == 1
        assert rows[0]["rule_pattern"] == "switch_to_light"
        assert rows[0]["automation_id"] == "automation.foo"
