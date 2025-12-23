"""
Area Name Resolver

Epic AI-12, Story AI12.3: Area Name Resolution
Resolves area names from natural language queries to area IDs, supports area hierarchies,
and provides area-aware entity filtering.
"""

import logging
from typing import Any, Optional
from dataclasses import dataclass
from collections import defaultdict

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    SentenceTransformer = None

logger = logging.getLogger(__name__)


@dataclass
class AreaInfo:
    """Represents area information"""
    area_id: str
    name: str
    aliases: list[str]
    parent_area_id: Optional[str] = None
    parent_area_name: Optional[str] = None
    embedding: Optional[list[float]] = None


class AreaResolver:
    """
    Resolves area names from natural language queries to area IDs.
    
    Features:
    - Area name resolution with semantic search
    - Area aliases support
    - Area hierarchies (floors, zones)
    - Area-aware entity filtering
    """
    
    def __init__(
        self,
        embedding_model: Optional[str] = None
    ):
        """
        Initialize area resolver.
        
        Args:
            embedding_model: Sentence transformer model name (default: 'all-MiniLM-L6-v2')
        """
        self.embedding_model_name = embedding_model or "all-MiniLM-L6-v2"
        
        # Area index: area_id -> AreaInfo
        self._area_index: dict[str, AreaInfo] = {}
        
        # Reverse index: area_name -> list[area_id] (for fast lookup)
        self._name_index: dict[str, list[str]] = defaultdict(list)
        
        # Hierarchy index: parent_area_id -> list[child_area_id]
        self._hierarchy_index: dict[str, list[str]] = defaultdict(list)
        
        # Embedding model (lazy load)
        self._embedding_model: Optional[Any] = None
        
        logger.info(f"AreaResolver initialized (model={self.embedding_model_name})")
    
    def _get_embedding_model(self) -> Any:
        """Get or load embedding model (lazy loading)"""
        if self._embedding_model is None:
            if not SENTENCE_TRANSFORMERS_AVAILABLE:
                logger.warning("sentence-transformers not available, embeddings disabled")
                return None
            
            try:
                logger.info(f"Loading embedding model: {self.embedding_model_name}")
                self._embedding_model = SentenceTransformer(self.embedding_model_name)
                logger.info("Embedding model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load embedding model: {e}", exc_info=True)
                return None
        
        return self._embedding_model
    
    def _generate_embedding(self, text: str) -> Optional[list[float]]:
        """Generate semantic embedding for text"""
        model = self._get_embedding_model()
        if model is None:
            return None
        
        try:
            embedding = model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            logger.warning(f"Failed to generate embedding for '{text}': {e}")
            return None
    
    def add_area(
        self,
        area_id: str,
        name: str,
        aliases: Optional[list[str]] = None,
        parent_area_id: Optional[str] = None,
        parent_area_name: Optional[str] = None
    ) -> None:
        """
        Add area to index.
        
        Args:
            area_id: Area ID
            name: Area name
            aliases: Optional list of aliases
            parent_area_id: Optional parent area ID (for hierarchies)
            parent_area_name: Optional parent area name
        """
        aliases = aliases or []
        
        # Generate embedding for area name
        embedding = self._generate_embedding(name)
        
        area_info = AreaInfo(
            area_id=area_id,
            name=name,
            aliases=aliases,
            parent_area_id=parent_area_id,
            parent_area_name=parent_area_name,
            embedding=embedding
        )
        
        # Add to index
        self._area_index[area_id] = area_info
        
        # Add to name index
        self._name_index[name.lower()].append(area_id)
        
        # Add aliases to name index
        for alias in aliases:
            if alias:
                self._name_index[alias.lower()].append(area_id)
        
        # Add to hierarchy index
        if parent_area_id:
            self._hierarchy_index[parent_area_id].append(area_id)
        
        logger.debug(f"Added area to index: {area_id} ({name})")
    
    def resolve_area_name(
        self,
        area_name: str,
        use_semantic: bool = True
    ) -> Optional[str]:
        """
        Resolve area name to area_id.
        
        Args:
            area_name: Area name to resolve
            use_semantic: If True, use semantic search for better matching
        
        Returns:
            Area ID if found, None otherwise
        """
        if not area_name or not area_name.strip():
            return None
        
        area_name_lower = area_name.strip().lower()
        
        # Try exact match first
        if area_name_lower in self._name_index:
            matches = self._name_index[area_name_lower]
            if matches:
                return matches[0]  # Return first match
        
        # Try semantic search if enabled
        if use_semantic:
            semantic_result = self._search_by_semantic(area_name)
            if semantic_result:
                return semantic_result
        
        # Try partial match
        for name, area_ids in self._name_index.items():
            if area_name_lower in name or name in area_name_lower:
                if area_ids:
                    return area_ids[0]
        
        return None
    
    def _search_by_semantic(self, query: str) -> Optional[str]:
        """Search for area using semantic similarity"""
        query_embedding = self._generate_embedding(query.strip())
        if query_embedding is None:
            return None
        
        best_match = None
        best_score = 0.0
        
        for area_id, area_info in self._area_index.items():
            if area_info.embedding is None:
                continue
            
            # Calculate similarity
            similarity = self._cosine_similarity(query_embedding, area_info.embedding)
            
            if similarity > best_score and similarity > 0.7:  # Threshold
                best_score = similarity
                best_match = area_id
        
        return best_match
    
    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            import numpy as np
            vec1_np = np.array(vec1)
            vec2_np = np.array(vec2)
            dot_product = np.dot(vec1_np, vec2_np)
            norm1 = np.linalg.norm(vec1_np)
            norm2 = np.linalg.norm(vec2_np)
            if norm1 == 0 or norm2 == 0:
                return 0.0
            return float(dot_product / (norm1 * norm2))
        except Exception as e:
            logger.warning(f"Failed to calculate cosine similarity: {e}")
            return 0.0
    
    def get_area_info(self, area_id: str) -> Optional[AreaInfo]:
        """Get area information by area_id"""
        return self._area_index.get(area_id)
    
    def get_area_name(self, area_id: str) -> Optional[str]:
        """Get area name by area_id"""
        area_info = self._area_index.get(area_id)
        return area_info.name if area_info else None
    
    def get_child_areas(self, parent_area_id: str) -> list[str]:
        """Get all child area IDs for a parent area"""
        return self._hierarchy_index.get(parent_area_id, []).copy()
    
    def get_all_areas_in_hierarchy(self, area_id: str) -> list[str]:
        """
        Get all areas in hierarchy (area itself + all children recursively).
        
        Args:
            area_id: Root area ID
        
        Returns:
            List of area IDs including the root and all descendants
        """
        result = [area_id]
        
        # Get direct children
        children = self.get_child_areas(area_id)
        result.extend(children)
        
        # Recursively get children of children
        for child_id in children:
            result.extend(self.get_all_areas_in_hierarchy(child_id))
        
        return result
    
    def filter_entities_by_area(
        self,
        entity_ids: list[str],
        area_id: str,
        include_children: bool = False,
        area_map: Optional[dict[str, str]] = None
    ) -> list[str]:
        """
        Filter entity IDs by area.
        
        Args:
            entity_ids: List of entity IDs to filter
            area_id: Area ID to filter by
            include_children: If True, include entities in child areas
            area_map: Optional map of entity_id -> area_id (if not provided, uses index)
        
        Returns:
            Filtered list of entity IDs
        """
        if not entity_ids or not area_id:
            return entity_ids
        
        # Get areas to include
        areas_to_include = [area_id]
        if include_children:
            areas_to_include.extend(self.get_all_areas_in_hierarchy(area_id))
        
        # Filter entities
        filtered = []
        for entity_id in entity_ids:
            entity_area_id = None
            
            if area_map:
                entity_area_id = area_map.get(entity_id)
            else:
                # Try to get from index (would need entity index access)
                # For now, assume area_map is provided
                continue
            
            if entity_area_id in areas_to_include:
                filtered.append(entity_id)
        
        return filtered
    
    def extract_area_from_query(
        self,
        query: str
    ) -> Optional[str]:
        """
        Extract area name from natural language query.
        
        Args:
            query: Natural language query
        
        Returns:
            Area name if found, None otherwise
        """
        if not query:
            return None
        
        query_lower = query.lower()
        
        # Try to match area names in query
        for area_id, area_info in self._area_index.items():
            # Check main name
            if area_info.name.lower() in query_lower:
                return area_info.name
            
            # Check aliases
            for alias in area_info.aliases:
                if alias.lower() in query_lower:
                    return area_info.name
        
        return None
    
    def clear(self) -> None:
        """Clear all areas from index"""
        self._area_index.clear()
        self._name_index.clear()
        self._hierarchy_index.clear()
        logger.info("Area index cleared")
    
    def get_stats(self) -> dict[str, Any]:
        """Get area index statistics"""
        return {
            "total_areas": len(self._area_index),
            "total_aliases": sum(len(area.aliases) for area in self._area_index.values()),
            "total_hierarchies": len(self._hierarchy_index)
        }

