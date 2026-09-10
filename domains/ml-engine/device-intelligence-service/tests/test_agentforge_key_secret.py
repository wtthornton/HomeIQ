"""Regression: the name-suggestion credential must be stored masked and unwrapped at use.

TAP-7275 replaced the OpenAI key with an AgentForge project key. The property
under test is unchanged and is what the original ``test_openai_key_secret``
guarded: the field is a ``SecretStr`` so a repr/log dump of the settings object
cannot leak it, the env var still populates it, and ``AINameSuggester`` unwraps
it before putting it on the wire.
"""

from src.config import Settings
from src.services.name_enhancement.ai_suggester import AINameSuggester


class TestAgentForgeKeySecret:
    def test_settings_repr_does_not_leak_key(self):
        settings = Settings(AGENTFORGE_API_KEY="afp-device-secret")
        assert "afp-device-secret" not in repr(settings)
        assert "afp-device-secret" not in str(settings)

    def test_env_var_still_populates_field(self, monkeypatch):
        monkeypatch.setenv("AGENTFORGE_API_KEY", "afp-env-value")
        settings = Settings()
        assert settings.AGENTFORGE_API_KEY is not None
        assert settings.AGENTFORGE_API_KEY.get_secret_value() == "afp-env-value"

    def test_suggester_unwraps_the_key(self):
        """The bearer must carry the real key, not the SecretStr wrapper."""
        settings = Settings(AGENTFORGE_API_KEY="afp-device-secret")
        suggester = AINameSuggester(settings)

        assert suggester.api_key == "afp-device-secret"
        assert "SecretStr" not in suggester.api_key
        assert suggester.configured is True

    def test_absent_key_is_not_configured(self):
        settings = Settings(AGENTFORGE_API_KEY=None)
        assert AINameSuggester(settings).configured is False
