# User Guide: Suggestion Preferences

**Epic AI-6: Blueprint-Enhanced Suggestion Intelligence**  
**Last Updated:** December 2025

---

## Overview

The AI Automation Service allows you to customize how automation suggestions are generated and ranked through preference settings. These preferences control the number of suggestions you see, how creative or experimental suggestions can be, and how much blueprint-based suggestions are prioritized.

---

## Accessing Preference Settings

1. Open the AI Automation UI (Port 3001)
2. Navigate to **Settings** from the main navigation
3. Scroll to the **🎯 Suggestion Preferences** section

---

## Preference Options

### Maximum Suggestions

**Control:** Slider (5-50)  
**Default:** 10  
**Location:** Settings → Suggestion Preferences → Maximum Suggestions

Controls how many suggestions are shown in results. This limit is applied after all suggestions are ranked and filtered.

**Recommendations:**
- **5-10 suggestions:** Focused view, top recommendations only
- **15-25 suggestions:** Balanced view, good variety
- **30-50 suggestions:** Comprehensive view, see all opportunities

**Example:**
- With `max_suggestions = 10`: You'll see the top 10 ranked suggestions
- With `max_suggestions = 20`: You'll see the top 20 ranked suggestions

---

### Creativity Level

**Control:** Dropdown  
**Options:** Conservative, Balanced, Creative  
**Default:** Balanced  
**Location:** Settings → Suggestion Preferences → Creativity Level

Controls how experimental or creative suggestions can be. This affects confidence thresholds, blueprint weighting, and limits on experimental suggestion types.

#### Conservative

**Best for:** Users who want only high-confidence, proven automations

**Behavior:**
- Minimum confidence threshold: **≥85%**
- Blueprint weight: **0.8x** (strong preference for blueprint-validated suggestions)
- Experimental boost: **0.0** (no experimental suggestions)
- Max experimental suggestions: **0**

**What you'll see:**
- Only high-confidence pattern-based suggestions
- Strong preference for blueprint-validated automations
- No anomaly-based or experimental suggestions
- Most reliable, tested automation ideas

**Example Suggestions:**
- "Turn on office light at 7:00 AM" (high confidence, blueprint-validated)
- "Motion-activated hallway light" (proven pattern)

#### Balanced (Recommended)

**Best for:** Most users who want a mix of reliable and creative suggestions

**Behavior:**
- Minimum confidence threshold: **≥70%**
- Blueprint weight: **0.6x** (moderate preference for blueprints)
- Experimental boost: **0.1** (slight boost for experimental suggestions)
- Max experimental suggestions: **2**

**What you'll see:**
- Mix of high and medium confidence suggestions
- Some experimental ideas (up to 2)
- Balanced preference for blueprint-validated suggestions
- Good variety of automation opportunities

**Example Suggestions:**
- "Turn on office light at 7:00 AM" (high confidence)
- "Motion-activated hallway light" (blueprint-validated)
- "Turn off devices when leaving home" (experimental, moderate confidence)
- "Dim lights during TV time" (synergy-based, moderate confidence)

#### Creative

**Best for:** Advanced users who want to explore automation possibilities

**Behavior:**
- Minimum confidence threshold: **≥55%** (allows lower confidence suggestions)
- Blueprint weight: **0.4x** (lower preference for blueprints)
- Experimental boost: **0.3** (significant boost for experimental suggestions)
- Max experimental suggestions: **5**

**What you'll see:**
- Wide variety of suggestions including lower confidence ideas
- More experimental and anomaly-based suggestions (up to 5)
- Less preference for blueprint-validated suggestions
- Creative automation opportunities

**Example Suggestions:**
- "Turn on office light at 7:00 AM" (high confidence)
- "Anomaly: Repeated manual light adjustments" (experimental)
- "Smart scheduling based on calendar events" (experimental)
- "Weather-based window automation" (creative synergy)
- "Energy optimization patterns" (experimental)

---

### Blueprint Preference

**Control:** Dropdown  
**Options:** Low, Medium, High  
**Default:** Medium  
**Location:** Settings → Suggestion Preferences → Blueprint Preference

Controls how much blueprint-based suggestions are prioritized in ranking. Blueprint opportunities are suggestions based on community-validated Home Assistant automation blueprints.

#### Low

**Weight Multiplier:** 0.5x  
**Best for:** Users who prefer original suggestions over blueprint-based ones

**Behavior:**
- Blueprint opportunities ranked lower (half weight)
- Pattern-based and feature-based suggestions prioritized
- Good for unique automation needs

**Example Ranking:**
1. Pattern suggestion (confidence: 0.90)
2. Feature suggestion (confidence: 0.85)
3. Blueprint opportunity (confidence: 0.80 → 0.40 after weighting)

#### Medium (Recommended)

**Weight Multiplier:** 1.0x  
**Best for:** Most users who want balanced ranking

**Behavior:**
- Blueprint opportunities ranked normally (full weight)
- Balanced preference between all suggestion types
- Good mix of blueprint and original suggestions

**Example Ranking:**
1. Pattern suggestion (confidence: 0.90)
2. Blueprint opportunity (confidence: 0.85)
3. Feature suggestion (confidence: 0.80)

#### High

**Weight Multiplier:** 1.5x  
**Best for:** Users who prefer proven, community-validated automations

**Behavior:**
- Blueprint opportunities ranked higher (1.5x weight)
- Strong preference for blueprint-validated suggestions
- Good for users who trust community-proven automations

