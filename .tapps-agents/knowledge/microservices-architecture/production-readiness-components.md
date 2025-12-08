# Production Readiness Components Guide

**Last Updated:** November 28, 2025  
**Epic:** Epic 43 - Model Quality & Documentation  
**Context:** Single-House NUC Deployment

---

## Overview

This document explains the purpose, dependencies, and resource requirements for each component in the HomeIQ production readiness pipeline. Use this guide to make informed decisions about what components to deploy based on your needs and hardware constraints.

---

## Component Classification

### Critical Components (Required for Production)

These components are **required** for a production-ready HomeIQ system. The system will not be marked as production-ready if any critical component fails.

### Optional Components (Enhancements)

These components provide additional capabilities but are **not required** for basic production deployment. The system can be production-ready even if optional components are not configured.

---

## Critical Components

### 1. Build System

**Purpose:** Compiles and packages all Docker images for deployment.

**Dependencies:**
- Docker and Docker Compose
- All service source code
- Service-specific dependencies (Python packages, Node.js, etc.)

**Resource Requirements:**
- CPU: Moderate (during build)
- Memory: 2-4GB during build
- Disk: ~2-5GB for images

**Impact if Skipped:**
- Cannot deploy services
- System cannot run

**When to Skip:**
- Only if images are already built and up-to-date
- Use `--skip-build` flag

---

### 2. Deployment System

**Purpose:** Starts all services using Docker Compose.

**Dependencies:**
- Built Docker images
- Docker Compose configuration
- Required environment variables

**Resource Requirements:**
- CPU: Low (orchestration only)
- Memory: Varies by services deployed
- Disk: Minimal

**Impact if Skipped:**
- Services not running
- System unavailable

**When to Skip:**
- Only if services are already running
- Use `--skip-deploy` flag

---

### 3. Smoke Tests

**Purpose:** Validates that critical services are running and responding correctly.

**Dependencies:**
- All services deployed and running
- Network connectivity
- Service health endpoints

**Resource Requirements:**
- CPU: Low (HTTP requests)
- Memory: Minimal
- Network: Low bandwidth

**Impact if Skipped:**
- Cannot verify system health
- Unknown if services are working correctly

**When to Skip:**
- Only for rapid iteration during development
- Use `--skip-smoke` flag

---

### 4. Test Data Generation

**Purpose:** Generates synthetic home data for model training.

**Dependencies:**
- Python 3.11+
- Required Python packages
- Disk space for data files

**Resource Requirements:**
- CPU: Moderate (data generation)
- Memory: 1-2GB
- Disk: ~100MB per 100 homes

**Impact if Skipped:**
- Cannot train models
- Models will not be available

**When to Skip:**
- Only if training data already exists
- Use `--skip-generation` flag

---

### 5. Home Type Classifier Model

**Purpose:** Classifies homes into categories (apartment, standard_home, etc.) based on device patterns and usage.

**What it does:**
- Analyzes device distribution (security, climate, lighting, etc.)
- Examines event patterns and peak usage hours
- Classifies home type for personalized recommendations

**Dependencies:**
- Synthetic home data (from test data generation)
- scikit-learn
- Trained model saved to disk

**Resource Requirements:**
- CPU: Moderate (training: 1-2 minutes)
- Memory: 500MB-1GB during training
- Disk: ~10MB for model file

**Quality Thresholds:**
- Minimum Accuracy: 90%
- Minimum Precision: 85%
- Minimum Recall: 85%
- Minimum F1 Score: 85%

**Impact if Failed:**
- Cannot provide home-type-specific recommendations
- System marked as NOT production-ready

**When to Skip:**
- Never (critical component)
- Use `--allow-low-quality` to proceed with below-threshold models

---

### 6. Device Intelligence Model

**Purpose:** Analyzes device health, performance, and provides intelligent insights about device usage patterns.

**What it does:**
- Detects device anomalies and health issues
- Analyzes device performance metrics
- Provides device utilization scores
- Generates device name enhancement suggestions

**Dependencies:**
- Device data from Home Assistant
- scikit-learn
- Trained model saved to disk

**Resource Requirements:**
- CPU: Moderate (training: <1 minute)
- Memory: 500MB-1GB during training
- Disk: ~5MB for model file

