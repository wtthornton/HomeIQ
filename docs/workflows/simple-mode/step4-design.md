# Step 4: Component Design - Pattern & Synergy Quality Evaluation Tool

## Component Specifications

### 1. Main Script: `scripts/evaluate_patterns_quality.py`

**Purpose:** Entry point for quality evaluation tool

**Structure:**
```python
#!/usr/bin/env python3
"""
Pattern and Synergy Quality Evaluation Tool

Evaluates the accuracy and quality of patterns and synergies detected by
the AI Pattern Service by validating them against actual Home Assistant events.
"""

import argparse
import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Main components
from database_accessor import DatabaseAccessor
from event_fetcher import EventFetcher
from pattern_validator import PatternValidator
from synergy_validator import SynergyValidator
from data_quality_analyzer import DataQualityAnalyzer
from report_generator import ReportGenerator

async def main():
    """Main execution function."""
    # Parse CLI arguments
    # Initialize components
    # Run evaluation
    # Generate reports
    pass

if __name__ == "__main__":
    asyncio.run(main())
```

**CLI Arguments:**
- `--time-window` (int, default=30): Days of events to analyze
- `--output-format` (str, choices=['json', 'markdown', 'html', 'all'], default='all')
- `--output-dir` (str, default='reports/quality'): Output directory
- `--min-confidence` (float, default=0.0): Minimum confidence filter
- `--pattern-type` (str, optional): Filter by pattern type
- `--synergy-type` (str, optional): Filter by synergy type
- `--verbose` (flag): Enable verbose logging

---

### 2. DatabaseAccessor Class

**File:** `scripts/quality_evaluation/database_accessor.py`

**Purpose:** Handle database connections and queries

**Class Definition:**
```python
class DatabaseAccessor:
    """Handles database access for patterns and synergies."""
    
    def __init__(self, db_path: str):
        """Initialize database connection."""
        
    async def get_all_patterns(
        self,
        pattern_type: Optional[str] = None,
        device_id: Optional[str] = None,
        min_confidence: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve all patterns with optional filters."""
        
    async def get_all_synergies(
        self,
        synergy_type: Optional[str] = None,
        min_confidence: Optional[float] = None,
        synergy_depth: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve all synergies with optional filters."""
        
    async def close(self) -> None:
        """Close database connection."""
```

**Data Models:**
- Pattern: `{id, pattern_type, device_id, confidence, occurrences, pattern_metadata, created_at, updated_at}`
- Synergy: `{id, synergy_id, synergy_type, device_ids, confidence, impact_score, pattern_support_score, validated_by_patterns, synergy_depth, chain_devices, ...}`

---

### 3. EventFetcher Class

**File:** `scripts/quality_evaluation/event_fetcher.py`

**Purpose:** Fetch events from Data API

**Class Definition:**
```python
class EventFetcher:
    """Fetches events from Data API for validation."""
    
    def __init__(self, data_api_url: str = "http://localhost:8006"):
        """Initialize Data API client."""
        
    async def fetch_events(
        self,
        start_time: datetime,
        end_time: datetime,
        limit: int = 50000
    ) -> pd.DataFrame:
        """Fetch events and return as DataFrame."""
        
    async def close(self) -> None:
        """Close API client connection."""
```

**Data Format:**
- DataFrame columns: `event_id, entity_id, state, timestamp, domain, device_id, area_id, ...`

---

### 4. PatternValidator Class

**File:** `scripts/quality_evaluation/pattern_validator.py`

**Purpose:** Validate patterns against events

**Class Definition:**
```python
class PatternValidator:
    """Validates patterns against actual events."""
    
    def __init__(self):
        """Initialize pattern detectors."""
        # Import TimeOfDayPatternDetector, CoOccurrencePatternDetector
        
    async def validate_patterns(
        self,
        stored_patterns: List[Dict[str, Any]],
        events_df: pd.DataFrame
    ) -> Dict[str, Any]:
        """Validate stored patterns against events."""
        # Returns: {
        #   'total_patterns': int,
        #   'validated_patterns': int,
        #   'false_positives': List[Dict],
        #   'precision': float,
        #   'recall': float,
        #   'f1_score': float,
        #   'confidence_accuracy': Dict[str, float],
        #   'details': List[Dict]
        # }
        
    async def redetect_patterns(
        self,
        events_df: pd.DataFrame
    ) -> List[Dict[str, Any]]:
        """Re-detect patterns from events using same algorithms."""
```

**Validation Logic:**
1. Re-detect patterns from events using same detectors
2. Match stored patterns with re-detected patterns (by pattern_type + device_id)
3. Calculate precision = matched / stored
4. Calculate recall = matched / re-detected
5. Calculate F1 = 2 * (precision * recall) / (precision + recall)
6. Identify false positives = stored patterns not in re-detected

---

### 5. SynergyValidator Class

**File:** `scripts/quality_evaluation/synergy_validator.py`

**Purpose:** Validate synergies against events

