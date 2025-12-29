# Fine-Tuning Guide for HomeIQ Experts

**Version**: 1.0  
**Last Updated**: January 2025  
**Status**: Preparation Guide (Fine-tuning not yet enabled)

## Overview

This guide documents the fine-tuning preparation process for HomeIQ project experts. Fine-tuning enables domain-specific model adaptation beyond RAG (Retrieval-Augmented Generation) for improved accuracy and domain-specific knowledge.

**Current Status**: All 13 project experts have `fine_tuned: false` in `.tapps-agents/experts.yaml`. This guide prepares for future fine-tuning when training data becomes available.

## Fine-Tuning vs RAG-Only

### When to Use RAG-Only (Current Setup)

✅ **RAG-Only is sufficient when:**
- Knowledge base is comprehensive and up-to-date (162 files currently)
- Domain knowledge is well-documented in markdown files
- Expert responses need to reference specific documentation
- Knowledge changes frequently and needs easy updates
- No specialized domain language or patterns beyond documentation

**Current Status**: All experts use RAG-only, which is working well for HomeIQ's documented knowledge domains.

### When to Enable Fine-Tuning

✅ **Fine-tuning is beneficial when:**
- Domain has specialized terminology or patterns not in documentation
- Expert needs to generate code patterns specific to HomeIQ architecture
- Response quality needs improvement beyond RAG retrieval
- Domain has implicit knowledge not easily documented
- High-frequency expert usage justifies training investment

**Example Domains for Fine-Tuning:**
- `microservices-architecture` - HomeIQ-specific service patterns
- `home-assistant` - Home Assistant API integration patterns
- `ai-machine-learning` - HomeIQ AI automation patterns

## Training Data Requirements

### Data Format

Fine-tuning requires structured training data in JSON format:

```json
{
  "messages": [
    {
      "role": "system",
      "content": "You are the HomeIQ Microservices Architecture Expert. You provide guidance on service design, communication patterns, and architecture decisions specific to HomeIQ's 30+ microservice ecosystem."
    },
    {
      "role": "user",
      "content": "How should I design a new service that integrates with InfluxDB and Home Assistant?"
    },
    {
      "role": "assistant",
      "content": "For a new HomeIQ service integrating with InfluxDB and Home Assistant, follow these patterns:\n\n1. **Direct InfluxDB Writes** (Epic 31 pattern):\n   - Write directly to InfluxDB, no intermediate services\n   - Use influxdb-client library\n   - Follow bucket naming: `home_assistant_events`\n\n2. **Home Assistant Integration**:\n   - Use WebSocket API for real-time events\n   - Implement fallback to REST API\n   - Handle connection management with retry logic\n\n3. **Service Structure**:\n   - Standalone service (no service-to-service HTTP)\n   - Query via data-api for reads\n   - Port assignment: Check services/ directory\n\nSee: services/websocket-ingestion for reference implementation."
    }
  ]
}
```

### Data Structure

**Required Fields:**
- `messages`: Array of message objects
- `role`: `system`, `user`, or `assistant`
- `content`: Message text

**System Message Guidelines:**
- Define expert role and domain
- Specify HomeIQ-specific context
- Include key architectural patterns (Epic 31, etc.)

**User Message Guidelines:**
- Real questions from development
- Common consultation scenarios
- Edge cases and complex queries

**Assistant Message Guidelines:**
- Accurate, HomeIQ-specific responses
- Reference actual code patterns
- Include code examples when relevant
- Link to knowledge base files

### Data Quality Standards

**Minimum Requirements:**
- ✅ 100+ training examples per domain (minimum)
- ✅ 500+ examples for high-priority domains (recommended)
- ✅ Diverse question types (architecture, implementation, troubleshooting)
- ✅ Accurate responses verified by domain experts
- ✅ No hallucinations or incorrect information
- ✅ Consistent formatting and style

**Quality Checklist:**
- [ ] All responses verified for accuracy
- [ ] Code examples tested and working
- [ ] Architecture patterns match current HomeIQ patterns
- [ ] No outdated information (Epic references current)
- [ ] Responses reference knowledge base when appropriate
- [ ] Style consistent across examples

## Domain-Specific Training Data Needs

### High-Priority Domains for Fine-Tuning

Based on expert usage frequency, domain complexity, and project-specific knowledge needs:

#### 1. Microservices Architecture (`expert-microservices`)
**Priority**: 🔴 High  
**Rationale**: 
- Largest knowledge base (68 files)
- HomeIQ-specific patterns (Epic 31, hybrid architecture)
- Complex service communication patterns
- High consultation frequency