**Example Ranking:**
1. Blueprint opportunity (confidence: 0.80 → 1.20 after weighting)
2. Pattern suggestion (confidence: 0.90)
3. Feature suggestion (confidence: 0.85)

---

## How Preferences Work Together

Preferences are applied in this order:

1. **Creativity Filtering:** Removes suggestions below confidence threshold and applies experimental limits
2. **Blueprint Weighting:** Adjusts ranking scores for blueprint opportunities
3. **Final Sorting:** Sorts all suggestions by adjusted confidence scores
4. **Max Suggestions Limit:** Keeps only the top N suggestions

**Example Flow:**

Starting with 25 suggestions:
- After creativity filtering (balanced): 18 suggestions remain
- After blueprint weighting: Scores adjusted, but all 18 still present
- After sorting: Re-ordered by adjusted scores
- After max suggestions limit (10): Top 10 suggestions kept

---

## Usage Examples

### Example 1: Focused, Reliable Suggestions

**Settings:**
- Maximum Suggestions: **5**
- Creativity Level: **Conservative**
- Blueprint Preference: **High**

**Result:** You'll see only the top 5, highest-confidence, blueprint-validated suggestions. Perfect for users who want only the most reliable automations.

### Example 2: Balanced Exploration

**Settings:**
- Maximum Suggestions: **15**
- Creativity Level: **Balanced**
- Blueprint Preference: **Medium**

**Result:** You'll see 15 suggestions with a good mix of reliable and creative ideas, balanced between blueprint and original suggestions. This is the recommended default configuration.

### Example 3: Maximum Creativity

**Settings:**
- Maximum Suggestions: **30**
- Creativity Level: **Creative**
- Blueprint Preference: **Low**

**Result:** You'll see up to 30 suggestions with a wide variety, including experimental ideas. Blueprint suggestions won't be heavily prioritized. Perfect for advanced users exploring automation possibilities.

---

## Frequently Asked Questions

### Q: Do preferences affect the daily 3 AM analysis?

**A:** Yes! Preferences are applied to suggestions generated during the daily batch job at 3 AM. Your preference settings affect which suggestions are stored and shown to you.

### Q: Do preferences affect Ask AI queries?

**A:** Yes! When you ask questions in the Ask AI interface, your preferences are applied to the suggestions generated from your query.

### Q: Can I change preferences anytime?

**A:** Yes! Changes to preferences take effect immediately for new suggestions. Existing suggestions won't change, but new ones will use your updated preferences.

### Q: What happens if I don't set preferences?

**A:** The service uses default values:
- Maximum Suggestions: 10
- Creativity Level: Balanced
- Blueprint Preference: Medium

### Q: Are preferences user-specific?

**A:** Currently, preferences are global for your Home Assistant instance. Multi-user support may be added in the future.

### Q: How do I reset to defaults?

**A:** Use the "Reset to Defaults" button in the Settings page, or manually set:
- Maximum Suggestions: 10
- Creativity Level: Balanced
- Blueprint Preference: Medium

---

## Best Practices

1. **Start with Balanced:** Use the default "Balanced" creativity level to see a good mix of suggestions, then adjust based on your needs.

2. **Adjust Max Suggestions Based on Usage:**
   - If you're overwhelmed: Lower to 5-10
   - If you want more options: Increase to 15-25
   - If you're exploring: Increase to 30-50

3. **Use Conservative for Reliability:** If you only want proven automations, use Conservative creativity with High blueprint preference.

4. **Use Creative for Exploration:** If you want to discover new automation possibilities, use Creative creativity with Low blueprint preference.

5. **Monitor Results:** Check which suggestions you actually approve and use, then adjust preferences accordingly.

---

## Technical Details

### Confidence Thresholds

Creativity levels set different minimum confidence thresholds:

- **Conservative:** ≥85% confidence
- **Balanced:** ≥70% confidence
- **Creative:** ≥55% confidence

Suggestions below the threshold are filtered out.

### Experimental Suggestions

Experimental suggestions include:
- Anomaly-based patterns
- Low-confidence patterns
- Advanced synergy suggestions
- ML-enhanced suggestions

The creativity level controls how many of these are shown (0, 2, or 5).

### Blueprint Weighting

Blueprint preference multiplies the ranking score of blueprint opportunities:

- **Low:** Score × 0.5
- **Medium:** Score × 1.0 (no change)
- **High:** Score × 1.5

This affects ranking order but doesn't filter suggestions.

---

## Troubleshooting

### I'm not seeing enough suggestions

**Solutions:**
- Increase Maximum Suggestions
- Change Creativity Level to Balanced or Creative
- Check if your devices have enough usage history

### I'm seeing too many experimental suggestions

**Solutions:**
- Change Creativity Level to Balanced or Conservative
- Increase Blueprint Preference to High
- Lower Maximum Suggestions to see only top suggestions

### Blueprint suggestions aren't appearing

**Solutions:**
- Check if automation-miner service is running (Port 8029)
- Increase Blueprint Preference to High
- Check if your devices match available blueprints

### Preferences aren't saving

**Solutions:**
- Check browser console for errors
- Verify API endpoint is accessible (`/api/v1/preferences`)
- Try refreshing the page and setting preferences again

---

## Support

For additional help:
- Check the technical documentation
- Review the API documentation
- Check service logs for errors
- Verify all services are running (automation-miner, AI automation service)

---

**Version:** 1.0  
**Last Updated:** December 2025  
**Epic:** AI-6 - Blueprint-Enhanced Suggestion Intelligence
