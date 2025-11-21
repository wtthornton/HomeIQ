"""
Feature-Based Suggestion Generator

Generates LLM-powered suggestions for unused device features.
Uses existing OpenAI client from Epic-AI-1.

Story: AI2.4 - Feature-Based Suggestion Generator
Epic: AI-2 - Device Intelligence System
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class FeatureSuggestionGenerator:
    """
    Generates LLM-powered suggestions for unused device features.

    Takes opportunities from FeatureAnalyzer and creates actionable
    suggestions with configuration guidance using OpenAI.

    Story AI2.4: Feature-Based Suggestion Generator
    Epic AI-2: Device Intelligence System

    Example Usage:
        generator = FeatureSuggestionGenerator(llm_client, analyzer, db_session)
        suggestions = await generator.generate_suggestions(max_suggestions=10)
    """

    def __init__(self, llm_client, feature_analyzer, db_session):
        """
        Initialize feature suggestion generator.

        Args:
            llm_client: OpenAI client from Epic-AI-1 (existing)
            feature_analyzer: FeatureAnalyzer from Story 2.3
            db_session: Database session for storing suggestions
        """
        self.llm = llm_client
        self.analyzer = feature_analyzer
        self.db = db_session

    async def generate_suggestions(self, max_suggestions: int = 10) -> list[dict]:
        """
        Generate feature-based suggestions for top opportunities.

        Analyzes all devices, identifies top opportunities, and generates
        LLM-powered suggestions with configuration guidance.

        Args:
            max_suggestions: Maximum number of suggestions to generate (default: 10)

        Returns:
            List of generated suggestion dictionaries

        Example Output:
            [
                {
                    "title": "Enable LED Notifications on Kitchen Switch",
                    "description": "Your Inovelli switch supports...",
                    "type": "feature_discovery",
                    "device_id": "light.kitchen_switch",
                    "feature_name": "led_notifications",
                    "confidence": 0.85,
                    "category": "convenience",
                    "priority": "high",
                    "configuration_steps": "..."
                }
            ]
        """
        logger.info(f"🤖 Generating feature-based suggestions (max: {max_suggestions})...")
        start_time = datetime.utcnow()

        # Get opportunities from analyzer (Story 2.3)
        analysis = await self.analyzer.analyze_all_devices()
        opportunities = analysis.get("opportunities", [])[:max_suggestions]

        if not opportunities:
            logger.info("ℹ️ No feature opportunities found (all devices fully utilized!)")
            return []

        logger.info(
            f"📊 Found {len(opportunities)} opportunities:\n"
            f"   Top opportunity: {opportunities[0]['feature_name']} "
            f"({opportunities[0]['impact']} impact, {opportunities[0]['complexity']} complexity)",
        )

        suggestions = []
        for i, opp in enumerate(opportunities, 1):
            try:
                logger.debug(f"Generating suggestion {i}/{len(opportunities)}: {opp['feature_name']}")
                suggestion = await self._generate_llm_suggestion(opp)

                if suggestion:
                    suggestions.append(suggestion)
                    logger.info(f"✅ [{i}/{len(opportunities)}] Generated: {suggestion['title'][:50]}...")

            except Exception as e:
                logger.exception(f"❌ Failed to generate suggestion for {opp['feature_name']}: {e}")
                # Continue with other opportunities
                continue

        duration = (datetime.utcnow() - start_time).total_seconds()

        logger.info(
            f"✅ Feature suggestion generation complete in {duration:.1f}s\n"
            f"   Generated: {len(suggestions)} suggestions\n"
            f"   LLM calls: {len(suggestions)}\n"
            f"   Success rate: {len(suggestions)/len(opportunities)*100:.0f}%",
        )

        return suggestions

    async def _generate_llm_suggestion(self, opportunity: dict) -> dict | None:
        """
        Generate single suggestion using LLM.

        Args:
            opportunity: Opportunity dict from FeatureAnalyzer

        Returns:
            Suggestion dict or None if generation fails
        """
        try:
            # Use unified prompt builder for consistent prompt generation
            from src.prompt_building.unified_prompt_builder import UnifiedPromptBuilder

            unified_builder = UnifiedPromptBuilder(device_intelligence_client=None)

            # Build device context from opportunity
            device_context = {
                "device_id": opportunity["device_id"],
                "friendly_name": opportunity["device_name"],
                "manufacturer": opportunity["manufacturer"],
                "model": opportunity["model"],
                "capabilities": [opportunity["feature_name"]],
            }

            # Build unified prompt for feature suggestion
            prompt_dict = await unified_builder.build_feature_prompt(
                opportunity=opportunity,
                device_context=device_context,
                output_mode="description",
            )

            # Generate suggestion with unified prompt
            suggestion_data = await self.llm.generate_with_unified_prompt(
                prompt_dict=prompt_dict,
                temperature=0.8,  # Creative but consistent
                max_tokens=300,  # Keep suggestions concise
                output_format="description",
            )

            # Extract suggestion content
            content = suggestion_data.get("description", "").strip()

            # Create suggestion dict
            return {
                "title": f"Enable {opportunity['feature_name'].replace('_', ' ').title()} on {opportunity['device_name']}",
                "description": content,
                "type": "feature_discovery",  # Distinguish from pattern suggestions
                "device_id": opportunity["device_id"],
                "feature_name": opportunity["feature_name"],
                "manufacturer": opportunity["manufacturer"],
                "model": opportunity["model"],
                "complexity": opportunity["complexity"],
                "impact": opportunity["impact"],
                "confidence": self._calculate_confidence(opportunity),
                "category": self._determine_category(opportunity),
                "priority": self._map_impact_to_priority(opportunity["impact"]),
                "automation_yaml": "",  # Feature suggestions don't have automation YAML (config steps instead)
                "status": "pending",
            }


        except Exception as e:
            logger.exception(f"❌ OpenAI API error for feature {opportunity['feature_name']}: {e}")
            raise

    def _build_feature_prompt(self, opportunity: dict) -> str:
        """
        Build LLM prompt for feature suggestion.

        Args:
            opportunity: Opportunity dict from FeatureAnalyzer

        Returns:
            Formatted prompt string for OpenAI
        """
        feature_friendly = opportunity["feature_name"].replace("_", " ").title()

        return f"""Device Feature Discovery Suggestion:

