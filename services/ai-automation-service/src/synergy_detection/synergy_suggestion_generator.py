"""
Synergy-Based Suggestion Generator

Generates AI-powered automation suggestions from detected synergy opportunities.

Epic AI-3: Cross-Device Synergy & Contextual Opportunities
Story AI3.4: Synergy-Based Suggestion Generation
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class SynergySuggestionGenerator:
    """
    Generates LLM-powered suggestions from synergy opportunities.

    Takes synergies from DeviceSynergyDetector and creates actionable
    automation suggestions using OpenAI (reuses Epic AI-1 infrastructure).

    Story AI3.4: Synergy-Based Suggestion Generation
    Epic AI-3: Cross-Device Synergy & Contextual Opportunities
    """

    def __init__(self, llm_client):
        """
        Initialize synergy suggestion generator.

        Args:
            llm_client: OpenAI client from Epic AI-1
        """
        self.llm = llm_client
        logger.info("SynergySuggestionGenerator initialized")

    async def generate_suggestions(
        self,
        synergies: list[dict],
        max_suggestions: int = 10,
    ) -> list[dict]:
        """
        Generate suggestions from synergy opportunities.

        Args:
            synergies: List of synergy opportunities from detector
            max_suggestions: Maximum suggestions to generate

        Returns:
            List of generated suggestion dictionaries
        """
        logger.info(f"🔗 Generating synergy-based suggestions (max: {max_suggestions})...")
        start_time = datetime.now(timezone.utc)

        if not synergies:
            logger.info("ℹ️  No synergies available for suggestion generation")
            return []

        # Synergies are already prioritized (by priority score or impact_score from database query)
        # Simply take first max_suggestions (already sorted)
        top_synergies = synergies[:max_suggestions]

        # Log priority scores if available for debugging
        if top_synergies and "pattern_support_score" in top_synergies[0]:
            priority_info = []
            for s in top_synergies[:3]:  # Log top 3
                impact = s.get("impact_score", 0)
                conf = s.get("confidence", 0)
                pattern = s.get("pattern_support_score", 0)
                validated = s.get("validated_by_patterns", False)
                priority_info.append(f"impact={impact:.2f}, conf={conf:.2f}, pattern={pattern:.2f}, validated={validated}")
            logger.debug(f"Top synergies priority details: {', '.join(priority_info)}")

        logger.info(f"Processing top {len(top_synergies)} synergies (already prioritized)")

        suggestions = []

        for i, synergy in enumerate(top_synergies, 1):
            try:
                logger.debug(f"Generating suggestion {i}/{len(top_synergies)}: {synergy['relationship']}")

                suggestion = await self._generate_llm_suggestion(synergy)

                if suggestion:
                    suggestions.append(suggestion)
                    logger.info(f"✅ [{i}/{len(top_synergies)}] Generated: {suggestion['title'][:50]}...")

            except Exception as e:
                logger.exception(f"❌ Failed to generate suggestion for synergy {synergy.get('synergy_id')}: {e}")
                continue

        duration = (datetime.now(timezone.utc) - start_time).total_seconds()

        logger.info(
            f"✅ Synergy suggestion generation complete in {duration:.1f}s\n"
            f"   Generated: {len(suggestions)} suggestions\n"
            f"   LLM calls: {len(suggestions)}\n"
            f"   Success rate: {len(suggestions)/len(top_synergies)*100:.0f}%",
        )

        return suggestions

    async def _generate_llm_suggestion(self, synergy: dict) -> dict | None:
        """
        Generate single suggestion using LLM.

        Args:
            synergy: Synergy opportunity from detector

        Returns:
            Suggestion dict or None if generation fails
        """
        # Build prompt based on synergy type
        prompt = self._build_prompt(synergy)

        try:
            # Use existing OpenAI client (Epic AI-1)
            response = await self.llm.client.chat.completions.create(
                model=self.llm.model,  # gpt-4o-mini
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a home automation expert creating Home Assistant automations. "
                            "Generate valid YAML automations from detected device synergies. "
                            "Focus on practical, easy-to-understand automations that provide real value. "
                            "Always use friendly device names in descriptions and rationale."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                temperature=0.7,  # Balanced creativity
                max_completion_tokens=600,  # Sufficient for automation YAML (use max_completion_tokens for newer models)
            )

            # Track token usage
            usage = response.usage
            self.llm.total_input_tokens += usage.prompt_tokens
            self.llm.total_output_tokens += usage.completion_tokens
            self.llm.total_tokens_used += usage.total_tokens

            logger.debug(
                f"OpenAI API call: {usage.total_tokens} tokens "
                f"(input: {usage.prompt_tokens}, output: {usage.completion_tokens})",
            )

            # Parse response
            content = response.choices[0].message.content
            return self._parse_response(content, synergy)


        except Exception as e:
            logger.exception(f"OpenAI API error: {e}")
            raise

    def _build_prompt(self, synergy: dict) -> str:
        """
        Build prompt from synergy opportunity.

        Args:
            synergy: Synergy opportunity dict

        Returns:
            Prompt string for OpenAI
        """
        synergy_type = synergy.get("synergy_type", "device_pair")

        if synergy_type == "device_pair":
            return self._build_device_pair_prompt(synergy)
        if synergy_type == "weather_context":
            return self._build_weather_context_prompt(synergy)
        if synergy_type == "energy_context":
            return self._build_energy_context_prompt(synergy)
        if synergy_type == "event_context":
            return self._build_event_context_prompt(synergy)
        msg = f"Unknown synergy type: {synergy_type}"
        raise ValueError(msg)

    def _build_device_pair_prompt(self, synergy: dict) -> str:
        """Build prompt for device pair synergy"""
        metadata = synergy.get("opportunity_metadata", synergy)

        trigger_name = metadata.get("trigger_name", synergy.get("trigger_entity", "Trigger Device"))
        action_name = metadata.get("action_name", synergy.get("action_entity", "Action Device"))
        trigger_entity = synergy.get("trigger_entity", metadata.get("trigger_entity", ""))
        action_entity = synergy.get("action_entity", metadata.get("action_entity", ""))
        area = synergy.get("area", "unknown")
        relationship = synergy.get("relationship", metadata.get("relationship", "automation"))

        # Determine relationship type for instructions
        if "motion" in relationship:
            automation_type = "motion-activated lighting"
            trigger_desc = "motion is detected"
            action_desc = "turn on the light"
            auto_off = "Optional: Turn off after no motion for 5 minutes"
        elif "door" in relationship and "lock" in relationship:
            automation_type = "automatic door lock"
            trigger_desc = "door closes"
            action_desc = "lock the door"
            auto_off = "Optional: Add delay before locking"
        elif "temp" in relationship:
            automation_type = "temperature-based climate control"
            trigger_desc = "temperature changes"
            action_desc = "adjust the climate device"
            auto_off = ""
        else:
            automation_type = "device automation"
            trigger_desc = "trigger activates"
            action_desc = "control the action device"
            auto_off = ""

        return f"""Create a Home Assistant automation for this device synergy opportunity:

