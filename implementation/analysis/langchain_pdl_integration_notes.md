# LangChain & PDL Integration Discovery Notes

## Current AI Orchestration Touchpoints

- `services/ai-automation-service/src/main.py`:
  - Initializes device intelligence, MQTT, APScheduler, and model manager.
  - Registers FastAPI routers for Ask AI, conversational refinement, validation, ranking, and synergy APIs.
  - Provides global scheduler (`DailyAnalysisScheduler`) and device intelligence clients used across routers.
- `services/ai-automation-service/src/scheduler/daily_analysis.py`:
  - Runs the unified 3 AM batch (device capability refresh → event fetch → multi-detector pattern analysis → synergy detection → suggestion generation).
  - Each detector is invoked via Python methods; execution order and fallbacks are hard-coded.
  - Lack of structured orchestration metadata makes post-run auditing manual.
- `services/ai-automation-service/src/synergy_detection/`:
  - `DeviceSynergyDetector` builds pairwise → 3-device → 4-device chains with domain heuristics.
  - Caching, ranking, and validation logic are embedded inside the detector, complicating experimentation with alternative search strategies.

## Integration Constraints (Single-Home Deployment)

- **Resource footprint**: The install runs on a single Home Assistant host; new dependencies must be optional and lightweight. Feature flags are required so default behaviour remains existing Python-only flow.
- **Dependency management**: `ai-automation-service` currently relies on `requirements.txt`. Any LangChain/PDL additions must be version-pinned and avoid adding heavy transitive packages (e.g., LangChain's optional vector DB extras).
- **Async compatibility**: Scheduler and routers use `async` extensively. LangChain integrations must avoid blocking operations—use async-compatible executors or run within existing event loop.
- **Observability**: Existing logging is textual. LangChain and PDL layers need to surface status via current logging framework to keep operations familiar.
- **Rollback**: New orchestration should wrap existing detectors/routers rather than replace them outright. Fallback paths must allow immediate disablement via environment variables.

## Recommended Integration Points

- **Ask AI Prompt Management**: Replace bespoke prompt assembly with a LangChain `LLMChain` when feature flag is enabled, leveraging existing validation & deployment endpoints as tools.
- **Pattern Detection Sequencing**: Model the 3 AM detector pipeline as a LangChain SequentialChain to standardize ordering, retries, and summarization without reimplementing detector logic.
- **Synergy Procedures**: Encode the batch pipeline and chain-depth guardrails in PDL scripts, executed before calling current detector methods to provide auditable workflow traces.

These notes complete discovery tasks ahead of prototype work.