**Quality Thresholds:**
- Minimum Accuracy: 85%
- Minimum Precision: 80%
- Minimum Recall: 80%
- Minimum F1 Score: 80%

**Impact if Failed:**
- Cannot provide device intelligence features
- No device health monitoring
- System marked as NOT production-ready

**When to Skip:**
- Never (critical component)
- Use `--allow-low-quality` to proceed with below-threshold models

---

## Optional Components

### 7. GNN Synergy Detector Model

**Purpose:** Detects device synergies and correlations using Graph Neural Networks (GNN).

**What it does:**
- Identifies devices that work well together
- Discovers usage patterns across device groups
- Provides advanced automation suggestions

**Dependencies:**
- OpenAI API key (`OPENAI_API_KEY`)
- Synthetic home data
- PyTorch Geometric (if applicable)
- OpenAI API access

**Resource Requirements:**
- CPU: High (training: 5-15 minutes)
- Memory: 2-4GB during training
- Disk: ~50MB for model file
- Network: OpenAI API calls

**Quality Thresholds:**
- Minimum Accuracy: 70% (if metrics available)
- No strict validation (optional component)

**Impact if Not Configured:**
- No advanced synergy detection
- Basic automation suggestions still available
- System can still be production-ready

**When to Skip:**
- If OpenAI API key not available
- If advanced features not needed
- Automatically skipped if `OPENAI_API_KEY` not set

**Cost Considerations:**
- Requires OpenAI API usage (pay-per-use)
- Training may use significant API credits

---

### 8. Soft Prompt Model

**Purpose:** Enhances AI automation suggestions using soft prompt techniques.

**What it does:**
- Improves quality of automation suggestions
- Personalizes suggestions based on home patterns
- Enhances natural language understanding

**Dependencies:**
- OpenAI API key (`OPENAI_API_KEY`)
- Synthetic home data
- OpenAI API access

**Resource Requirements:**
- CPU: Moderate (training: 3-10 minutes)
- Memory: 1-2GB during training
- Disk: ~20MB for model file
- Network: OpenAI API calls

**Quality Thresholds:**
- Minimum Accuracy: 70% (if metrics available)
- No strict validation (optional component)

**Impact if Not Configured:**
- Basic automation suggestions still work
- Enhanced personalization not available
- System can still be production-ready

**When to Skip:**
- If OpenAI API key not available
- If enhanced suggestions not needed
- Automatically skipped if `OPENAI_API_KEY` not set

**Cost Considerations:**
- Requires OpenAI API usage (pay-per-use)
- Training may use significant API credits

---

## Component Dependency Graph

```
Build System
    ↓
Deployment System
    ↓
Smoke Tests
    ↓
Test Data Generation
    ↓
    ├─→ Home Type Classifier (CRITICAL)
    ├─→ Device Intelligence (CRITICAL)
    ├─→ GNN Synergy Detector (OPTIONAL) ──→ Requires OPENAI_API_KEY
    └─→ Soft Prompt (OPTIONAL) ───────────→ Requires OPENAI_API_KEY
```

---

## Decision Tree: What Do I Need?

### Scenario 1: Basic Production Deployment

**Goal:** Get system running with core features

**Required:**
- ✅ Build System
- ✅ Deployment System
- ✅ Smoke Tests
- ✅ Test Data Generation
- ✅ Home Type Classifier
- ✅ Device Intelligence

**Optional:**
- ❌ GNN Synergy (skip if no OpenAI key)
- ❌ Soft Prompt (skip if no OpenAI key)

**Result:** ✅ Production-ready system with core features

---

### Scenario 2: Full-Featured Deployment

**Goal:** All features including advanced AI capabilities

**Required:**
- ✅ All Critical Components
- ✅ GNN Synergy Detector
- ✅ Soft Prompt

**Requirements:**
- OpenAI API key configured
- Budget for API usage

**Result:** ✅ Production-ready system with all features

---

### Scenario 3: Resource-Constrained NUC

**Goal:** Deploy on limited hardware (8GB RAM, i3 CPU)

**Required:**
- ✅ All Critical Components
- ⚠️  Use `--quick` flag for smaller dataset (10 homes, 7 days)
- ⚠️  Skip optional components to save resources

**Optional:**
- ❌ GNN Synergy (resource-intensive)
- ❌ Soft Prompt (resource-intensive)

**Result:** ✅ Production-ready system optimized for limited resources

---

