# Epic 96: Proactive Predictive Automation

**Priority:** P2 High — 2026 Differentiator (demoted from P1: high value but largest effort, no blockers)
**Effort:** 2–3 weeks (8 stories, 34 points)
**Sprint:** 44–45
**Depends on:** None (uses existing deployed services)
**Origin:** Sapphire Review — 2026 Research Recommendation #5

## Problem Statement

HomeIQ's automation pipeline is entirely reactive: the user asks, the AI generates YAML. The user must know what they want before they get it. Meanwhile, HomeIQ already has deployed services that detect patterns, predict energy usage, and recognize activities — but they're siloed:

| Service | Port | What It Does | Status | Connected To Pipeline? |
|---------|------|-------------|--------|----------------------|
| `proactive-agent-service` | 8031 | Observe-Reason-Act loop, autonomous execution, suggestion pipeline | Production | **No** — runs independently |
| `energy-forecasting` | 8037 | NHits model, peak prediction, optimization recommendations | Production | **No** — standalone API |
| `activity-recognition` | 8036 | LSTM activity classification (sleeping, cooking, working, etc.) | Production | **No** — standalone API |
| `device-context-classifier` | 8034 | Device type classification from entity patterns | Production | **No** — standalone API |
| `websocket-ingestion` | 8001 | Real-time HA events → InfluxDB | Production | Data source only |

The opportunity: wire these services together so HomeIQ proactively suggests automations based on detected patterns, predicts energy waste, and alerts on anomalies — **before the user asks**.

Every 2026 smart home market report identifies proactive AI as the defining trend. 25–30% energy reduction is cited when predictive automation is deployed (MarketsAndMarkets, Statista, IEEE IoT Journal 2026).

## Approach

Three proactive capabilities, building on existing services:

1. **Pattern Detection → Automation Suggestion**: "You turn on office lights at 8am every weekday — want me to create that automation?"
2. **Energy Optimization Alerts**: "Tomorrow's energy peak is 2–5pm. Shift EV charging to overnight?"
3. **Anomaly Detection**: "Garage door has been open for 2 hours — notify?"

Each capability connects existing services — no new ML models needed.

---

## Story 96.1: Activity Pattern Detection Pipeline

**Points:** 5 | **Type:** Feature
**Goal:** Detect repeating user behavior patterns and generate automation suggestions

### Tasks

- [ ] **96.1.1** Create `src/services/pattern_detector.py` in `proactive-agent-service`:
  ```python
  class PatternDetector:
      """Detects repeating behavior patterns from entity state history."""

      async def detect_time_patterns(self, days: int = 14) -> list[DetectedPattern]:
          """
          Query InfluxDB for entity state changes over N days.
          Find repeating time-based patterns:
          - Same entity, same action, same time (±15min), ≥5 occurrences
          - Example: light.office turned on between 7:45-8:15 on weekdays, 10/14 days
          """
          ...

      async def detect_sequence_patterns(self) -> list[DetectedPattern]:
          """
          Find entity sequences that repeat:
          - Example: motion detected in kitchen → coffee maker turns on (within 5min)
          """
          ...
  ```
- [ ] **96.1.2** Define `DetectedPattern` dataclass:
  ```python
  @dataclass
  class DetectedPattern:
      entity_ids: list[str]        # Entities involved
      action: str                  # "turn_on", "set_temperature", etc.
      time_window: str             # "07:45-08:15" or None for sequence patterns
      days_of_week: list[str]      # ["mon", "tue", "wed", "thu", "fri"]
      occurrences: int             # How many times observed
      total_days: int              # Over how many days
      confidence: float            # 0.0-1.0
      suggested_automation: str    # Natural language description
  ```
- [ ] **96.1.3** Query InfluxDB `entity_states` measurement for state change history
- [ ] **96.1.4** Filter patterns: require ≥70% occurrence rate (e.g., 10/14 weekdays)
- [ ] **96.1.5** Add unit tests with synthetic InfluxDB data

### Acceptance Criteria

- [ ] Detects "light.office turned on at ~8am on weekdays" from 14 days of data
- [ ] Detects "thermostat set to 72°F at ~6pm daily" patterns
- [ ] Ignores one-off events (< 5 occurrences)
- [ ] Confidence score reflects consistency (10/14 = 0.71, 14/14 = 1.0)

