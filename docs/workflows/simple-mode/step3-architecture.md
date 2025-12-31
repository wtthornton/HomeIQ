# Step 3: Architecture Design - Pattern & Synergy Quality Evaluation Tool

## System Overview
A standalone Python script that evaluates the quality and accuracy of patterns and synergies detected by the AI Pattern Service. The tool validates stored patterns/synergies against actual Home Assistant events, measures data quality, and generates comprehensive reports.

## Architecture Pattern
**Standalone Script** - Command-line tool that runs independently, connects to existing services and databases.

## Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Quality Evaluation Tool                    │
│                      (scripts/evaluate_patterns.py)           │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│   Database   │   │  Data API   │   │   Pattern   │
│   Access     │   │   Client     │   │  Detectors   │
│              │   │              │   │              │
│ - Patterns   │   │ - Fetch      │   │ - TimeOfDay │
│ - Synergies  │   │   Events     │   │ - CoOccur   │
│ - SQLite     │   │ - DataFrame  │   │ - Synergy   │
└──────────────┘   └──────────────┘   └──────────────┘
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
                            ▼
                   ┌─────────────────┐
                   │   Validators    │
                   │                 │
                   │ - Pattern       │
                   │   Validator     │
                   │ - Synergy       │
                   │   Validator     │
                   │ - Data Quality  │
                   │   Analyzer      │
                   └─────────────────┘
                            │
                            ▼
                   ┌─────────────────┐
                   │   Report        │
                   │   Generator     │
                   │                 │
                   │ - JSON          │
                   │ - Markdown      │
                   │ - HTML          │
                   └─────────────────┘
```

## Technology Stack

### Core Technologies
- **Python 3.11+** - Language
- **SQLAlchemy** - Database ORM (async)
- **pandas** - Data analysis and DataFrame operations
- **argparse** - CLI interface
- **json** - JSON report generation
- **jinja2** - HTML template rendering (optional)

### Dependencies
- **Data API Client** - For fetching events (shared/client)
- **Pattern Detectors** - TimeOfDayPatternDetector, CoOccurrencePatternDetector (from ai-pattern-service)
- **Synergy Detectors** - Synergy detection algorithms (from ai-pattern-service)
- **SQLite** - Database (ai_automation.db)

### External Services
- **Data API** (Port 8006) - Event data source
- **SQLite Database** (ai_automation.db) - Pattern/synergy storage

## Data Flow

```
1. CLI Execution
   ↓
2. Initialize Components
   - Database connection
   - Data API client
   - Pattern/synergy detectors
   ↓
3. Fetch Data
   - Retrieve patterns from database
   - Retrieve synergies from database
   - Fetch events from Data API (last N days)
   ↓
4. Validation Phase
   - Re-detect patterns from events
   - Re-detect synergies from events
   - Compare with stored patterns/synergies
   - Calculate metrics (precision, recall, F1)
   ↓
5. Quality Analysis
   - Data completeness checks
   - Confidence score distribution
   - Metadata quality assessment
   ↓
6. Report Generation
   - Aggregate results
   - Generate JSON/Markdown/HTML reports
   - Write to output directory
   ↓
