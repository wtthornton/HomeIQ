"""Lightweight Hugging Face soft prompt fallback for Ask AI suggestions."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class SoftPromptAdapter:
    """Wraps a locally fine-tuned Hugging Face model for low-cost refinements."""

    def __init__(self, model_dir: str, max_new_tokens: int = 120) -> None:
        self.model_path = Path(model_dir)
        self.max_new_tokens = max_new_tokens
        self._pipeline = None
        self._model_id = None

        if not self.model_path.exists():
            logger.info("Soft prompt directory %s not found; adapter disabled", self.model_path)
            return

        try:  # pragma: no cover - optional dependency
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, pipeline

            tokenizer = AutoTokenizer.from_pretrained(self.model_path)
            model = AutoModelForSeq2SeqLM.from_pretrained(self.model_path)
            self._pipeline = pipeline(
                "text2text-generation",
                model=model,
                tokenizer=tokenizer,
                device=-1
            )
            self._model_id = getattr(model.config, "name_or_path", str(self.model_path))
            logger.info("Soft prompt adapter initialized with model %s", self._model_id)
        except Exception as exc:
            logger.warning("Unable to initialize soft prompt adapter: %s", exc)
            self._pipeline = None

    @property
    def is_ready(self) -> bool:
        """Return True when the adapter has a usable generation pipeline."""
        return self._pipeline is not None

    @property
    def model_id(self) -> Optional[str]:
        return self._model_id

    def enhance_suggestions(
        self,
        query: str,
        suggestions: List[Dict],
        context: Optional[str],
        threshold: float
    ) -> List[Dict]:
        """Augment low-confidence suggestions with a locally generated refinement."""
        if not self.is_ready or not suggestions:
            return suggestions

        updated: List[Dict] = []
        for suggestion in suggestions:
            confidence = float(suggestion.get("confidence", 0.0) or 0.0)
            if confidence >= threshold:
                updated.append(suggestion)
                continue

            refinement = self._generate_refinement(query, suggestion, context)
            if refinement:
                suggestion = dict(suggestion)
                suggestion["description"] = (
                    suggestion.get("description", "").rstrip()
                    + "\n\nSoft Prompt Boost: "
                    + refinement
                ).strip()
                suggestion.setdefault("metadata", {})["soft_prompt"] = {
                    "applied": True,
                    "model_id": self.model_id,
                    "confidence_before": confidence
                }
                suggestion["confidence"] = max(confidence, threshold - 0.05)

            updated.append(suggestion)

        return updated

    def _generate_refinement(
        self,
        query: str,
        suggestion: Dict,
        context: Optional[str]
    ) -> Optional[str]:
        """Generate a short refinement string using the local pipeline."""
        if not self.is_ready:
            return None

        prompt_parts = [
            "You improve Home Assistant automations for a single occupant home.",
            f"User request: {query.strip()}",
            f"Existing idea: {suggestion.get('description', '').strip()}"
        ]

        devices = suggestion.get("devices_involved") or []
        if devices:
            prompt_parts.append(f"Devices mentioned: {', '.join(devices)}")

        if context:
            prompt_parts.append("Key context:\n" + context.strip())

        prompt_parts.append(
            "Provide one concise improvement that keeps setup simple and practical."
        )

        prompt = "\n\n".join(part for part in prompt_parts if part)

        try:  # pragma: no cover - optional dependency
            output = self._pipeline(
                prompt,
                max_new_tokens=self.max_new_tokens,
                num_return_sequences=1,
                do_sample=False
            )
            if not output:
                return None
            text = output[0].get("generated_text", "").strip()
            return text if text else None
        except Exception as exc:
            logger.debug("Soft prompt generation failed: %s", exc)
            return None


_adapter_singleton: Optional[SoftPromptAdapter] = None
_adapter_initialized = False


def get_soft_prompt_adapter(model_dir: str) -> Optional[SoftPromptAdapter]:
    """Return a cached adapter instance if initialization succeeds."""
    global _adapter_singleton, _adapter_initialized

    if _adapter_initialized:
        return _adapter_singleton

    _adapter_initialized = True
    adapter = SoftPromptAdapter(model_dir=model_dir)
    if adapter.is_ready:
        _adapter_singleton = adapter
    else:
        _adapter_singleton = None
    return _adapter_singleton