---

## Story 96.2: Connect Activity Recognition to Proactive Agent

**Points:** 3 | **Type:** Integration
**Goal:** Proactive agent's observe phase includes real-time activity classification

### Tasks

- [ ] **96.2.1** Add `ActivityRecognitionClient` to `proactive-agent-service/src/clients/`:
  ```python
  class ActivityRecognitionClient:
      async def predict_current_activity(self) -> ActivityPrediction:
          """Call activity-recognition /api/v1/predict with recent sensor data."""
          ...
  ```
- [ ] **96.2.2** Integrate into `agent_loop.py` observe phase:
  ```python
  async def _observe(self) -> ObservationContext:
      ...
      # Add activity recognition
      activity = await self.activity_client.predict_current_activity()
      context.current_activity = activity  # "sleeping", "cooking", "working", etc.
      ...
  ```
- [ ] **96.2.3** Fetch recent sensor readings from InfluxDB (motion, door, temperature, humidity, power — last 20 readings) to feed activity-recognition model
- [ ] **96.2.4** Use activity in reasoning: "User is sleeping → suppress non-critical suggestions"
- [ ] **96.2.5** Add unit tests with mocked activity predictions

### Acceptance Criteria

- [ ] Proactive agent observe phase includes current activity
- [ ] Activity "sleeping" suppresses non-critical suggestions (energy tips, pattern suggestions)
- [ ] Activity "arriving" triggers welcome-home suggestions if applicable
- [ ] Graceful degradation: if activity-recognition is down, agent continues without activity context

---

## Story 96.3: Connect Energy Forecasting to Proactive Agent

**Points:** 3 | **Type:** Integration
**Goal:** Proactive agent uses energy forecasts to generate optimization suggestions

### Tasks

- [ ] **96.3.1** Add `EnergyForecastClient` to `proactive-agent-service/src/clients/`:
  ```python
  class EnergyForecastClient:
      async def get_forecast(self, hours: int = 24) -> ForecastResponse:
          ...
      async def get_peak_prediction(self) -> PeakPrediction:
          ...
      async def get_optimization(self) -> OptimizationRecommendation:
          ...
  ```
- [ ] **96.3.2** Integrate into observe phase:
  ```python
  context.energy_forecast = await self.energy_client.get_forecast(24)
  context.peak_prediction = await self.energy_client.get_peak_prediction()
  ```
- [ ] **96.3.3** Add energy-specific suggestion templates:
  - "Tomorrow's peak is {peak_hour}. Shift {device} to {optimal_hour}?"
  - "Your energy usage is {pct}% above forecast. Check {high_usage_entities}."
  - "Best hours for EV charging tonight: {optimal_hours} (lowest rate)"
- [ ] **96.3.4** Rate-limit energy suggestions: max 2 per day (avoid notification fatigue)
- [ ] **96.3.5** Add unit tests with mocked forecast responses

### Acceptance Criteria

- [ ] Proactive agent generates energy optimization suggestions based on forecast
- [ ] Peak prediction triggers "shift usage" suggestion when peak > threshold
- [ ] No more than 2 energy suggestions per day
- [ ] Graceful degradation: if energy-forecasting is down, agent continues

---

## Story 96.4: Anomaly Detection & Alerts

**Points:** 5 | **Type:** Feature
**Goal:** Detect anomalous device states and alert the user

### Tasks

- [ ] **96.4.1** Create `src/services/anomaly_detector.py` in `proactive-agent-service`:
  ```python
  class AnomalyDetector:
      """Detects anomalous device states based on duration and context."""

      ANOMALY_RULES = [
          # (entity_pattern, state, max_duration_minutes, message)
          ("cover.garage*", "open", 120, "Garage door has been open for {duration}"),
          ("lock.*", "unlocked", 30, "Door has been unlocked for {duration} — lock?"),
          ("light.*", "on", 480, "Lights have been on for {duration} with no activity"),
          ("climate.*", "heat", 360, "Heating has been running for {duration}"),
          ("media_player.*", "playing", 360, "Media player running for {duration}"),
      ]

      async def check_anomalies(self) -> list[Anomaly]:
          """Check all entities against anomaly rules."""
          ...
  ```