**Training Data Needs:**
- Service creation patterns
- InfluxDB integration patterns
- Home Assistant integration patterns
- Service communication (Epic 39)
- Architecture decision scenarios

**Estimated Examples**: 500-1000

#### 2. Home Assistant (`expert-home-assistant`)
**Priority**: 🔴 High  
**Rationale**:
- Core integration domain
- WebSocket API patterns
- Home Assistant-specific code generation
- High consultation frequency

**Training Data Needs:**
- WebSocket API usage
- REST API fallback patterns
- Entity management
- Automation YAML generation
- Service call patterns

**Estimated Examples**: 300-500

#### 3. AI & Machine Learning (`expert-ai-ml`)
**Priority**: 🟡 Medium-High  
**Rationale**:
- AI automation patterns
- Pattern detection algorithms
- HomeIQ-specific AI workflows

**Training Data Needs:**
- AI automation generation
- Pattern detection strategies
- Recommendation system patterns
- LLM integration patterns

**Estimated Examples**: 300-500

#### 4. Time-Series Analytics (`expert-time-series`)
**Priority**: 🟡 Medium  
**Rationale**:
- InfluxDB query patterns
- Data aggregation strategies
- Performance optimization

**Training Data Needs:**
- InfluxDB query patterns
- Schema design decisions
- Aggregation strategies
- Performance optimization

**Estimated Examples**: 200-300

#### 5. IoT & Home Automation (`expert-iot`)
**Priority**: 🟡 Medium  
**Rationale**:
- Device management patterns
- Protocol integration
- Automation rules

**Training Data Needs:**
- Device protocol integration
- Automation rule patterns
- Device health monitoring
- Protocol-specific patterns

**Estimated Examples**: 200-300

### Lower-Priority Domains

These domains may benefit from fine-tuning but have lower priority:

- `frontend-ux` - React/TypeScript patterns (framework experts may suffice)
- `automation-strategy` - Business logic, RAG may be sufficient
- `energy-management` - Well-documented, RAG may be sufficient
- `security-privacy` - Built-in security expert may suffice
- `proactive-intelligence` - Business logic, RAG may be sufficient
- `smart-home-ux` - UX principles, RAG may be sufficient
- `energy-economics` - Business logic, RAG may be sufficient
- `pattern-analytics` - Statistical patterns, RAG may be sufficient
- `device-ecosystem` - Well-documented, RAG may be sufficient

## Fine-Tuning Process Overview

### Step 1: Data Collection

1. **Extract Consultation History**
   - Review expert consultation logs
   - Extract user queries and expert responses
   - Filter for high-quality interactions

2. **Generate Synthetic Examples**
   - Create scenarios based on knowledge base
   - Generate question-answer pairs
   - Validate with domain experts

3. **Manual Curation**
   - Domain experts review examples
   - Correct inaccuracies
   - Add missing patterns

### Step 2: Data Preparation

1. **Format Conversion**
   - Convert to JSON format
   - Structure as message arrays
   - Validate format

2. **Quality Validation**
   - Check for accuracy
   - Verify code examples
   - Ensure consistency

3. **Data Splitting**
   - Training set: 80%
   - Validation set: 10%
   - Test set: 10%

### Step 3: Fine-Tuning Configuration

**Update `.tapps-agents/experts.yaml`:**

```yaml
experts:
  - expert_id: expert-microservices
    expert_name: Microservices Architecture Expert
    primary_domain: microservices-architecture
    rag_enabled: true
    fine_tuned: true  # Enable fine-tuning
    fine_tuning_config:
      model: "gpt-4"  # Base model
      training_data: ".tapps-agents/training-data/microservices-architecture.jsonl"
      epochs: 3
      learning_rate: 1e-5
```

### Step 4: Fine-Tuning Execution

1. **Upload Training Data**
   - Prepare JSONL file
   - Upload to fine-tuning service
   - Monitor upload progress

2. **Start Fine-Tuning Job**
   - Configure hyperparameters
   - Start training job
   - Monitor training progress

3. **Validation**
   - Test on validation set
   - Evaluate response quality
   - Compare to RAG-only baseline

### Step 5: Deployment

1. **Model Integration**
   - Update expert configuration
   - Deploy fine-tuned model
   - Test in staging environment

