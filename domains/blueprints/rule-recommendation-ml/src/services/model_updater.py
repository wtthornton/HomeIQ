"""
Incremental model update service.

When enough feedback accumulates, retrains the RuleRecommender
using the original interaction matrix augmented with feedback signals.
Runs as a background ``asyncio`` task so the API response is not blocked.
"""

import asyncio
import logging
from collections import defaultdict
from pathlib import Path

from scipy.sparse import csr_matrix, lil_matrix

from ..data.feedback_store import POSITIVE_FEEDBACK_TYPES, FeedbackStore
from ..models.rule_recommender import RuleRecommender

logger = logging.getLogger(__name__)

# How many new feedback items must accumulate before a retrain is triggered
DEFAULT_RETRAIN_THRESHOLD = 50

# Module-level lock to prevent concurrent retrains
_retrain_lock = asyncio.Lock()


async def maybe_trigger_retrain(
    feedback_store: FeedbackStore,
    recommender: RuleRecommender,
    model_path: Path,
    *,
    threshold: int = DEFAULT_RETRAIN_THRESHOLD,
) -> bool:
    """Check feedback count and spawn a background retrain if threshold met.

    Returns ``True`` if a retrain task was launched.
    """
    if not recommender._is_fitted:
        logger.debug("Model not fitted yet -- skipping retrain check")
        return False

    count = await feedback_store.count_since_last_retrain()
    if count < threshold:
        logger.debug(
            "Only %d feedback items since last retrain (threshold=%d)",
            count,
            threshold,
        )
        return False

    logger.info(
        "Feedback threshold reached (%d >= %d) -- scheduling retrain",
        count,
        threshold,
    )
    asyncio.create_task(_run_retrain(feedback_store, recommender, model_path))
    return True


async def _run_retrain(
    feedback_store: FeedbackStore,
    recommender: RuleRecommender,
    model_path: Path,
) -> None:
    """Execute the actual retrain in a background task.

    The heavy lifting (matrix construction + ALS fit) is offloaded to a
    thread via ``asyncio.to_thread`` so the event loop stays responsive.
    """
    if _retrain_lock.locked():
        logger.info("Retrain already in progress -- skipping")
        return

    feedback_count = 0
    async with _retrain_lock:
        try:
            all_feedback = await feedback_store.get_all_feedback()
            feedback_count = len(all_feedback)
            logger.info("Starting incremental retrain with %d feedback items", feedback_count)

            await feedback_store.log_retrain(feedback_count, "started")

            # Offload CPU-bound work to a thread
            await asyncio.to_thread(
                _apply_feedback_and_fit,
                recommender,
                all_feedback,
                model_path,
            )

            await feedback_store.log_retrain(feedback_count, "completed")
            logger.info("Incremental retrain completed successfully")

        except Exception:
            logger.exception("Incremental retrain failed")
            try:
                await feedback_store.log_retrain(feedback_count, "failed")
            except Exception:
                logger.exception("Failed to log retrain failure")


# ---------------------------------------------------------------------------
# CPU-bound helpers (run in worker thread)
# ---------------------------------------------------------------------------


def _aggregate_signals(
    feedback_rows: list[dict],
) -> dict[tuple[str, str], float]:
    """Aggregate feedback rows into per-(user, pattern) weight signals."""
    signals: dict[tuple[str, str], float] = defaultdict(float)
    for row in feedback_rows:
        user_id = row.get("user_id")
        pattern = row.get("rule_pattern")
        if not user_id or not pattern:
            continue

        feedback_type = row.get("feedback_type", "")
        rating = row.get("rating")

        if feedback_type in POSITIVE_FEEDBACK_TYPES:
            weight = rating / 5.0 if rating is not None else 1.0
            signals[(user_id, pattern)] += weight
        elif feedback_type == "rejected":
            signals[(user_id, pattern)] -= 0.5

    return dict(signals)


def _resolve_index(
    key: str,
    existing_map: dict[str, int],
    new_map: dict[str, int],
    base_offset: int,
) -> int:
    """Return the matrix index for *key*, creating a new one if needed."""
    if key in existing_map:
        return existing_map[key]
    if key in new_map:
        return new_map[key]
    idx = base_offset + len(new_map)
    new_map[key] = idx
    return idx


def _build_augmented_matrix(
    recommender: RuleRecommender,
    signals: dict[tuple[str, str], float],
) -> tuple[csr_matrix, dict[int, str], dict[int, str]]:
    """Expand the interaction matrix with feedback signals and return it."""
    matrix = recommender._user_items.copy().tolil()
    rows, cols = matrix.shape

    new_users: dict[str, int] = {}
    new_patterns: dict[str, int] = {}

    # Resolve indices and apply weights in a single pass
    for (user_id, pattern), weight in signals.items():
        u_idx = _resolve_index(user_id, recommender.user_to_idx, new_users, rows)
        p_idx = _resolve_index(pattern, recommender.pattern_to_idx, new_patterns, cols)

        # Expand matrix lazily when new rows/cols are needed
        if u_idx >= matrix.shape[0] or p_idx >= matrix.shape[1]:
            expanded = lil_matrix((
                max(matrix.shape[0], u_idx + 1),
                max(matrix.shape[1], p_idx + 1),
            ))
            expanded[:matrix.shape[0], :matrix.shape[1]] = matrix
            matrix = expanded

        current = matrix[u_idx, p_idx]
        matrix[u_idx, p_idx] = max(0.0, current + weight)

    # Merge mappings
    idx_to_user = dict(recommender.idx_to_user)
    idx_to_pattern = dict(recommender.idx_to_pattern)
    for uid, idx in new_users.items():
        idx_to_user[idx] = uid
    for pat, idx in new_patterns.items():
        idx_to_pattern[idx] = pat

    logger.info(
        "Augmented matrix: %d users x %d patterns "
        "(%d new users, %d new patterns, %d signals)",
        matrix.shape[0],
        matrix.shape[1],
        len(new_users),
        len(new_patterns),
        len(signals),
    )

    return csr_matrix(matrix), idx_to_user, idx_to_pattern


def _apply_feedback_and_fit(
    recommender: RuleRecommender,
    feedback_rows: list[dict],
    model_path: Path,
) -> None:
    """Build updated interaction matrix from feedback and retrain.

    This runs in a worker thread -- no ``await`` allowed.

    Strategy:
    - Start from the existing ``_user_items`` sparse matrix.
    - For each feedback row, boost (positive) or dampen (negative) the
      corresponding user-pattern cell.
    - Refit the ALS model with the augmented matrix.
    - Save the updated model to disk.
    """
    if recommender._user_items is None:
        logger.warning("No existing interaction matrix -- cannot apply feedback")
        return

    signals = _aggregate_signals(feedback_rows)
    if not signals:
        logger.info("No actionable feedback signals -- skipping retrain")
        return

    augmented_csr, idx_to_user, idx_to_pattern = _build_augmented_matrix(
        recommender, signals,
    )

    recommender.fit(augmented_csr, idx_to_user, idx_to_pattern)
    recommender.save(model_path)

    logger.info("Updated model saved to %s", model_path)
