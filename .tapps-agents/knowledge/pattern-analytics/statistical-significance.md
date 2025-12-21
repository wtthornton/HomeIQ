# Statistical Significance Analysis

**Last Updated**: December 2025  
**Status**: Current statistical methods for pattern analysis in 2025

## Significance Testing

### Hypothesis Testing

**Null Hypothesis (H0)**: Pattern occurs by chance (random behavior)

**Alternative Hypothesis (H1)**: Pattern is real (non-random behavior)

**Test**: Determine if we can reject H0 (pattern is significant)

### P-Value Interpretation

**P-Value**: Probability of observing pattern if null hypothesis is true (pattern is random)

**Thresholds**:
- p < 0.05: Statistically significant (5% chance of false positive)
- p < 0.01: Highly significant (1% chance of false positive)
- p < 0.001: Very highly significant (0.1% chance of false positive)

**Decision**: Reject H0 if p < threshold (pattern is significant)

### Sample Size Requirements

**Minimum Sample Sizes**:
- Basic pattern: 20-30 occurrences
- High confidence: 30-50 occurrences
- Complex patterns: 50+ occurrences

**Factors**:
- Pattern complexity
- Variance in pattern
- Desired confidence level
- Effect size (pattern strength)

## Confidence Intervals

### Definition

**Confidence Interval**: Range of values likely to contain true pattern parameter

**Common Levels**:
- 90% confidence interval
- 95% confidence interval (most common)
- 99% confidence interval

### Interpretation

**Example**: Pattern occurs at 7:00 AM ± 5 minutes (95% confidence)

**Meaning**: 95% of the time, pattern occurs between 6:55 AM and 7:05 AM

**Narrower intervals** = More precise pattern
**Wider intervals** = Less precise pattern

## Pattern Strength Metrics

### Support

**Definition**: Frequency of pattern occurrence

**Calculation**: (Number of occurrences) / (Total time period)

**Example**: Lights turn on at 7 AM in 28 of 30 days = 93% support

**Interpretation**: Higher support = stronger pattern

### Confidence

**Definition**: Probability of pattern given trigger

**Calculation**: (Co-occurrences) / (Trigger occurrences)

**Example**: Motion detected → Light turns on in 45 of 50 cases = 90% confidence

**Interpretation**: Higher confidence = more reliable pattern

### Lift

**Definition**: How much more likely pattern is than random

**Calculation**: Confidence / Expected frequency

**Example**: Lift of 3.0 means pattern is 3x more likely than random

**Interpretation**: Lift > 1.0 indicates meaningful pattern

## Significance Best Practices

### Multiple Testing Correction

**Problem**: Testing many patterns increases false positive rate

**Solution**: Adjust significance thresholds (Bonferroni correction, FDR)

**Example**: Testing 20 patterns at p < 0.05 → Use p < 0.0025 per test

### Effect Size Consideration

**Principle**: Statistical significance ≠ Practical significance

**Large Effect**: Pattern is strong and actionable
**Small Effect**: Pattern is statistically significant but weak

**Decision**: Consider both statistical significance AND effect size

### Temporal Validation

**Approach**: Validate pattern on new data

**Methods**:
- Train on historical data
- Test on recent data
- Measure prediction accuracy

**Benefit**: Ensures pattern generalizes, not overfitted

## Practical Significance

### Actionability Criteria

**Pattern is actionable if**:
- Statistically significant (p < 0.05)
- Sufficiently frequent (support > 70%)
- Reliable (confidence > 80%)
- Provides value (time/money saved)
- User would benefit from automation

### Value Assessment

**Quantify Value**:
- Time saved per occurrence
- Money saved (energy, etc.)
- Convenience improvement
- Error reduction

**Decision**: Proceed if value exceeds automation complexity

### Risk Assessment

**Consider**:
- False positive cost (automation triggers incorrectly)
- False negative cost (missed automation opportunity)
- Automation reliability
- User impact of errors

**Balance**: Statistical significance vs. practical risk

