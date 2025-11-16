import time

import pytest

from utils import TestOpenVINOManager


@pytest.fixture
def perf_manager(tmp_path):
    return TestOpenVINOManager(models_dir=str(tmp_path))


@pytest.mark.asyncio
async def test_single_embedding_latency(perf_manager):
    start = time.perf_counter()
    await perf_manager.generate_embeddings(["Performance test sentence"])
    duration_ms = (time.perf_counter() - start) * 1000
    assert duration_ms < 100


@pytest.mark.asyncio
async def test_batch_embedding_throughput(perf_manager):
    texts = [f"Sentence {i}" for i in range(100)]
    start = time.perf_counter()
    embeddings = await perf_manager.generate_embeddings(texts)
    duration_ms = (time.perf_counter() - start) * 1000

    assert embeddings.shape[0] == len(texts)
    assert duration_ms < 5000  # <5s for large batch
