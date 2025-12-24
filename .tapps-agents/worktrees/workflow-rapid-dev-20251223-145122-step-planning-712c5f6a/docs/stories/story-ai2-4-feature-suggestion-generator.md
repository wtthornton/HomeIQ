# Story AI2.4: Feature-Based Suggestion Generator

**Epic:** Epic-AI-2 - Device Intelligence System  
**Story ID:** AI2.4  
**Priority:** High  
**Estimated Effort:** 12-14 hours  
**Dependencies:** 
- Story AI2.3 ✅ Complete (Feature Analysis)
- Epic-AI-1 LLM Integration ✅ Complete (OpenAI client exists)

**Related Documents:**
- PRD v2.0: `docs/prd.md` (Story 2.4, FR15, NFR15)
- Architecture: `docs/architecture-device-intelligence.md` (Section 5.4)

---

## User Story

**As a** Home Assistant user  
**I want** AI-powered suggestions for unused device features  
**so that** I can learn about and configure capabilities I didn't know existed

---

## Business Value

- **Feature Discovery:** Automated suggestions for unused device capabilities
- **Educational:** Learn what devices can do beyond basic on/off
- **Actionable:** Specific configuration steps for each suggested feature
- **Personalized:** Suggestions based on actual device ownership
- **Complements Epic-AI-1:** Feature suggestions + pattern suggestions = comprehensive optimization

**Example Output:**
> "Your Kitchen Switch (Inovelli VZM31-SN) supports LED notifications but isn't using them. Configure the LED bar to show different colors for different automation states (e.g., red when security armed, green when all clear)."

---

## Acceptance Criteria

### Functional Requirements (from PRD)

1. ✅ **FR15:** Generate suggestions for top 10 unused features
2. ✅ **FR15:** Use OpenAI LLM to create natural language suggestions
3. ✅ **FR15:** Include configuration guidance for each feature
4. ✅ **FR15:** Store suggestions in suggestions table with type='feature_discovery'
5. ✅ **FR15:** Rank by impact and complexity (from Story 2.3)
6. ✅ **FR15:** Include device-specific context (manufacturer, model)
7. ✅ **FR15:** Generate actionable Home Assistant configuration examples

### Non-Functional Requirements (from PRD)

8. ✅ **NFR15:** Generate 10 suggestions in <60 seconds
9. ✅ **NFR15:** LLM cost <$0.10 per batch (use gpt-4o-mini)
10. ✅ **NFR15:** Graceful handling of LLM API failures
11. ✅ **Testing:** 80%+ test coverage
12. ✅ **Integration:** Works with Epic-AI-1 LLM client

---

## Technical Implementation Notes

### Component: FeatureSuggestionGenerator

**File:** `services/ai-automation-service/src/device_intelligence/feature_suggestion_generator.py` (NEW)

**Purpose:** Generate LLM-powered suggestions for unused device features

**Implementation:**

