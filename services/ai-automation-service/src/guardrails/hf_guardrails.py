"""Simple Hugging Face based guardrail checks for Ask AI suggestions."""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class GuardrailResult:
    text: str
    label: str
    score: float
    flagged: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "label": self.label,
            "score": self.score,
            "flagged": self.flagged,
        }


class HuggingFaceGuardrail:
    """Wraps a text-classification pipeline for lightweight safety checks."""

    def __init__(self, model_name: str, threshold: float = 0.6) -> None:
        self.model_name = model_name
        self.threshold = threshold
        self._pipeline = None

        try:  # pragma: no cover - optional dependency
            from transformers import pipeline

            self._pipeline = pipeline(
                "text-classification",
                model=model_name,
                truncation=True,
                max_length=256,
                device=-1,
            )
            logger.info("Guardrail pipeline initialised with model %s", model_name)
        except Exception as exc:
            logger.warning("Unable to load guardrail model %s: %s", model_name, exc)
            self._pipeline = None

    @property
    def is_ready(self) -> bool:
        return self._pipeline is not None

    def evaluate_batch(self, texts: Iterable[str]) -> list[GuardrailResult]:
        if not self.is_ready:
            return []

        source_texts = list(texts)
        if not source_texts:
            return []

        cleaned_texts: list[str] = []
        mapping: list[int] = []
        for idx, text in enumerate(source_texts):
            if text and text.strip():
                cleaned_texts.append(text.strip())
                mapping.append(idx)

        if not cleaned_texts:
            return [GuardrailResult(text="", label="NOT_EVALUATED", score=0.0, flagged=False) for _ in source_texts]

        try:  # pragma: no cover - optional dependency
            raw = self._pipeline(cleaned_texts, batch_size=4)
        except Exception as exc:
            logger.debug("Guardrail evaluation failed: %s", exc)
            return [GuardrailResult(text="", label="NOT_EVALUATED", score=0.0, flagged=False) for _ in source_texts]

        results: list[GuardrailResult] = [
            GuardrailResult(text="", label="NOT_EVALUATED", score=0.0, flagged=False)
            for _ in source_texts
        ]

        for idx, (text, item) in zip(mapping, zip(cleaned_texts, raw, strict=False), strict=False):
            label = item.get("label", "SAFE")
            score = float(item.get("score", 0.0))
            flagged = label.lower() not in {"safe", "non_toxic"} and score >= self.threshold
            results[idx] = GuardrailResult(text=text, label=label, score=score, flagged=flagged)

        return results


_guardrail_singleton: HuggingFaceGuardrail | None = None
_guardrail_initialized = False


def get_guardrail_checker(model_name: str, threshold: float) -> HuggingFaceGuardrail | None:
    global _guardrail_initialized, _guardrail_singleton

    if _guardrail_initialized:
        return _guardrail_singleton

    _guardrail_initialized = True
    checker = HuggingFaceGuardrail(model_name=model_name, threshold=threshold)
    _guardrail_singleton = checker if checker.is_ready else None
    return _guardrail_singleton