2. **A/B Testing**
   - Compare fine-tuned vs RAG-only
   - Measure improvement metrics
   - Collect user feedback

3. **Rollout**
   - Gradual rollout to production
   - Monitor performance
   - Collect metrics

## Fine-Tuning Checklist

### Pre-Fine-Tuning

- [ ] Identify high-priority domains for fine-tuning
- [ ] Collect consultation history and examples
- [ ] Generate synthetic training examples
- [ ] Review and curate training data
- [ ] Validate data quality (accuracy, consistency)
- [ ] Format data as JSON/JSONL
- [ ] Split into train/validation/test sets
- [ ] Document data collection process

### Fine-Tuning Configuration

- [ ] Choose base model (GPT-4, Claude, etc.)
- [ ] Set hyperparameters (epochs, learning rate)
- [ ] Configure training data paths
- [ ] Update `.tapps-agents/experts.yaml`
- [ ] Test configuration validation

### Fine-Tuning Execution

- [ ] Upload training data
- [ ] Start fine-tuning job
- [ ] Monitor training progress
- [ ] Validate on validation set
- [ ] Evaluate response quality
- [ ] Compare to RAG-only baseline

### Post-Fine-Tuning

- [ ] Test fine-tuned model in staging
- [ ] A/B test against RAG-only
- [ ] Measure improvement metrics
- [ ] Collect user feedback
- [ ] Document results and learnings
- [ ] Plan rollout strategy
- [ ] Deploy to production
- [ ] Monitor performance

## Training Data Collection Strategies

### 1. Consultation History Extraction

**Source**: Expert consultation logs from `.tapps-agents/events/`

**Process**:
1. Extract user queries
2. Extract expert responses
3. Filter for high-quality interactions
4. Anonymize if needed
5. Format as training examples

### 2. Synthetic Example Generation

**Process**:
1. Review knowledge base files
2. Generate question-answer pairs
3. Create scenarios based on patterns
4. Validate with domain experts

**Tools**:
- LLM-assisted generation (with human review)
- Template-based generation
- Pattern extraction from code

### 3. Manual Curation

**Process**:
1. Domain experts create examples
2. Review generated examples
3. Correct inaccuracies
4. Add missing patterns
5. Ensure consistency

## Success Metrics

### Quality Metrics

- **Accuracy**: Response correctness (expert-reviewed)
- **Relevance**: Response relevance to query
- **Completeness**: Response covers all aspects
- **Code Quality**: Generated code follows HomeIQ patterns

### Performance Metrics

- **Response Time**: Fine-tuned vs RAG-only
- **Token Usage**: Cost comparison
- **User Satisfaction**: Feedback scores
- **Consultation Frequency**: Usage patterns

### Baseline Comparison

Compare fine-tuned expert to:
- RAG-only expert (current)
- Built-in technical experts
- Manual expert consultation

## Cost Considerations

### Fine-Tuning Costs

- **Training**: One-time cost per domain
- **Inference**: Per-query cost (may be higher than RAG)
- **Storage**: Model storage costs
- **Maintenance**: Re-training when knowledge updates

### ROI Analysis

**Benefits**:
- Improved response quality
- Faster response times (potentially)
- Better domain-specific knowledge
- Reduced need for manual review

**Costs**:
- Training data collection
- Fine-tuning execution
- Model storage and inference
- Maintenance and updates

**Break-Even**: Consider fine-tuning when consultation frequency justifies investment.

## Maintenance and Updates

### When to Re-Train

- Major architecture changes (new Epic)
- Significant knowledge base updates
- Response quality degradation
- New patterns emerge
- Quarterly review (recommended)

### Update Process

1. Collect new training examples
2. Merge with existing data
3. Re-train model
4. Validate improvements
5. Deploy updated model

## Current Status

**Fine-Tuning**: Not enabled  
**Training Data**: Not collected  
**Priority Domains**: Identified (see High-Priority Domains section)  
**Next Steps**: Begin training data collection for high-priority domains

## References

- TappsCodingAgents Expert System Documentation
- `.tapps-agents/experts.yaml` - Expert configuration
- `.tapps-agents/knowledge/` - Knowledge base files
- `.tapps-agents/EXPERT_PRIORITY_GUIDE.md` - Expert priority system

## Notes

- Fine-tuning is optional - RAG-only may be sufficient for many domains
- Start with high-priority domains (microservices, home-assistant)
- Collect training data gradually
- Validate quality before fine-tuning
- Monitor costs and ROI
- Regular maintenance required for accuracy

