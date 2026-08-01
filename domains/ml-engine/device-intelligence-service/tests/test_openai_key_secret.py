"""Regression: OPENAI_API_KEY must be stored masked and unwrapped at use.

The field was a plain ``str`` on ``Settings``, so any repr/log dump of the
settings object leaked the raw key. It is now a ``SecretStr``; the env var
OPENAI_API_KEY still populates it, and ``AINameSuggester`` must unwrap it
before handing it to the OpenAI SDK (mirrors ai-query-service's
TestBuildProcessorOpenAIKey).
"""

from src.config import Settings
from src.services.name_enhancement.ai_suggester import AINameSuggester


class TestOpenAIKeySecret:
    def test_settings_repr_does_not_leak_key(self):
        settings = Settings(OPENAI_API_KEY="sk-device-secret")
        assert "sk-device-secret" not in repr(settings)
        assert "sk-device-secret" not in str(settings)

    def test_env_var_still_populates_field(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-env-value")
        settings = Settings()
        assert settings.OPENAI_API_KEY is not None
        assert settings.OPENAI_API_KEY.get_secret_value() == "sk-env-value"

    def test_ai_suggester_receives_unwrapped_key(self, monkeypatch):
        """The SDK must receive the real key, not the SecretStr wrapper."""
        captured = {}

        class FakeAsyncOpenAI:
            def __init__(self, **kwargs):
                captured.update(kwargs)

        monkeypatch.setattr(
            "src.services.name_enhancement.ai_suggester.AsyncOpenAI",
            FakeAsyncOpenAI,
        )
        settings = Settings(OPENAI_API_KEY="sk-device-secret", ENABLE_LOCAL_LLM=False)

        AINameSuggester(settings)

        # str(SecretStr) is "**********"; passing the wrapper straight through
        # would authenticate with the mask instead of the key.
        assert captured["api_key"] == "sk-device-secret"
