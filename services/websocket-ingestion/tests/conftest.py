from tests.path_setup import add_service_src

add_service_src(__file__)

import pytest

pytest.skip(
    "websocket-ingestion tests require legacy modules not available in alpha environment",
    allow_module_level=True,
)