**Class Definition:**
```python
class SynergyValidator:
    """Validates synergies against actual events."""
    
    def __init__(self):
        """Initialize synergy detectors."""
        
    async def validate_synergies(
        self,
        stored_synergies: List[Dict[str, Any]],
        events_df: pd.DataFrame
    ) -> Dict[str, Any]:
        """Validate stored synergies against events."""
        # Returns: {
        #   'total_synergies': int,
        #   'validated_synergies': int,
        #   'false_positives': List[Dict],
        #   'precision': float,
        #   'recall': float,
        #   'f1_score': float,
        #   'pattern_support_accuracy': Dict[str, float],
        #   'depth_accuracy': Dict[str, int],
        #   'details': List[Dict]
        # }
        
    async def redetect_synergies(
        self,
        events_df: pd.DataFrame
    ) -> List[Dict[str, Any]]:
        """Re-detect synergies from events."""
```

**Validation Logic:**
1. Re-detect synergies from events
2. Match stored synergies with re-detected (by synergy_id or device_ids)
3. Validate pattern_support_score accuracy
4. Check validated_by_patterns flag correctness
5. Validate synergy_depth accuracy

---

### 6. DataQualityAnalyzer Class

**File:** `scripts/quality_evaluation/data_quality_analyzer.py`

**Purpose:** Analyze data quality metrics

**Class Definition:**
```python
class DataQualityAnalyzer:
    """Analyzes data quality metrics for patterns and synergies."""
    
    def analyze_pattern_quality(
        self,
        patterns: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze pattern data quality."""
        # Returns: {
        #   'total_patterns': int,
        #   'completeness': {
        #     'pattern_type': float,  # % with value
        #     'device_id': float,
        #     'confidence': float,
        #     'occurrences': float,
        #     'metadata': float
        #   },
        #   'confidence_distribution': {
        #     'mean': float,
        #     'median': float,
        #     'std': float,
        #     'min': float,
        #     'max': float,
        #     'histogram': List[int]  # 10 bins
        #   },
        #   'occurrence_validation': {
        #     'zero_occurrences': int,
        #     'negative_occurrences': int,
        #     'unusual_high': int
        #   },
        #   'metadata_quality': {
        #     'empty_metadata': int,
        #     'missing_fields': Dict[str, int]
        #   }
        # }
        
    def analyze_synergy_quality(
        self,
        synergies: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Analyze synergy data quality."""
        # Similar structure to pattern quality
```

---

### 7. ReportGenerator Class

**File:** `scripts/quality_evaluation/report_generator.py`

**Purpose:** Generate quality reports

**Class Definition:**
```python
class ReportGenerator:
    """Generates quality evaluation reports."""
    
    def generate_json_report(
        self,
        results: Dict[str, Any],
        output_path: Path
    ) -> None:
        """Generate JSON report."""
        
    def generate_markdown_report(
        self,
        results: Dict[str, Any],
        output_path: Path
    ) -> None:
        """Generate Markdown report."""
        
    def generate_html_report(
        self,
        results: Dict[str, Any],
        output_path: Path
    ) -> None:
        """Generate HTML report with charts."""
```

**Report Structure:**
```json
{
  "evaluation_date": "2025-12-31T01:00:00Z",
  "time_window_days": 30,
  "summary": {
    "total_patterns": 150,
    "total_synergies": 75,
    "overall_quality_score": 0.85
  },
  "pattern_validation": { ... },
  "synergy_validation": { ... },
  "data_quality": {
    "patterns": { ... },
    "synergies": { ... }
  },
  "recommendations": [ ... ]
}
```

---

## Data Structures

### ValidationResult
```python
@dataclass
class ValidationResult:
    total_items: int
    validated_items: int
    false_positives: List[Dict[str, Any]]
    precision: float
    recall: float
    f1_score: float
    confidence_accuracy: Dict[str, float]
    details: List[Dict[str, Any]]
```

### QualityMetrics
```python
@dataclass
class QualityMetrics:
    completeness: Dict[str, float]
    confidence_distribution: Dict[str, Any]
    occurrence_validation: Dict[str, int]
    metadata_quality: Dict[str, Any]
```

---

## Error Handling

### Database Errors
- **Connection Failure:** Retry 3 times with exponential backoff
- **Query Error:** Log error, return empty list with warning
- **Missing Table:** Raise clear error with instructions

### API Errors
- **Connection Failure:** Retry 3 times with exponential backoff
- **Rate Limiting:** Implement backoff, wait and retry
- **Invalid Response:** Log error, return empty DataFrame

### Validation Errors
- **Missing Detector:** Log warning, skip validation type
- **Data Mismatch:** Log warning, continue with available data
- **Calculation Error:** Handle division by zero, return NaN with explanation

---

## Logging Configuration

```python
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('quality_evaluation.log')
    ]
)
```

---

## Progress Indicators

Use `tqdm` or custom progress bars for:
- Database queries
- Event fetching
- Pattern validation
- Synergy validation
- Report generation
