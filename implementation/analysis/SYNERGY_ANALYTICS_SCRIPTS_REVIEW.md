# Synergy Analytics Scripts Review

**Date:** January 16, 2026  
**Status:** ✅ **COMPLETE - INVENTORY OF EXISTING SCRIPTS**

---

## Executive Summary

This document catalogs all existing scripts for analyzing synergy data in the `synergy_opportunities` database table. These scripts provide various analytics capabilities for understanding synergy distribution, scoring, quality, and types.

---

## Database Location

**Primary Database:** `data/ai_automation.db` (SQLite)  
**Table:** `synergy_opportunities`  
**Service:** ai-pattern-service (Port 8020)

---

## Available Analytics Scripts

### 1. **`scripts/check_synergy_types.py`** ✅ **SIMPLE - QUICK CHECK**

**Purpose:** Quick check of synergy types and depths  
**Output:** Basic counts by type and depth  
**Best For:** Quick verification of synergy types present

**Features:**
- Lists synergy types and depths with counts
- Shows total synergies
- Samples a few synergies
- Checks for specific types (scene_based, context_aware)

**Usage:**
```bash
python scripts/check_synergy_types.py
```

**Output Example:**
```
Synergy Types and Depths:
  Type: device_pair, Depth: 2, Count: 5000
  Type: device_chain, Depth: 3, Count: 200
  
Total synergies: 5200
```

---

### 2. **`scripts/diagnose_synergy_types.py`** ✅ **COMPREHENSIVE - TYPE ANALYSIS**

**Purpose:** Detailed analysis of synergy types distribution  
**Output:** Comprehensive breakdown by type, depth, impact, confidence  
**Best For:** Understanding synergy type distribution and diagnosing issues

**Features:**
- Counts by synergy_type with averages (impact, confidence)
- Distribution by synergy_depth (2, 3, 4)
- Sample synergies with metadata
- Created timestamps (first/last)
- Supports Docker container database access

**Usage:**
```bash
# Local database
python scripts/diagnose_synergy_types.py --db-path data/ai_automation.db

# Docker container database
python scripts/diagnose_synergy_types.py --use-docker-db --docker-container ai-pattern-service
```

**Output Includes:**
- Synergy types summary (count, avg impact, avg confidence, timestamps)
- Synergy depth distribution
- Sample synergies (most recent)
- Device pair/chain counts

---

### 3. **`scripts/analyze_synergy_scoring.py`** ✅ **DETAILED - SCORING ANALYSIS**

**Purpose:** Deep dive into scoring distributions  
**Output:** Detailed score distributions and statistics  
**Best For:** Understanding score ranges, quality tiers, impact/confidence distributions

**Features:**
- Quality score distribution (by ranges and tiers)
- Impact score distribution
- Confidence distribution
- Final score analysis
- Statistics by synergy type
- Supports Docker container access

**Usage:**
```bash
# Local database
python scripts/analyze_synergy_scoring.py

# Docker container (default)
python scripts/analyze_synergy_scoring.py --use-docker
```

**Output Includes:**
- Quality score ranges (0.0-1.0, NULL)
- Quality tiers (high, medium, low, poor)
- Impact score ranges and stats (min/max/avg)
- Confidence ranges and stats
- Final score analysis
- Breakdown by synergy type

---

### 4. **`scripts/analyze_device_chain_scoring.py`** ✅ **SPECIALIZED - CHAIN ANALYSIS**

**Purpose:** Compare device_chain vs device_pair scoring  
**Output:** Comparative analysis of chain vs pair synergies  
**Best For:** Understanding why device_chain has different quality scores

**Features:**
- Comparison of device_pair vs device_chain
- Complexity distribution comparison
- Validation status comparison
- Sample device_chain synergies with breakdown

**Usage:**
```bash
python scripts/analyze_device_chain_scoring.py data/ai_automation.db
```

**Output Includes:**
- Overall comparison (count, avg quality, avg impact, avg confidence)
- Complexity distribution by type
- Validation status breakdown
- Sample device_chain synergies

---

### 5. **`scripts/show_synergy_stats.py`** ✅ **NEW - BY TYPE AND LEVEL**

**Purpose:** Statistics by type, depth, and complexity  
**Output:** Formatted tables showing breakdown by multiple dimensions  
**Best For:** Comprehensive view of synergies by type and level (depth/complexity)

**Features:**
- Statistics by Type and Depth (Level)
- Statistics by Type and Complexity
- Total counts, averages, min/max ranges
- Formatted tables with grouping
- Handles Windows encoding

**Usage:**
```bash
python scripts/show_synergy_stats.py
```