DEVICE INFORMATION:
- Device Name: {opportunity['device_name']}
- Manufacturer: {opportunity['manufacturer']}
- Model: {opportunity['model']}

UNUSED FEATURE:
- Feature: {feature_friendly}
- Type: {opportunity['feature_type']}
- Complexity: {opportunity['complexity']}
- Impact: {opportunity['impact']}

TASK:
Create a brief, encouraging suggestion (2-3 sentences) explaining:
1. What this feature does and why it's useful
2. How the user can configure it in Home Assistant
3. A practical use case or benefit

TONE: Friendly, educational, actionable
LENGTH: 2-3 sentences maximum
FOCUS: Practical benefits, not technical jargon

Example for LED Notifications:
"Your Inovelli switch has a built-in LED bar that can display status information! You can configure it to show different colors based on your home's state - like red when the security system is armed, or blue when it's raining outside. Configure this in Home Assistant under Device Settings → Configure."
"""

    def _calculate_confidence(self, opportunity: dict) -> float:
        """
        Calculate confidence score for feature suggestion.

        Based on impact and complexity - high impact + easy = high confidence.

        Args:
            opportunity: Opportunity dict

        Returns:
            Confidence score between 0.3 and 0.95
        """
        impact_scores = {"high": 0.9, "medium": 0.7, "low": 0.5}
        complexity_penalties = {"easy": 0.0, "medium": -0.1, "advanced": -0.2}

        base = impact_scores.get(opportunity["impact"], 0.5)
        penalty = complexity_penalties.get(opportunity["complexity"], 0.0)

        # Ensure score stays in reasonable range
        return max(0.3, min(0.95, base + penalty))

    def _determine_category(self, opportunity: dict) -> str:
        """
        Determine suggestion category based on feature name.

        Args:
            opportunity: Opportunity dict

        Returns:
            Category: "energy" | "comfort" | "security" | "convenience"
        """
        feature_lower = opportunity["feature_name"].lower()

        # Energy-related features
        if any(k in feature_lower for k in ["energy", "power", "consumption", "watt", "monitoring"]):
            return "energy"

        # Security-related features
        if any(k in feature_lower for k in ["security", "alert", "notification", "alarm", "status", "led"]):
            return "security"

        # Comfort-related features
        if any(k in feature_lower for k in ["temperature", "climate", "comfort", "fan", "humidity"]):
            return "comfort"

        # Default to convenience
        return "convenience"

    def _map_impact_to_priority(self, impact: str) -> str:
        """
        Map impact level to priority.

        Args:
            impact: Impact level from FeatureAnalyzer

        Returns:
            Priority: "high" | "medium" | "low"
        """
        return {"high": "high", "medium": "medium", "low": "low"}.get(impact, "medium")