### Scenario 4: Development/Testing

**Goal:** Rapid iteration during development

**Can Skip:**
- ⚠️  Build (if images already built)
- ⚠️  Deploy (if services already running)
- ⚠️  Smoke Tests (for faster iteration)
- ⚠️  Data Generation (if data exists)
- ⚠️  Training (if models exist)

**Use Flags:**
```bash
python scripts/prepare_for_production.py \
    --skip-build \
    --skip-deploy \
    --skip-smoke \
    --skip-generation \
    --skip-training
```

**Result:** ⚠️  Quick validation, not full production readiness

---

## Quality Validation

### How Quality Validation Works

1. **After Training:** Each model's metrics are validated against defined thresholds
2. **Threshold Check:** Metrics (accuracy, precision, recall, F1) compared to minimums
3. **Result:**
   - ✅ **Passed:** All metrics meet thresholds → Model approved
   - ❌ **Failed:** Metrics below thresholds → Training marked as failed
   - ⚠️  **Warning:** Metrics below thresholds but `--allow-low-quality` used → Proceeds with warning

### Quality Thresholds by Model

| Model | Accuracy | Precision | Recall | F1 Score |
|-------|----------|-----------|--------|----------|
| Home Type Classifier | ≥ 90% | ≥ 85% | ≥ 85% | ≥ 85% |
| Device Intelligence | ≥ 85% | ≥ 80% | ≥ 80% | ≥ 80% |
| GNN Synergy | ≥ 70%* | - | - | - |
| Soft Prompt | ≥ 70%* | - | - | - |

*Optional models - thresholds only checked if metrics available

### Handling Low-Quality Models

**If Model Fails Quality Validation:**

1. **Review Training Data:**
   - Check for data imbalance
   - Verify data quality
   - Ensure sufficient training samples

2. **Adjust Model Parameters:**
   - Review model configuration
   - Try different hyperparameters
   - Increase training data size

3. **Proceed Anyway (Advanced):**
   - Use `--allow-low-quality` flag
   - System will proceed with warning
   - Not recommended for production

---

## Resource Usage Guide

### Single-House NUC Deployment

**Typical Hardware:**
- Intel NUC i3/i5
- 8-16GB RAM
- 128-256GB SSD

**Resource Allocation:**

| Component | CPU Usage | Memory | Disk | Duration |
|-----------|-----------|--------|------|----------|
| Build | High | 2-4GB | 2-5GB | 5-15 min |
| Deploy | Low | Varies | Minimal | <1 min |
| Smoke Tests | Low | Minimal | Minimal | <30 sec |
| Data Generation | Moderate | 1-2GB | ~100MB | 10-30 min |
| Home Type Training | Moderate | 500MB-1GB | ~10MB | 1-2 min |
| Device Intelligence | Moderate | 500MB-1GB | ~5MB | <1 min |
| GNN Synergy | High | 2-4GB | ~50MB | 5-15 min |
| Soft Prompt | Moderate | 1-2GB | ~20MB | 3-10 min |

**Total Estimated:**
- **Critical Only:** ~15-45 minutes, 4-8GB RAM peak
- **With Optional:** ~25-70 minutes, 6-12GB RAM peak

---

## Troubleshooting

### Model Quality Issues

**Problem:** Model fails quality validation

**Solutions:**
1. Check training data quality and quantity
2. Review model configuration
3. Verify thresholds are appropriate for your use case
4. Use `--allow-low-quality` if acceptable for your deployment

### Resource Constraints

**Problem:** Out of memory during training

**Solutions:**
1. Use `--quick` flag for smaller dataset
2. Skip optional components
3. Close other applications
4. Consider upgrading hardware

### Missing Dependencies

**Problem:** Training fails due to missing packages

**Solutions:**
1. Run pre-flight validation (automatic)
2. Install missing packages
3. Check environment variables
4. Review error messages for specific fixes

---

## Related Documentation

- **Production Readiness Script:** `scripts/prepare_for_production.py`
- **Epic 42:** Status Reporting & Validation
- **Epic 43:** Model Quality & Documentation
- **Architecture:** `docs/architecture/tech-stack.md`
- **Coding Standards:** `docs/architecture/coding-standards.md`

---

**Document Created:** November 28, 2025  
**Epic:** Epic 43 - Story 43.2  
**Status:** ✅ Complete