```python
# services/ai-automation-service/src/device_intelligence/feature_suggestion_generator.py

import logging
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class FeatureSuggestionGenerator:
    """
    Generates LLM-powered suggestions for unused device features.
    
    Takes opportunities from FeatureAnalyzer and creates actionable
    suggestions with configuration guidance.
    
    Story AI2.4: Feature-Based Suggestion Generator
    Epic AI-2: Device Intelligence System
    """
    
    def __init__(self, llm_client, feature_analyzer, db_session):
        """
        Initialize feature suggestion generator.
        
        Args:
            llm_client: OpenAI client for LLM generation
            feature_analyzer: FeatureAnalyzer for getting opportunities
            db_session: Database session for storing suggestions
        """
        self.llm = llm_client
        self.analyzer = feature_analyzer
        self.db = db_session
    
    async def generate_suggestions(self, max_suggestions: int = 10) -> List[Dict]:
        """
        Generate feature-based suggestions for top opportunities.
        
        Args:
            max_suggestions: Maximum number of suggestions to generate
            
        Returns:
            List of generated suggestion dicts
        """
        logger.info(f"🤖 Generating feature-based suggestions (max: {max_suggestions})...")
        
        # Get opportunities from analyzer
        analysis = await self.analyzer.analyze_all_devices()
        opportunities = analysis.get('opportunities', [])[:max_suggestions]
        
        if not opportunities:
            logger.info("No feature opportunities found")
            return []
        
        logger.info(f"Found {len(opportunities)} opportunities, generating LLM suggestions...")
        
        suggestions = []
        for opp in opportunities:
            try:
                suggestion = await self._generate_llm_suggestion(opp)
                if suggestion:
                    suggestions.append(suggestion)
            except Exception as e:
                logger.error(f"Failed to generate suggestion for {opp['feature_name']}: {e}")
                continue
        
        logger.info(f"✅ Generated {len(suggestions)} feature-based suggestions")
        return suggestions
    
    async def _generate_llm_suggestion(self, opportunity: Dict) -> Optional[Dict]:
        """Generate single suggestion using LLM"""
        
        prompt = self._build_feature_prompt(opportunity)
        
        # Use existing OpenAI client (from Epic-AI-1)
        response = await self.llm.client.chat.completions.create(
            model=self.llm.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a smart home expert helping users discover unused device features. "
                        "Create concise, actionable suggestions for enabling device capabilities. "
                        "Focus on practical benefits and simple configuration steps."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.8,
            max_tokens=400
        )
        
        content = response.choices[0].message.content
        
        # Parse response and create suggestion
        suggestion = {
            "title": f"Enable {opportunity['feature_name'].replace('_', ' ').title()} on {opportunity['device_name']}",
            "description": content,
            "type": "feature_discovery",
            "device_id": opportunity["device_id"],
            "feature_name": opportunity["feature_name"],
            "manufacturer": opportunity["manufacturer"],
            "model": opportunity["model"],
            "complexity": opportunity["complexity"],
            "impact": opportunity["impact"],
            "confidence": self._calculate_confidence(opportunity),
            "category": self._determine_category(opportunity),
            "priority": self._map_impact_to_priority(opportunity["impact"])
        }
        
        return suggestion
    
    def _build_feature_prompt(self, opportunity: Dict) -> str:
        """Build LLM prompt for feature suggestion"""
        
        return f"""
Device: {opportunity['device_name']}
Manufacturer: {opportunity['manufacturer']}
Model: {opportunity['model']}
Unused Feature: {opportunity['feature_name'].replace('_', ' ').title()}
Feature Type: {opportunity['feature_type']}
Complexity: {opportunity['complexity']}

Create a brief, actionable suggestion (2-3 sentences) for why the user should enable this feature and how to configure it in Home Assistant.

Focus on:
- Practical benefits
- Simple configuration steps
- Real-world use cases

Keep it conversational and encouraging!
"""
    
    def _calculate_confidence(self, opportunity: Dict) -> float:
        """Calculate confidence score based on impact and complexity"""
        impact_scores = {"high": 0.9, "medium": 0.7, "low": 0.5}
        complexity_penalties = {"easy": 0.0, "medium": -0.1, "advanced": -0.2}
        
        base = impact_scores.get(opportunity["impact"], 0.5)
        penalty = complexity_penalties.get(opportunity["complexity"], 0.0)
        
        return max(0.3, min(0.95, base + penalty))
    
    def _determine_category(self, opportunity: Dict) -> str:
        """Determine suggestion category"""
        feature_lower = opportunity["feature_name"].lower()
        
        if any(k in feature_lower for k in ["energy", "power", "consumption"]):
            return "energy"
        elif any(k in feature_lower for k in ["security", "alert", "notification"]):
            return "security"
        elif any(k in feature_lower for k in ["temperature", "climate", "comfort"]):
            return "comfort"
        else:
            return "convenience"
    
    def _map_impact_to_priority(self, impact: str) -> str:
        """Map impact level to priority"""
        return {"high": "high", "medium": "medium", "low": "low"}.get(impact, "medium")
```

---

## Tasks and Subtasks

### Task 1: Implement FeatureSuggestionGenerator
- [ ] Create `feature_suggestion_generator.py`
- [ ] Implement `__init__()` with dependencies
- [ ] Implement `generate_suggestions()` main method
- [ ] Implement `_generate_llm_suggestion()` for single opportunity
- [ ] Add comprehensive docstrings

### Task 2: Create LLM Prompts
- [ ] Implement `_build_feature_prompt()` for feature suggestions
- [ ] Design prompt template for unused features
- [ ] Include device context and configuration guidance
- [ ] Test prompt quality with various features

### Task 3: Implement Helper Methods
- [ ] Implement `_calculate_confidence()` scoring
- [ ] Implement `_determine_category()` classification
- [ ] Implement `_map_impact_to_priority()` mapping
- [ ] Add logging throughout

### Task 4: Integrate with Existing Components
- [ ] Use existing OpenAI client from Epic-AI-1
- [ ] Integrate with FeatureAnalyzer from Story 2.3
- [ ] Store suggestions in existing suggestions table
- [ ] Add type='feature_discovery' to differentiate from pattern suggestions

### Task 5: Write Comprehensive Tests
- [ ] Test suggestion generation
- [ ] Test LLM prompt building
- [ ] Test confidence calculation
- [ ] Test category determination
- [ ] Mock OpenAI responses
- [ ] Test batch generation (10 suggestions)
- [ ] Achieve 80%+ coverage

### Task 6: Integration Testing
- [ ] Test with Story 2.3 opportunities
- [ ] Verify suggestions stored in database
- [ ] Test LLM cost tracking
- [ ] Test error handling

---

## Status

**Current Status:** Draft - Ready for Implementation  
**Next Step:** Implement FeatureSuggestionGenerator  
**Blocked By:** None  
**Blocking:** Story 2.5 (Unified Pipeline)

---

**Ready for Implementation!** 🚀

