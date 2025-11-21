"""
Discourse API Client

Implements async HTTP client for community.home-assistant.io with:
- Retry logic (3 attempts, exponential backoff) - Context7 validated
- Timeout configuration - Context7 validated
- Rate limiting (2 requests/second)
- Connection pooling - Context7 validated
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import httpx
from bs4 import BeautifulSoup

from src.config import settings

logger = logging.getLogger(__name__)


class DiscourseClient:
    """Async client for Discourse API with retry and rate limiting"""

    def __init__(
        self,
        base_url: str | None = None,
        rate_limit_per_sec: float | None = None,
        retries: int | None = None,
    ):
        self.base_url = base_url or settings.discourse_base_url
        self.rate_limit = rate_limit_per_sec or settings.discourse_rate_limit_per_sec
        self.retries = retries or settings.http_retries

        # Rate limiting state
        self._last_request_time = 0.0
        self._rate_limit_delay = 1.0 / self.rate_limit

        # Configure httpx transport with retry (Context7 pattern)
        self._transport = httpx.AsyncHTTPTransport(retries=self.retries)

        # Configure timeout (Context7 pattern)
        self._timeout = httpx.Timeout(
            connect=settings.http_timeout_connect,
            read=settings.http_timeout_read,
            write=settings.http_timeout_write,
            pool=settings.http_timeout_pool,
        )

        # Configure connection limits (Context7 pattern)
        self._limits = httpx.Limits(
            max_keepalive_connections=settings.http_max_keepalive,
            max_connections=settings.http_max_connections,
        )

        # Client will be created in async context
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self):
        """Async context manager entry"""
        self._client = httpx.AsyncClient(
            transport=self._transport,
            timeout=self._timeout,
            limits=self._limits,
            headers={"User-Agent": "homeiq-miner/1.0"},
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self._client:
            await self._client.aclose()

    async def _rate_limit(self):
        """Enforce rate limiting (2 requests/second)"""
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
        params: dict[str, Any] | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """Make HTTP request with rate limiting and error handling"""
        if not self._client:
            msg = "Client not initialized. Use 'async with' context manager."
            raise RuntimeError(msg)

        correlation_id = correlation_id or str(uuid4())
        url = f"{self.base_url}{endpoint}"

        # Enforce rate limiting
        await self._rate_limit()

        try:
            logger.debug(f"[{correlation_id}] {method} {url} params={params}")

            response = await self._client.request(method, url, params=params)
            response.raise_for_status()

            data = response.json()
            logger.debug(f"[{correlation_id}] Response received: {len(str(data))} chars")

            return data

        except httpx.TimeoutException as e:
            logger.exception(f"[{correlation_id}] Timeout: {url} - {e}")
            raise

        except httpx.HTTPStatusError as e:
            logger.exception(f"[{correlation_id}] HTTP {e.response.status_code}: {url}")
            raise

        except Exception as e:
            logger.exception(f"[{correlation_id}] Unexpected error: {url} - {e}")
            raise

    async def fetch_blueprints(
        self,
        min_likes: int | None = None,
        since: datetime | None = None,
        limit: int | None = None,
        page: int = 0,
    ) -> list[dict[str, Any]]:
        """
        Fetch blueprint posts from Discourse Blueprints Exchange

        Args:
            min_likes: Minimum likes threshold (default from settings)
            since: Only fetch posts updated since this date
            limit: Maximum posts to fetch
            page: Page number for pagination

        Returns:
            List of post metadata dictionaries
        """
        min_likes = min_likes or settings.discourse_min_likes
        limit = limit or settings.crawler_max_posts
        correlation_id = str(uuid4())

        logger.info(f"[{correlation_id}] Fetching blueprints: min_likes={min_likes}, page={page}")

        # Query category 53 (Blueprints Exchange)
        params = {
            "page": page,
        }

        data = await self._request(
            "GET",
            f"/c/blueprints-exchange/{settings.discourse_category_id}.json",
            params=params,
            correlation_id=correlation_id,
        )

        # Extract topic list
        topic_list = data.get("topic_list", {})
        topics = topic_list.get("topics", [])

        # Filter by likes
        filtered_topics = []
        for topic in topics:
            likes = topic.get("like_count", 0)

            # Filter by likes threshold
            if likes < min_likes:
                continue

            # Filter by date if provided
            if since:
                updated_at = datetime.fromisoformat(
                    topic.get("last_posted_at", "").replace("Z", "+00:00"),
                )
                # Ensure both datetimes are timezone-aware for comparison
                since_aware = since
                if since_aware.tzinfo is None:
                    # If since is naive, assume UTC (create new datetime to avoid modifying parameter)
                    since_aware = since_aware.replace(tzinfo=timezone.utc)
                if updated_at.tzinfo is None:
                    # If updated_at is naive, assume UTC
                    updated_at = updated_at.replace(tzinfo=timezone.utc)
                if updated_at < since_aware:
                    continue

            filtered_topics.append({
                "id": topic.get("id"),
                "title": topic.get("title"),
                "slug": topic.get("slug"),
                "likes": likes,
                "posts_count": topic.get("posts_count", 0),
                "views": topic.get("views", 0),
                "created_at": topic.get("created_at"),
                "last_posted_at": topic.get("last_posted_at"),
                "category_id": topic.get("category_id"),
                "tags": topic.get("tags", []),
            })

        logger.info(
            f"[{correlation_id}] Found {len(filtered_topics)} blueprints "
            f"(filtered from {len(topics)} total)",
        )

        return filtered_topics[:limit]

    async def fetch_post_details(
        self,
        post_id: int,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Fetch full post content including YAML blueprints

        Args:
            post_id: Discourse topic ID
            correlation_id: Optional correlation ID for logging

        Returns:
            Dictionary with post content and metadata
        """
        correlation_id = correlation_id or str(uuid4())

        logger.debug(f"[{correlation_id}] Fetching post details: {post_id}")

        data = await self._request(
            "GET",
            f"/t/{post_id}.json",
            correlation_id=correlation_id,
        )

        # Extract first post (main content)
        posts = data.get("post_stream", {}).get("posts", [])
        if not posts:
            logger.warning(f"[{correlation_id}] No posts found for topic {post_id}")
            return {}

        first_post = posts[0]
        raw_content = first_post.get("cooked", "")  # HTML content

        # Parse HTML to extract text and code blocks
        soup = BeautifulSoup(raw_content, "lxml")

        # Extract YAML code blocks
        yaml_blocks = []
        for code_block in soup.find_all("code", class_="lang-yaml"):
            yaml_blocks.append(code_block.get_text())

        # Also check for pre tags with yaml
        for pre_block in soup.find_all("pre"):
            code = pre_block.find("code")
            if code and "yaml" in code.get("class", []):
                yaml_blocks.append(code.get_text())

        # Extract plain text description
        # Remove code blocks first
        for code in soup.find_all(["code", "pre"]):
            code.decompose()

        description = soup.get_text().strip()

        result = {
            "id": post_id,
            "title": data.get("title", ""),
            "description": description[:1000],  # Limit description length
            "yaml_blocks": yaml_blocks,
            "author": first_post.get("username", ""),
            "created_at": first_post.get("created_at", ""),
            "updated_at": first_post.get("updated_at", ""),
            "likes": first_post.get("like_count", 0),
            "tags": data.get("tags", []),
            "category_id": data.get("category_id"),
            "views": data.get("views", 0),
        }

        logger.debug(
            f"[{correlation_id}] Post {post_id}: "
            f"{len(yaml_blocks)} YAML blocks, "
            f"{len(description)} chars description",
        )

        return result

    async def fetch_post_metadata(
        self,
        post_id: int,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Fetch only post metadata (for quality score updates)

        Args:
            post_id: Discourse topic ID
            correlation_id: Optional correlation ID

        Returns:
            Dictionary with updated metadata (likes, views, etc.)
        """
        correlation_id = correlation_id or str(uuid4())

        data = await self._request(
            "GET",
            f"/t/{post_id}.json",
            correlation_id=correlation_id,
        )

        posts = data.get("post_stream", {}).get("posts", [])
        if not posts:
            return {}

        first_post = posts[0]

        return {
            "id": post_id,
            "likes": first_post.get("like_count", 0),
            "views": data.get("views", 0),
            "updated_at": first_post.get("updated_at", ""),
        }

