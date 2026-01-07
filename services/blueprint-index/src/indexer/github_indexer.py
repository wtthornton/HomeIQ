"""GitHub indexer for discovering blueprints from repositories."""

import asyncio
import base64
import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

import httpx

from ..config import settings
from ..models import IndexedBlueprint
from .blueprint_parser import BlueprintParser

logger = logging.getLogger(__name__)


# Known blueprint repositories to index
BLUEPRINT_REPOSITORIES = [
    # Official Home Assistant
    ("home-assistant", "core"),
    ("home-assistant", "addons"),
    
    # Popular community repositories
    ("home-assistant", "example-custom-config"),
    
    # Searched via GitHub API for blueprint repositories
]

# GitHub search queries to find more blueprint repositories
BLUEPRINT_SEARCH_QUERIES = [
    "home assistant blueprint",
    "homeassistant blueprint yaml",
    "ha blueprint automation",
]


class GitHubBlueprintIndexer:
    """
    Indexes blueprints from GitHub repositories.
    
    Features:
    - Crawls known blueprint repositories
    - Searches for new repositories via GitHub API
    - Parses blueprint YAML files
    - Extracts metadata and quality scores
    """
    
    def __init__(
        self,
        token: Optional[str] = None,
        rate_limit_per_sec: float = None,
    ):
        """Initialize GitHub indexer."""
        self.token = token or settings.github_token
        self.rate_limit = rate_limit_per_sec or settings.github_rate_limit_per_sec
        self.parser = BlueprintParser()
        self.base_url = "https://api.github.com"
        
        # Rate limiting
        self._last_request_time = 0.0
        self._rate_limit_delay = 1.0 / self.rate_limit
        
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        headers = {
            "User-Agent": "homeiq-blueprint-indexer/1.0",
            "Accept": "application/vnd.github.v3+json",
        }
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        
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
    ) -> dict[str, Any] | list[Any]:
        """Make rate-limited HTTP request."""
        if not self._client:
            raise RuntimeError("Client not initialized")
        
        await self._rate_limit()
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = await self._client.request(method, url, params=params)
            
            if response.status_code == 404:
                return {}
            elif response.status_code == 403:
                logger.warning(f"Rate limited: {url}")
                await asyncio.sleep(60)
                return {}
            
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            logger.error(f"GitHub request failed: {url} - {e}")
            return {}
    
    async def index_all(self, progress_callback=None) -> list[IndexedBlueprint]:
        """
        Index blueprints from all known sources.
        
        Args:
            progress_callback: Optional callback(processed, total) for progress updates
            
        Returns:
            List of indexed blueprints
        """
        all_blueprints = []
        
        # Index known repositories
        logger.info(f"Indexing {len(BLUEPRINT_REPOSITORIES)} known repositories...")
        
        for i, (owner, repo) in enumerate(BLUEPRINT_REPOSITORIES):
            try:
                blueprints = await self.index_repository(owner, repo)
                all_blueprints.extend(blueprints)
                logger.info(f"Indexed {len(blueprints)} blueprints from {owner}/{repo}")
                
                if progress_callback:
                    progress_callback(i + 1, len(BLUEPRINT_REPOSITORIES))
                    
            except Exception as e:
                logger.error(f"Failed to index {owner}/{repo}: {e}")
        
        # Search for more repositories
        logger.info("Searching for additional blueprint repositories...")
        discovered_repos = await self.discover_repositories()
        
        for i, (owner, repo) in enumerate(discovered_repos):
            if (owner, repo) not in BLUEPRINT_REPOSITORIES:
                try:
                    blueprints = await self.index_repository(owner, repo)
                    all_blueprints.extend(blueprints)
                    logger.info(f"Indexed {len(blueprints)} blueprints from discovered repo {owner}/{repo}")
                except Exception as e:
                    logger.error(f"Failed to index discovered repo {owner}/{repo}: {e}")
        
        logger.info(f"Total indexed from GitHub: {len(all_blueprints)} blueprints")
        return all_blueprints
    
    async def index_repository(
        self, 
        owner: str, 
        repo: str,
        path: str = "",
    ) -> list[IndexedBlueprint]:
        """
        Index blueprints from a single repository.
        
        Recursively searches for YAML files containing blueprints.
        """
        blueprints = []
        
        try:
            # Get repository metadata for stars
            repo_data = await self._request("GET", f"/repos/{owner}/{repo}")
            stars = repo_data.get("stargazers_count", 0) if repo_data else 0
            created_at_str = repo_data.get("created_at") if repo_data else None
            updated_at_str = repo_data.get("pushed_at") if repo_data else None
            
            # Parse timestamps
            created_at = None
            if created_at_str:
                created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
            
            updated_at = None
            if updated_at_str:
                updated_at = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
            
            # Find blueprint files
            blueprint_files = await self._find_blueprint_files(owner, repo, path)
            
            for file_info in blueprint_files:
                blueprint = self.parser.parse_blueprint(
                    yaml_content=file_info["content"],
                    source_url=file_info["url"],
                    source_type="github",
                    source_id=f"{owner}/{repo}:{file_info['path']}",
                    stars=stars,
                    author=owner,
                    created_at=created_at,
                    updated_at=updated_at,
                )
                
                if blueprint:
                    blueprints.append(blueprint)
            
        except Exception as e:
            logger.error(f"Failed to index repository {owner}/{repo}: {e}", exc_info=True)
        
        return blueprints
    
    async def _find_blueprint_files(
        self,
        owner: str,
        repo: str,
        path: str = "",
    ) -> list[dict[str, Any]]:
        """Recursively find blueprint YAML files in repository."""
        blueprint_files = []
        
        try:
            contents = await self._request("GET", f"/repos/{owner}/{repo}/contents/{path}")
            
            if not contents or isinstance(contents, dict):
                return blueprint_files
            
            for item in contents:
                item_type = item.get("type")
                item_name = item.get("name", "")
                item_path = item.get("path", "")
                
                if item_type == "file" and item_name.endswith((".yaml", ".yml")):
                    # Download and check if it's a blueprint
                    content = await self._get_file_content(owner, repo, item_path)
                    
                    if content and "blueprint:" in content.lower():
                        blueprint_files.append({
                            "path": item_path,
                            "name": item_name,
                            "content": content,
                            "url": f"https://github.com/{owner}/{repo}/blob/main/{item_path}",
                        })
                        logger.debug(f"Found blueprint: {item_path}")
                
                elif item_type == "dir":
                    # Skip common non-blueprint directories
                    if item_name.lower() in [".git", "node_modules", "__pycache__", ".github", "tests"]:
                        continue
                    
                    # Recursively search subdirectories
                    sub_files = await self._find_blueprint_files(owner, repo, item_path)
                    blueprint_files.extend(sub_files)
            
        except Exception as e:
            logger.warning(f"Error searching {owner}/{repo}/{path}: {e}")
        
        return blueprint_files
    
    async def _get_file_content(
        self,
        owner: str,
        repo: str,
        path: str,
    ) -> Optional[str]:
        """Get raw file content from repository."""
        try:
            data = await self._request("GET", f"/repos/{owner}/{repo}/contents/{path}")
            
            if isinstance(data, dict) and data.get("encoding") == "base64":
                content = base64.b64decode(data.get("content", "")).decode("utf-8")
                return content
            
        except Exception as e:
            logger.warning(f"Error getting file {path}: {e}")
        
        return None
    
    async def discover_repositories(self) -> list[tuple[str, str]]:
        """
        Discover new blueprint repositories via GitHub search.
        
        Returns:
            List of (owner, repo) tuples
        """
        discovered = set()
        
        for query in BLUEPRINT_SEARCH_QUERIES:
            try:
                params = {
                    "q": f"{query} in:readme in:description",
                    "sort": "stars",
                    "order": "desc",
                    "per_page": 30,
                }
                
                data = await self._request("GET", "/search/repositories", params=params)
                
                if data and "items" in data:
                    for item in data["items"]:
                        owner = item.get("owner", {}).get("login")
                        repo = item.get("name")
                        
                        if owner and repo:
                            discovered.add((owner, repo))
                
            except Exception as e:
                logger.warning(f"Search failed for query '{query}': {e}")
        
        logger.info(f"Discovered {len(discovered)} potential blueprint repositories")
        return list(discovered)
    
    async def search_code(self, query: str, limit: int = 100) -> list[dict[str, Any]]:
        """
        Search for blueprint code across GitHub.
        
        Args:
            query: Search query
            limit: Maximum results to return
            
        Returns:
            List of code search results
        """
        results = []
        
        try:
            params = {
                "q": f"{query} language:yaml",
                "per_page": min(limit, 100),
            }
            
            data = await self._request("GET", "/search/code", params=params)
            
            if data and "items" in data:
                for item in data["items"]:
                    results.append({
                        "path": item.get("path"),
                        "repository": item.get("repository", {}).get("full_name"),
                        "url": item.get("html_url"),
                    })
            
        except Exception as e:
            logger.warning(f"Code search failed: {e}")
        
        return results[:limit]
