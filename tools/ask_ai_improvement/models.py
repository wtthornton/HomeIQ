"""
Data models for Ask AI continuous improvement.
"""
from dataclasses import dataclass, field
from typing import Any, List, Optional
from datetime import datetime


@dataclass
class PromptResult:
    """Result of processing a single prompt."""
    prompt_id: str
    prompt: str
    query_id: Optional[str] = None
    clarification_rounds: int = 0
    suggestions_count: int = 0
    selected_suggestion_id: Optional[str] = None
    automation_yaml: Optional[str] = None
    score: float = 0.0
    automation_score: float = 0.0
    yaml_score: float = 0.0
    clarification_score: float = 0.0
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class CycleResult:
    """Result of a complete improvement cycle."""
    cycle_number: int
    prompt_results: List[PromptResult] = field(default_factory=list)
    total_score: float = 0.0
    average_score: float = 0.0
    improvements_made: bool = False
    deployment_successful: bool = False
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

