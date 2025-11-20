import json
import tempfile
from pathlib import Path

import numpy as np
import pytest
from utils import (
    EMBEDDING_DIMENSION,
    TestOpenVINOManager,
    cosine_similarity,
)

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def embedding_data():
    with open(FIXTURES / "embedding_test_data.json", encoding="utf-8") as handle:
        return json.load(handle)


@pytest.fixture
def embedding_manager(tmp_path):
    return TestOpenVINOManager(models_dir=str(tmp_path))


@pytest.mark.asyncio
async def test_embedding_dimensions(embedding_manager, embedding_data):
    embeddings = await embedding_manager.generate_embeddings(embedding_data["batch_texts"])
    assert embeddings.shape == (len(embedding_data["batch_texts"]), EMBEDDING_DIMENSION)


@pytest.mark.asyncio
async def test_embedding_normalization(embedding_manager, embedding_data):
    embeddings = await embedding_manager.generate_embeddings(embedding_data["batch_texts"])
    norms = np.linalg.norm(embeddings, axis=1)
    assert np.all((norms > 0.99) & (norms < 1.01))


@pytest.mark.asyncio
async def test_semantic_similarity(embedding_manager, embedding_data):
    for text_a, text_b in embedding_data["similar_pairs"]:
        vectors = await embedding_manager.generate_embeddings([text_a, text_b])
        similarity = cosine_similarity(vectors[0], vectors[1])
        assert similarity > 0.4


@pytest.mark.asyncio
async def test_semantic_dissimilarity(embedding_manager, embedding_data):
    for text_a, text_b in embedding_data["dissimilar_pairs"]:
        vectors = await embedding_manager.generate_embeddings([text_a, text_b])
        similarity = cosine_similarity(vectors[0], vectors[1])
        assert similarity < 0.3


@pytest.mark.parametrize("text", [
    "Turn on the lights",
    "Set temperature to 72 degrees",
    "Close the garage door",
    "Start the vacuum cleaner",
    "A" * 240  # Max length test
])
@pytest.mark.asyncio
async def test_embedding_properties_property(text):
    """Test embedding properties for various text inputs"""
    with tempfile.TemporaryDirectory() as temp_dir:
        manager = TestOpenVINOManager(models_dir=temp_dir)
        vectors = await manager.generate_embeddings([text])
        vector = vectors[0]
        assert len(vector) == EMBEDDING_DIMENSION
        assert not np.isnan(vector).any()
        assert not np.isinf(vector).any()
        norm = np.linalg.norm(vector)
        assert 0.99 <= norm <= 1.01
