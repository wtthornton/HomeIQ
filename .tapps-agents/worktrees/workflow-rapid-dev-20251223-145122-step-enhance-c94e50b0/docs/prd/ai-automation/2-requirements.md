# 2. Requirements

### 2.1 Functional Requirements

**FR1:** The system SHALL analyze historical Home Assistant event data from the Data API to identify automation opportunities
- **Scope:** Last 30 days of device state changes and events
- **Frequency:** Daily batch analysis at 3 AM
- **Patterns:** Time-of-day, device co-occurrence, manual intervention anomalies

**FR2:** The system SHALL detect three types of automation patterns:
- **FR2.1:** Time-of-day patterns (device actions at consistent times)
- **FR2.2:** Device co-occurrence patterns (devices used together)
- **FR2.3:** Anomaly patterns (manual interventions indicating automation opportunities)

**FR3:** The system SHALL generate 5-10 automation suggestions per week using LLM-based natural language generation
- **Quality over quantity:** Focus on high-confidence patterns only (>70%)
- **LLM:** OpenAI GPT-4o-mini for cost-effectiveness
- **Format:** Natural language explanation + Home Assistant YAML automation

**FR4:** The system SHALL provide a web-based interface for users to browse, review, and manage automation suggestions
- **Actions:** View, Approve, Modify, Reject, Archive
- **Status tracking:** Pending, Approved, Deployed, Rejected
- **History:** Track suggestion evolution and user feedback

**FR5:** The system SHALL allow users to approve automation suggestions before deployment
- **Human-in-the-loop:** No automations deploy without explicit approval
- **Modification:** Users can edit suggested automations before deployment
- **Preview:** Show automation logic in human-readable format

**FR6:** The system SHALL deploy approved automations to Home Assistant via REST API
- **Format:** Convert to Home Assistant automation YAML schema
- **Validation:** Verify automation syntax before deployment
- **Rollback:** Track deployed automations for potential removal

**FR7:** The system SHALL communicate dynamic automation triggers via MQTT
- **Topics:** `ha-ai/events/*` for AI-detected events
- **HA Integration:** Home Assistant subscribed to AI topics
- **Bi-directional:** HA publishes execution feedback to `ha-ai/responses/*`

**FR8:** The system SHALL display current Home Assistant automations
- **Source:** Query HA API for existing automations
- **Purpose:** Avoid suggesting duplicate automations
- **Comparison:** Show how suggestions differ from existing

**FR9:** The system SHALL store pattern detection results and suggestions in SQLite database
- **Persistence:** Patterns, suggestions, user decisions, deployment status
- **History:** Track pattern evolution over time
- **Analytics:** Support future reporting and ML improvements

**FR10:** The system SHALL provide real-time status updates via MQTT
- **Events:** Analysis complete, new suggestions available, deployment status
- **Feedback loop:** Automation execution success/failure from HA

---

### 2.2 Non-Functional Requirements

**NFR1:** The system SHALL complete daily pattern analysis within 10 minutes
- **Target:** 5-10 minutes for 30 days of data
- **Acceptable:** Up to 15 minutes on high-load days
- **Failure:** Alert if exceeds 20 minutes

**NFR2:** The system SHALL operate within 1GB of RAM during pattern analysis
- **Peak:** <1GB during analysis
- **Idle:** <200MB between analyses
- **Constraint:** Must coexist with Home Assistant on single NUC

**NFR3:** The system SHALL support 100-200 devices in Phase 1
- **Minimum:** 50 devices (small home)
- **Target:** 100-150 devices (typical home)
- **Maximum:** 200 devices (large home)

**NFR4:** The API SHALL respond to UI requests within 500ms
- **Cached data:** <200ms
- **Database queries:** <500ms
- **LLM generation:** Async (background job)

**NFR5:** The system SHALL maintain 95% uptime
- **Critical:** Pattern analysis can run next day if missed
- **Non-critical:** Service restarts don't affect deployed automations (they live in HA)
- **Recovery:** Automatic restart on failure

**NFR6:** The system SHALL integrate with existing Home Assistant Ingestor architecture
- **Data API:** Use existing Data API (port 8006) for historical data
- **MQTT:** Share MQTT broker with other services
- **Docker:** Deploy as Docker Compose service
- **Minimal impact:** <5% CPU usage when idle

**NFR7:** The system SHALL limit API costs to $10/month
- **LLM:** GPT-4o-mini for cost optimization
- **Batch processing:** Generate 5-10 suggestions weekly
- **Monitoring:** Track token usage and costs

**NFR8:** The system SHALL be maintainable by developers with Python and React experience
- **Code quality:** Follow existing coding standards
- **Documentation:** Comprehensive inline documentation
- **Testing:** Unit tests for pattern detection logic
- **Debugging:** Logging for pattern analysis steps

**NFR9:** The system SHALL secure communication between services
- **MQTT:** Internal network only (no external exposure)
- **API:** Authentication via Home Assistant tokens
- **Data:** No sensitive data sent to external LLM (only anonymized patterns)

**NFR10:** The system SHALL gracefully handle insufficient data scenarios
- **Bootstrap:** Provide helpful messages when <7 days of data
- **Confidence:** Only suggest patterns with >70% confidence
- **Feedback:** Explain why suggestions may be limited initially

---

### 2.3 Compatibility Requirements

**CR1:** The system SHALL maintain compatibility with existing Home Assistant installation
- **HA Version:** Support Home Assistant 2024.1+
- **API:** Use stable HA REST API endpoints
- **Automations:** Generated automations must be valid HA YAML
- **No modification:** Do not require HA configuration changes

**CR2:** The system SHALL integrate with existing Data API without modification
- **Endpoints:** Use existing `/api/events`, `/api/devices`, `/api/entities`
- **No schema changes:** Do not require Data API updates
- **Graceful degradation:** Handle Data API downtime

**CR3:** The system SHALL use existing MQTT broker (Mosquitto)
- **Shared broker:** Coexist with other services using MQTT
- **Topic namespace:** Use `ha-ai/*` to avoid conflicts
- **QoS:** Respect broker capacity limits

**CR4:** The system SHALL deploy alongside existing services without resource conflicts
- **Ports:** Use available port 8011 (AI service), 3002 (frontend)
- **Memory:** Stay within hardware constraints (8-16GB total)
- **CPU:** Batch processing scheduled during low-usage times (3 AM)

**CR5:** The system SHALL preserve all existing Home Assistant automations
- **Non-destructive:** Never delete or modify existing automations without user approval
- **Additive only:** Only add new automations when user approves
- **Rollback:** Support removing deployed automations

---
