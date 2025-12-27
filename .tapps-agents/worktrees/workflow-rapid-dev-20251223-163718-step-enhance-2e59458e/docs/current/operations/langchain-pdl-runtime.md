# LangChain & PDL Runtime Operations

**Last Updated:** 2025-11-10  
**Service:** `ai-automation-service`

## Feature Flags

Environment variables (via `config.Settings`) guard each integration so the default
single-home deployment remains lightweight:

| Flag | Default | Description |
| ---- | ------- | ----------- |
| `ENABLE_LANGCHAIN_PROMPT_BUILDER` (`enable_langchain_prompt_builder`) | `False` | Wrap Ask-AI prompt construction with LangChain templates. |
| `ENABLE_LANGCHAIN_PATTERN_CHAIN` (`enable_langchain_pattern_chain`) | `False` | Route time-of-day + co-occurrence detectors through a LangChain runnable chain. |
| `ENABLE_PDL_WORKFLOWS` (`enable_pdl_workflows`) | `False` | Execute PDL guardrail scripts for nightly batch and synergy detection. |
| `ENABLE_SELF_IMPROVEMENT_PILOT` (`enable_self_improvement_pilot`) | `False` | Generate weekly prompt tuning reports using LangChain templating. |

Set the corresponding environment variables (upper snake-case) to `true` to enable.

## Operational Notes

### Ask-AI Prompt Chain
- Located in `langchain_integration/ask_ai_chain.py`.
- Applies only to new queries; existing flows fall back automatically on error.
- Adds metadata to prompt dict (`metadata.langchain`) to aid debugging.

### Pattern Detection Chain
- Implements LangChain runner in `langchain_integration/pattern_chain.py`.
- When enabled, scheduler logs `🧱 LangChain pattern chain executed...`.
- Any failure reverts to the legacy detector pipeline with a warning.

### PDL Guardrails
- Interpreter lives in `pdl/runtime.py`.
- Scripts stored in `pdl/scripts/nightly_batch.yaml` and `pdl/scripts/synergy_guardrails.yaml`.
- Nightly batch script warns on MQTT or incremental mode issues; synergy guardrails abort if chain depth exceeds supported limits.

### Self-Improvement Pilot
- Weekly review runs inside `DailyAnalysisScheduler` (Mondays only) when `enable_self_improvement_pilot` is true.
- Metrics collected from `ask_ai_queries` and summarised via `langchain_integration/self_improvement.py`.
- Manual workflow script: `python scripts/run_self_improvement_pilot.py` (writes report to `implementation/analysis/self_improvement_pilot_report.md`).
- Recommendations are logged but not applied automatically; operators must review and adjust configuration manually.

## Cleanup Expectations

- Deprecated orchestration code is untouched; feature flags ensure new integrations can be disabled without redeploy.
- Dependency footprint remains limited to `langchain==0.2.7`; no vector/DB extras required.
- Logs clearly differentiate LangChain/PDL paths for operators.

## Verification Checklist

1. Toggle desired flag(s) in `infrastructure/env.ai-automation`.
2. Restart `ai-automation-service`.
3. Monitor service logs for:
   - `🧱 LangChain pattern chain executed...` (pattern chain active)
   - `🧱 LangChain prompt builder applied...` (Ask-AI chain active)
   - `📜 Executing PDL script ...` (PDL guardrails running)
4. Revert flag to `false` and restart to disable integrations.