7. Exit
```

## Component Design

### 1. DatabaseAccessor
**Purpose:** Handle database connections and queries

**Responsibilities:**
- Connect to SQLite database (ai_automation.db)
- Retrieve patterns with filters
- Retrieve synergies with filters
- Handle connection errors

**Methods:**
- `get_all_patterns(pattern_type=None, device_id=None, min_confidence=None) -> List[Pattern]`
- `get_all_synergies(synergy_type=None, min_confidence=None, synergy_depth=None) -> List[SynergyOpportunity]`

### 2. EventFetcher
**Purpose:** Fetch events from Data API

**Responsibilities:**
- Initialize Data API client
- Fetch events for time window
- Convert to DataFrame
- Handle API errors

**Methods:**
- `fetch_events(start_time: datetime, end_time: datetime, limit: int = 50000) -> pd.DataFrame`

### 3. PatternValidator
**Purpose:** Validate patterns against events

**Responsibilities:**
- Re-detect patterns from events using same algorithms
- Compare with stored patterns
- Calculate precision, recall, F1
- Identify false positives

**Methods:**
- `validate_patterns(stored_patterns: List[Pattern], events_df: pd.DataFrame) -> ValidationResult`
- `redetect_patterns(events_df: pd.DataFrame) -> List[dict]`

### 4. SynergyValidator
**Purpose:** Validate synergies against events

**Responsibilities:**
- Re-detect synergies from events
- Compare with stored synergies
- Validate pattern_support_score
- Calculate metrics

**Methods:**
- `validate_synergies(stored_synergies: List[SynergyOpportunity], events_df: pd.DataFrame) -> ValidationResult`
- `redetect_synergies(events_df: pd.DataFrame) -> List[dict]`

### 5. DataQualityAnalyzer
**Purpose:** Analyze data quality metrics

**Responsibilities:**
- Check data completeness
- Analyze confidence distributions
- Validate occurrence counts
- Assess metadata quality

**Methods:**
- `analyze_pattern_quality(patterns: List[Pattern]) -> QualityMetrics`
- `analyze_synergy_quality(synergies: List[SynergyOpportunity]) -> QualityMetrics`

### 6. ReportGenerator
**Purpose:** Generate quality reports

**Responsibilities:**
- Aggregate validation results
- Generate JSON reports
- Generate Markdown reports
- Generate HTML reports (with charts)

**Methods:**
- `generate_json_report(results: EvaluationResults, output_path: str) -> None`
- `generate_markdown_report(results: EvaluationResults, output_path: str) -> None`
- `generate_html_report(results: EvaluationResults, output_path: str) -> None`

## Integration Points

### Database Integration
- **Connection:** SQLite database at `data/ai_automation.db`
- **ORM:** SQLAlchemy async (or raw SQL fallback)
- **Tables:** `patterns`, `synergy_opportunities`

### Data API Integration
- **Endpoint:** `http://localhost:8006` (or configurable)
- **Client:** Shared DataAPIClient from `shared/client/`
- **Method:** `fetch_events(start_time, end_time, limit)`

### Pattern Detection Integration
- **Import:** Pattern detectors from `services/ai-pattern-service/src/detection/`
- **Algorithms:** TimeOfDayPatternDetector, CoOccurrencePatternDetector
- **Reuse:** Same detection logic as production service

### Synergy Detection Integration
- **Import:** Synergy detectors from `services/ai-pattern-service/src/detection/`
- **Algorithms:** Multi-hop synergy detection
- **Reuse:** Same detection logic as production service

## Scalability Considerations

### Current Scale
- **Target:** Single-home deployment (~50-100 devices)
- **Event Volume:** ~50,000 events per 30 days
- **Pattern Count:** ~100-500 patterns
- **Synergy Count:** ~50-200 synergies

### Performance Optimizations
- **Batch Processing:** Process patterns/synergies in batches
- **DataFrame Operations:** Use pandas for efficient event analysis
- **Caching:** Cache event data during validation
- **Progress Indicators:** Show progress for long operations

### Future Scalability
- **Parallel Processing:** Use multiprocessing for large datasets
- **Streaming:** Stream events for very large time windows
- **Database Indexing:** Ensure proper indexes on database queries

## Security Considerations

### Database Access
- **Read-Only:** Tool should only read from database (no writes)
- **Connection Security:** Use file permissions to protect database

### Data API Access
- **Local Network:** Data API should be on local network
- **No Authentication:** Current setup has no auth (local only)

### Output Files
- **File Permissions:** Set appropriate permissions on generated reports
- **Sensitive Data:** Reports may contain device IDs and patterns (handle appropriately)

## Deployment Architecture

### Execution Model
- **Standalone Script:** Run directly with Python
- **Location:** `scripts/evaluate_patterns_quality.py`
- **Dependencies:** Install via requirements.txt or use existing venv

### Execution Flow
```bash
python scripts/evaluate_patterns_quality.py \
  --time-window 30 \
  --output-format all \
  --output-dir reports/quality \
  --min-confidence 0.5
```

### Output Structure
```
reports/quality/
├── evaluation_report.json
├── evaluation_report.md
└── evaluation_report.html
```

## Error Handling Strategy

### Database Errors
- **Connection Failures:** Retry with exponential backoff
- **Query Errors:** Log error and continue with available data
- **Missing Tables:** Provide clear error message

### API Errors
- **Connection Failures:** Retry with exponential backoff
- **Rate Limiting:** Implement backoff strategy
- **Invalid Responses:** Log error and skip event fetching

### Validation Errors
- **Missing Detectors:** Use fallback or skip validation
- **Data Mismatches:** Log warnings, continue analysis
- **Calculation Errors:** Handle division by zero, null values

## Performance Targets

- **Execution Time:** < 5 minutes for 30 days of data
- **Memory Usage:** < 500 MB for typical dataset
- **Database Queries:** < 10 seconds total
- **API Calls:** < 30 seconds for event fetching
- **Report Generation:** < 10 seconds
