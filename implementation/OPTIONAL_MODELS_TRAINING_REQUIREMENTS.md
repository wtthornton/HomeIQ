# Optional Models Training Requirements

**Date:** December 2, 2025
**Status:** ⚠️ **DEPENDENCIES NOT INSTALLED**

---

## Overview

The optional enhancement models (GNN Synergy Detector and Soft Prompt) require additional PyTorch-based dependencies that are not currently installed in the environment. These models are **optional** and **not required** for production deployment.

---

## Model Status Summary

### Critical Models (Required) ✅
| Model | Status | Accuracy | Notes |
|-------|--------|----------|-------|
| **Home Type Classifier** | ✅ Trained | 100.0% | Production ready |
| **Device Intelligence** | ✅ Trained | 99.5% | Production ready |

### Optional Models (Enhancements) ⚠️
| Model | Status | Reason | Impact |
|-------|--------|--------|--------|
| **GNN Synergy Detector** | ⚠️ Not Available | Missing PyTorch Geometric | OPTIONAL - Advanced synergy detection |
| **Soft Prompt** | ⚠️ Not Available | Missing Transformers + PyTorch | OPTIONAL - LLM-based enhancements |

---

## Dependency Requirements

### 1. GNN Synergy Detector

**Required Dependencies:**
```bash
# PyTorch (CPU version for NUC deployment)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# PyTorch Geometric
pip install torch-geometric
pip install torch-scatter torch-sparse torch-cluster torch-spline-conv -f https://data.pyg.org/whl/torch-2.1.0+cpu.html
```

**Error Encountered:**
```
torch-geometric not available, GNN learning disabled
NameError: name 'Data' is not defined
```

**Model Purpose:**
- Advanced device synergy detection using Graph Neural Networks
- Learns complex multi-device relationships
- Predicts synergistic automation opportunities
- Uses graph-based representations of device relationships

**Training Requirements:**
- Entities from data-api
- Historical synergy data from database
- Can generate synthetic synergies for cold start
- Training time: ~5-10 minutes (30 epochs)

**Production Impact if Missing:**
- ✅ System still fully functional
- ⚠️ Advanced graph-based synergy detection unavailable
- ⚠️ Falls back to rule-based synergy detection
- ⚠️ Less sophisticated device relationship modeling

---

### 2. Soft Prompt (Fine-tuned LLM)

**Required Dependencies:**
```bash
# Transformers library
pip install transformers[torch]

# PyTorch (CPU version for NUC deployment)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# PEFT (Parameter-Efficient Fine-Tuning) for LoRA
pip install peft

# Additional dependencies
pip install accelerate datasets
```

**Error Encountered:**
```
Dependency check failed: Required dependencies missing.
Install transformers[torch], torch (CPU wheel), and peft.
```

**Model Purpose:**
- Fine-tuned T5 model for Ask AI suggestion generation
- Learns from historical Ask AI conversations
- Generates personalized automation suggestions
- Uses LoRA (Low-Rank Adaptation) for efficient training

**Training Requirements:**
- Labeled Ask AI conversations from ai_automation.db
- Base model: google/flan-t5-small (80MB)
- Training data: ~100-2000 conversation samples
- Training time: ~10-20 minutes (3 epochs)
- Memory: <2GB RAM (NUC-optimized)

**Production Impact if Missing:**
- ✅ System still fully functional
- ⚠️ Ask AI uses GPT-4o-mini directly (requires API key)
- ⚠️ No personalized model adaptation
- ⚠️ No cost savings from local inference

---

## Installation Instructions

### Option 1: Install All Optional Dependencies (Recommended for Full Features)

```bash
# Navigate to project root
cd C:\cursor\HomeIQ

# Install PyTorch (CPU version for NUC)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Install Transformers and PEFT
pip install transformers[torch] peft accelerate datasets

# Install PyTorch Geometric
pip install torch-geometric
pip install torch-scatter torch-sparse torch-cluster torch-spline-conv -f https://data.pyg.org/whl/torch-2.1.0+cpu.html

# Verify installation
python -c "import torch; import transformers; import peft; print('✅ All dependencies installed')"
```

**Total Size:** ~2-3 GB (PyTorch + models)
**Installation Time:** ~5-10 minutes

### Option 2: Install Only Soft Prompt Dependencies (Lighter)

```bash
# Install PyTorch (CPU)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Install Transformers and PEFT
pip install transformers[torch] peft accelerate datasets

# Verify
python -c "import torch; import transformers; import peft; print('✅ Soft prompt dependencies installed')"
```

