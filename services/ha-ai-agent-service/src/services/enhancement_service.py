"""
Automation Enhancement Service

Generates automation enhancements using:
- LLM for small/medium/large enhancements
- Patterns API for advanced enhancements
- Synergies API for fun/crazy enhancements
"""
import asyncio
import logging
import re
from typing import Any

import yaml
from openai import AsyncOpenAI, APITimeoutError

from ..clients.patterns_client import PatternsClient
from ..clients.synergies_client import SynergiesClient
from ..config import Settings

logger = logging.getLogger(__name__)


class Enhancement:
    """Represents a single automation enhancement"""
    
    def __init__(
        self,
        level: str,
        title: str,
        description: str,
        enhanced_yaml: str,
        changes: list[str],
        source: str = "llm",
        pattern_id: int | None = None,
        synergy_id: str | None = None
    ):
        self.level = level
        self.title = title
        self.description = description
        self.enhanced_yaml = enhanced_yaml
        self.changes = changes
        self.source = source
        self.pattern_id = pattern_id
        self.synergy_id = synergy_id
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response"""
        return {
            "level": self.level,
            "title": self.title,
            "description": self.description,
            "enhanced_yaml": self.enhanced_yaml,
            "changes": self.changes,
            "source": self.source,
            "pattern_id": self.pattern_id,
            "synergy_id": self.synergy_id
        }


class AutomationEnhancementService:
    """
    Generates automation enhancements using patterns and synergies.
    """
    
    def __init__(
        self,
        openai_client: AsyncOpenAI,
        patterns_client: PatternsClient | None = None,
        synergies_client: SynergiesClient | None = None,
        settings: Settings | None = None
    ):
        """
        Initialize enhancement service.

        Args:
            openai_client: OpenAI client for LLM-based enhancements
            patterns_client: Patterns API client (optional)
            synergies_client: Synergies API client (optional)
            settings: Settings instance (optional)
        """
        if settings is None:
            settings = Settings()
        self.openai_client = openai_client
        self.settings = settings
        self.patterns_client = patterns_client or PatternsClient(settings=settings)
        self.synergies_client = synergies_client or SynergiesClient(settings=settings)
    
    async def generate_enhancements(
        self,
        automation_yaml: str,
        original_prompt: str,
        entities: list[str],
        areas: list[str]
    ) -> list[Enhancement]:
        """
        Generate 5 enhancements:
        1-3: LLM-based (small, medium, large)
        4: Pattern-driven (advanced)
        5: Synergy-driven (fun/crazy)

        Args:
            automation_yaml: Original automation YAML
            original_prompt: User's original request
            entities: List of entity IDs in the automation
            areas: List of area IDs in the automation

        Returns:
            List of 5 Enhancement objects (may be fewer if some fail)
        """
        enhancements = []
        
        # 1-3: LLM-based enhancements (with timeout)
        logger.info("Generating LLM-based enhancements (small, medium, large)")
        try:
            llm_enhancements = await asyncio.wait_for(
                self._generate_llm_enhancements(automation_yaml, original_prompt, entities),
                timeout=45.0  # 45 second timeout for 3 enhancements (LLM can be slow)
            )
            enhancements.extend(llm_enhancements)
        except (asyncio.TimeoutError, APITimeoutError) as e:
            logger.warning(f"LLM enhancements timed out: {e}. Using fallbacks.")
            enhancements.extend([
                self._create_fallback_enhancement(automation_yaml, 1),
                self._create_fallback_enhancement(automation_yaml, 2),
                self._create_fallback_enhancement(automation_yaml, 3)
            ])
        except Exception as e:
            logger.error(f"Error generating LLM enhancements: {e}", exc_info=True)
            enhancements.extend([
                self._create_fallback_enhancement(automation_yaml, 1),
                self._create_fallback_enhancement(automation_yaml, 2),
                self._create_fallback_enhancement(automation_yaml, 3)
            ])
        
        # 4: Pattern-driven (Advanced) - with timeout
        logger.info("Generating pattern-driven enhancement (advanced)")
        try:
            pattern_enhancement = await asyncio.wait_for(
                self._generate_pattern_enhancement(automation_yaml, entities, areas),
                timeout=30.0  # Increased timeout for pattern + LLM enhancement
            )
            enhancements.append(pattern_enhancement)
        except (asyncio.TimeoutError, APITimeoutError) as e:
            logger.warning(f"Pattern enhancement timed out: {e}. Using fallback.")
            enhancements.append(await self._generate_fallback_advanced(automation_yaml))
        except Exception as e:
            logger.error(f"Error generating pattern enhancement: {e}", exc_info=True)
            enhancements.append(await self._generate_fallback_advanced(automation_yaml))
        
        # 5: Synergy-driven (Fun/Crazy) - with timeout
        logger.info("Generating synergy-driven enhancement (fun/crazy)")
        try:
            synergy_enhancement = await asyncio.wait_for(
                self._generate_synergy_enhancement(automation_yaml, entities, areas),
                timeout=30.0  # Increased timeout for synergy + LLM enhancement
            )
            enhancements.append(synergy_enhancement)
        except (asyncio.TimeoutError, APITimeoutError) as e:
            logger.warning(f"Synergy enhancement timed out: {e}. Using fallback.")
            enhancements.append(self._create_fallback_enhancement(automation_yaml, 5))
        except Exception as e:
            logger.error(f"Error generating synergy enhancement: {e}", exc_info=True)
            enhancements.append(self._create_fallback_enhancement(automation_yaml, 5))
        
        # Ensure we have at least 3 enhancements
        while len(enhancements) < 3:
            enhancements.append(self._create_fallback_enhancement(automation_yaml, len(enhancements) + 1))
        
        return enhancements[:5]  # Return up to 5
    
    async def _generate_llm_enhancements(
        self,
        automation_yaml: str,
        original_prompt: str,
        entities: list[str]
    ) -> list[Enhancement]:
        """Generate 3 LLM-based enhancements (small, medium, large)"""
        try:
            prompt = f"""You are an automation enhancement expert. Given this automation:

