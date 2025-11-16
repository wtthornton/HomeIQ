import json
from pathlib import Path

import pytest

from utils import TestOpenVINOManager


FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="module")
def ner_benchmark():
    with open(FIXTURES / "ner_benchmark.json", "r", encoding="utf-8") as handle:
        return json.load(handle)


@pytest.fixture
def classification_manager(tmp_path):
    return TestOpenVINOManager(models_dir=str(tmp_path))


@pytest.mark.asyncio
async def test_classification_matches_benchmark(classification_manager, ner_benchmark):
    for case in ner_benchmark:
        result = await classification_manager.classify_pattern(case["text"])
        assert result["category"] == case["expected_category"]
        assert result["priority"] == case["expected_priority"]


@pytest.mark.asyncio
async def test_category_parser_handles_noisy_outputs(classification_manager):
    noisy_output = "Category:  SECURITY !!! "
    category = classification_manager._parse_category(noisy_output)
    assert category == "security"


@pytest.mark.asyncio
async def test_priority_parser_handles_unknown_tokens(classification_manager):
    noisy_output = "Priority --> medium-level"
    priority = classification_manager._parse_priority(noisy_output)
    assert priority == "medium"
