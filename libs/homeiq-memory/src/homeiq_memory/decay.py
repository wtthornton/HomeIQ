"""Confidence and decay engine for HomeIQ Memory Brain.

Implements exponential decay based on memory type half-lives, confidence
reinforcement from confirming observations, and access tracking.

Based on Mem0's consolidation architecture adapted for IoT behavioral data.
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Memory

from .models import MemoryType

HALF_LIVES: dict[MemoryType, int | None] = {
    MemoryType.BEHAVIORAL: 90,  # days
    MemoryType.PREFERENCE: 180,
    MemoryType.BOUNDARY: None,  # never decays
    MemoryType.OUTCOME: 120,
    MemoryType.ROUTINE: None,  # replaced, not decayed
}

MAX_CONFIDENCE = 0.95
ACCESS_CONFIDENCE_BUMP = 0.02


def effective_confidence(memory: "Memory") -> float:
    """Calculate confidence with exponential decay based on memory type.

    Applies time-based decay using the formula:
        effective = confidence * 0.5 ** (days_since_update / half_life)

    Args:
        memory: Memory instance with confidence, memory_type, and updated_at.

    Returns:
        Decayed confidence value. Returns original confidence if memory type
        has no decay (boundary, routine).
    """
    half_life = HALF_LIVES.get(memory.memory_type)
    if half_life is None:
        return memory.confidence

    now = datetime.now(UTC)
    days_since_update = (now - memory.updated_at).total_seconds() / 86400
    decay_factor = 0.5 ** (days_since_update / half_life)
    return memory.confidence * decay_factor


def reinforce(memory: "Memory", amount: float = 0.1) -> "Memory":
    """Increase confidence from a confirming observation.

    Called when behavior/preference is observed again, reinforcing the memory.

    Args:
        memory: Memory instance to reinforce.
        amount: Confidence increase (default 0.1).

    Returns:
        Modified memory with bumped confidence (capped at 0.95) and
        updated timestamp.
    """
    new_confidence = min(memory.confidence + amount, MAX_CONFIDENCE)
    memory.confidence = new_confidence
    memory.updated_at = datetime.now(UTC)
    return memory


def record_access(memory: "Memory") -> "Memory":
    """Record that memory was retrieved and found useful.

    Increments access count and optionally bumps confidence by 0.02.
    Access tracking helps identify frequently-used memories.

    Args:
        memory: Memory instance that was accessed.

    Returns:
        Modified memory with incremented access_count, updated last_accessed,
        and small confidence bump.
    """
    memory.access_count += 1
    memory.last_accessed = datetime.now(UTC)
    memory.confidence = min(memory.confidence + ACCESS_CONFIDENCE_BUMP, MAX_CONFIDENCE)
    return memory


def should_archive(memory: "Memory", threshold: float = 0.15) -> bool:
    """Determine if memory should be moved to archive.

    Memories with effective confidence below threshold are candidates for
    garbage collection and archival.

    Args:
        memory: Memory instance to evaluate.
        threshold: Minimum effective confidence to remain active (default 0.15).

    Returns:
        True if memory should be archived (effective_confidence < threshold).
    """
    return effective_confidence(memory) < threshold


def contradict(memory: "Memory", new_confidence: float = 0.1) -> "Memory":
    """Mark memory as contradicted by newer information.

    Sets confidence to a low value. Caller is responsible for setting
    superseded_by to link to the contradicting memory.

    Args:
        memory: Memory instance that was contradicted.
        new_confidence: Confidence value to set (default 0.1).

    Returns:
        Modified memory with reduced confidence.
    """
    memory.confidence = new_confidence
    return memory
