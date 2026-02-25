"""
Agent Evaluation Framework (Pattern D)

Reusable infrastructure for evaluating any AI agent against a 5-level
Evaluation Pyramid: Outcome, Path, Details, Quality, Safety.

Quick start::

    from shared.patterns.evaluation import (
        SessionTrace, SessionTracer, trace_session,
        BaseEvaluator, OutcomeEvaluator, QualityEvaluator,
        LLMJudge, JudgeRubric,
    )
"""

from .models import (
    AgentResponse,
    Alert,
    BatchReport,
    EvalAlert,
    EvalLevel,
    EvalScope,
    EvaluationReport,
    EvaluationResult,
    LevelSummary,
    MetricResult,
    SessionTrace,
    SummaryMatrix,
    ToolCall,
    UserMessage,
)
from .base_evaluator import (
    BaseEvaluator,
    DetailsEvaluator,
    OutcomeEvaluator,
    PathEvaluator,
    QualityEvaluator,
    SafetyEvaluator,
)
from .llm_judge import (
    AnthropicProvider,
    JudgeResult,
    JudgeRubric,
    LLMJudge,
    LLMProvider,
    OpenAIProvider,
)
from .session_tracer import (
    CallbackSink,
    InMemorySink,
    PersistentSink,
    SessionTracerContext,
    TraceSink,
    get_tracer_context,
    trace_session,
)
from .scoring_engine import ScoringEngine
from .registry import EvaluationRegistry
from .alerts import AlertEngine
from .scheduler import EvaluationScheduler, InMemorySessionSource, SessionSource
from .store import EvaluationStore
from .session_generator import SyntheticSessionGenerator
from .config import (
    AgentEvalConfig,
    ConfigLoader,
    ParamDef,
    ParamRule,
    PathRule,
    PriorityEntry,
    PromptRule,
    ToolDef,
)

__all__ = [
    # Models
    "AgentResponse",
    "Alert",
    "BatchReport",
    "EvalAlert",
    "EvalLevel",
    "EvalScope",
    "EvaluationReport",
    "EvaluationResult",
    "LevelSummary",
    "MetricResult",
    "SessionTrace",
    "SummaryMatrix",
    "ToolCall",
    "UserMessage",
    # Evaluator base classes
    "BaseEvaluator",
    "DetailsEvaluator",
    "OutcomeEvaluator",
    "PathEvaluator",
    "QualityEvaluator",
    "SafetyEvaluator",
    # LLM Judge
    "AnthropicProvider",
    "JudgeResult",
    "JudgeRubric",
    "LLMJudge",
    "LLMProvider",
    "OpenAIProvider",
    # Session Tracer
    "CallbackSink",
    "InMemorySink",
    "PersistentSink",
    "SessionTracerContext",
    "TraceSink",
    "get_tracer_context",
    "trace_session",
    # Scoring Engine
    "ScoringEngine",
    # Registry
    "EvaluationRegistry",
    # Scheduler (Sprint 6)
    "EvaluationScheduler",
    "InMemorySessionSource",
    "SessionSource",
    # Store (Sprint 6)
    "EvaluationStore",
    # Alerts (Sprint 6)
    "AlertEngine",
    # Session Generator (Sprint 6)
    "SyntheticSessionGenerator",
    # Config
    "AgentEvalConfig",
    "ConfigLoader",
    "ParamDef",
    "ParamRule",
    "PathRule",
    "PriorityEntry",
    "PromptRule",
    "ToolDef",
]
