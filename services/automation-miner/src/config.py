"""
Configuration for Automation Miner

Uses Pydantic Settings for environment variable management.
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Feature Flags
    enable_automation_miner: bool = False
    enable_startup_initialization: bool = True  # Run refresh on startup if corpus empty/stale
    
    # Database
    miner_db_path: str = "data/automation_miner.db"
    
    # Discourse API
    discourse_base_url: str = "https://community.home-assistant.io"
    discourse_category_id: int = 53  # Blueprints Exchange
    discourse_min_likes: int = 500
    discourse_rate_limit_per_sec: float = 2.0
    
    # GitHub API (optional)
    github_token: Optional[str] = None
    github_min_stars: int = 50
    
    # HTTP Client
    http_timeout_connect: float = 10.0
    http_timeout_read: float = 30.0
    http_timeout_write: float = 10.0
    http_timeout_pool: float = 10.0
    http_max_connections: int = 10
    http_max_keepalive: int = 5
    http_retries: int = 3
    
    # Crawler
    crawler_batch_size: int = 50
    crawler_max_posts: int = 3000
    
    # Quality Thresholds
    min_quality_score: float = 0.4
    target_avg_quality: float = 0.7
    dedup_similarity_threshold: float = 0.85
    pruning_quality_threshold: float = 0.3  # Automations below this will be pruned
    pruning_age_days: int = 365  # Automations older than this with low quality will be pruned
    
    # Logging
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

