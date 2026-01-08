# Dataset Research & Recommendations for HomeIQ

**Date:** January 7, 2026  
**Purpose:** Prioritized dataset recommendations for enhancing HomeIQ's ML capabilities  
**Focus:** Top-value sources with immediate integration potential

---

## Executive Summary

Based on research of smart home datasets and analysis of HomeIQ's current architecture, **3 datasets provide immediate high-value opportunities** for improving automation recommendations, NLP accuracy, and pattern detection quality.

**Top Priority (Immediate ROI):**
1. **Wyze Rule Recommendation Dataset** - Direct enhancement to rule recommendation system
2. **Home Assistant Requests Dataset** - NLP model fine-tuning for conversational AI
3. **Smart* / REFIT Sensor Datasets** - Activity recognition and energy pattern analysis

**Secondary Priority (Medium-term ROI):**
4. GHOST IoT Dataset - Security anomaly detection
5. ThoughtfulThings/Sasha - Command reasoning enhancement

---

## HomeIQ Current State Analysis

### ✅ Existing Capabilities
- **Pattern Detection:** Time-of-day patterns, co-occurrence patterns, device pairs
- **Synergy Detection:** Multi-device relationships, chains, scenes
- **Blueprint-First Architecture:** Community blueprint recommendations (completed Jan 2026)
- **Conversational AI:** Natural language automation creation
- **Rule Recommendation:** Device-to-blueprint matching with fit scores
- **Multi-Source Enrichment:** Weather, energy pricing, air quality, sports data

### ⚠️ Identified Gaps
- **Automation Adoption:** 0% (Create Automation button is TODO)
- **NLP Accuracy:** No external training data mentioned
- **Activity Recognition:** Not implemented
- **Energy Forecasting:** Not implemented
- **Anomaly Detection:** Not implemented
- **Pattern Validation:** Limited validation against real-world outcomes

---

## Top 3 Priority Recommendations

### 🥇 Priority 1: Wyze Rule Recommendation Dataset

**Source:** Hugging Face - `wyzelabs/RuleRecommendation`  
**Size:** 1M+ real rules from 300K+ users  
**License:** Check Hugging Face dataset card

#### Value Proposition

**Direct Alignment with HomeIQ:**
- HomeIQ already has rule recommendation infrastructure (blueprint matching, synergy detection)
- Wyze dataset provides **real-world automation patterns** from actual users
- Can train models to improve recommendation relevance and personalization

**Use Cases for HomeIQ:**

1. **Enhanced Rule Recommendation Engine**
   - Train collaborative filtering model on Wyze patterns
   - Improve device-to-automation matching accuracy
   - Personalize recommendations based on user's existing automations
   - **Impact:** Increase automation adoption rate from 0% → 30% target

2. **Pattern Mining Enhancement**
   - Discover common automation sequences not currently detected
   - Validate existing synergy detection patterns against real-world data
   - Identify device combinations that lead to successful automations
   - **Impact:** Improve pattern quality from current → 90% target

3. **Blueprint Opportunity Scoring**
   - Enhance blueprint fit score algorithm with Wyze patterns
   - Prioritize blueprints that match proven automation patterns
   - Reduce false positives in blueprint recommendations
   - **Impact:** Higher automation success rate (85% target)

#### Integration Strategy

**Phase 1: Data Ingestion (Week 1-2)**
```python
# Example: Load and preprocess Wyze dataset
from datasets import load_dataset

dataset = load_dataset("wyzelabs/RuleRecommendation")
# Filter for Home Assistant compatible patterns
# Extract: triggers, actions, device types, temporal patterns
```

**Phase 2: Model Training (Week 3-4)**
- Train recommendation model (collaborative filtering or neural network)
- Integrate with existing `ai-pattern-service/src/blueprint_opportunity/device_matcher.py`
- Enhance fit score calculation with learned patterns

**Phase 3: API Integration (Week 5-6)**
- Update `/api/v1/blueprint-opportunities/*` endpoints
- Add Wyze-pattern-based confidence scores
- A/B test against current blueprint-only recommendations

**Files to Modify:**
- `services/ai-pattern-service/src/blueprint_opportunity/device_matcher.py`
- `services/ai-pattern-service/src/synergy_detection/` (pattern validation)
- New service: `services/rule-recommendation-ml/` (optional microservice)

**Expected ROI:**
- **Automation Adoption:** +30% (from 0% baseline)
- **Pattern Quality:** +15-20% improvement
- **User Satisfaction:** Higher relevance in recommendations

---

### 🥈 Priority 2: Home Assistant Requests Dataset

**Source:** Hugging Face - `acon96/Home-Assistant-Requests`  
**Content:** User requests + assistant responses + structured device/intent contexts  
**License:** Check Hugging Face dataset card

#### Value Proposition

**Direct Alignment with HomeIQ:**
- HomeIQ uses conversational AI for automation creation
- Current NLP models likely not fine-tuned on Home Assistant-specific commands
- Dataset provides real user command patterns and intents

