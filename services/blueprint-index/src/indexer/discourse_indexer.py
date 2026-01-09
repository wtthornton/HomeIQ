"""Discourse indexer for discovering blueprints from Home Assistant Community forums."""

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from ..config import settings
from ..models import IndexedBlueprint
from .blueprint_parser import BlueprintParser

logger = logging.getLogger(__name__)


# Blueprint exchange category on Home Assistant Community
BLUEPRINT_EXCHANGE_CATEGORY = "blueprints-exchange"
BLUEPRINT_EXCHANGE_CATEGORY_ID = 53


class DiscourseBlueprintIndexer:
    """
    Indexes blueprints from Home Assistant Community Discourse forums.
    
    Specifically targets the Blueprints Exchange category.
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        rate_limit_per_sec: float = None,
    ):
        """Initialize Discourse indexer."""
        self.base_url = (base_url or settings.discourse_base_url).rstrip("/")
        self.rate_limit = rate_limit_per_sec or settings.discourse_rate_limit_per_sec
        self.parser = BlueprintParser()
        
        # Rate limiting
        self._last_request_time = 0.0
        self._rate_limit_delay = 1.0 / self.rate_limit
        
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        headers = {
            "User-Agent": "homeiq-blueprint-indexer/1.0",
            "Accept": "application/json",
        }
        
        timeout = httpx.Timeout(
            connect=settings.http_timeout_connect,
            read=settings.http_timeout_read,
            write=settings.http_timeout_write,
            pool=settings.http_timeout_pool,
        )
        
        self._client = httpx.AsyncClient(
            headers=headers,
            timeout=timeout,
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()
    
    async def _rate_limit(self):
        """Enforce rate limiting."""
        current_time = asyncio.get_event_loop().time()
        time_since_last = current_time - self._last_request_time
        
        if time_since_last < self._rate_limit_delay:
            sleep_time = self._rate_limit_delay - time_since_last
            await asyncio.sleep(sleep_time)
        
        self._last_request_time = asyncio.get_event_loop().time()
    
    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Make rate-limited HTTP request."""
        if not self._client:
            raise RuntimeError("Client not initialized")
        
        await self._rate_limit()
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = await self._client.request(method, url, params=params)
            
            if response.status_code == 404:
                return {}
            elif response.status_code == 429:
                logger.warning(f"Rate limited: {url}")
                await asyncio.sleep(60)
                return {}
            
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"Discourse request failed: {url} - {e}")
            return {}
    
    async def index_all(self, progress_callback=None) -> list[IndexedBlueprint]:
        """
        Index all blueprints from Discourse.
        
        Args:
            progress_callback: Optional callback(processed, total) for progress updates
            
        Returns:
            List of indexed blueprints
        """
        all_blueprints = []
        
        logger.info("Fetching topics from Blueprint Exchange category...")
        
        # Get all topics from the blueprint exchange category
        topics = await self._get_category_topics(BLUEPRINT_EXCHANGE_CATEGORY_ID)
        
        logger.info(f"Found {len(topics)} topics to process")
        
        for i, topic in enumerate(topics):
            try:
                blueprint = await self._process_topic(topic)
                if blueprint:
                    all_blueprints.append(blueprint)
                
                if progress_callback:
                    progress_callback(i + 1, len(topics))
                    
            except Exception as e:
                logger.warning(f"Failed to process topic {topic.get('id')}: {e}")
        
        logger.info(f"Total indexed from Discourse: {len(all_blueprints)} blueprints")
        return all_blueprints
    
    async def _get_category_topics(
        self, 
        category_id: int,
        category_slug: str = BLUEPRINT_EXCHANGE_CATEGORY,
        max_pages: int = 50,
    ) -> list[dict[str, Any]]:
        """Get all topics from a category."""
        topics = []
        page = 0
        
        while page < max_pages:
            # Use the full category path with slug to avoid redirects
            data = await self._request(
                "GET", 
                f"/c/{category_slug}/{category_id}.json",
                params={"page": page}
            )
            
            topic_list = data.get("topic_list", {})
            page_topics = topic_list.get("topics", [])
            
            if not page_topics:
                break
            
            topics.extend(page_topics)
            page += 1
            
            # Check if there are more pages
            if not topic_list.get("more_topics_url"):
                break
        
        return topics
    
    async def _process_topic(self, topic: dict[str, Any]) -> Optional[IndexedBlueprint]:
        """Process a single topic and extract blueprint."""
        topic_id = topic.get("id")
        if not topic_id:
            return None
        
        # Get full topic data
        topic_data = await self._request("GET", f"/t/{topic_id}.json")
        
        if not topic_data:
            return None
        
        # Extract post content
        posts = topic_data.get("post_stream", {}).get("posts", [])
        if not posts:
            return None
        
        first_post = posts[0]
        raw_content = first_post.get("raw", "") or first_post.get("cooked", "")
        
        # Extract YAML blocks from content
        yaml_blocks = self._extract_yaml_blocks(raw_content)
        
        if not yaml_blocks:
            return None
        
        # Try to parse each YAML block as a blueprint
        for yaml_content in yaml_blocks:
            # Check if it's a blueprint
            if "blueprint:" not in yaml_content.lower():
                continue
            
            # Parse timestamps
            created_at = None
            created_at_str = topic.get("created_at")
            if created_at_str:
                try:
                    created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    pass
            
            # Calculate community score from likes/views
            likes = topic.get("like_count", 0)
            views = topic.get("views", 0)
            reply_count = topic.get("posts_count", 1) - 1
            
            # Normalize community rating (likes have high weight)
            community_rating = min(1.0, (likes / 50) + (reply_count / 100) + (views / 10000))
            
            blueprint = self.parser.parse_blueprint(
                yaml_content=yaml_content,
                source_url=f"{self.base_url}/t/{topic.get('slug', '')}/{topic_id}",
                source_type="discourse",
                source_id=str(topic_id),
                stars=likes,
                author=first_post.get("username"),
                created_at=created_at,
            )
            
            if blueprint:
                # Update community metrics
                blueprint.community_rating = community_rating
                blueprint.vote_count = likes
                blueprint.downloads = views  # Use views as proxy for downloads
                
                # Use topic title if blueprint name is generic
                topic_title = topic.get("title", "")
                if blueprint.name == "Unnamed Blueprint" and topic_title:
                    blueprint.name = topic_title
                
                # Extract tags from topic
                topic_tags = topic.get("tags", [])
                if topic_tags:
                    blueprint.tags = list(set((blueprint.tags or []) + topic_tags))
                
                return blueprint
        
        return None
    
    def _extract_yaml_blocks(self, content: str) -> list[str]:
        """Extract YAML code blocks from content."""
        yaml_blocks = []
        
        # Pattern for markdown code blocks
        code_block_pattern = r"```(?:yaml|YAML)?\s*\n(.*?)```"
        
        matches = re.findall(code_block_pattern, content, re.DOTALL | re.IGNORECASE)
        
        for match in matches:
            yaml_content = match.strip()
            if yaml_content:
                yaml_blocks.append(yaml_content)
        
        return yaml_blocks
    
    async def search_blueprints(
        self, 
        query: str, 
        limit: int = 50
    ) -> list[dict[str, Any]]:
        """
        Search for blueprints on Discourse.
        
        Args:
            query: Search query
            limit: Maximum results
            
        Returns:
            List of search results
        """
        results = []
        
        try:
            data = await self._request(
                "GET",
                "/search.json",
                params={
                    "q": f"{query} #blueprints-exchange",
                }
            )
            
            topics = data.get("topics", [])
            
            for topic in topics[:limit]:
                results.append({
                    "id": topic.get("id"),
                    "title": topic.get("title"),
                    "slug": topic.get("slug"),
                    "url": f"{self.base_url}/t/{topic.get('slug')}/{topic.get('id')}",
                    "likes": topic.get("like_count", 0),
                })
            
        except Exception as e:
            logger.warning(f"Search failed: {e}")
        
        return results
