"""One process, one model load (TAP-7276).

model-server folds openvino-service's embedding/rerank/classify model into
the same process that used to be rag-service, which previously called that
model over HTTP to a separate container. This test asserts the merged app
constructs exactly one ``OpenVINOManager`` on startup, and that both the
openvino routes and RAG's embedding path (via ``LocalOpenVINOBridge``) share
that same instance -- not a second copy and not a network hop to a container
that no longer exists.
"""

from __future__ import annotations

from unittest.mock import patch

import numpy as np
import pytest
from fastapi.testclient import TestClient

import src.main as main_module


def test_openvino_manager_constructed_exactly_once_on_startup():
    """Two former services (openvino-service, rag-service) shared one
    OpenVINO deployment before the merge only by both pointing at the same
    *container*. In the merged process that guarantee has to come from the
    code instead: exactly one ``OpenVINOManager()`` call during startup."""
    real_cls = main_module.OpenVINOManager
    with patch("src.main.OpenVINOManager", side_effect=real_cls) as counted_ctor:
        with TestClient(main_module.app):
            pass
        assert counted_ctor.call_count == 1, (
            f"expected exactly one OpenVINOManager() construction on startup, got {counted_ctor.call_count}"
        )


def test_rag_bridge_shares_the_openvino_router_instance():
    """RAG's embedding calls must go through the *same* manager object the
    /embeddings and /rerank routes use, not a second instance."""
    with TestClient(main_module.app):
        bridge = main_module.app.state.openvino_client
        assert bridge is not None
        assert bridge._manager is main_module.openvino_manager


@pytest.mark.asyncio
async def test_rag_bridge_generate_embeddings_delegates_to_shared_manager():
    """Assert on the call, not just the identity: RAG's bridge must route
    through the shared manager's own generate_embeddings, proving the model
    that answers a RAG query is the same model instance serving /embeddings."""
    with TestClient(main_module.app):
        manager = main_module.openvino_manager
        bridge = main_module.app.state.openvino_client
        with patch.object(manager, "generate_embeddings", wraps=manager.generate_embeddings) as spy:
            spy.return_value = np.array([[0.1, 0.2, 0.3]])
            result = await bridge.get_embeddings(["hello"], normalize=True)
            assert spy.call_count == 1
            assert result == [[0.1, 0.2, 0.3]]
