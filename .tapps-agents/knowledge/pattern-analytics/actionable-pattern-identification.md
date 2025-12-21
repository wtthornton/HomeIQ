# Actionable Pattern Identification

**Last Updated**: December 2025  
**Status**: Current actionability assessment methods for 2025

## Actionability Criteria

### Pattern Requirements

**1. Statistical Significance**:
- Pattern is real, not random
- Sufficient data points (>20 occurrences)
- Low probability of false positive (p < 0.05)

**2. Consistency**:
- Pattern occurs frequently (>70% of time)
- Reliable and predictable
- Low variance in timing/conditions

**3. Actionability**:
- Can be automated
- Automation is feasible
- Automation provides value

**4. User Value**:
- Saves time or money
- Improves convenience
- Addresses user need
- ROI is positive

### Non-Actionable Patterns

**One-Time Events**:
- Single occurrence
- No repetition
- Not a pattern

**Random Co-Occurrences**:
- Coincidental timing
- No causal relationship
- Low support/confidence

**User Preferences**:
- Highly variable
- User wants manual control
- Context-dependent decisions

**Complex Patterns**:
- Too many conditions
- Unpredictable timing
- Difficult to automate reliably

## Actionability Assessment

### Scoring Framework

**Score Components** (0-100 scale):

1. **Pattern Strength** (30 points)
   - Statistical significance: 0-15 points
   - Consistency: 0-15 points

2. **Automation Feasibility** (25 points)
   - Can be automated: 0-15 points
   - Reliability: 0-10 points

3. **User Value** (25 points)
   - Time/money saved: 0-15 points
   - Convenience: 0-10 points

4. **User Fit** (20 points)
   - Matches user patterns: 0-10 points
   - User acceptance likelihood: 0-10 points

**Actionability Thresholds**:
- **High (>70)**: Suggest immediately
- **Medium (50-70)**: Suggest with review
- **Low (<50)**: Don't suggest, or monitor

### Example Scoring

**Pattern**: "Lights turn on at 7 AM daily"

**Scoring**:
- Pattern Strength: 28/30 (high significance, very consistent)
- Automation Feasibility: 25/25 (easy to automate, reliable)
- User Value: 20/25 (saves time, convenient)
- User Fit: 18/20 (matches routine, high acceptance)

**Total**: 91/100 → **High Actionability** ✅

## Pattern Prioritization

### High Priority Patterns

**Characteristics**:
- High actionability score (>70)
- Clear user benefit
- Easy to automate
- Low risk

**Examples**:
- Daily time-based routines
- Consistent device co-occurrences
- High-frequency manual actions
- Obvious automation opportunities

### Medium Priority Patterns

**Characteristics**:
- Medium actionability score (50-70)
- Moderate user benefit
- Moderate automation complexity
- Some risk

**Examples**:
- Weekly patterns
- Context-dependent patterns
- Moderate-frequency actions
- Requires some refinement

### Low Priority Patterns

**Characteristics**:
- Low actionability score (<50)
- Unclear benefit
- Complex automation
- High risk

**Examples**:
- Infrequent patterns
- Highly variable patterns
- Complex multi-factor patterns
- Low confidence patterns

## Pattern Validation

### Pre-Suggestion Validation

**Check**:
- Pattern meets actionability criteria
- Sufficient data (not overfitted)
- Pattern is current (not obsolete)
- No conflicting patterns
- User hasn't rejected similar patterns

**Result**: Only suggest validated patterns

### Post-Deployment Validation

**Monitor**:
- Automation execution success
- User satisfaction
- Pattern persistence
- Performance metrics

**Result**: Validate pattern was actionable, learn for future

## Pattern Refinement

### Improving Actionability

**Enhance Pattern Strength**:
- Collect more data
- Improve detection algorithms
- Add context factors
- Reduce noise

**Improve Automation Feasibility**:
- Simplify automation logic
- Add safety conditions
- Improve reliability
- Handle edge cases

**Increase User Value**:
- Quantify benefits better
- Highlight convenience
- Show time/money savings
- Demonstrate value

**Better User Fit**:
- Personalize suggestions
- Match user preferences
- Consider user context
- Learn from feedback

### Pattern Evolution

**Monitor Changes**:
- Pattern consistency over time
- User behavior changes
- Automation effectiveness
- Pattern relevance

**Adapt**:
- Update patterns as behavior changes
- Refine automations based on performance
- Remove obsolete patterns
- Detect new patterns

