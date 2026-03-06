"""Pytest configuration and shared fixtures for homeiq-memory tests."""

import pytest


def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers",
        "asyncio: mark test as async",
    )


@pytest.fixture(autouse=True)
def reset_thread_pool():
    """Reset the shared thread pool after each test to avoid state leakage."""
    yield
    import homeiq_memory.embeddings as emb_module

    if emb_module._thread_pool is not None:
        emb_module._thread_pool.shutdown(wait=False)
        emb_module._thread_pool = None