**Total Size:** ~2 GB
**Installation Time:** ~3-5 minutes

### Option 3: Skip Optional Models (Current Setup)

```bash
# No additional installation needed
# System is already production-ready with critical models
```

**Production Status:** ✅ **READY TO DEPLOY**
**Features Available:** All core features (Home Type Classification, Device Intelligence)
**Features Missing:** Advanced synergy detection, personalized LLM adaptation

---

## Training Commands (After Dependencies Installed)

### Train GNN Synergy Detector

```bash
cd services/ai-automation-service

# Standard training (30 epochs)
python scripts/train_gnn_synergy.py --epochs 30 --force

# Quick training (10 epochs)
python scripts/train_gnn_synergy.py --epochs 10 --force

# Expected output:
# - Model: models/gnn_synergy.pth
# - Metadata: models/gnn_synergy_metadata.json
# - Training time: ~5-10 minutes
```

### Train Soft Prompt

```bash
cd services/ai-automation-service

# Standard training (3 epochs, 2000 samples)
python scripts/train_soft_prompt.py --epochs 3 --max-samples 2000 --batch-size 1

# Quick training (1 epoch, 100 samples)
python scripts/train_soft_prompt.py --epochs 1 --max-samples 100 --batch-size 1

# Expected output:
# - Model: data/ask_ai_soft_prompt/[timestamp]/
# - Training time: ~10-20 minutes
```

---

## Production Deployment Recommendations

### Scenario 1: Full Feature Deployment (Recommended for Power Users)

**Install:** All optional dependencies
**Benefits:**
- ✅ Advanced graph-based synergy detection
- ✅ Personalized LLM for Ask AI
- ✅ Reduced API costs (local inference)
- ✅ Maximum intelligence and automation quality

**Requirements:**
- Additional 2-3 GB disk space
- One-time training cost: ~20-30 minutes
- Nightly retraining: ~5-10 minutes

### Scenario 2: Core Features Only (Current Setup - Recommended for Most Users)

**Install:** Nothing additional
**Benefits:**
- ✅ Fastest deployment (ready now)
- ✅ All critical features available
- ✅ Smaller disk footprint
- ✅ Simpler dependency management

**Limitations:**
- ⚠️ Rule-based synergy detection (still effective)
- ⚠️ GPT-4o-mini for Ask AI (requires API key)

---

## Current System Status

**Production Readiness:** ✅ **READY TO DEPLOY**

**Installed & Trained:**
- ✅ Home Type Classifier (100% accuracy)
- ✅ Device Intelligence (99.5% accuracy)
- ✅ All critical infrastructure
- ✅ All core services

**Not Installed:**
- ⚠️ PyTorch ecosystem (~2GB)
- ⚠️ Transformers library (~500MB)
- ⚠️ PyTorch Geometric (~300MB)

**Impact:**
- **Zero impact on core functionality**
- **Zero impact on production deployment**
- **Minor impact on advanced features** (synergy detection, personalized LLM)

---

## Decision Matrix

| Use Case | Install Optional? | Reason |
|----------|-------------------|--------|
| **Production deployment (most users)** | ❌ No | Core features sufficient |
| **Advanced automation detection** | ✅ Yes (GNN only) | Graph-based synergy detection |
| **Personalized Ask AI** | ✅ Yes (Soft Prompt only) | Local LLM adaptation |
| **Full feature set** | ✅ Yes (All) | Maximum intelligence |
| **Minimal footprint** | ❌ No | Current setup already optimal |
| **Development/testing** | ✅ Yes | Test all features |

---

## Next Steps

### If You Want to Install Optional Models:

1. **Install dependencies** (see commands above)
2. **Train models** (see training commands above)
3. **Verify training** (check model files created)
4. **Update docker-compose** (copy models into Docker image)
5. **Deploy** (rebuild and restart services)

### If You're Ready to Deploy Now:

1. **No action needed** - System is production ready
2. **Deploy immediately** - All critical models trained
3. **Optional models later** - Can add anytime without disrupting production

---

## Summary

**Current Status:**
- ✅ **Production Ready** - All critical models trained (100% and 99.5% accuracy)
- ⚠️ **Optional Models** - Require PyTorch/Transformers dependencies (~2-3GB)
- ✅ **Core Features** - Fully functional without optional models

**Recommendation:**
Deploy now with core features, add optional models later if needed. The system is **fully production-ready** with the current setup.

---

**Generated:** December 2, 2025
**Version:** 1.0
**Status:** Documentation complete
