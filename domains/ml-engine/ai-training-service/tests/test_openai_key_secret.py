"""Regression: openai_api_key must be stored masked (SecretStr).

The field was a plain ``str`` on ``Settings``, so any repr/log dump of the
settings object leaked the raw key. It is now a ``SecretStr``; the env var
OPENAI_API_KEY still populates it, and consumers unwrap the raw value via
``get_secret_value()`` (mirrors ai-query-service's TestBuildProcessorOpenAIKey).
"""

from src.config import Settings


class TestOpenAIKeySecret:
    def test_settings_repr_does_not_leak_key(self):
        settings = Settings(openai_api_key="sk-training-secret")
        assert "sk-training-secret" not in repr(settings)
        assert "sk-training-secret" not in str(settings)

    def test_env_var_round_trips_unwrapped(self, monkeypatch):
        """Env binding is unchanged and the raw key is recoverable at use sites."""
        monkeypatch.setenv("OPENAI_API_KEY", "sk-env-value")

        settings = Settings()

        assert settings.openai_api_key is not None
        assert settings.openai_api_key.get_secret_value() == "sk-env-value"
