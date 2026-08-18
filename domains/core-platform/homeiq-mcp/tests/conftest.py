from __future__ import annotations

import pytest
from src.backends import Backings, HttpBacking
from src.catalogue import load_catalogue
from src.config import Settings
from src.registry import ToolRegistry
from src.server import HomeIQMCP

READ_TOKEN = "read-token-for-tests"
WRITE_TOKEN = "write-token-for-tests"


@pytest.fixture
def settings() -> Settings:
    return Settings(
        read_tokens=READ_TOKEN,
        write_tokens=WRITE_TOKEN,
        data_api_url="http://data-api.test:8006",
        data_api_key="data-api-key",
        pattern_service_url="http://patterns.test:8020",
        device_intelligence_url="http://devint.test:8028",
    )


@pytest.fixture
def catalogue():
    return load_catalogue()


@pytest.fixture
def registry(catalogue) -> ToolRegistry:
    return ToolRegistry(catalogue)


@pytest.fixture
def backings(settings) -> Backings:
    return Backings(
        data_api=HttpBacking("data-api", settings.data_api_url, bearer_token="data-api-key"),
        patterns=HttpBacking("ai-pattern-service", settings.pattern_service_url),
        device_intelligence=HttpBacking(
            "device-intelligence-service", settings.device_intelligence_url
        ),
    )


@pytest.fixture
def app(settings, registry, backings) -> HomeIQMCP:
    return HomeIQMCP(settings, registry=registry, backings=backings)
