"""
Centralized fuzzy matching utilities using rapidfuzz.

2025 Best Practices:
- Module-level import with availability check
- Multiple algorithm combination (WRatio)
- Batch processing with process.extract()
- Normalized 0.0-1.0 confidence scores
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Module-level import check
RAPIDFUZZ_AVAILABLE = False
try:
    from rapidfuzz import fuzz, process
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    logger.warning("rapidfuzz not available, fuzzy matching disabled")

# Default configuration
DEFAULT_THRESHOLD = 0.7
DEFAULT_SCORER = fuzz.WRatio if RAPIDFUZZ_AVAILABLE else None


def fuzzy_score(
    query: str,
    candidate: str,
    scorer: Any = None,
    threshold: float = DEFAULT_THRESHOLD
) -> float:
    """
    Calculate fuzzy similarity score between query and candidate.
    
    Uses WRatio (weighted ratio) which combines multiple algorithms:
    - token_sort_ratio (order-independent)
    - partial_ratio (substring matching)
    - token_set_ratio (set-based matching)
    
    Args:
        query: Query string
        candidate: Candidate string to match
        scorer: Optional rapidfuzz scorer (default: WRatio)
        threshold: Minimum score to return (default: 0.7)
        
    Returns:
        Normalized score 0.0-1.0, or 0.0 if below threshold
        
    Examples:
        >>> fuzzy_score("office lite", "office light")
        0.95  # Handles typos
        
        >>> fuzzy_score("LR light", "Living Room Light")
        0.85  # Handles abbreviations
        
        >>> fuzzy_score("light living room", "living room light")
        1.0  # Order-independent matching
    """
    if not RAPIDFUZZ_AVAILABLE:
        # Fallback to simple substring matching
        query_lower = query.lower()
        candidate_lower = candidate.lower()
        if query_lower == candidate_lower:
            return 1.0
        if query_lower in candidate_lower or candidate_lower in query_lower:
            return 0.7
        return 0.0
    
    if not candidate:
        return 0.0
    
    if scorer is None:
        scorer = DEFAULT_SCORER
    
    # Use WRatio for best overall matching
    score = scorer(query.lower(), candidate.lower()) / 100.0
    
    # Apply threshold
    return score if score >= threshold else 0.0


def fuzzy_match_best(
    query: str,
    candidates: list[str],
    threshold: float = DEFAULT_THRESHOLD,
    limit: int = 1
) -> list[tuple[str, float]]:
    """
    Find best fuzzy matches from candidate list.
    
    Uses rapidfuzz.process.extract() for efficient batch matching.
    
    Args:
        query: Query string
        candidates: List of candidate strings
        threshold: Minimum score (0.0-1.0)
        limit: Maximum number of results (default: 1)
        
    Returns:
        List of (candidate, score) tuples, sorted by score (highest first)
        
    Examples:
        >>> fuzzy_match_best("office light", ["office light", "office lamp", "kitchen light"])
        [("office light", 1.0)]
        
        >>> fuzzy_match_best("LR light", ["Living Room Light", "Living Room Lamp"], limit=2)
        [("Living Room Light", 0.85), ("Living Room Lamp", 0.75)]
    """
    if not RAPIDFUZZ_AVAILABLE:
        # Fallback to simple matching
        query_lower = query.lower()
        results = []
        for candidate in candidates:
            candidate_lower = candidate.lower()
            if query_lower == candidate_lower:
                results.append((candidate, 1.0))
            elif query_lower in candidate_lower or candidate_lower in query_lower:
                results.append((candidate, 0.7))
        return results[:limit]
    
    if not candidates:
        return []
    
    # Use process.extract() for efficient batch matching
    matches = process.extract(
        query,
        candidates,
        scorer=fuzz.WRatio,
        limit=limit,
        score_cutoff=int(threshold * 100)  # Convert to 0-100 range
    )
    
    # Normalize scores to 0.0-1.0
    return [(match[0], match[1] / 100.0) for match in matches]


def fuzzy_match_with_context(
    query: str,
    candidate: str,
    context_bonuses: dict[str, float] | None = None
) -> float:
    """
    Calculate fuzzy score with domain-specific context bonuses.
    
    Combines rapidfuzz base score with context-aware bonuses:
    - Location matches
    - Device type matches
    - Domain-specific patterns
    
    Args:
        query: Query string
        candidate: Candidate string
        context_bonuses: Optional dict of bonus factors (e.g., {'location': 0.2})
        
    Returns:
        Enhanced score 0.0-1.0 (capped at 1.0)
        
    Examples:
        >>> fuzzy_match_with_context("office light", "office light", {'location': 0.1})
        1.0  # Base score 1.0 + bonus capped at 1.0
        
        >>> fuzzy_match_with_context("light", "office light", {'location': 0.2})
        0.9  # Base score 0.7 + 0.2 bonus
    """
    base_score = fuzzy_score(query, candidate, threshold=0.0)  # Get raw score
    
    if not context_bonuses:
        return base_score
    
    # Apply context bonuses (additive, capped at 1.0)
    enhanced_score = base_score
    for bonus_type, bonus_value in context_bonuses.items():
        enhanced_score += bonus_value
    
    return min(enhanced_score, 1.0)

