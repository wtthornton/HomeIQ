"""Configuration settings for Blueprint Suggestion Service."""

from homeiq_data import BaseServiceSettings


class Settings(BaseServiceSettings):
    """Application settings loaded from environment variables."""

    # Database (additional to base)
    database_pool_size: int = 10
    database_max_overflow: int = 5

    # Service URLs
    blueprint_index_url: str = "http://blueprint-index:8031"
    ai_pattern_service_url: str = "http://ai-pattern-service:8020"

    # HTTP Settings
    http_timeout_connect: float = 10.0
    http_timeout_read: float = 30.0
    http_timeout_write: float = 30.0
    http_timeout_pool: float = 10.0
    http_max_keepalive: int = 5
    http_max_connections: int = 10

    # Suggestion Settings
    min_suggestion_score: float = 0.6
    max_suggestions_per_blueprint: int = 5
    min_suggestions_per_blueprint: int = 1

    # Fetch limits
    max_blueprints_fetch: int = 200
    max_entities_fetch: int = 1000

    # Combination generation limits
    max_single_device_candidates: int = 10
    max_per_domain_candidates: int = 5
    max_cross_domain_candidates: int = 3
    max_multi_device_entity_pool: int = 20
    max_combinations_to_score: int = 50

    # Scoring Settings
    device_match_weight: float = 0.50
    blueprint_quality_weight: float = 0.15
    community_rating_weight: float = 0.10
    temporal_relevance_weight: float = 0.10
    user_profile_weight: float = 0.10
    complexity_bonus_weight: float = 0.05

    # Auth
    admin_api_key: str | None = None  # Required for destructive endpoints like DELETE /delete-all

    # Override base defaults
    service_port: int = 8032
    service_name: str = "blueprint-suggestion-service"


settings = Settings()