DETECTED OPPORTUNITY:
- Trigger Device: {trigger_name} (in {area})
- Action Device: {action_name} (in {area})
- Relationship Type: {automation_type}
- Trigger Entity ID: {trigger_entity}
- Action Entity ID: {action_entity}
- Impact Score: {synergy.get('impact_score', 0.7):.2f}
- Complexity: {synergy.get('complexity', 'medium')}

INSIGHT:
You have {trigger_name} and {action_name} in the same area ({area}) with NO automation
connecting them. This is a valuable automation opportunity for {automation_type}.

INSTRUCTIONS:
1. Create valid Home Assistant automation YAML
2. Use {trigger_name} ({trigger_entity}) as trigger - trigger when {trigger_desc}
3. {action_desc.capitalize()} - {action_name} ({action_entity})
4. {auto_off}
5. Provide clear rationale explaining the benefit using device names
6. Categorize appropriately (energy/comfort/security/convenience)
7. Assign priority (high/medium/low)

OUTPUT FORMAT:
```yaml
alias: "AI Suggested: [Clear descriptive name using device names]"
description: "[Brief description of what this automation does]"
trigger:
  - platform: state  # or appropriate trigger type
    entity_id: {trigger_entity}
    # Add appropriate trigger conditions
action:
  - service: [appropriate service]
    target:
      entity_id: {action_entity}
```

RATIONALE: [Explain benefit using friendly names: "{trigger_name}" and "{action_name}"]
CATEGORY: [energy|comfort|security|convenience]
PRIORITY: [high|medium|low]
"""

    def _build_weather_context_prompt(self, synergy: dict) -> str:
        """
        Build prompt for weather context synergy.

        Story AI3.5: Weather Context Integration
        """
        metadata = synergy.get("opportunity_metadata", {})

        device_name = metadata.get("action_name", synergy.get("action_entity", "Climate Device"))
        weather_condition = metadata.get("weather_condition", "Weather condition detected")
        suggested_action = metadata.get("suggested_action", "Adjust climate control")
        rationale = metadata.get("rationale", "Weather-based automation")
        synergy.get("relationship", "weather_automation")

        return f"""Create a Home Assistant automation for this weather-aware opportunity:

