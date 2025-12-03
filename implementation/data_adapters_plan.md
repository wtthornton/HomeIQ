# Data Adapters Plan - Option A Implementation

**Date:** December 3, 2025  
**Goal:** Create data adapters to bridge simulation JSON data with production training scripts

## Overview

Production training scripts expect:
- **GNN Synergy**: Data API service + Database synergies
- **Soft Prompt**: Database table `ask_ai_queries`

We have simulation data in JSON files. Adapters will convert JSON to the expected formats.

## Adapter Architecture

### 1. GNN Synergy Adapter

**Input:** `simulation/training_data/gnn_synergy_data.json`

**Requirements:**
- Extract entities from synergy data (device1, device2)
- Create mock Data API client that returns entities
- Populate database `synergy_opportunities` table with synergies from JSON

**Implementation:**
- `GNNDataAdapter` class
- Method: `prepare_training_environment(json_path, db_path)`
- Creates entities list from synergy pairs
- Inserts synergies into database
- Returns entities list and database path

### 2. Soft Prompt Adapter

**Input:** `simulation/training_data/soft_prompt_data.json`

**Requirements:**
- Create `ask_ai_queries` table if it doesn't exist
- Populate table with data from JSON
- Format: `original_query`, `suggestions` (JSON string)

**Implementation:**
- `SoftPromptDataAdapter` class
- Method: `prepare_training_database(json_path, db_path)`
- Creates table schema
- Inserts data from JSON
- Returns database path

## Integration Points

### Retraining Manager Integration

Update `RetrainingManager.retrain_model()` to:
1. Check if training data JSON exists
2. If yes, use adapter to prepare environment
3. Then run training script

### Training Script Modifications

**Option 1 (Preferred):** Use adapters before calling scripts
- Adapters prepare data
- Scripts run normally
- No script modifications needed

**Option 2:** Modify scripts to accept JSON input
- More invasive
- Requires script changes

## File Structure

```
simulation/src/retraining/adapters/
├── __init__.py
├── gnn_adapter.py      # GNN Synergy adapter
└── soft_prompt_adapter.py  # Soft Prompt adapter
```

## Implementation Steps

1. ✅ Create adapter directory structure
2. ✅ Implement GNN adapter
3. ✅ Implement Soft Prompt adapter
4. ✅ Update retraining manager to use adapters
5. ✅ Test adapters with simulation data
6. ✅ Re-run training

