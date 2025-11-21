"""
Component Detector for Test Stage Enhancement
Task 1.2: Fuzzy Component Detection

Detects timing/delay/repeat components in automation descriptions and YAML
using rapidfuzz for fuzzy matching to handle variations and typos.

Target: 90%+ accuracy in detecting stripped components.
"""

import logging
import re
from dataclasses import dataclass
from typing import Any

import yaml

RAPIDFUZZ_AVAILABLE = False
try:
    from rapidfuzz import fuzz
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    logging.warning("rapidfuzz not available, fuzzy matching disabled")

logger = logging.getLogger(__name__)


@dataclass
class DetectedComponent:
    """Represents a detected component that was stripped for testing"""
    # component_type behaves like an enum; keep the documentation in sync with
    # the actual supported values to avoid confusion elsewhere in the service.
    component_type: str  # One of: 'delay', 'repeat', 'time_condition', 'queue', 'numeric_state'
    original_value: str  # Original text/value from description or YAML
    detected_from: str  # 'description' or 'yaml'
    confidence: float  # 0.0-1.0 confidence score
    reason: str  # Why it was stripped


class ComponentDetector:
    """
    Detects timing/delay/repeat components in automation descriptions and YAML.

    Uses rapidfuzz for fuzzy matching to handle variations like:
    - "wait 30 seconds" vs "delay 30s"
    - "repeat 3 times" vs "loop 3x"
    - "after 5pm" vs "post 5:00 PM"
    """

    def __init__(self):
        """Initialize component detector"""
        self.use_fuzzy = RAPIDFUZZ_AVAILABLE
        if not self.use_fuzzy:
            logger.warning("⚠️ rapidfuzz not available, using exact matching only")

        # Pattern definitions for exact matching
        self.delay_patterns = [
            r'delay[:\s]+["\']?(\d+(?:\.\d+)?)\s*(second|sec|secs|minute|min|mins|hour|hr|hrs)',
            r'wait[:\s]+["\']?(\d+(?:\.\d+)?)\s*(second|sec|secs|minute|min|mins|hour|hr|hrs)',
            r'for[:\s]+["\']?(\d+(?:\.\d+)?)\s*(second|sec|secs|minute|min|mins|hour|hr|hrs)',
        ]

        self.repeat_patterns = [
            r"repeat[:\s]+(\d+)",
            r"(\d+)\s*times",
            r"loop[:\s]+(\d+)",
            r"cycle[:\s]+(\d+)",
        ]

        self.time_condition_patterns = [
            r"after[:\s]+(\d{1,2}:?\d{0,2}\s*(?:am|pm|AM|PM)?)",
            r"before[:\s]+(\d{1,2}:?\d{0,2}\s*(?:am|pm|AM|PM)?)",
            r"at[:\s]+(\d{1,2}:?\d{0,2}\s*(?:am|pm|AM|PM)?)",
            r"between[:\s]+(\d{1,2}:?\d{0,2})\s+and\s+(\d{1,2}:?\d{0,2})",
        ]

        # Fuzzy search keywords
        self.delay_keywords = ["delay", "wait", "for", "pause", "sleep", "hold"]
        self.repeat_keywords = ["repeat", "loop", "cycle", "times", "iterations"]
        self.time_keywords = ["after", "before", "at", "between", "sunset", "sunrise", "pm", "am"]

    def detect_stripped_components(
        self,
        yaml_content: str,
        original_description: str,
    ) -> list[DetectedComponent]:
        """
        Detect components that were stripped for testing.

        Args:
            yaml_content: Generated test YAML (should not have delays/repeats)
            original_description: Original automation description

        Returns:
            List of detected components with type, value, and confidence
        """
        detected = []

        # Detect from YAML (sometimes components leak through)
        yaml_components = self._detect_from_yaml(yaml_content)
        detected.extend(yaml_components)

        # Detect from original description (primary source)
        description_components = self._detect_from_description(original_description)
        detected.extend(description_components)

        # Deduplicate (prefer description-based with higher confidence)
        detected = self._deduplicate_components(detected)

        logger.info(f"🔍 Detected {len(detected)} stripped components: {[c.component_type for c in detected]}")
        return detected

    def _detect_from_yaml(self, yaml_content: str) -> list[DetectedComponent]:
        """Detect components from YAML content"""
        detected = []

        try:
            yaml_data = yaml.safe_load(yaml_content)
            if not yaml_data:
                return detected

            # Detect delays in action blocks
            actions = yaml_data.get("action", [])
            if isinstance(actions, list):
                for _i, action in enumerate(actions):
                    if isinstance(action, dict):
                        # Check for delay
                        if "delay" in action:
                            delay_value = action["delay"]
                            detected.append(DetectedComponent(
                                component_type="delay",
                                original_value=str(delay_value),
                                detected_from="yaml",
                                confidence=1.0,
                                reason="Found delay in YAML action block",
                            ))

                        # Check for repeat
                        if "repeat" in action:
                            repeat_value = action.get("repeat", {})
                            if isinstance(repeat_value, dict) and "count" in repeat_value:
                                count = repeat_value["count"]
                                detected.append(DetectedComponent(
                                    component_type="repeat",
                                    original_value=str(count),
                                    detected_from="yaml",
                                    confidence=1.0,
                                    reason="Found repeat block in YAML",
                                ))

            # Detect time conditions
            conditions = yaml_data.get("condition", [])
            if isinstance(conditions, list):
                for condition in conditions:
                    if isinstance(condition, dict) and condition.get("condition") == "time":
                        after = condition.get("after")
                        before = condition.get("before")
                        if after or before:
                            time_value = f"after={after}" if after else f"before={before}"
                            detected.append(DetectedComponent(
                                component_type="time_condition",
                                original_value=time_value,
                                detected_from="yaml",
                                confidence=1.0,
                                reason="Found time condition in YAML",
                            ))

        except Exception as e:
            logger.warning(f"Error parsing YAML for component detection: {e}")

        return detected

    def _detect_from_description(self, description: str) -> list[DetectedComponent]:
        """Detect components from original description using pattern matching and fuzzy search"""
        detected = []
        description_lower = description.lower()

        # Detect delays
        delay_matches = self._detect_delays(description, description_lower)
        detected.extend(delay_matches)

        # Detect repeats
        repeat_matches = self._detect_repeats(description, description_lower)
        detected.extend(repeat_matches)

        # Detect time conditions
        time_matches = self._detect_time_conditions(description, description_lower)
        detected.extend(time_matches)

        return detected

    def _detect_delays(self, description: str, description_lower: str) -> list[DetectedComponent]:
        """Detect delay components"""
        detected = []

        # Exact pattern matching
        for pattern in self.delay_patterns:
            matches = re.finditer(pattern, description_lower, re.IGNORECASE)
            for match in matches:
                value = match.group(0)
                detected.append(DetectedComponent(
                    component_type="delay",
                    original_value=value,
                    detected_from="description",
                    confidence=0.95,
                    reason=f"Matched delay pattern: {pattern}",
                ))

        # Fuzzy matching for variations
        if self.use_fuzzy:
            for keyword in self.delay_keywords:
                # Look for keyword followed by time values
                keyword_pos = description_lower.find(keyword)
                if keyword_pos != -1:
                    # Extract surrounding text
                    start = max(0, keyword_pos - 10)
                    end = min(len(description_lower), keyword_pos + 50)
                    context = description_lower[start:end]

                    # Check if context contains time references
                    if re.search(r"\d+\s*(?:second|Using|min|hour|sec)", context):
                        # Calculate fuzzy score with common delay phrases
                        delay_phrases = [
                            f"{keyword} 30 seconds",
                            f"{keyword} for 30 seconds",
                            f"{keyword} 1 minute",
                        ]

                        max_score = 0.0
                        best_match = None
                        for phrase in delay_phrases:
                            score = fuzz.token_sort_ratio(context, phrase) / 100.0
                            if score > max_score and score > 0.6:  # 60% threshold
                                max_score = score
                                best_match = phrase

                        if best_match:
                            detected.append(DetectedComponent(
                                component_type="delay",
                                original_value=context.strip(),
                                detected_from="description",
                                confidence=max_score * 0.8,  # Lower confidence for fuzzy
                                reason=f"Fuzzy matched delay keyword: {keyword}",
                            ))

        return detected

    def _detect_repeats(self, description: str, description_lower: str) -> list[DetectedComponent]:
        """Detect repeat/loop components"""
        detected = []

        # Exact pattern matching
        for pattern in self.repeat_patterns:
            matches = re.finditer(pattern, description_lower, re.IGNORECASE)
            for match in matches:
                value = match.group(0)
                count = match.group(1) if match.groups() else None
                detected.append(DetectedComponent(
                    component_type="repeat",
                    original_value=f"{count} times" if count else value,
                    detected_from="description",
                    confidence=0.95,
                    reason=f"Matched repeat pattern: {pattern}",
                ))

        # Fuzzy matching
        if self.use_fuzzy:
            for keyword in self.repeat_keywords:
                keyword_pos = description_lower.find(keyword)
                if keyword_pos != -1:
                    context = description_lower[max(0, keyword_pos - 5):min(len(description_lower), keyword_pos + 30)]

                    if re.search(r"\d+", context):
                        repeat_phrases = [
                            "repeat 3 times",
                            "loop 3 times",
                            f"{keyword} 3",
                        ]

                        max_score = 0.0
                        for phrase in repeat_phrases:
                            score = fuzz.token_sort_ratio(context, phrase) / 100.0
                            if score > max_score and score > 0.6:
                                max_score = score

                        if max_score > 0.6:
                            detected.append(DetectedComponent(
                                component_type="repeat",
                                original_value=context.strip(),
                                detected_from="description",
                                confidence=max_score * 0.8,
                                reason=f"Fuzzy matched repeat keyword: {keyword}",
                            ))

        return detected

    def _detect_time_conditions(self, description: str, description_lower: str) -> list[DetectedComponent]:
        """Detect time-based conditions"""
        detected = []

        # Exact pattern matching
        for pattern in self.time_condition_patterns:
            matches = re.finditer(pattern, description_lower, re.IGNORECASE)
            for match in matches:
                value = match.group(0)
                detected.append(DetectedComponent(
                    component_type="time_condition",
                    original_value=value,
                    detected_from="description",
                    confidence=0.95,
                    reason=f"Matched time condition pattern: {pattern}",
                ))

        # Special time references
        special_times = ["sunset", "sunrise", "dawn", "dusk"]
        for time_ref in special_times:
            if time_ref in description_lower:
                detected.append(DetectedComponent(
                    component_type="time_condition",
                    original_value=time_ref,
                    detected_from="description",
                    confidence=0.9,
                    reason=f"Found special time reference: {time_ref}",
                ))

        return detected

    def _deduplicate_components(self, components: list[DetectedComponent]) -> list[DetectedComponent]:
        """Remove duplicate components, keeping highest confidence"""
        seen = {}

        for component in components:
            key = (component.component_type, component.original_value.lower())

            if key not in seen or component.confidence > seen[key].confidence:
                seen[key] = component

        return list(seen.values())

    def format_components_for_preview(self, components: list[DetectedComponent]) -> list[dict[str, Any]]:
        """
        Format detected components for user-friendly preview.

        Returns:
            List of dictionaries with formatted component info
        """
        formatted = []

        for comp in components:
            # Format based on component type
            if comp.component_type == "delay":
                preview = f"Delay: {comp.original_value}"
            elif comp.component_type == "repeat":
                preview = f"Repeat: {comp.original_value}"
            elif comp.component_type == "time_condition":
                preview = f"Time condition: {comp.original_value}"
            else:
                preview = f"{comp.component_type}: {comp.original_value}"

            formatted.append({
                "type": comp.component_type,
                "preview": preview,
                "original_value": comp.original_value,
                "confidence": round(comp.confidence, 2),
                "reason": comp.reason,
            })

        return formatted