**Output Includes:**
- Summary (total synergies, unique types)
- By Type and Depth table (type, depth, count, avg impact, avg confidence, min/max impact)
- By Type and Complexity table (type, complexity, count, avg impact, avg confidence)
- Type totals with subtotals

**Note:** This is the script we just created - provides the most comprehensive breakdown by type and level.

---

### 6. **`scripts/validate_synergy_patterns.py`** ✅ **VALIDATION**

**Purpose:** Validate synergies against patterns  
**Output:** Validation results  
**Best For:** Checking pattern validation status

---

### 7. **`scripts/evaluate_synergy_detection.py`** ✅ **EVALUATION**

**Purpose:** Evaluate synergy detection quality  
**Output:** Evaluation metrics  
**Best For:** Quality assessment of detection algorithms

---

### 8. **`scripts/cleanup_low_quality_synergies.py`** ✅ **CLEANUP**

**Purpose:** Clean up low-quality synergies  
**Output:** Cleanup report  
**Best For:** Removing synergies below quality threshold

**Features:**
- Filters by quality threshold
- Shows tier breakdown before/after
- Supports dry-run mode

---

### 9. **`scripts/cleanup_stale_synergies.py`** ✅ **CLEANUP**

**Purpose:** Remove stale/inactive synergies  
**Output:** Cleanup report  
**Best For:** Removing synergies for inactive devices

---

## Script Comparison Matrix

| Script | Type Analysis | Depth/Level | Complexity | Scoring | Quality | Best Use Case |
|--------|--------------|-------------|------------|---------|---------|---------------|
| `check_synergy_types.py` | ✅ Basic | ✅ | ❌ | ❌ | ❌ | Quick check |
| `diagnose_synergy_types.py` | ✅ Detailed | ✅ | ❌ | ✅ Avg | ❌ | Type distribution |
| `analyze_synergy_scoring.py` | ✅ By Type | ❌ | ❌ | ✅ Detailed | ✅ | Score distributions |
| `analyze_device_chain_scoring.py` | ✅ Compare | ❌ | ✅ | ✅ Compare | ✅ | Chain vs Pair |
| `show_synergy_stats.py` | ✅ Detailed | ✅ | ✅ | ✅ Summary | ❌ | **Comprehensive breakdown** |

---

## Recommended Workflow

### Quick Check
```bash
python scripts/check_synergy_types.py
```

### Comprehensive Analysis
```bash
# 1. Overall statistics by type and level
python scripts/show_synergy_stats.py

# 2. Detailed scoring analysis
python scripts/analyze_synergy_scoring.py

# 3. Type distribution details
python scripts/diagnose_synergy_types.py
```

### Specific Investigations
```bash
# Compare device_chain vs device_pair
python scripts/analyze_device_chain_scoring.py data/ai_automation.db

# Check quality distribution
python scripts/analyze_synergy_scoring.py
```

---

## Database Schema Reference

**Key Fields for Analytics:**
- `synergy_type`: Type of synergy (device_pair, device_chain, event_context, scene_based, context_aware)
- `synergy_depth`: Depth/level (2=pair, 3=chain, 4=4-chain)
- `complexity`: Complexity level (low, medium, high)
- `impact_score`: Impact score (0.0-1.0)
- `confidence`: Confidence score (0.0-1.0)
- `quality_score`: Quality score (0.0-1.0, nullable)
- `quality_tier`: Quality tier (high, medium, low, poor, nullable)
- `validated_by_patterns`: Boolean validation flag
- `pattern_support_score`: Pattern support score (0.0-1.0)
- `filter_reason`: Reason if filtered (NULL = not filtered)

---

## API Endpoint

**Statistics Endpoint (Fixed):**
```
GET http://localhost:8020/api/v1/synergies/statistics
```

**Returns:**
- `total_synergies`: Total count
- `by_type`: Count by synergy_type
- `by_complexity`: Count by complexity
- `avg_impact_score`: Average impact score
- `avg_confidence`: Average confidence
- `unique_areas`: Count of unique areas

**Note:** This endpoint was recently fixed to use SQL aggregates instead of loading records into memory, providing accurate counts regardless of database size.

---

## Summary

**Available Scripts:** 9+ scripts for synergy analytics  
**Most Comprehensive:** `show_synergy_stats.py` (by type, depth, complexity)  
**Best for Quick Check:** `check_synergy_types.py`  
**Best for Scoring Analysis:** `analyze_synergy_scoring.py`  
**Best for Type Investigation:** `diagnose_synergy_types.py`

All scripts support the standard database location: `data/ai_automation.db`  
Some scripts support Docker container access for production databases.

---

**Status:** ✅ **REVIEW COMPLETE**  
**Last Updated:** January 16, 2026
