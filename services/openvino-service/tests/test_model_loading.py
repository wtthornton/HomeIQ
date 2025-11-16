import sys
import types

import numpy as np
import pytest

from src.models.openvino_manager import OpenVINOManager


class _StubSentenceTransformer:
    def __init__(self, model_name: str, cache_folder: str):
        self.model_name = model_name
        self.cache_folder = cache_folder

    def encode(self, texts, convert_to_numpy=True):
        vectors = np.ones((len(texts), 384))
        return vectors / np.linalg.norm(vectors, axis=1, keepdims=True)


@pytest.fixture
def patched_manager(monkeypatch, tmp_path):
    module = types.ModuleType("sentence_transformers")
    module.SentenceTransformer = _StubSentenceTransformer
    monkeypatch.setitem(sys.modules, "sentence_transformers", module)
    manager = OpenVINOManager(models_dir=str(tmp_path))
    return manager


@pytest.mark.asyncio
async def test_manager_falls_back_to_standard_models(patched_manager):
    await patched_manager._load_embedding_model()
    assert isinstance(patched_manager._embed_model, _StubSentenceTransformer)
    assert patched_manager._embed_tokenizer is None
    assert patched_manager.use_openvino is False


@pytest.mark.asyncio
async def test_cleanup_purges_models_and_reports_status(patched_manager):
    await patched_manager._load_embedding_model()
    status_before = patched_manager.get_model_status()
    assert status_before["embedding_loaded"] is True

    await patched_manager.cleanup()
    status_after = patched_manager.get_model_status()
    assert status_after["embedding_loaded"] is False
    assert patched_manager._embed_model is None
