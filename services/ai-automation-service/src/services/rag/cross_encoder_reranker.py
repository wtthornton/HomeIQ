"""
Cross-Encoder Reranking for Improved Search Results

Uses cross-encoder models to rerank initial retrieval results.
Cross-encoders are more accurate than bi-encoders but slower,
so they're used for final reranking of top candidates.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Try to import sentence-transformers for cross-encoder
try:
    from sentence_transformers import CrossEncoder
    CROSS_ENCODER_AVAILABLE = True
except ImportError:
    CROSS_ENCODER_AVAILABLE = False
    logger.warning("sentence-transformers not available, cross-encoder reranking disabled")


class CrossEncoderReranker:
    """
    Cross-encoder reranker for final result ranking.

    Cross-encoders process query-document pairs together,
    providing more accurate relevance scores than bi-encoders.
    """

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        """
        Initialize cross-encoder reranker.

        Args:
            model_name: HuggingFace model name for cross-encoder
                       Default: ms-marco-MiniLM-L-6-v2 (fast, good accuracy)
        """
        self.model_name = model_name
        self.model: Any | None = None

        if not CROSS_ENCODER_AVAILABLE:
            logger.warning("Cross-encoder reranking disabled (sentence-transformers not available)")
            return

        try:
            logger.info(f"Loading cross-encoder model: {model_name}")
            self.model = CrossEncoder(model_name, max_length=512)
            logger.info("Cross-encoder model loaded successfully")
        except Exception as e:
            logger.exception(f"Failed to load cross-encoder model: {e}")
            self.model = None

    def rerank(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        top_k: int | None = None,
        text_field: str = "text",
    ) -> list[dict[str, Any]]:
        """
        Rerank candidates using cross-encoder.

        Args:
            query: Query text
            candidates: List of candidate documents (with scores from initial retrieval)
            top_k: Number of top results to return (None = return all)
            text_field: Field name containing text to rerank

        Returns:
            Reranked list of candidates with cross-encoder scores
        """
        if not self.model or not candidates:
            logger.debug("Cross-encoder not available or no candidates, returning original order")
            return candidates

        if len(candidates) == 0:
            return []

        try:
            # Prepare query-document pairs
            pairs = []
            for candidate in candidates:
                text = candidate.get(text_field, "")
                pairs.append([query, text])

            # Get cross-encoder scores (batch processing)
            scores = self.model.predict(pairs)

            # Add scores to candidates
            reranked = []
            for i, candidate in enumerate(candidates):
                reranked_candidate = candidate.copy()
                reranked_candidate["cross_encoder_score"] = float(scores[i])
                reranked.append(reranked_candidate)

            # Sort by cross-encoder score (descending)
            reranked.sort(key=lambda x: x.get("cross_encoder_score", 0.0), reverse=True)

            # Return top_k if specified
            if top_k is not None:
                reranked = reranked[:top_k]

            logger.debug(
                f"Reranked {len(candidates)} candidates → {len(reranked)} results "
                f"(top score: {reranked[0].get('cross_encoder_score', 0.0):.3f})",
            )

            return reranked

        except Exception as e:
            logger.exception(f"Error during cross-encoder reranking: {e}")
            # Return original candidates on error
            return candidates

    def rerank_with_hybrid_score(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        top_k: int | None = None,
        text_field: str = "text",
        cross_encoder_weight: float = 0.7,
        original_score_weight: float = 0.3,
    ) -> list[dict[str, Any]]:
        """
        Rerank candidates combining cross-encoder scores with original scores.

        Args:
            query: Query text
            candidates: List of candidate documents
            top_k: Number of top results to return
            text_field: Field name containing text
            cross_encoder_weight: Weight for cross-encoder score (default: 0.7)
            original_score_weight: Weight for original score (default: 0.3)

        Returns:
            Reranked candidates with combined scores
        """
        if not self.model or not candidates:
            return candidates

        try:
            # Get cross-encoder scores
            reranked = self.rerank(query, candidates, top_k=None, text_field=text_field)

            # Normalize scores to [0, 1] range
            max_cross_score = max(
                (c.get("cross_encoder_score", 0.0) for c in reranked),
                default=1.0,
            )

            # Get original score field (could be 'similarity', 'hybrid_score', etc.)
            original_score_fields = ["hybrid_score", "similarity", "bm25_score"]
            max_original_score = 0.0

            for field in original_score_fields:
                max_field_score = max(
                    (c.get(field, 0.0) for c in reranked),
                    default=0.0,
                )
                max_original_score = max(max_original_score, max_field_score)

            if max_original_score == 0.0:
                max_original_score = 1.0

            # Combine scores
            for candidate in reranked:
                cross_score = candidate.get("cross_encoder_score", 0.0)
                original_score = 0.0

                # Find original score
                for field in original_score_fields:
                    if field in candidate:
                        original_score = candidate[field]
                        break

                # Normalize
                norm_cross = cross_score / max_cross_score if max_cross_score > 0 else 0.0
                norm_original = original_score / max_original_score if max_original_score > 0 else 0.0

                # Weighted combination
                combined_score = (cross_encoder_weight * norm_cross) + (original_score_weight * norm_original)
                candidate["final_score"] = combined_score

            # Sort by final score
            reranked.sort(key=lambda x: x.get("final_score", 0.0), reverse=True)

            if top_k is not None:
                reranked = reranked[:top_k]

            logger.debug(
                f"Hybrid reranking: {len(candidates)} candidates → {len(reranked)} results "
                f"(final top score: {reranked[0].get('final_score', 0.0):.3f})",
            )

            return reranked

        except Exception as e:
            logger.exception(f"Error during hybrid reranking: {e}")
            return candidates