**Use Cases for HomeIQ:**

1. **NLP Model Fine-Tuning**
   - Fine-tune OpenAI/GPT models on Home Assistant command patterns
   - Improve entity extraction accuracy (device names, areas, actions)
   - Better intent classification (turn on, schedule, automate)
   - **Impact:** Reduce user back-and-forth in automation creation

2. **Command Parsing Enhancement**
   - Train on structured device/intent contexts from dataset
   - Improve accuracy of device selection and mapping
   - Better handling of ambiguous commands
   - **Impact:** Higher automation generation success rate

3. **Conversational Flow Improvement**
   - Learn from real user-assistant dialogue patterns
   - Improve clarification questions when intent is unclear
   - Better handling of complex multi-step automation requests
   - **Impact:** Better user experience, faster automation creation

#### Integration Strategy

**Phase 1: Data Analysis (Week 1)**
- Analyze dataset structure and command patterns
- Extract common intent patterns and entity mentions
- Identify gaps in current NLP coverage

**Phase 2: Fine-Tuning Pipeline (Week 2-3)**
- Create fine-tuning dataset from Home Assistant Requests
- Fine-tune OpenAI models (or open-source alternatives)
- Validate improvements on test set

**Phase 3: Integration (Week 4)**
- Update `services/ai-automation-service/` NLP pipelines
- Replace/enhance entity extraction with fine-tuned models
- Update conversational AI prompts with learned patterns

**Files to Modify:**
- `services/ai-automation-service/src/automation_generator/` (NLP pipelines)
- `shared/homeiq_automation/` (entity extraction, intent classification)
- New: `services/nlp-fine-tuning/` (optional service for continuous learning)

**Expected ROI:**
- **Automation Generation Accuracy:** +20-30% improvement
- **User Satisfaction:** Faster automation creation, less frustration
- **Reduced Support:** Fewer failed automation generations

---

### 🥉 Priority 3: Smart* / REFIT Sensor Datasets

**Sources:**
- Smart* Dataset: UMass Trace Repository (CC BY 4.0)
- REFIT Smart Home Dataset: Edinburgh Research (20 UK homes)

**Content:** Real sensor data (energy, environment, motion, occupancy)  
**License:** Open (CC BY 4.0 for Smart*)

#### Value Proposition

**New Capabilities for HomeIQ:**
- HomeIQ currently lacks activity recognition
- Energy forecasting could enhance energy pricing integrations
- Anomaly detection could improve system reliability

**Use Cases for HomeIQ:**

1. **Activity Recognition (New Feature)**
   - Train models on Smart* / REFIT sensor patterns
   - Detect user activities from device usage patterns
   - Create activity-based automations (e.g., "when user wakes up")
   - **Impact:** New automation trigger type, better personalization

2. **Energy Pattern Analysis**
   - Analyze energy consumption patterns from REFIT dataset
   - Forecast peak usage periods (complement existing energy pricing data)
   - Suggest energy-saving automations
   - **Impact:** Cost savings for users, new automation recommendations

3. **Anomaly Detection**
   - Train anomaly detection models on normal sensor patterns
   - Detect unusual device behavior (security, maintenance)
   - Alert users to potential issues
   - **Impact:** Proactive maintenance, security enhancements

#### Integration Strategy

**Phase 1: Activity Recognition (Weeks 1-4)**
- Preprocess Smart* / REFIT datasets for activity labels
- Train sequence classification models (LSTM/Transformer)
- Create new activity recognition service
- Integrate with pattern detection service

**Phase 2: Energy Forecasting (Weeks 5-8)**
- Analyze REFIT energy consumption patterns
- Train time series forecasting models
- Integrate with existing energy pricing service
- Create energy-saving automation recommendations

**Phase 3: Anomaly Detection (Weeks 9-12)**
- Train autoencoder models on normal device patterns
- Create anomaly detection service
- Integrate alerts with health dashboard
- Trigger security/maintenance automations

**Files to Create:**
- `services/activity-recognition/` (new microservice)
- `services/energy-forecasting/` (new microservice or enhance existing)
- `services/anomaly-detection/` (new microservice)

**Expected ROI:**
- **New Features:** Activity recognition, energy forecasting, anomaly detection
- **User Value:** Proactive automations, cost savings, security
- **Competitive Advantage:** Advanced ML capabilities beyond basic pattern detection

---

## Secondary Recommendations (Lower Priority)

### 4. GHOST IoT Dataset
**Use Case:** Network-level anomaly detection for security  
**Priority:** Medium (security enhancement, but HomeIQ focuses on single-home deployment)  
**ROI:** Medium - Useful for multi-device security monitoring

### 5. ThoughtfulThings/Sasha Smart Home Reasoning
**Use Case:** Enhance command reasoning capabilities  
**Priority:** Low (Home Assistant Requests dataset is more relevant)  
**ROI:** Low - Synthetic data, less valuable than real user data

