"""
Query Expansion for Device Matching

Expands queries with synonyms and related terms to improve device matching.
Implements 2025 best practices for natural language understanding.
"""

import logging
import re

logger = logging.getLogger(__name__)


class QueryExpander:
    """
    Expands queries with device synonyms and related terms.
    
    Improves matching by:
    - Adding synonyms (light → lamp, bulb, fixture)
    - Adding related terms (office → workspace, desk)
    - Expanding abbreviations (LR → Living Room)
    """

    # Device type synonyms
    DEVICE_SYNONYMS = {
        'light': ['lamp', 'bulb', 'fixture', 'luminaire', 'lighting'],
        'lights': ['lamps', 'bulbs', 'fixtures', 'luminaires', 'lighting'],
        'switch': ['toggle', 'control', 'button'],
        'switches': ['toggles', 'controls', 'buttons'],
        'fan': ['ventilator', 'blower', 'vent'],
        'fans': ['ventilators', 'blowers', 'vents'],
        'sensor': ['detector', 'monitor'],
        'sensors': ['detectors', 'monitors'],
        'thermostat': ['temperature control', 'climate control'],
        'thermostats': ['temperature controls', 'climate controls'],
        'lock': ['deadbolt', 'door lock'],
        'locks': ['deadbolts', 'door locks'],
        'camera': ['cam', 'security camera'],
        'cameras': ['cams', 'security cameras'],
        'door': ['entrance', 'entry'],
        'doors': ['entrances', 'entries'],
        'window': ['opening'],
        'windows': ['openings'],
    }

    # Location synonyms and abbreviations
    LOCATION_SYNONYMS = {
        'office': ['workspace', 'study', 'desk area'],
        'living room': ['lounge', 'family room', 'sitting room'],
        'bedroom': ['sleeping room', 'master bedroom'],
        'kitchen': ['cooking area'],
        'bathroom': ['restroom', 'washroom'],
        'garage': ['carport', 'parking'],
        'basement': ['cellar', 'lower level'],
        'attic': ['loft', 'upper level'],
        # Abbreviations
        'lr': 'living room',
        'br': 'bedroom',
        'ba': 'bathroom',
        'gar': 'garage',
        'bas': 'basement',
    }

    # Action synonyms
    ACTION_SYNONYMS = {
        'turn on': ['activate', 'enable', 'power on', 'switch on'],
        'turn off': ['deactivate', 'disable', 'power off', 'switch off'],
        'dim': ['lower brightness', 'reduce brightness'],
        'brighten': ['increase brightness', 'raise brightness'],
        'flash': ['blink', 'pulse', 'strobe'],
        'fade': ['gradually change', 'smooth transition'],
    }

    def expand(self, query: str) -> str:
        """
        Expand query with synonyms and related terms.
        
        Args:
            query: Original query text
            
        Returns:
            Expanded query with synonyms added
        """
        if not query or not query.strip():
            return query

        original_query = query
        expanded_terms: set[str] = set()

        # Split query into words (preserve case for matching)
        query_lower = query.lower()
        words = re.findall(r'\b\w+\b', query_lower)

        # Expand device synonyms
        for word in words:
            if word in self.DEVICE_SYNONYMS:
                expanded_terms.update(self.DEVICE_SYNONYMS[word])

        # Expand location synonyms and abbreviations
        for word in words:
            if word in self.LOCATION_SYNONYMS:
                synonym = self.LOCATION_SYNONYMS[word]
                if isinstance(synonym, str):
                    # Abbreviation expansion
                    expanded_terms.add(synonym)
                elif isinstance(synonym, list):
                    expanded_terms.update(synonym)

        # Check for multi-word location matches
        for location, synonyms in self.LOCATION_SYNONYMS.items():
            if location in query_lower:
                if isinstance(synonyms, list):
                    expanded_terms.update(synonyms)
                elif isinstance(synonyms, str):
                    expanded_terms.add(synonyms)

        # Expand action synonyms (for phrase matching)
        for action, synonyms in self.ACTION_SYNONYMS.items():
            if action in query_lower:
                expanded_terms.update(synonyms)

        # Build expanded query
        if expanded_terms:
            # Add expanded terms to original query
            expanded_query = f"{query} {' '.join(sorted(expanded_terms))}"
            logger.debug(f"Query expansion: '{query}' → '{expanded_query}' (added {len(expanded_terms)} terms)")
            return expanded_query

        return query

    def expand_with_context(self, query: str, context: list[str]) -> str:
        """
        Expand query with context-aware synonyms.
        
        Args:
            query: Original query text
            context: List of context terms (e.g., device names, locations)
            
        Returns:
            Expanded query
        """
        expanded = self.expand(query)

        # Add context terms that might help matching
        if context:
            # Filter context terms (avoid duplicates, very short terms)
            context_terms = [
                term for term in context
                if len(term) > 2 and term.lower() not in expanded.lower()
            ]

            if context_terms:
                expanded = f"{expanded} {' '.join(context_terms[:5])}"  # Limit to 5 context terms
                logger.debug(f"Added {len(context_terms[:5])} context terms to query")

        return expanded

