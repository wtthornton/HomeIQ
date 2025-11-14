"""
Pattern Matcher - Intelligent pattern detection and variable extraction

Analyzes user requests to find matching automation patterns and extracts
required variables from available entities.
"""

from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass
import logging
import re

from .common_patterns import PatternDefinition, PatternVariable, get_all_patterns

logger = logging.getLogger(__name__)


@dataclass
class PatternMatch:
    """Result of matching a pattern to a user request"""
    pattern_id: str
    pattern: PatternDefinition
    variables: Dict[str, str]  # variable_name -> entity_id (or value)
    confidence: float  # 0.0 - 1.0
    missing_variables: List[str] = None

    def __post_init__(self):
        if self.missing_variables is None:
            self.missing_variables = []


class PatternMatcher:
    """
    Matches user requests to automation patterns and extracts variables.

    Process:
    1. Analyze request text for keyword matches
    2. For each matching pattern, try to extract required variables
    3. Return ranked list of matches with confidence scores
    """

    def __init__(self, patterns: Optional[Dict[str, PatternDefinition]] = None):
        """
        Initialize pattern matcher.

        Args:
            patterns: Pattern library (defaults to all built-in patterns)
        """
        self.patterns = patterns or get_all_patterns()

    async def match_patterns(
        self,
        user_request: str,
        available_entities: List[Dict[str, Any]]
    ) -> List[PatternMatch]:
        """
        Find patterns that match the user's request.

        Args:
            user_request: Natural language automation request
            available_entities: List of available HA entities

        Returns:
            List of pattern matches sorted by confidence (highest first)
        """
        logger.info(f"Matching patterns for request: '{user_request[:100]}'")

        matches = []
        request_lower = user_request.lower()

        for pattern_id, pattern in self.patterns.items():
            # Calculate keyword match score
            keyword_score = self._calculate_keyword_match(request_lower, pattern.keywords)

            if keyword_score > 0.3:  # 30% minimum keyword match
                logger.debug(f"Pattern '{pattern_id}' keyword match: {keyword_score:.2f}")

                # Try to extract variables
                variables, missing = await self._extract_variables(
                    user_request,
                    pattern.variables,
                    available_entities
                )

                if variables:
                    # Calculate final confidence based on keyword match and variable extraction
                    variable_score = len(variables) / max(1, len(pattern.variables))
                    confidence = (keyword_score * 0.6) + (variable_score * 0.4)

                    # Boost confidence by pattern priority
                    confidence = confidence * (pattern.priority / 100.0)

                    matches.append(PatternMatch(
                        pattern_id=pattern_id,
                        pattern=pattern,
                        variables=variables,
                        confidence=confidence,
                        missing_variables=missing
                    ))

                    logger.info(
                        f"✓ Pattern '{pattern_id}' matched "
                        f"(confidence: {confidence:.2f}, "
                        f"vars: {len(variables)}/{len(pattern.variables)})"
                    )

        # Sort by confidence (highest first)
        matches.sort(key=lambda m: m.confidence, reverse=True)

        logger.info(f"Found {len(matches)} pattern match(es)")

        return matches

    def _calculate_keyword_match(self, request: str, keywords: List[str]) -> float:
        """
        Calculate how well request matches pattern keywords.

        Args:
            request: Lowercased user request
            keywords: Pattern keywords

        Returns:
            Match score 0.0 - 1.0
        """
        if not keywords:
            return 0.0

        matched_keywords = 0
        for keyword in keywords:
            # Check for whole word matches (more accurate than substring)
            if re.search(r'\b' + re.escape(keyword) + r'\b', request):
                matched_keywords += 1

        return matched_keywords / len(keywords)

    async def _extract_variables(
        self,
        user_request: str,
        variable_defs: List[PatternVariable],
        available_entities: List[Dict[str, Any]]
    ) -> tuple[Dict[str, str], List[str]]:
        """
        Extract variable values from user request and available entities.

        Args:
            user_request: User's natural language request
            variable_defs: Pattern variable definitions
            available_entities: Available HA entities

        Returns:
            Tuple of (extracted_variables, missing_required_variables)
        """
        extracted = {}
        missing = []

        request_lower = user_request.lower()

        for var_def in variable_defs:
            # Try to find matching entity
            if var_def.domain in ['light', 'binary_sensor', 'sensor', 'person', 'climate', 'cover']:
                match = await self._find_entity_match(
                    request_lower,
                    var_def,
                    available_entities
                )

                if match:
                    extracted[var_def.name] = match
                elif var_def.default:
                    extracted[var_def.name] = var_def.default
                elif var_def.required:
                    missing.append(var_def.name)

            # Handle duration/time/number variables
            elif var_def.domain in ['duration', 'time', 'number']:
                value = self._extract_value_from_request(request_lower, var_def)
                if value:
                    extracted[var_def.name] = value
                elif var_def.default:
                    extracted[var_def.name] = var_def.default
                elif var_def.required:
                    missing.append(var_def.name)

            # Handle action type (turn_on/turn_off)
            elif var_def.domain == 'action':
                if 'turn on' in request_lower or 'turn_on' in request_lower:
                    extracted[var_def.name] = 'turn_on'
                elif 'turn off' in request_lower or 'turn_off' in request_lower:
                    extracted[var_def.name] = 'turn_off'
                elif var_def.default:
                    extracted[var_def.name] = var_def.default

            # Handle any domain (generic entity)
            elif var_def.domain == 'any':
                # Try to extract any entity mention
                match = await self._find_any_entity_match(request_lower, available_entities)
                if match:
                    extracted[var_def.name] = match
                elif var_def.default:
                    extracted[var_def.name] = var_def.default

        return extracted, missing

    async def _find_entity_match(
        self,
        request: str,
        var_def: PatternVariable,
        entities: List[Dict[str, Any]]
    ) -> Optional[str]:
        """
        Find best matching entity for variable definition.

        Scoring based on:
        - Domain match
        - Device class match (if specified)
        - Friendly name appears in request
        - Entity ID appears in request
        """
        candidates = []

        for entity in entities:
            entity_id = entity.get('entity_id', '')

            # Filter by domain
            if not entity_id.startswith(var_def.domain + '.'):
                continue

            # Filter by device class if specified
            if var_def.device_class:
                device_class = entity.get('attributes', {}).get('device_class')
                if device_class != var_def.device_class:
                    continue

            # Calculate match score
            score = 0.0
            friendly_name = entity.get('friendly_name', '').lower()
            entity_id_lower = entity_id.lower()

            # Check if friendly name appears in request
            if friendly_name and friendly_name in request:
                score += 2.0

            # Check if parts of entity_id appear in request
            entity_parts = entity_id_lower.split('.')[1].split('_')
            for part in entity_parts:
                if part in request and len(part) > 2:  # Skip very short words
                    score += 0.5

            # Prefer entities with area info
            if entity.get('area_id'):
                area_name = entity.get('area_id', '').lower()
                if area_name in request:
                    score += 1.0

            if score > 0:
                candidates.append((entity_id, score, friendly_name))

        if not candidates:
            return None

        # Sort by score (highest first) and return best match
        candidates.sort(key=lambda x: x[1], reverse=True)
        best_match = candidates[0]

        logger.debug(
            f"Variable '{var_def.name}' matched to '{best_match[0]}' "
            f"({best_match[2]}) with score {best_match[1]:.1f}"
        )

        return best_match[0]

    async def _find_any_entity_match(
        self,
        request: str,
        entities: List[Dict[str, Any]]
    ) -> Optional[str]:
        """Find any entity that appears in the request"""
        for entity in entities:
            friendly_name = entity.get('friendly_name', '').lower()
            if friendly_name and friendly_name in request:
                return entity.get('entity_id')
        return None

    def _extract_value_from_request(
        self,
        request: str,
        var_def: PatternVariable
    ) -> Optional[str]:
        """
        Extract numeric/time values from request.

        Examples:
        - "5 minutes" → "5"
        - "at 7 AM" → "07:00:00"
        - "20 percent" → "20"
        """
        if var_def.domain == 'duration':
            # Look for duration patterns
            patterns = [
                r'(\d+)\s*minute',
                r'(\d+)\s*min',
                r'(\d+)\s*hour',
                r'(\d+)\s*hr',
            ]
            for pattern in patterns:
                match = re.search(pattern, request)
                if match:
                    value = match.group(1)
                    # Convert hours to minutes if needed
                    if 'hour' in pattern or 'hr' in pattern:
                        value = str(int(value) * 60)
                    return value

        elif var_def.domain == 'time':
            # Look for time patterns
            patterns = [
                r'at\s+(\d{1,2})(?::(\d{2}))?\s*([ap]m)?',
                r'(\d{1,2}):(\d{2})',
            ]
            for pattern in patterns:
                match = re.search(pattern, request)
                if match:
                    hour = int(match.group(1))
                    minute = int(match.group(2)) if match.group(2) else 0

                    # Handle AM/PM
                    if match.lastindex >= 3 and match.group(3):
                        if match.group(3).lower() == 'pm' and hour < 12:
                            hour += 12
                        elif match.group(3).lower() == 'am' and hour == 12:
                            hour = 0

                    return f"{hour:02d}:{minute:02d}:00"

        elif var_def.domain == 'number':
            # Look for number patterns
            patterns = [
                r'(\d+)\s*percent',
                r'(\d+)\s*%',
                r'(\d+)\s*degree',
                r'(\d+)\s*°',
                r'(\d+)',  # Fallback: any number
            ]
            for pattern in patterns:
                match = re.search(pattern, request)
                if match:
                    return match.group(1)

        return None


def get_pattern_matcher() -> PatternMatcher:
    """Factory function to create pattern matcher"""
    return PatternMatcher()
