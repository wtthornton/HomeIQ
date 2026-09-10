"""Rate-limit coverage for the GitHub and HA community forum crawl sources.

TAP-7311 requires rate limiting to be present before the refresh runs on a
schedule -- GitHubBlueprintIndexer and DiscourseBlueprintIndexer already
enforce a per-request delay computed from settings, but nothing asserted it.
Locking it in here so a future edit can't silently drop the delay while the
scheduler keeps firing unattended.
"""

from src.config import settings
from src.indexer.discourse_indexer import DiscourseBlueprintIndexer
from src.indexer.github_indexer import GitHubBlueprintIndexer


class TestGitHubRateLimiting:
    def test_default_delay_derives_from_settings(self):
        indexer = GitHubBlueprintIndexer()
        assert indexer.rate_limit == settings.github_rate_limit_per_sec
        assert indexer._rate_limit_delay == 1.0 / settings.github_rate_limit_per_sec

    def test_explicit_rate_limit_overrides_settings(self):
        indexer = GitHubBlueprintIndexer(rate_limit_per_sec=2.0)
        assert indexer._rate_limit_delay == 0.5


class TestDiscourseRateLimiting:
    def test_default_delay_derives_from_settings(self):
        indexer = DiscourseBlueprintIndexer()
        assert indexer.rate_limit == settings.discourse_rate_limit_per_sec
        assert indexer._rate_limit_delay == 1.0 / settings.discourse_rate_limit_per_sec

    def test_explicit_rate_limit_overrides_settings(self):
        indexer = DiscourseBlueprintIndexer(rate_limit_per_sec=4.0)
        assert indexer._rate_limit_delay == 0.25
