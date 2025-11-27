"""
GitHub API Client for Blueprint Repositories

Implements async HTTP client for GitHub API to crawl blueprint repositories with:
- Retry logic (3 attempts, exponential backoff)
- Timeout configuration
- Rate limiting (GitHub API limits)
- Connection pooling
"""
import asyncio
import base64
import logging
import re
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import httpx

from ..config import settings

logger = logging.getLogger(__name__)


class GitHubClient:
    """Async client for GitHub API with retry and rate limiting"""

    def __init__(
        self,
        token: str | None = None,
        rate_limit_per_sec: float = None,
        retries: int = None
    ):
        self.token = token or settings.github_token
        self.rate_limit = rate_limit_per_sec or 5.0  # GitHub allows 5000/hour, ~83/min, ~1.4/sec
        self.retries = retries or settings.http_retries
        self.base_url = "https://api.github.com"

        # Rate limiting state
        self._last_request_time = 0.0
        self._rate_limit_delay = 1.0 / self.rate_limit

        # Configure httpx transport with retry
        self._transport = httpx.AsyncHTTPTransport(retries=self.retries)

        # Configure timeout
        self._timeout = httpx.Timeout(
            connect=settings.http_timeout_connect,
            read=settings.http_timeout_read,
            write=settings.http_timeout_write,
            pool=settings.http_timeout_pool
        )

        # Configure connection limits
        self._limits = httpx.Limits(
            max_keepalive_connections=settings.http_max_keepalive,
            max_connections=settings.http_max_connections
        )

        # Client will be created in async context
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self):
        """Async context manager entry"""
        headers = {"User-Agent": "homeiq-miner/1.0"}
        if self.token:
            headers["Authorization"] = f"token {self.token}"

        self._client = httpx.AsyncClient(
            transport=self._transport,
            timeout=self._timeout,
            limits=self._limits,
            headers=headers
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self._client:
            await self._client.aclose()

    async def _rate_limit(self):
        """Enforce rate limiting"""
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
        correlation_id: str | None = None
    ) -> dict[str, Any] | list[Any]:
        """Make HTTP request with rate limiting and error handling"""
        if not self._client:
            raise RuntimeError("Client not initialized. Use 'async with' context manager.")

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
            logger.error(f"[{correlation_id}] Timeout: {url} - {e}")
            raise

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"[{correlation_id}] Not found: {url}")
                return {}
            elif e.response.status_code == 403:
                logger.warning(f"[{correlation_id}] Rate limited: {url}")
                # Wait a bit before retrying
                await asyncio.sleep(60)
                raise
            logger.error(f"[{correlation_id}] HTTP {e.response.status_code}: {url}")
            raise

        except Exception as e:
            logger.error(f"[{correlation_id}] Unexpected error: {url} - {e}")
            raise

    async def get_repository(
        self,
        owner: str,
        repo: str,
        correlation_id: str | None = None
    ) -> dict[str, Any]:
        """
        Get repository metadata
        
        Args:
            owner: Repository owner (username/organization)
            repo: Repository name
            correlation_id: Optional correlation ID for logging
        
        Returns:
            Repository metadata dictionary
        """
        correlation_id = correlation_id or str(uuid4())
        
        logger.debug(f"[{correlation_id}] Fetching repository: {owner}/{repo}")
        
        data = await self._request(
            "GET",
            f"/repos/{owner}/{repo}",
            correlation_id=correlation_id
        )
        
        return data

    async def get_repository_contents(
        self,
        owner: str,
        repo: str,
        path: str = "",
        correlation_id: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Get repository contents (files and directories)
        
        Args:
            owner: Repository owner
            repo: Repository name
            path: Path in repository (empty for root)
            correlation_id: Optional correlation ID
        
        Returns:
            List of file/directory metadata
        """
        correlation_id = correlation_id or str(uuid4())
        
        logger.debug(f"[{correlation_id}] Fetching contents: {owner}/{repo}/{path}")
        
        data = await self._request(
            "GET",
            f"/repos/{owner}/{repo}/contents/{path}",
            correlation_id=correlation_id
        )
        
        if isinstance(data, dict):
            # Single file returned
            return [data]
        elif isinstance(data, list):
            # Directory listing returned
            return data
        else:
            return []

    async def get_file_content(
        self,
        owner: str,
        repo: str,
        path: str,
        correlation_id: str | None = None
    ) -> str:
        """
        Get raw file content from repository
        
        Args:
            owner: Repository owner
            repo: Repository name
            path: File path in repository
            correlation_id: Optional correlation ID
        
        Returns:
            File content as string
        """
        correlation_id = correlation_id or str(uuid4())
        
        logger.debug(f"[{correlation_id}] Fetching file: {owner}/{repo}/{path}")
        
        data = await self._request(
            "GET",
            f"/repos/{owner}/{repo}/contents/{path}",
            correlation_id=correlation_id
        )
        
        if isinstance(data, dict) and data.get("encoding") == "base64":
            content = base64.b64decode(data.get("content", "")).decode("utf-8")
            return content
        else:
            logger.warning(f"[{correlation_id}] Unexpected file format: {path}")
            return ""

    async def find_blueprint_files(
        self,
        owner: str,
        repo: str,
        path: str = "",
        correlation_id: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Recursively find blueprint YAML files in repository
        
        Args:
            owner: Repository owner
            repo: Repository name
            path: Starting path (empty for root)
            correlation_id: Optional correlation ID
        
        Returns:
            List of blueprint file metadata
        """
        correlation_id = correlation_id or str(uuid4())
        blueprint_files = []
        
        try:
            contents = await self.get_repository_contents(owner, repo, path, correlation_id)
            
            for item in contents:
                if item.get("type") == "file":
                    # Check if it's a YAML file
                    name = item.get("name", "")
                    if name.endswith((".yaml", ".yml")):
                        # Read file to check if it contains blueprint:
                        try:
                            file_content = await self.get_file_content(
                                owner, repo, item.get("path", ""), correlation_id
                            )
                            # Check if it's a blueprint (contains "blueprint:" key)
                            if "blueprint:" in file_content.lower():
                                blueprint_files.append({
                                    "path": item.get("path", ""),
                                    "name": name,
                                    "size": item.get("size", 0),
                                    "content": file_content
                                })
                                logger.debug(f"[{correlation_id}] Found blueprint: {item.get('path')}")
                        except Exception as e:
                            logger.warning(f"[{correlation_id}] Error reading file {item.get('path')}: {e}")
                            continue
                
                elif item.get("type") == "dir":
                    # Skip common non-blueprint directories
                    dir_name = item.get("name", "").lower()
                    if dir_name in [".git", "node_modules", "__pycache__", ".github"]:
                        continue
                    
                    # Recursively search subdirectories
                    try:
                        sub_files = await self.find_blueprint_files(
                            owner, repo, item.get("path", ""), correlation_id
                        )
                        blueprint_files.extend(sub_files)
                    except Exception as e:
                        logger.warning(f"[{correlation_id}] Error searching directory {item.get('path')}: {e}")
                        continue
            
        except Exception as e:
            logger.error(f"[{correlation_id}] Error finding blueprints in {owner}/{repo}/{path}: {e}")
        
        return blueprint_files

    async def crawl_repository(
        self,
        owner: str,
        repo: str,
        correlation_id: str | None = None
    ) -> list[dict[str, Any]]:
        """
        Crawl a GitHub repository and extract blueprint data
        
        Args:
            owner: Repository owner
            repo: Repository name
            correlation_id: Optional correlation ID
        
        Returns:
            List of blueprint post data (compatible with Discourse format)
        """
        correlation_id = correlation_id or str(uuid4())
        
        logger.info(f"[{correlation_id}] Crawling repository: {owner}/{repo}")
        
        # Get repository metadata
        repo_data = await self.get_repository(owner, repo, correlation_id)
        if not repo_data:
            logger.warning(f"[{correlation_id}] Repository not found: {owner}/{repo}")
            return []
        
        # Find blueprint files
        blueprint_files = await self.find_blueprint_files(owner, repo, "", correlation_id)
        
        logger.info(f"[{correlation_id}] Found {len(blueprint_files)} blueprints in {owner}/{repo}")
        
        # Convert to post-like format for parser compatibility
        results = []
        for blueprint_file in blueprint_files:
            # Extract title from filename or first line of blueprint
            title = blueprint_file["name"].replace(".yaml", "").replace(".yml", "").replace("_", " ").replace("-", " ")
            
            # Try to extract description from blueprint metadata
            content = blueprint_file["content"]
            description = ""
            if "description:" in content.lower():
                # Try to extract description from blueprint metadata
                desc_match = re.search(r'description:\s*["\']([^"\']+)["\']', content, re.IGNORECASE)
                if desc_match:
                    description = desc_match.group(1)
            
            # Get repository stars for quality score
            stars = repo_data.get("stargazers_count", 0)
            
            # Create post-like structure
            result = {
                "id": f"{owner}/{repo}:{blueprint_file['path']}",  # Unique ID
                "title": title.title(),
                "description": description or f"Blueprint from {owner}/{repo}",
                "yaml_blocks": [blueprint_file["content"]],
                "author": owner,
                "created_at": repo_data.get("created_at", datetime.now(timezone.utc).isoformat()),
                "updated_at": repo_data.get("updated_at", repo_data.get("pushed_at", datetime.now(timezone.utc).isoformat())),
                "likes": stars,  # Use stars as likes for quality scoring
                "tags": repo_data.get("topics", []),
                "category_id": None,
                "views": 0,
                "source_url": repo_data.get("html_url", ""),
                "file_path": blueprint_file["path"]
            }
            
            results.append(result)
        
        return results





