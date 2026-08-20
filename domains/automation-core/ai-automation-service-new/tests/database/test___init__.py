"""
Tests for __init__.py
"""

import src.database as database


def test_database_module_exports():
    """The module exposes get_db, init_db, and the session-maker alias.

    ``async_session_maker`` is a lazily bound alias: it stays None until
    ``init_db()`` runs, so only its presence is asserted here.
    """
    assert callable(database.get_db)
    assert callable(database.init_db)
    assert "async_session_maker" in vars(database)