- [ ] **96.4.2** Query HA states and compare against rules
- [ ] **96.4.3** Combine with activity recognition: "lights on for 8 hours" is normal if activity is "working", anomalous if "sleeping" or "away"
- [ ] **96.4.4** Add `Anomaly` dataclass:
  ```python
  @dataclass
  class Anomaly:
      entity_id: str
      state: str
      duration_minutes: int
      message: str
      severity: str  # "info", "warning", "critical"
      suggested_action: str  # "notify", "turn_off", "lock"
  ```
- [ ] **96.4.5** Integrate into proactive agent observe phase
- [ ] **96.4.6** Send anomaly notifications via HA notify service (existing `ha-agent-client`)
- [ ] **96.4.7** Add cooldown: don't re-alert for same entity within 2 hours
- [ ] **96.4.8** Add unit tests for anomaly rules and cooldown

### Acceptance Criteria

- [ ] Garage door open > 2 hours → notification sent
- [ ] Lights on > 8 hours with no activity → notification sent
- [ ] Lights on > 8 hours with activity "working" → no notification
- [ ] Same anomaly not re-alerted within 2 hours
- [ ] Anomalies logged with severity for audit

---

## Story 96.5: Pattern-to-Automation Suggestion API

**Points:** 5 | **Type:** Feature
**Goal:** Detected patterns generate actionable automation suggestions via the existing suggestion pipeline

### Tasks

- [ ] **96.5.1** Create `src/services/pattern_to_suggestion.py`:
  ```python
  class PatternToSuggestion:
      """Converts detected patterns into automation suggestions."""

      def generate_suggestion(self, pattern: DetectedPattern) -> Suggestion:
          """
          Create a Suggestion record from a detected pattern.
          Uses the LLM to generate a natural-language description and draft YAML.
          """
          ...
  ```
- [ ] **96.5.2** Integrate with existing `SuggestionPipelineService`:
  - Use `gpt-5-mini` (already configured in proactive agent) to generate automation YAML from pattern
  - Create `Suggestion` ORM record with `source="pattern_detection"`
- [ ] **96.5.3** Add approval flow: suggestions appear in UI → user approves → automation created via `ha-ai-agent-service`
- [ ] **96.5.4** Deduplicate: don't suggest automations that already exist (check `enhanced_context_builder.build_existing_automations_context()`)
- [ ] **96.5.5** Add API endpoint: `GET /api/v1/suggestions?source=pattern_detection`
- [ ] **96.5.6** Add unit tests: pattern → suggestion → draft YAML

### Acceptance Criteria

- [ ] Detected pattern generates a suggestion with natural-language description
- [ ] Suggestion includes draft automation YAML
- [ ] Duplicate automation detection prevents redundant suggestions
- [ ] Suggestions are retrievable via API

---

## Story 96.6: Proactive Agent Loop Enhancement

**Points:** 3 | **Type:** Enhancement
**Goal:** Wire all new capabilities into the existing 15-minute observe-reason-act loop

### Tasks

- [ ] **96.6.1** Update `agent_loop.py` observe phase to include:
  - Pattern detection results (run pattern detection every 6 hours, cache results)
  - Activity recognition (real-time, every cycle)
  - Energy forecast (refresh hourly)
  - Anomaly detection (every cycle)
- [ ] **96.6.2** Update reason phase: LLM receives enriched context with patterns, activity, energy, anomalies
- [ ] **96.6.3** Update act phase: new action types:
  - `suggest_automation` — create pattern-based suggestion
  - `send_anomaly_alert` — send HA notification
  - `energy_optimization_tip` — create energy suggestion
- [ ] **96.6.4** Add configurable cycle intervals per capability:
  ```yaml
  proactive_intervals:
    anomaly_check: 15m      # Every cycle
    activity_check: 15m     # Every cycle
    energy_forecast: 1h     # Hourly
    pattern_detection: 6h   # Every 6 hours
  ```
- [ ] **96.6.5** Add metrics: suggestions generated, anomalies detected, automations created from suggestions

### Acceptance Criteria

- [ ] Observe phase collects all 4 data sources
- [ ] Reason phase produces contextual actions (not random suggestions)
- [ ] Act phase executes suggestions/alerts correctly
- [ ] Intervals are configurable and respected

---

## Story 96.7: User Preferences & Notification Settings