DETECTED OPPORTUNITY:
- Device: {device_name}
- Entity ID: {synergy.get('action_entity', '')}
- Weather Condition: {weather_condition}
- Suggested Action: {suggested_action}
- Impact Score: {synergy.get('impact_score', 0.75):.2f}
- Complexity: {synergy.get('complexity', 'medium')}

INSIGHT:
{rationale}

Your smart home has weather data available but it's not being used for climate automation.
This is an opportunity to make your home more responsive to weather conditions.

INSTRUCTIONS:
1. Create valid Home Assistant automation YAML
2. Use numeric state or threshold trigger based on weather sensor
3. Include appropriate condition checks (time of day, current state)
4. Implement the suggested action: {suggested_action}
5. Provide clear rationale explaining energy/comfort benefits
6. Categorize appropriately (typically 'comfort' or 'energy')

OUTPUT FORMAT:
```yaml
alias: "AI Suggested: Weather-Aware [Device Name] Control"
description: "[Brief description of weather-based automation]"
trigger:
  - platform: numeric_state  # or template
    entity_id: sensor.outdoor_temperature  # or weather.forecast
    # Add appropriate threshold
condition:
  # Optional: time-based conditions
action:
  - service: climate.set_temperature
    # or appropriate service
    target:
      entity_id: {synergy.get('action_entity', '')}
```

RATIONALE: [Explain weather-aware benefit for "{device_name}"]
CATEGORY: [energy|comfort]
PRIORITY: [high|medium|low]
"""

    def _build_energy_context_prompt(self, synergy: dict) -> str:
        """Build prompt for energy context synergy (Story AI3.6)"""
        return "Energy context prompt - to be implemented in Story AI3.6"

    def _build_event_context_prompt(self, synergy: dict) -> str:
        """Build prompt for event context synergy (Story AI3.7)"""
        return "Event context prompt - to be implemented in Story AI3.7"

    def _parse_response(self, content: str, synergy: dict) -> dict:
        """
        Parse OpenAI response into suggestion structure.

        Args:
            content: OpenAI response text
            synergy: Original synergy opportunity

        Returns:
            Parsed suggestion dictionary
        """
        import re

        try:
            # Extract YAML block
            yaml_match = re.search(r"```yaml\n(.*?)\n```", content, re.DOTALL)
            automation_yaml = yaml_match.group(1) if yaml_match else ""

            # Extract RATIONALE
            rationale_match = re.search(r"RATIONALE:\s*(.+?)(?:\n|$)", content)
            rationale = rationale_match.group(1).strip() if rationale_match else synergy.get("rationale", "")

            # Extract CATEGORY
            category_match = re.search(r"CATEGORY:\s*(\w+)", content)
            category = category_match.group(1).lower() if category_match else "convenience"

            # Extract PRIORITY
            priority_match = re.search(r"PRIORITY:\s*(\w+)", content)
            priority = priority_match.group(1).lower() if priority_match else "medium"

            # Extract title from YAML alias
            title_match = re.search(r'alias:\s*["\'](.+?)["\']', automation_yaml)
            if not title_match:
                title_match = re.search(r"alias:\s*(.+?)(?:\n|$)", automation_yaml)
            title = title_match.group(1).strip() if title_match else f"Synergy: {synergy.get('relationship', 'Automation')}"

            # Extract description from YAML
            desc_match = re.search(r'description:\s*["\'](.+?)["\']', automation_yaml)
            if not desc_match:
                desc_match = re.search(r"description:\s*(.+?)(?:\n|$)", automation_yaml)
            description = desc_match.group(1).strip() if desc_match else rationale

            # Build suggestion
            return {
                "type": f"synergy_{synergy.get('synergy_type', 'device_pair')}",
                "synergy_id": synergy.get("synergy_id"),
                "title": title,
                "description": description,
                "automation_yaml": automation_yaml,
                "rationale": rationale,
                "category": category,
                "priority": priority,
                "confidence": synergy.get("confidence", 0.85),
                "complexity": synergy.get("complexity", "low"),
                "impact_score": synergy.get("impact_score", 0.7),
                "devices_involved": synergy.get("devices", []),
                # Include pattern validation fields for ranking boost
                "validated_by_patterns": synergy.get("validated_by_patterns", False),
                "pattern_support_score": synergy.get("pattern_support_score", 0.0),
            }


        except Exception as e:
            logger.exception(f"Failed to parse OpenAI response: {e}")
            raise

