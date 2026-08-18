import pytest
from src.config import ConfigError, load_settings


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for key in (
        "HOMEIQ_MCP_READ_TOKENS",
        "HOMEIQ_MCP_WRITE_TOKENS",
        "DATA_API_URL",
        "API_KEY",
        "HOMEIQ_MCP_TRANSPORT",
    ):
        monkeypatch.delenv(key, raising=False)


def test_http_requires_tokens_url_and_key():
    with pytest.raises(ConfigError) as exc:
        load_settings()
    message = str(exc.value)
    assert "refusing to start" in message
    for name in ("HOMEIQ_MCP_READ_TOKENS", "DATA_API_URL", "API_KEY"):
        assert name in message


def test_stdio_needs_no_tokens(monkeypatch):
    monkeypatch.setenv("HOMEIQ_MCP_TRANSPORT", "stdio")
    monkeypatch.setenv("DATA_API_URL", "http://data-api:8006/")
    monkeypatch.setenv("API_KEY", "k")
    settings = load_settings()
    assert settings.transport == "stdio"
    assert settings.data_api_url == "http://data-api:8006"


def test_token_overlap_is_rejected(monkeypatch):
    monkeypatch.setenv("HOMEIQ_MCP_READ_TOKENS", "same")
    monkeypatch.setenv("HOMEIQ_MCP_WRITE_TOKENS", "same,other")
    monkeypatch.setenv("DATA_API_URL", "http://data-api:8006")
    monkeypatch.setenv("API_KEY", "k")
    with pytest.raises(ConfigError, match="both"):
        load_settings()


def test_allowed_host_patterns_include_public_hostname(monkeypatch):
    monkeypatch.setenv("HOMEIQ_MCP_READ_TOKENS", "r")
    monkeypatch.setenv("DATA_API_URL", "http://data-api:8006")
    monkeypatch.setenv("API_KEY", "k")
    monkeypatch.setenv("HOMEIQ_MCP_ALLOWED_HOSTS", "agentforge-main,10.0.0.5:8030")
    settings = load_settings()
    assert "homeiq-mcp:*" in settings.allowed_host_patterns
    assert "agentforge-main:*" in settings.allowed_host_patterns
    assert "10.0.0.5:8030" in settings.allowed_host_patterns


def test_invalid_port_is_a_config_error(monkeypatch):
    monkeypatch.setenv("HOMEIQ_MCP_READ_TOKENS", "r")
    monkeypatch.setenv("DATA_API_URL", "http://data-api:8006")
    monkeypatch.setenv("API_KEY", "k")
    monkeypatch.setenv("HOMEIQ_MCP_PORT", "70000")
    with pytest.raises(ConfigError, match="port"):
        load_settings()


def test_catalogue_path_resolution_prefers_explicit_then_repo(monkeypatch, tmp_path):
    from src import catalogue as cat

    monkeypatch.delenv("HOMEIQ_MCP_CATALOGUE_PATH", raising=False)
    explicit = tmp_path / "x.json"
    assert cat.resolve_catalogue_path(str(explicit)) == explicit
    monkeypatch.setenv("HOMEIQ_MCP_CATALOGUE_PATH", str(explicit))
    assert cat.resolve_catalogue_path() == explicit
    monkeypatch.delenv("HOMEIQ_MCP_CATALOGUE_PATH")
    assert cat.resolve_catalogue_path().name == "homeiq-mcp-tools.schema.json"
    # A shallow install (e.g. /app/src) must not raise; it falls back to the image path.
    monkeypatch.setattr(cat, "_repo_candidate", lambda: None)
    assert cat.resolve_catalogue_path() == cat._IMAGE_PATH


def test_tokens_never_appear_in_settings_repr(monkeypatch):
    monkeypatch.setenv("HOMEIQ_MCP_READ_TOKENS", "read-secret-abc")
    monkeypatch.setenv("HOMEIQ_MCP_WRITE_TOKENS", "write-secret-xyz")
    monkeypatch.setenv("DATA_API_URL", "http://data-api:8006")
    monkeypatch.setenv("API_KEY", "k-secret")
    settings = load_settings()
    dumped = repr(settings) + str(settings.model_dump())
    for secret in ("read-secret-abc", "write-secret-xyz", "k-secret"):
        assert secret not in dumped
    assert settings.read_token_list == ["read-secret-abc"]
