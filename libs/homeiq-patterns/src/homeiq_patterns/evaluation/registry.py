"""
Agent Evaluation Framework — EvaluationRegistry & Pipeline Orchestration

Loads an agent's YAML config and instantiates the correct evaluators
into an evaluation pipeline. Running a full 5-level evaluation is a
single call: ``registry.evaluate(session)``.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .base_evaluator import BaseEvaluator
from .config import AgentEvalConfig, ConfigLoader
from .llm_judge import LLMJudge
from .models import BatchReport, EvaluationReport, SessionTrace
from .scoring_engine import ScoringEngine

logger = logging.getLogger(__name__)

# Rubric directory for quality/safety evaluators
_RUBRICS_DIR = Path(__file__).resolve().parent / "rubrics"


class EvaluationRegistry:
    """
    Registry that loads agent configs and instantiates evaluators.

    Usage::

        registry = EvaluationRegistry()
        registry.register_agent(config)
        report = await registry.evaluate(session)
    """

    # Deploy-dependent evaluators that correctly score 0% in preview mode.
    # Skipping them in preview avoids dragging the L4 average down.
    _DEPLOY_ONLY_EVALUATORS = frozenset({
        "validation_before_deploy",
        "post_deploy_verification",
        "audit_trail_complete",
    })

    def __init__(
        self,
        llm_judge: LLMJudge | None = None,
    ):
        self._judge = llm_judge or LLMJudge()
        self._agents: dict[str, _AgentEntry] = {}

    def register_agent(self, config: AgentEvalConfig) -> None:
        """Register an agent's evaluation config and instantiate evaluators."""
        evaluators = self._build_evaluators(config)
        thresholds = config.thresholds or {}
        engine = ScoringEngine(thresholds=thresholds)
        self._agents[config.agent_name] = _AgentEntry(
            config=config,
            evaluators=evaluators,
            engine=engine,
        )
        logger.info(
            "Registered agent '%s' with %d evaluators",
            config.agent_name,
            len(evaluators),
        )

    def register_from_yaml(self, path: str | Path) -> None:
        """Load a YAML config file and register the agent."""
        config = ConfigLoader.load(path)
        self.register_agent(config)

    @property
    def registered_agents(self) -> list[str]:
        """List names of all registered agents."""
        return list(self._agents.keys())

    def get_evaluators(self, agent_name: str) -> list[BaseEvaluator]:
        """Get the evaluators for a registered agent."""
        entry = self._agents.get(agent_name)
        if entry is None:
            raise KeyError(f"Agent '{agent_name}' not registered")
        return list(entry.evaluators)

    async def evaluate(self, session: SessionTrace) -> EvaluationReport:
        """Run all registered evaluators for the session's agent."""
        agent_name = session.agent_name
        entry = self._agents.get(agent_name)
        if entry is None:
            raise KeyError(
                f"Agent '{agent_name}' not registered. "
                f"Registered: {self.registered_agents}"
            )

        evaluators = entry.evaluators

        # Enhancement A: skip deploy-dependent evaluators in preview mode
        # so they don't drag L4 average down with correct-but-irrelevant 0%s.
        if session.metadata.get("execution_mode") == "preview":
            evaluators = [
                e for e in evaluators
                if e.name not in self._DEPLOY_ONLY_EVALUATORS
            ]

        return await entry.engine.score(session, evaluators)

    async def evaluate_batch(
        self,
        sessions: list[SessionTrace],
    ) -> BatchReport:
        """Run evaluators on a batch of sessions (all same agent)."""
        if not sessions:
            return BatchReport()

        agent_name = sessions[0].agent_name
        entry = self._agents.get(agent_name)
        if entry is None:
            raise KeyError(f"Agent '{agent_name}' not registered")

        return await entry.engine.score_batch(sessions, entry.evaluators)

    def _build_evaluators(
        self,
        config: AgentEvalConfig,
    ) -> list[BaseEvaluator]:
        """Instantiate evaluators based on the agent's config."""
        evaluators: list[BaseEvaluator] = []

        # L1 Outcome: always include GoalSuccessRate
        evaluators.extend(self._build_l1_evaluators(config))

        # L2 Path: if paths are defined
        evaluators.extend(self._build_l2_evaluators(config))

        # L3 Details: if parameter_rules are defined
        evaluators.extend(self._build_l3_evaluators(config))

        # L4 Quality: from quality_rubrics + system_prompt_rules
        evaluators.extend(self._build_l4_evaluators(config))

        # L5 Safety: from safety_rubrics
        evaluators.extend(self._build_l5_evaluators(config))

        return evaluators

    def _build_l1_evaluators(
        self, config: AgentEvalConfig
    ) -> list[BaseEvaluator]:
        """Build L1 Outcome evaluators.

        Enables ``metadata_success_signals`` when the agent config has
        pipeline-related tools (create_plan, compile_yaml), indicating
        a structured pipeline that writes concrete outcome metadata.
        """
        from .evaluators.l1_outcome import GoalSuccessRateEvaluator

        # Auto-detect pipeline agents that emit metadata success signals
        tool_names = {t.name for t in config.tools} if config.tools else set()
        use_metadata = bool(tool_names & {"create_plan", "compile_yaml"})

        return [
            GoalSuccessRateEvaluator(
                llm_judge=self._judge,
                metadata_success_signals=use_metadata,
            )
        ]

    def _build_l2_evaluators(
        self, config: AgentEvalConfig
    ) -> list[BaseEvaluator]:
        """Build L2 Path evaluators from config paths and tools."""
        if not config.paths and not config.tools:
            return []

        from .evaluators.l2_path import (
            ToolSelectionAccuracyEvaluator,
            ToolSequenceValidatorEvaluator,
        )

        evals: list[BaseEvaluator] = []

        if config.tools:
            evals.append(
                ToolSelectionAccuracyEvaluator(
                    config=config, llm_judge=self._judge
                )
            )

        if config.paths:
            evals.append(
                ToolSequenceValidatorEvaluator(
                    config=config, llm_judge=self._judge
                )
            )

        # Story 3.4: Template appropriateness evaluator (always included)
        from .evaluators.l2_template_match import (
            TemplateAppropriatenessEvaluator,
        )

        evals.append(
            TemplateAppropriatenessEvaluator(llm_judge=self._judge)
        )

        return evals

    def _build_l3_evaluators(
        self, config: AgentEvalConfig
    ) -> list[BaseEvaluator]:
        """Build L3 Details evaluators from config parameter_rules."""
        evals: list[BaseEvaluator] = []

        if config.parameter_rules or config.tools:
            from .evaluators.l3_details import ToolParameterAccuracyEvaluator

            evals.append(
                ToolParameterAccuracyEvaluator(
                    config=config, llm_judge=self._judge
                )
            )

        # Story 3.4: HA-specific deterministic evaluators (always included)
        from .evaluators.l3_yaml_completeness import YAMLCompletenessEvaluator
        from .evaluators.l3_entity_resolution import EntityResolutionEvaluator

        evals.append(YAMLCompletenessEvaluator())
        evals.append(EntityResolutionEvaluator())

        return evals

    def _build_l4_evaluators(
        self, config: AgentEvalConfig
    ) -> list[BaseEvaluator]:
        """Build L4 Quality evaluators from quality_rubrics + system_prompt_rules."""
        from .evaluators.l4_quality import (
            CoherenceEvaluator,
            ConcisenessEvaluator,
            CorrectnessEvaluator,
            FaithfulnessEvaluator,
            HelpfulnessEvaluator,
            InstructionFollowingEvaluator,
            ResponseRelevanceEvaluator,
            SystemPromptRuleEvaluator,
        )

        # Map rubric name → evaluator class
        quality_map: dict[str, type[BaseEvaluator]] = {
            "correctness": CorrectnessEvaluator,
            "faithfulness": FaithfulnessEvaluator,
            "coherence": CoherenceEvaluator,
            "helpfulness": HelpfulnessEvaluator,
            "conciseness": ConcisenessEvaluator,
            "response_relevance": ResponseRelevanceEvaluator,
        }

        evals: list[BaseEvaluator] = []
        for rubric_name in config.quality_rubrics:
            if rubric_name == "instruction_following":
                evals.append(
                    InstructionFollowingEvaluator(
                        llm_judge=self._judge,
                        system_prompt=config.system_prompt,
                    )
                )
                continue
            cls = quality_map.get(rubric_name)
            if cls is not None:
                evals.append(cls(llm_judge=self._judge))  # type: ignore[call-arg]
            else:
                logger.warning(
                    "Unknown quality rubric '%s' — skipping", rubric_name
                )

        # System prompt rule evaluators (one per rule)
        for rule in config.system_prompt_rules:
            evals.append(
                SystemPromptRuleEvaluator(rule=rule, llm_judge=self._judge)
            )

        return evals

    def _build_l5_evaluators(
        self, config: AgentEvalConfig
    ) -> list[BaseEvaluator]:
        """Build L5 Safety evaluators from safety_rubrics config."""
        from .evaluators.l5_safety import (
            HarmfulnessEvaluator,
            RefusalEvaluator,
            StereotypingEvaluator,
        )

        safety_map: dict[str, type[BaseEvaluator]] = {
            "harmfulness": HarmfulnessEvaluator,
            "stereotyping": StereotypingEvaluator,
            "refusal": RefusalEvaluator,
        }

        evals: list[BaseEvaluator] = []
        for rubric_name in config.safety_rubrics:
            cls = safety_map.get(rubric_name)
            if cls is not None:
                evals.append(cls(llm_judge=self._judge))  # type: ignore[call-arg]
            else:
                logger.warning(
                    "Unknown safety rubric '%s' — skipping", rubric_name
                )

        return evals


class _AgentEntry:
    """Internal container for a registered agent."""

    __slots__ = ("config", "evaluators", "engine")

    def __init__(
        self,
        config: AgentEvalConfig,
        evaluators: list[BaseEvaluator],
        engine: ScoringEngine,
    ):
        self.config = config
        self.evaluators = evaluators
        self.engine = engine