**Points:** 3 | **Type:** Feature
**Goal:** Users control which proactive features are enabled and how they're notified

### Tasks

- [ ] **96.7.1** Extend existing `UserPreference` model with proactive feature flags:
  ```python
  class ProactivePreferences:
      pattern_suggestions_enabled: bool = True
      energy_tips_enabled: bool = True
      anomaly_alerts_enabled: bool = True
      max_suggestions_per_day: int = 5
      max_energy_tips_per_day: int = 2
      quiet_hours_start: str = "22:00"  # No notifications
      quiet_hours_end: str = "07:00"
      notification_method: str = "ha_notify"  # or "in_app_only"
  ```
- [ ] **96.7.2** Update `PUT /api/proactive/preferences` to accept new fields
- [ ] **96.7.3** Respect quiet hours: suppress notifications during sleep hours
- [ ] **96.7.4** Respect per-feature toggles: disabled features skip processing
- [ ] **96.7.5** Add unit tests for preference enforcement

### Acceptance Criteria

- [ ] User can disable pattern suggestions while keeping anomaly alerts
- [ ] No notifications during quiet hours
- [ ] Max suggestions per day is enforced (excess queued for next day)
- [ ] Preferences persist across service restarts (PostgreSQL)

---

## Story 96.8: Dashboard & Observability

**Points:** 5 | **Type:** Feature
**Goal:** Users can see proactive agent activity, suggestions, and detected patterns

### Tasks

- [ ] **96.8.1** Add proactive agent metrics to Prometheus:
  - `homeiq_proactive_cycles_total` (counter)
  - `homeiq_proactive_suggestions_total{source}` (counter, labels: pattern/energy/anomaly)
  - `homeiq_proactive_anomalies_detected{severity}` (counter)
  - `homeiq_proactive_automations_created` (counter — suggestions that became automations)
  - `homeiq_proactive_pattern_count` (gauge — number of detected patterns)
- [ ] **96.8.2** Add API endpoint: `GET /api/proactive/patterns` — list detected patterns with confidence scores
- [ ] **96.8.3** Add API endpoint: `GET /api/proactive/anomalies` — recent anomaly history
- [ ] **96.8.4** Add Grafana dashboard panel: proactive agent activity (suggestions/day, anomalies/day, conversion rate)
- [ ] **96.8.5** Add health-dashboard integration: proactive agent status card

### Acceptance Criteria

- [ ] Prometheus metrics are scraped and visible in Grafana
- [ ] Patterns API returns detected patterns with confidence scores
- [ ] Anomalies API returns recent anomaly history with resolution status
- [ ] Dashboard shows proactive agent activity trends

---

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| Notification fatigue | Rate limiting (max 5/day), quiet hours, per-feature toggles |
| False positive patterns | 70% threshold, deduplication against existing automations |
| False positive anomalies | Activity-aware rules, 2-hour cooldown, severity levels |
| LLM cost for suggestion generation | Use `gpt-5-mini` (cheap), cache pattern→suggestion mapping |
| Service dependencies | Graceful degradation — each capability works independently |
| InfluxDB query performance | Cache pattern detection results (6h), limit query range (14 days) |

## Architecture Diagram

```
┌─────────────────┐     ┌────────────────────┐     ┌───────────────────┐
│  InfluxDB       │────▶│  Pattern Detector   │────▶│                   │
│  (entity states)│     └────────────────────┘     │                   │
│                 │                                 │   Proactive       │
│                 │     ┌────────────────────┐     │   Agent Loop      │
│                 │────▶│  Anomaly Detector   │────▶│   (15-min cycle)  │
│                 │     └────────────────────┘     │                   │
└─────────────────┘                                 │   Observe →       │
                        ┌────────────────────┐     │   Reason →        │
                        │  Activity          │────▶│   Act             │
                        │  Recognition :8036 │     │                   │
                        └────────────────────┘     │                   │
                        ┌────────────────────┐     │                   │
                        │  Energy            │────▶│                   │
                        │  Forecasting :8037 │     └─────────┬─────────┘
                        └────────────────────┘               │
                                                             ▼
                                                  ┌─────────────────────┐
                                                  │  Suggestions DB     │
                                                  │  (PostgreSQL)       │
                                                  │                     │
                                                  │  + HA Notifications  │
                                                  └─────────────────────┘
```
