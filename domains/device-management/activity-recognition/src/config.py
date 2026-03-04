"""Configuration settings for Activity Recognition Service."""

from homeiq_data import BaseServiceSettings


class Settings(BaseServiceSettings):
    """Application settings loaded from environment variables."""

    # Override base defaults
    service_port: int = 8036
    service_name: str = "activity-recognition"

    # Service-specific
    model_path: str = "./models/activity_lstm.onnx"
    debug: bool = False


settings = Settings()
