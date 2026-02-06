"""
Deduplication Logic

Uses rapidfuzz for fuzzy string matching to detect duplicate automations.
"""
import hashlib
import logging

from rapidfuzz import fuzz

from ..config import settings
from .models import AutomationMetadata

logger = logging.getLogger(__name__)


class Deduplicator:
    """Detect and handle duplicate automations"""

    def __init__(self, similarity_threshold: float = None):
        """
        Initialize deduplicator
        
        Args:
            similarity_threshold: Minimum similarity score (0.0-1.0) to consider duplicates
                                 Default from settings (0.85 = 85% similar)
        """
        self.threshold = similarity_threshold or settings.dedup_similarity_threshold

    def calculate_similarity_hash(self, metadata: AutomationMetadata) -> str:
        """
        Calculate hash for quick duplicate detection

        Based on normalized title + devices

        Args:
            metadata: AutomationMetadata instance

        Returns:
            SHA256 hash string
        """
        # Normalize title (lowercase, no spaces)
        normalized_title = metadata.title.lower().replace(' ', '').replace('-', '')

        # Sort devices for consistent hashing
        sorted_devices = sorted(metadata.devices)

        # Create hash input
        hash_input = f"{normalized_title}|{','.join(sorted_devices)}"

        return hashlib.sha256(hash_input.encode()).hexdigest()

    def calculate_title_similarity(self, title1: str, title2: str) -> float:
        """
        Calculate similarity between two titles using fuzzy matching
        
        Args:
            title1: First title
            title2: Second title
        
        Returns:
            Similarity score (0.0-1.0)
        """
        # Use token sort ratio for better matching with word order variations
        score = fuzz.token_sort_ratio(title1.lower(), title2.lower())

        # Convert to 0.0-1.0 scale
        return score / 100.0

    def is_duplicate(
        self,
        metadata: AutomationMetadata,
        existing: AutomationMetadata
    ) -> bool:
        """
        Check if two automations are duplicates
        
        Args:
            metadata: New automation to check
            existing: Existing automation in corpus
        
        Returns:
            True if duplicate, False otherwise
        """
        # Quick check: same source_id = definitely duplicate
        if metadata.source == existing.source and metadata.source_id == existing.source_id:
            return True

        # Calculate title similarity
        title_similarity = self.calculate_title_similarity(
            metadata.title,
            existing.title
        )

        # If titles are very similar (>= threshold), check devices
        if title_similarity >= self.threshold:
            # Check device overlap
            devices1 = set(metadata.devices)
            devices2 = set(existing.devices)

            if not devices1 and not devices2:
                # Both have no devices, use title only
                return True

            if devices1 and devices2:
                # Calculate Jaccard similarity for devices
                intersection = len(devices1 & devices2)
                union = len(devices1 | devices2)
                device_similarity = intersection / union if union > 0 else 0.0

                # Consider duplicate if device similarity > 0.7
                if device_similarity >= 0.7:
                    logger.debug(
                        f"Duplicate detected: '{metadata.title}' vs '{existing.title}' "
                        f"(title: {title_similarity:.2f}, devices: {device_similarity:.2f})"
                    )
                    return True

        return False

    def find_duplicates(
        self,
        metadata: AutomationMetadata,
        existing_automations: list[AutomationMetadata]
    ) -> list[AutomationMetadata]:
        """
        Find all duplicates of an automation in existing corpus
        
        Args:
            metadata: Automation to check
            existing_automations: List of existing automations
        
        Returns:
            List of duplicate automations
        """
        duplicates = []

        for existing in existing_automations:
            if self.is_duplicate(metadata, existing):
                duplicates.append(existing)

        return duplicates

    def select_best(
        self,
        automations: list[AutomationMetadata]
    ) -> AutomationMetadata:
        """
        Select the best automation from a list of duplicates
        
        Criteria: highest quality_score
        
        Args:
            automations: List of duplicate automations
        
        Returns:
            Best automation
        """
        if not automations:
            raise ValueError("No automations to select from")

        # Sort by quality_score descending
        sorted_autos = sorted(automations, key=lambda a: a.quality_score, reverse=True)

        best = sorted_autos[0]

        logger.debug(
            f"Selected best from {len(automations)} duplicates: "
            f"'{best.title}' (quality: {best.quality_score})"
        )

        return best

    def deduplicate_batch(
        self,
        new_automations: list[AutomationMetadata],
        existing_automations: list[AutomationMetadata]
    ) -> list[AutomationMetadata]:
        """
        Deduplicate a batch of new automations against existing corpus
        
        Args:
            new_automations: List of new automations to add
            existing_automations: Existing corpus
        
        Returns:
            Deduplicated list of automations to add
        """
        to_add = []
        to_skip = []

        for new_auto in new_automations:
            # Find duplicates in existing corpus
            duplicates = self.find_duplicates(new_auto, existing_automations)

            if duplicates:
                # Compare quality scores
                all_candidates = duplicates + [new_auto]
                best = self.select_best(all_candidates)

                if best.source_id == new_auto.source_id:
                    # New automation is best quality, add it
                    to_add.append(new_auto)
                    logger.info(
                        f"Adding '{new_auto.title}' - better quality than existing "
                        f"({new_auto.quality_score} vs {duplicates[0].quality_score})"
                    )
                else:
                    # Existing is better, skip new
                    to_skip.append(new_auto)
                    logger.debug(
                        f"Skipping '{new_auto.title}' - duplicate of existing "
                        f"with higher quality"
                    )
            else:
                # No duplicates, add it
                to_add.append(new_auto)

        logger.info(
            f"Deduplication complete: {len(to_add)} to add, {len(to_skip)} to skip"
        )

        return to_add