### 6. CASAS / ARAS Activity Datasets
**Use Case:** Activity recognition (alternative to Smart*/REFIT)  
**Priority:** Low (Smart*/REFIT are more comprehensive)  
**ROI:** Low - Redundant with Priority 3 datasets

---

## Implementation Roadmap

### Q1 2026: Quick Wins (Wyze + Home Assistant Requests)

**Month 1-2: Wyze Dataset Integration**
- Load and analyze Wyze rule recommendation dataset
- Train recommendation model
- Integrate with blueprint opportunity engine
- **Deliverable:** Enhanced rule recommendations with Wyze patterns

**Month 3: Home Assistant Requests Integration**
- Fine-tune NLP models on Home Assistant Requests dataset
- Update conversational AI pipelines
- **Deliverable:** Improved NLP accuracy for automation creation

### Q2 2026: New Capabilities (Smart*/REFIT)

**Months 4-6: Activity Recognition**
- Implement activity recognition service
- Train models on Smart*/REFIT datasets
- Integrate with pattern detection
- **Deliverable:** Activity-based automation triggers

**Months 7-9: Energy Forecasting & Anomaly Detection**
- Implement energy forecasting
- Implement anomaly detection
- Integrate with health dashboard
- **Deliverable:** Energy optimization and proactive maintenance features

---

## Success Metrics

### Priority 1 (Wyze Dataset)
- **Automation Adoption Rate:** 0% → 30% (target from RECOMMENDATIONS_FEASIBILITY_ANALYSIS.md)
- **Pattern Quality Score:** Current → 90% (target)
- **Blueprint Fit Accuracy:** +15% improvement

### Priority 2 (Home Assistant Requests)
- **NLP Entity Extraction Accuracy:** +20-30% improvement
- **Automation Generation Success Rate:** Current → 85% (target)
- **User Back-and-Forth Cycles:** -50% reduction

### Priority 3 (Smart*/REFIT)
- **Activity Recognition Accuracy:** >85% (new metric)
- **Energy Forecast Accuracy:** >80% (new metric)
- **Anomaly Detection Precision:** >90% (new metric)

---

## Data Access & Legal Considerations

### Hugging Face Datasets
- **Access:** Use `datasets` library: `load_dataset("dataset_name")`
- **License:** Check each dataset's card on Hugging Face
- **Storage:** Datasets can be cached locally or streamed

### External Datasets (Smart*, REFIT)
- **Access:** Download from original sources (UMass, Edinburgh Research)
- **License:** CC BY 4.0 for Smart*, check REFIT license
- **Storage:** Larger datasets, consider local storage or cloud storage

### Data Privacy
- **Training Data:** Use datasets for model training only (no user data sharing)
- **User Data:** HomeIQ user data stays local (single-home deployment)
- **Compliance:** No GDPR/privacy concerns if using datasets for training only

---

## Technical Requirements

### Infrastructure
- **Compute:** Model training can be done offline, deployed models run on NUC
- **Storage:** Hugging Face datasets can be streamed or cached (~GB scale)
- **ML Framework:** PyTorch/TensorFlow for training, ONNX for deployment

### Integration Points
- **Existing Services:**
  - `ai-pattern-service` (pattern detection, blueprint opportunities)
  - `ai-automation-service` (NLP, conversational AI)
  - `health-dashboard` (visualization, alerts)
- **New Services:**
  - `rule-recommendation-ml` (optional, for Wyze model)
  - `activity-recognition` (for Smart*/REFIT)
  - `energy-forecasting` (for REFIT)
  - `anomaly-detection` (for Smart*/REFIT)

---

## Next Steps

1. **Validate Dataset Access:** Test loading Wyze and Home Assistant Requests datasets
2. **Proof of Concept:** Train small model on Wyze dataset subset, measure improvement
3. **Architecture Design:** Design integration points for each dataset
4. **Implementation Plan:** Create detailed implementation plan for Priority 1 (Wyze)
5. **Resource Allocation:** Allocate development time for Q1 2026 implementation

---

## References

- **Wyze Rule Recommendation:** https://huggingface.co/datasets/wyzelabs/RuleRecommendation
- **Home Assistant Requests:** https://huggingface.co/datasets/acon96/Home-Assistant-Requests
- **Smart* Dataset:** https://traces.cs.umass.edu/docs/traces/smartstar/
- **REFIT Dataset:** https://www.research.ed.ac.uk/en/datasets/refit-smart-home-dataset/
- **HomeIQ Pattern Recommendations:** `services/ai-pattern-service/tests/PATTERNS_SYNERGIES_IMPROVEMENT_RECOMMENDATIONS.md`
- **HomeIQ Feasibility Analysis:** `services/ai-pattern-service/tests/RECOMMENDATIONS_FEASIBILITY_ANALYSIS.md`
