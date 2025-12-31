# Step 1: Enhanced Prompt - Pattern & Synergy Quality Evaluation Tool

## Original Request
Create a program to evaluate the accuracy and quality of patterns and synergies detected by the AI pattern service.

## Enhanced Specification

### Purpose
Build a comprehensive quality evaluation tool that validates the accuracy, reliability, and data quality of patterns and synergies detected by the AI Pattern Service. The tool should help identify issues, measure confidence score accuracy, and provide actionable insights for improving pattern detection algorithms.

### Requirements

#### Functional Requirements
1. **Pattern Quality Evaluation**
   - Validate patterns against actual Home Assistant events
   - Check pattern confidence scores against observed occurrences
   - Identify false positives (patterns that don't match actual behavior)
   - Measure pattern stability over time
   - Analyze pattern metadata completeness

2. **Synergy Quality Evaluation**
   - Validate synergies against actual device co-occurrence in events
   - Check synergy confidence, impact_score, and final_score accuracy
   - Validate pattern_support_score and validated_by_patterns flags
   - Identify synergies with low supporting evidence
   - Analyze synergy depth (2, 3, 4) accuracy

3. **Data Quality Metrics**
   - Pattern data completeness (required fields present)
   - Synergy data completeness (required fields present)
   - Confidence score distribution analysis
   - Occurrence count validation
   - Metadata quality assessment

4. **Validation Against Events**
   - Fetch events from Data API (last 30-90 days)
   - Re-detect patterns from events and compare with stored patterns
   - Re-detect synergies from events and compare with stored synergies
   - Calculate precision, recall, and F1 scores
   - Identify patterns/synergies not supported by events

5. **Reporting**
   - Generate comprehensive quality report (JSON, Markdown, HTML)
   - Summary statistics (total patterns, synergies, quality scores)
   - Detailed findings with examples
   - Recommendations for improvement
   - Export capability for further analysis

#### Non-Functional Requirements
- **Performance**: Should complete evaluation in < 5 minutes for typical dataset
- **Accuracy**: Validation should use same algorithms as pattern service
- **Reliability**: Handle missing data gracefully, provide clear error messages
- **Usability**: CLI interface with clear output, progress indicators
- **Maintainability**: Well-documented, follows HomeIQ code patterns

### Technical Context

#### Database Schema
- **Patterns Table**: `patterns` (pattern_type, device_id, confidence, occurrences, pattern_metadata, created_at, updated_at)
- **Synergies Table**: `synergy_opportunities` (synergy_id, synergy_type, device_ids, confidence, impact_score, pattern_support_score, validated_by_patterns, synergy_depth, chain_devices, embedding_similarity, rerank_score, final_score)

#### Pattern Types
- `time_of_day`: Recurring time-based patterns
- `co_occurrence`: Devices used together frequently

#### Synergy Types
- `device_pair`: Two-device relationships
- `device_chain`: Multi-device chains (3-4 devices)
- `weather_context`: Weather-based synergies
- `energy_context`: Energy-based synergies
- `event_context`: Event-based synergies

#### Dependencies
- Data API client for fetching events
- Pattern Service database (SQLite: ai_automation.db)
- Pattern detection algorithms (TimeOfDayPatternDetector, CoOccurrencePatternDetector)
- Synergy detection algorithms (from ai-pattern-service)

### Quality Standards
- Code quality score: ≥ 70
- Test coverage: ≥ 80%
- Type hints: Required for all functions
- Error handling: Comprehensive try/except with logging
- Documentation: Docstrings for all functions and classes

### Implementation Strategy
1. Create standalone Python script in `scripts/` directory
2. Use existing Data API client for event fetching
3. Reuse pattern/synergy detection logic from ai-pattern-service
4. Generate reports in multiple formats (JSON, Markdown, HTML)
5. Include progress indicators for long-running operations
6. Add CLI arguments for configuration (time window, output format, etc.)