Original Request: {original_prompt}

Automation YAML:
```yaml
{automation_yaml}
```

Generate 3 enhancement suggestions with increasing complexity:

1. **Small Enhancement**: Minor tweaks (timing, colors, brightness, simple conditions)
2. **Medium Enhancement**: Functional improvements (notifications, multi-room, time conditions)
3. **Large Enhancement**: Feature additions (multi-device coordination, scenes, weather triggers)

For each enhancement, provide:
- Title: Short descriptive name
- Description: What the enhancement does
- Enhanced YAML: Complete valid Home Assistant automation YAML
- Changes: List of 2-3 key changes made

Return your response as a JSON object with this structure:
{{
  "enhancements": [
    {{
      "level": "small",
      "title": "...",
      "description": "...",
      "enhanced_yaml": "...",
      "changes": ["...", "..."]
    }},
    {{
      "level": "medium",
      "title": "...",
      "description": "...",
      "enhanced_yaml": "...",
      "changes": ["...", "..."]
    }},
    {{
      "level": "large",
      "title": "...",
      "description": "...",
      "enhanced_yaml": "...",
      "changes": ["...", "..."]
    }}
  ]
}}

Ensure all YAML is valid and maintains the original automation's intent."""

            response = await self.openai_client.chat.completions.create(
                model=self.settings.openai_model,
                messages=[
                    {"role": "system", "content": "You are an expert at enhancing Home Assistant automations. Always return valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty response from OpenAI")
            
            import json
            data = json.loads(content)
            
            enhancements = []
            for enh_data in data.get("enhancements", []):
                enhancements.append(Enhancement(
                    level=enh_data.get("level", "small"),
                    title=enh_data.get("title", "Enhancement"),
                    description=enh_data.get("description", ""),
                    enhanced_yaml=enh_data.get("enhanced_yaml", automation_yaml),
                    changes=enh_data.get("changes", []),
                    source="llm"
                ))
            
            # Ensure we have exactly 3 enhancements
            while len(enhancements) < 3:
                enhancements.append(self._create_fallback_enhancement(
                    automation_yaml, len(enhancements) + 1
                ))
            
            return enhancements[:3]
            
        except Exception as e:
            logger.error(f"Error generating LLM enhancements: {e}", exc_info=True)
            # Return fallback enhancements
            return [
                self._create_fallback_enhancement(automation_yaml, 1),
                self._create_fallback_enhancement(automation_yaml, 2),
                self._create_fallback_enhancement(automation_yaml, 3)
            ]
    
    async def _generate_pattern_enhancement(
        self,
        automation_yaml: str,
        entities: list[str],
        areas: list[str]
    ) -> Enhancement:
        """Generate pattern-driven enhancement (advanced)"""
        try:
            # Query patterns for relevant devices/entities
            patterns = await self.patterns_client.get_patterns(
                device_ids=entities,
                min_confidence=0.7,
                limit=10
            )
            
            if not patterns:
                logger.info("No patterns found, generating fallback advanced enhancement")
                return await self._generate_fallback_advanced(automation_yaml)
            
            # Find most relevant pattern
            relevant_pattern = self._find_best_pattern(patterns, automation_yaml)
            
            if relevant_pattern:
                # Generate enhancement YAML using pattern
                enhanced_yaml = await self._apply_pattern_to_automation(
                    automation_yaml,
                    relevant_pattern
                )
                
                pattern_type = relevant_pattern.get("pattern_type", "pattern")
                confidence = relevant_pattern.get("confidence", 0.0)
                occurrences = relevant_pattern.get("occurrences", 0)
                
                return Enhancement(
                    level="advanced",
                    title=f"Optimize with {pattern_type.replace('_', ' ').title()} Pattern",
                    description=f"Based on detected pattern: {relevant_pattern.get('pattern_metadata', {}).get('description', 'Pattern-based optimization')}",
                    enhanced_yaml=enhanced_yaml,
                    changes=[
                        f"Applied {pattern_type.replace('_', ' ')} pattern",
                        f"Confidence: {confidence:.0%}",
                        f"Occurrences: {occurrences} times"
                    ],
                    source="pattern",
                    pattern_id=relevant_pattern.get("id")
                )
            else:
                return await self._generate_fallback_advanced(automation_yaml)
                
        except Exception as e:
            logger.error(f"Error generating pattern enhancement: {e}", exc_info=True)
            return await self._generate_fallback_advanced(automation_yaml)
    
    async def _generate_synergy_enhancement(
        self,
        automation_yaml: str,
        entities: list[str],
        areas: list[str]
    ) -> Enhancement:
        """Generate synergy-driven enhancement (fun/crazy)"""
        try:
            # Query synergies for relevant areas/devices
            area = areas[0] if areas else None
            synergies = await self.synergies_client.get_synergies(
                area=area,
                device_ids=entities,
                min_confidence=0.6,
                limit=10
            )
            
            if not synergies:
                logger.info("No synergies found, generating fallback fun enhancement")
                return await self._generate_fallback_fun(automation_yaml)
            
            # Find most relevant synergy
            relevant_synergy = self._find_best_synergy(synergies, entities, areas)
            
            if relevant_synergy:
                # Generate enhancement YAML using synergy
                enhanced_yaml = await self._apply_synergy_to_automation(
                    automation_yaml,
                    relevant_synergy
                )
                
                synergy_type = relevant_synergy.get("synergy_type", "device_pair")
                impact_score = relevant_synergy.get("impact_score", 0.0)
                device_ids = relevant_synergy.get("device_ids", [])
                explanation = relevant_synergy.get("explanation", {})
                description = explanation.get("summary", "") if isinstance(explanation, dict) else str(explanation)
                
                return Enhancement(
                    level="fun",
                    title=f"Combine with {synergy_type.replace('_', ' ').title()}",
                    description=description or f"Creative multi-device coordination using {synergy_type}",
                    enhanced_yaml=enhanced_yaml,
                    changes=[
                        f"Added {synergy_type.replace('_', ' ')} coordination",
                        f"Impact score: {impact_score:.1f}",
                        f"Devices: {', '.join(device_ids[:3])}"
                    ],
                    source="synergy",
                    synergy_id=relevant_synergy.get("synergy_id")
                )
            else:
                return await self._generate_fallback_fun(automation_yaml)
                
        except Exception as e:
            logger.error(f"Error generating synergy enhancement: {e}", exc_info=True)
            return await self._generate_fallback_fun(automation_yaml)
    
    def _find_best_pattern(
        self,
        patterns: list[dict[str, Any]],
        automation_yaml: str
    ) -> dict[str, Any] | None:
        """Find the most relevant pattern for the automation"""
        if not patterns:
            return None
        
        # Simple scoring: prefer higher confidence and more occurrences
        scored_patterns = [
            (p, p.get("confidence", 0.0) * p.get("occurrences", 0))
            for p in patterns
        ]
        scored_patterns.sort(key=lambda x: x[1], reverse=True)
        
        return scored_patterns[0][0] if scored_patterns else None
    
    def _find_best_synergy(
        self,
        synergies: list[dict[str, Any]],
        entities: list[str],
        areas: list[str]
    ) -> dict[str, Any] | None:
        """Find the most relevant synergy for the automation"""
        if not synergies:
            return None
        
        # Score synergies by impact and relevance
        scored_synergies = []
        for synergy in synergies:
            synergy_device_ids = synergy.get("device_ids", [])
            # Check overlap with automation entities
            overlap = len(set(entities) & set(synergy_device_ids))
            impact_score = synergy.get("impact_score", 0.0)
            confidence = synergy.get("confidence", 0.0)
            
            # Score: impact * confidence * (1 + overlap bonus)
            score = impact_score * confidence * (1 + overlap * 0.2)
            scored_synergies.append((synergy, score))
        
        scored_synergies.sort(key=lambda x: x[1], reverse=True)
        return scored_synergies[0][0] if scored_synergies else None
    
    async def _apply_pattern_to_automation(
        self,
        automation_yaml: str,
        pattern: dict[str, Any]
    ) -> str:
        """Apply pattern to automation YAML using LLM"""
        try:
            pattern_type = pattern.get("pattern_type", "")
            pattern_metadata = pattern.get("pattern_metadata", {})
            
            prompt = f"""You are an automation enhancement expert. Apply this detected pattern to the automation:

Pattern Type: {pattern_type}
Pattern Details: {pattern_metadata}

Original Automation YAML:
```yaml
{automation_yaml}
```

Enhance the automation to leverage this pattern. For example:
- If pattern_type is "time_of_day", optimize the trigger timing
- If pattern_type is "co_occurrence", add related device coordination

Return ONLY the enhanced YAML, no explanations."""

            response = await self.openai_client.chat.completions.create(
                model=self.settings.openai_model,
                messages=[
                    {"role": "system", "content": "You are an expert at enhancing Home Assistant automations with patterns. Return only valid YAML."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5
            )
            
            enhanced_yaml = response.choices[0].message.content or automation_yaml
            # Clean up markdown code blocks if present
            enhanced_yaml = re.sub(r'```yaml\n?', '', enhanced_yaml)
            enhanced_yaml = re.sub(r'```\n?', '', enhanced_yaml).strip()
            
            return enhanced_yaml
            
        except Exception as e:
            logger.error(f"Error applying pattern: {e}", exc_info=True)
            return automation_yaml
    
    async def _apply_synergy_to_automation(
        self,
        automation_yaml: str,
        synergy: dict[str, Any]
    ) -> str:
        """Apply synergy to automation YAML using LLM"""
        try:
            synergy_type = synergy.get("synergy_type", "")
            device_ids = synergy.get("device_ids", [])
            explanation = synergy.get("explanation", {})
            description = explanation.get("summary", "") if isinstance(explanation, dict) else ""
            
            prompt = f"""You are an automation enhancement expert. Apply this detected synergy to create a fun, creative enhancement:

Synergy Type: {synergy_type}
Devices: {', '.join(device_ids)}
Description: {description}

Original Automation YAML:
```yaml
{automation_yaml}
```

Enhance the automation to coordinate with these devices in a creative, fun way. Make it interactive and engaging!

Return ONLY the enhanced YAML, no explanations."""

            response = await self.openai_client.chat.completions.create(
                model=self.settings.openai_model,
                messages=[
                    {"role": "system", "content": "You are an expert at creating fun, creative Home Assistant automations with synergies. Return only valid YAML."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8  # Higher temperature for creativity
            )
            
            enhanced_yaml = response.choices[0].message.content or automation_yaml
            # Clean up markdown code blocks if present
            enhanced_yaml = re.sub(r'```yaml\n?', '', enhanced_yaml)
            enhanced_yaml = re.sub(r'```\n?', '', enhanced_yaml).strip()
            
            return enhanced_yaml
            
        except Exception as e:
            logger.error(f"Error applying synergy: {e}", exc_info=True)
            return automation_yaml
    
    async def _generate_fallback_advanced(self, automation_yaml: str) -> Enhancement:
        """Generate fallback advanced enhancement using LLM"""
        try:
            prompt = f"""Create an advanced enhancement for this automation:

```yaml
{automation_yaml}
```

Add smart features like:
- Time-based conditions
- Multi-device coordination
- Energy optimization
- Adaptive behavior

Return JSON with: title, description, enhanced_yaml, changes (array)"""

            response = await self.openai_client.chat.completions.create(
                model=self.settings.openai_model,
                messages=[
                    {"role": "system", "content": "You are an expert at creating advanced Home Assistant automations. Return valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.6,
                response_format={"type": "json_object"}
            )
            
            import json
            data = json.loads(response.choices[0].message.content or "{}")
            
            return Enhancement(
                level="advanced",
                title=data.get("title", "Advanced Enhancement"),
                description=data.get("description", "Smart automation features"),
                enhanced_yaml=data.get("enhanced_yaml", automation_yaml),
                changes=data.get("changes", ["Advanced features added"]),
                source="llm"
            )
        except Exception as e:
            logger.error(f"Error generating fallback advanced: {e}", exc_info=True)
            return self._create_fallback_enhancement(automation_yaml, 4)
    
    async def _generate_fallback_fun(self, automation_yaml: str) -> Enhancement:
        """Generate fallback fun enhancement using LLM"""
        try:
            prompt = f"""Create a fun, creative enhancement for this automation:

```yaml
{automation_yaml}
```

Make it creative and fun with:
- Random variations
- Interactive patterns
- Surprise elements
- Themed effects

Return JSON with: title, description, enhanced_yaml, changes (array)"""

            response = await self.openai_client.chat.completions.create(
                model=self.settings.openai_model,
                messages=[
                    {"role": "system", "content": "You are an expert at creating fun, creative Home Assistant automations. Return valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.9,  # High temperature for creativity
                response_format={"type": "json_object"}
            )
            
            import json
            data = json.loads(response.choices[0].message.content or "{}")
            
            return Enhancement(
                level="fun",
                title=data.get("title", "Fun Enhancement"),
                description=data.get("description", "Creative automation features"),
                enhanced_yaml=data.get("enhanced_yaml", automation_yaml),
                changes=data.get("changes", ["Fun features added"]),
                source="llm"
            )
        except Exception as e:
            logger.error(f"Error generating fallback fun: {e}", exc_info=True)
            return self._create_fallback_enhancement(automation_yaml, 5)
    
    def _create_fallback_enhancement(
        self,
        automation_yaml: str,
        level_num: int
    ) -> Enhancement:
        """Create a simple fallback enhancement"""
        level_map = {
            1: ("small", "Small Enhancement", "Minor tweaks and improvements"),
            2: ("medium", "Medium Enhancement", "Functional improvements"),
            3: ("large", "Large Enhancement", "Feature additions"),
            4: ("advanced", "Advanced Enhancement", "Smart pattern-based features"),
            5: ("fun", "Fun Enhancement", "Creative and interactive features")
        }
        
        level, title, description = level_map.get(level_num, ("small", "Enhancement", "Automation enhancement"))
        
        return Enhancement(
            level=level,
            title=title,
            description=description,
            enhanced_yaml=automation_yaml,
            changes=["Enhancement applied"],
            source="fallback"
        )
    
    @staticmethod
    def extract_entities_from_yaml(yaml_str: str) -> list[str]:
        """Extract entity IDs from YAML string"""
        entities = []
        # Match entity_id patterns
        entity_pattern = r'entity_id:\s*["\']?([^"\'\n]+)["\']?'
        matches = re.findall(entity_pattern, yaml_str, re.IGNORECASE)
        entities.extend(matches)
        
        # Match target.entity_id patterns
        target_pattern = r'target:\s*\n\s*entity_id:\s*["\']?([^"\'\n]+)["\']?'
        matches = re.findall(target_pattern, yaml_str, re.IGNORECASE | re.MULTILINE)
        entities.extend(matches)
        
        return list(set(entities))  # Remove duplicates
    
    @staticmethod
    def extract_areas_from_yaml(yaml_str: str) -> list[str]:
        """Extract area IDs from YAML string"""
        areas = []
        # Match area_id patterns
        area_pattern = r'area_id:\s*["\']?([^"\'\n]+)["\']?'
        matches = re.findall(area_pattern, yaml_str, re.IGNORECASE)
        areas.extend(matches)
        
        # Match target.area_id patterns
        target_pattern = r'target:\s*\n\s*area_id:\s*["\']?([^"\'\n]+)["\']?'
        matches = re.findall(target_pattern, yaml_str, re.IGNORECASE | re.MULTILINE)
        areas.extend(matches)
        
        return list(set(areas))  # Remove duplicates

