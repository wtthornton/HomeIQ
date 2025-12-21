# Suggestion Prioritization

**Last Updated**: December 2025  
**Status**: Current prioritization methods for 2025

## Prioritization Factors

### 1. Confidence Score

**Definition**: How confident the system is in the suggestion's value.

**Scoring**:
- High confidence (>80%): Strong pattern, clear benefit
- Medium confidence (60-80%): Good pattern, moderate benefit
- Low confidence (<60%): Weak pattern, unclear benefit

**Weight**: 25% of priority score

### 2. User Value

**Definition**: Expected benefit to user (time saved, money saved, convenience).

**Scoring**:
- High value: Significant savings (>$50/year, >10 hours/year)
- Medium value: Moderate savings ($20-50/year, 5-10 hours/year)
- Low value: Small savings (<$20/year, <5 hours/year)

**Weight**: 30% of priority score

### 3. User Relevancy

**Definition**: How relevant the suggestion is to user's current needs/patterns.

**Scoring**:
- High relevancy: Matches current patterns, addresses active pain points
- Medium relevancy: Generally relevant but not urgent
- Low relevancy: May be useful but not pressing

**Weight**: 20% of priority score

### 4. Timing Urgency

**Definition**: How time-sensitive the suggestion is.

**Scoring**:
- High urgency: Time-sensitive opportunity (energy price spike, weather change)
- Medium urgency: Relevant now but can wait
- Low urgency: No time pressure

**Weight**: 15% of priority score

### 5. User Feedback History

**Definition**: How user has responded to similar suggestions in the past.

**Scoring**:
- High acceptance: User approves similar suggestions >60%
- Medium acceptance: User approves similar suggestions 40-60%
- Low acceptance: User approves similar suggestions <40%

**Weight**: 10% of priority score

## Priority Calculation

### Formula

```
Priority Score = 
  (Confidence × 0.25) + 
  (User Value × 0.30) + 
  (Relevancy × 0.20) + 
  (Urgency × 0.15) + 
  (Feedback History × 0.10)
```

### Priority Tiers

**Tier 1 (80-100)**: Immediate suggestion
- High confidence + high value + high relevancy
- Deploy immediately, high-visibility channel

**Tier 2 (60-80)**: High priority suggestion
- Good combination of factors
- Include in daily suggestions, prominent placement

**Tier 3 (40-60)**: Standard suggestion
- Moderate priority
- Include in batch suggestions, standard placement

**Tier 4 (<40)**: Low priority
- Don't suggest, or include in weekly summary only

## Prioritization Examples

### Example 1: High Priority

**Suggestion**: "Energy prices will spike at 2 PM today. Pre-cool your home now to save $5-10."

**Scoring**:
- Confidence: 90% (clear price forecast)
- User Value: 95% (significant savings, $5-10)
- Relevancy: 85% (user has cooling system, home now)
- Urgency: 100% (action needed now, before 2 PM)
- Feedback History: 80% (user accepts energy suggestions)

**Priority Score**: (90×0.25) + (95×0.30) + (85×0.20) + (100×0.15) + (80×0.10) = 90.5

**Action**: Immediate push notification, high priority

### Example 2: Medium Priority

**Suggestion**: "I noticed you turn on kitchen lights at 7 AM daily. Would you like to automate this?"

**Scoring**:
- Confidence: 75% (consistent pattern, 20+ occurrences)
- User Value: 60% (moderate time savings, ~5 hours/year)
- Relevancy: 70% (matches current routine)
- Urgency: 30% (no time pressure)
- Feedback History: 70% (user accepts routine automations)

**Priority Score**: (75×0.25) + (60×0.30) + (70×0.20) + (30×0.15) + (70×0.10) = 63.75

**Action**: Include in daily suggestion batch, standard priority

### Example 3: Low Priority

**Suggestion**: "Your smart switch has LED notification features you're not using."

**Scoring**:
- Confidence: 50% (feature exists, but unclear if user wants it)
- User Value: 40% (low value, convenience feature)
- Relevancy: 50% (user hasn't expressed interest)
- Urgency: 10% (no time pressure)
- Feedback History: 40% (user rarely uses advanced features)

**Priority Score**: (50×0.25) + (40×0.30) + (50×0.20) + (10×0.15) + (40×0.10) = 41.5

**Action**: Include in weekly summary only, or skip

## Dynamic Prioritization

### Context Adjustment

**Boost Priority When**:
- Context is highly relevant (perfect timing, conditions align)
- User is actively using related devices
- Environmental factors favor suggestion (weather, energy pricing)

**Reduce Priority When**:
- Context is not ideal (poor timing, conditions don't align)
- User is busy or inactive
- Similar suggestions recently shown

### Learning from Feedback

**Adjust Based On**:
- User acceptance rate for suggestion type
- User modifications to similar suggestions
- User engagement with suggestion channel
- Time-to-review patterns

**Adaptation**:
- Increase priority for suggestion types user accepts
- Decrease priority for types user rejects
- Adjust timing based on engagement patterns
- Refine weighting based on success metrics

## Prioritization Best Practices

### Quality Over Quantity

- Prioritize high-quality suggestions over volume
- Better to suggest 3 excellent suggestions than 10 mediocre ones
- Focus on Tier 1 and Tier 2 suggestions

### Diversity

- Don't prioritize only one type of suggestion
- Mix pattern suggestions, optimizations, feature discoveries
- Balance immediate value with long-term value

### User Preferences

- Respect user's prioritization preferences
- Learn from user behavior
- Allow user to customize prioritization factors

### Continuous Improvement

- Monitor prioritization effectiveness
- A/B test different prioritization strategies
- Refine weights based on user feedback
- Adapt to changing user needs

