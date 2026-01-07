"""
Chain Detection Module

Detects 3-device and 4-device chains from pairwise synergies.

Epic AI-4: N-Level Synergy Detection
Extracted from synergy_detector.py for better maintainability.
"""

import logging
import uuid
from typing import Any, Optional, Protocol

logger = logging.getLogger(__name__)


# Configuration constants
TOP_PAIRS_FOR_CHAINS = 1000  # Use top N pairs by quality for chain detection
MAX_3_DEVICE_CHAINS = 200  # Maximum 3-device chains to detect
MAX_4_DEVICE_CHAINS = 100  # Maximum 4-device chains to detect


class SynergyCacheProtocol(Protocol):
    """Protocol for synergy cache interface."""
    
    async def get_chain_result(self, chain_key: str) -> Optional[dict[str, Any]]:
        """Get cached chain result."""
        ...
    
    async def set_chain_result(self, chain_key: str, chain: dict[str, Any]) -> None:
        """Set cached chain result."""
        ...


class ChainDetector:
    """
    Detects device chains (3-device and 4-device) from pairwise synergies.
    
    A chain represents a sequence of device interactions:
    - 3-device chain: A → B → C (e.g., motion → light → fan)
    - 4-device chain: A → B → C → D (e.g., motion → light → fan → climate)
    
    Attributes:
        synergy_cache: Optional cache for storing chain results
    """
    
    def __init__(self, synergy_cache: Optional[SynergyCacheProtocol] = None):
        """
        Initialize chain detector.
        
        Args:
            synergy_cache: Optional cache for chain results
        """
        self.synergy_cache = synergy_cache
    
    def build_action_lookup(
        self,
        pairwise_synergies: list[dict[str, Any]]
    ) -> dict[str, list[dict[str, Any]]]:
        """
        Build lookup dictionary: action_entity -> list of synergies where it's the action.
        
        This enables O(1) lookup when finding chains.
        
        Args:
            pairwise_synergies: List of 2-device synergy opportunities
        
        Returns:
            Dictionary mapping action entities to lists of synergies
        """
        action_lookup: dict[str, list[dict[str, Any]]] = {}
        for synergy in pairwise_synergies:
            action_entity = synergy.get('action_entity')
            if action_entity:
                if action_entity not in action_lookup:
                    action_lookup[action_entity] = []
                action_lookup[action_entity].append(synergy)
        return action_lookup
    
    def _calculate_quality_score(self, synergy: dict[str, Any]) -> float:
        """
        Calculate quality score for a synergy.
        
        Uses weighted combination of confidence (60%) and impact (40%).
        
        Args:
            synergy: Synergy dictionary
            
        Returns:
            Quality score (0.0-1.0)
        """
        confidence = synergy.get('confidence', 0)
        impact = synergy.get('impact_score', 0)
        return confidence * 0.6 + impact * 0.4
    
    def _get_top_pairs_by_quality(
        self,
        pairwise_synergies: list[dict[str, Any]],
        limit: int = TOP_PAIRS_FOR_CHAINS
    ) -> list[dict[str, Any]]:
        """
        Get top pairs sorted by quality score.
        
        Args:
            pairwise_synergies: All pairwise synergies
            limit: Maximum number of pairs to return
            
        Returns:
            List of top pairs by quality
        """
        if len(pairwise_synergies) <= limit:
            return pairwise_synergies
        
        sorted_pairs = sorted(
            pairwise_synergies,
            key=self._calculate_quality_score,
            reverse=True
        )
        return sorted_pairs[:limit]
    
    def _should_skip_3_chain(
        self,
        trigger_entity: str,
        next_action: str,
        synergy: dict[str, Any],
        next_synergy: dict[str, Any],
        is_valid_cross_area_fn: Optional[callable] = None
    ) -> bool:
        """
        Check if a 3-device chain should be skipped.
        
        Args:
            trigger_entity: First entity in chain
            next_action: Third entity in chain
            synergy: First synergy in chain
            next_synergy: Second synergy in chain
            is_valid_cross_area_fn: Optional function to validate cross-area chains
        
        Returns:
            True if chain should be skipped, False otherwise
        """
        # Skip if same device (A→B→A is not useful)
        if next_action == trigger_entity:
            return True
        
        # Skip if devices not in same area (unless validated)
        if synergy.get('area') != next_synergy.get('area'):
            if is_valid_cross_area_fn:
                action_entity = synergy.get('action_entity')
                if not is_valid_cross_area_fn(trigger_entity, action_entity, next_action):
                    return True
        
        return False
    
    def _create_3_device_chain(
        self,
        trigger_entity: str,
        action_entity: str,
        next_action: str,
        synergy: dict[str, Any],
        next_synergy: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Create a 3-device chain synergy dictionary.
        
        Args:
            trigger_entity: First entity in chain
            action_entity: Second entity in chain
            next_action: Third entity in chain
            synergy: First synergy in chain
            next_synergy: Second synergy in chain
        
        Returns:
            3-device chain synergy dictionary
        """
        return {
            'synergy_id': str(uuid.uuid4()),
            'synergy_type': 'device_chain',
            'devices': [trigger_entity, action_entity, next_action],
            'chain_path': f"{trigger_entity} → {action_entity} → {next_action}",
            'trigger_entity': trigger_entity,
            'action_entity': next_action,
            'impact_score': round(
                (synergy.get('impact_score', 0) + next_synergy.get('impact_score', 0)) / 2, 
                2
            ),
            'confidence': min(
                synergy.get('confidence', 0.7),
                next_synergy.get('confidence', 0.7)
            ),
            'complexity': 'medium',
            'area': synergy.get('area'),
            'rationale': f"Chain: {synergy.get('rationale', '')} then {next_synergy.get('rationale', '')}",
            'synergy_depth': 3,
            'chain_devices': [trigger_entity, action_entity, next_action]
        }
    
    async def _try_get_cached_chain(self, chain_key: str) -> Optional[dict[str, Any]]:
        """
        Try to get cached chain result.
        
        Args:
            chain_key: Cache key for the chain
        
        Returns:
            Cached chain dictionary if found, None otherwise
        """
        if not self.synergy_cache:
            return None
        
        try:
            return await self.synergy_cache.get_chain_result(chain_key)
        except Exception:
            return None
    
    async def _cache_chain(self, chain_key: str, chain: dict[str, Any]) -> None:
        """
        Cache a chain result.
        
        Args:
            chain_key: Cache key
            chain: Chain dictionary to cache
        """
        if not self.synergy_cache:
            return
        
        try:
            await self.synergy_cache.set_chain_result(chain_key, chain)
        except Exception as e:
            logger.debug(f"Cache set failed for chain {chain_key}: {e}")
    
    async def detect_3_device_chains(
        self,
        pairwise_synergies: list[dict[str, Any]],
        is_valid_cross_area_fn: Optional[callable] = None
    ) -> list[dict[str, Any]]:
        """
        Detect 3-device chains by connecting pairs.
        
        For each pair A→B, find pairs B→C to create chains A→B→C.
        
        Args:
            pairwise_synergies: List of 2-device synergy opportunities
            is_valid_cross_area_fn: Optional function to validate cross-area chains
        
        Returns:
            List of 3-device chain synergies
        """
        # Use top pairs by quality score
        pairs_to_use = self._get_top_pairs_by_quality(pairwise_synergies)
        
        if len(pairwise_synergies) > TOP_PAIRS_FOR_CHAINS:
            avg_quality = sum(self._calculate_quality_score(p) for p in pairs_to_use) / len(pairs_to_use)
            logger.info(
                f"   → Using top {TOP_PAIRS_FOR_CHAINS} pairs by quality for 3-chain detection "
                f"(from {len(pairwise_synergies)} total, avg quality: {avg_quality:.3f})"
            )
        
        chains: list[dict[str, Any]] = []
        action_lookup = self.build_action_lookup(pairs_to_use)
        
        processed_count = 0
        for synergy in pairs_to_use:
            if len(chains) >= MAX_3_DEVICE_CHAINS:
                logger.info(f"   → Reached chain limit ({MAX_3_DEVICE_CHAINS}), stopping detection")
                break
            
            trigger_entity = synergy.get('trigger_entity')
            action_entity = synergy.get('action_entity')
            
            # Find pairs where action_entity is the trigger (B→C)
            if action_entity not in action_lookup:
                processed_count += 1
                continue
            
            for next_synergy in action_lookup[action_entity]:
                if len(chains) >= MAX_3_DEVICE_CHAINS:
                    break
                
                next_action = next_synergy.get('action_entity')
                
                # Skip invalid chains
                if self._should_skip_3_chain(
                    trigger_entity, next_action, synergy, next_synergy, is_valid_cross_area_fn
                ):
                    continue
                
                # Check cache
                chain_key = f"chain:{trigger_entity}:{action_entity}:{next_action}"
                cached = await self._try_get_cached_chain(chain_key)
                if cached:
                    chains.append(cached)
                    continue
                
                # Create chain
                chain = self._create_3_device_chain(
                    trigger_entity, action_entity, next_action, synergy, next_synergy
                )
                
                # Cache result
                await self._cache_chain(chain_key, chain)
                chains.append(chain)
            
            processed_count += 1
            if processed_count % 100 == 0:
                logger.debug(
                    f"   → Processed {processed_count}/{len(pairs_to_use)} pairs, "
                    f"found {len(chains)} chains"
                )
        
        return chains
    
    def _should_skip_4_chain(
        self,
        d: str,
        a: str,
        chain_devices: list[str],
        three_chain: dict[str, Any],
        next_synergy: dict[str, Any],
        is_valid_cross_area_fn: Optional[callable] = None
    ) -> bool:
        """
        Check if a 4-device chain should be skipped.
        
        Args:
            d: Fourth entity in chain
            a: First entity in chain
            chain_devices: List of devices in 3-chain
            three_chain: 3-device chain dictionary
            next_synergy: Next synergy to extend chain
            is_valid_cross_area_fn: Optional function to validate cross-area chains
        
        Returns:
            True if chain should be skipped, False otherwise
        """
        # Skip if D already in chain (prevent circular paths)
        if d in chain_devices:
            return True
        
        # Skip if same device (A→B→C→A is not useful)
        if d == a:
            return True
        
        # Skip if devices not in same area (unless validated)
        if three_chain.get('area') != next_synergy.get('area'):
            if is_valid_cross_area_fn:
                b, c = chain_devices[1], chain_devices[2]
                if not is_valid_cross_area_fn(a, b, c):
                    return True
                if not is_valid_cross_area_fn(b, c, d):
                    return True
        
        return False
    
    def _create_4_device_chain(
        self,
        a: str,
        b: str,
        c: str,
        d: str,
        three_chain: dict[str, Any],
        next_synergy: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Create a 4-device chain synergy dictionary.
        
        Args:
            a: First entity in chain
            b: Second entity in chain
            c: Third entity in chain
            d: Fourth entity in chain
            three_chain: 3-device chain dictionary
            next_synergy: Next synergy to extend chain
        
        Returns:
            4-device chain synergy dictionary
        """
        return {
            'synergy_id': str(uuid.uuid4()),
            'synergy_type': 'device_chain',
            'devices': [a, b, c, d],
            'chain_path': f"{a} → {b} → {c} → {d}",
            'trigger_entity': a,
            'action_entity': d,
            'impact_score': round(
                (three_chain.get('impact_score', 0) + next_synergy.get('impact_score', 0)) / 2,
                2
            ),
            'confidence': min(
                three_chain.get('confidence', 0.7),
                next_synergy.get('confidence', 0.7)
            ),
            'complexity': 'medium',
            'area': three_chain.get('area'),
            'rationale': (
                f"4-device chain: {three_chain.get('rationale', '')} "
                f"then {next_synergy.get('rationale', '')}"
            ),
            'synergy_depth': 4,
            'chain_devices': [a, b, c, d]
        }
    
    async def detect_4_device_chains(
        self,
        three_level_chains: list[dict[str, Any]],
        pairwise_synergies: list[dict[str, Any]],
        is_valid_cross_area_fn: Optional[callable] = None
    ) -> list[dict[str, Any]]:
        """
        Detect 4-device chains by extending 3-level chains.
        
        For each 3-chain A→B→C, find pairs C→D to create chains A→B→C→D.
        
        Args:
            three_level_chains: List of 3-device chain synergies
            pairwise_synergies: List of 2-device synergy opportunities
            is_valid_cross_area_fn: Optional function to validate cross-area chains
        
        Returns:
            List of 4-device chain synergies
        """
        if not three_level_chains:
            logger.debug("   → No 3-level chains to extend to 4-level")
            return []
        
        # Use top pairs by quality
        pairs_to_use = self._get_top_pairs_by_quality(pairwise_synergies)
        
        if len(pairwise_synergies) > TOP_PAIRS_FOR_CHAINS:
            logger.info(
                f"   → Using top {TOP_PAIRS_FOR_CHAINS} pairs for 4-chain detection "
                f"(from {len(pairwise_synergies)} total)"
            )
        
        chains: list[dict[str, Any]] = []
        action_lookup = self.build_action_lookup(pairs_to_use)
        
        processed_count = 0
        for three_chain in three_level_chains:
            if len(chains) >= MAX_4_DEVICE_CHAINS:
                logger.info(f"   → Reached 4-level chain limit ({MAX_4_DEVICE_CHAINS}), stopping detection")
                break
            
            chain_devices = three_chain.get('devices', [])
            if len(chain_devices) != 3:
                processed_count += 1
                continue
            
            a, b, c = chain_devices
            
            # Find pairs where C is the trigger (C→D)
            if c not in action_lookup:
                processed_count += 1
                continue
            
            for next_synergy in action_lookup[c]:
                if len(chains) >= MAX_4_DEVICE_CHAINS:
                    break
                
                d = next_synergy.get('action_entity')
                
                # Skip invalid chains
                if self._should_skip_4_chain(
                    d, a, chain_devices, three_chain, next_synergy, is_valid_cross_area_fn
                ):
                    continue
                
                # Check cache
                chain_key = f"chain4:{a}:{b}:{c}:{d}"
                cached = await self._try_get_cached_chain(chain_key)
                if cached:
                    chains.append(cached)
                    continue
                
                # Create 4-chain
                chain = self._create_4_device_chain(a, b, c, d, three_chain, next_synergy)
                
                # Cache result
                await self._cache_chain(chain_key, chain)
                chains.append(chain)
            
            processed_count += 1
            if processed_count % 50 == 0:
                logger.debug(
                    f"   → Processed {processed_count}/{len(three_level_chains)} 3-chains, "
                    f"found {len(chains)} 4-chains"
                )
        
        return chains
