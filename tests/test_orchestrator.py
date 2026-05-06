"""End-to-end orchestrator tests with mocked HTTP."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from geo_audit.crawler import FetchResult
from geo_audit.orchestrator import run_audit


@pytest.fixture
def stub_fetcher(good_html, good_robots, good_sitemap):
    """Patch geo_audit.crawler.fetch in BOTH orchestrator + llmstxt."""
    def _stub(url, **_):
        if "robots.txt" in url:
            return FetchResult(url, url, 200, {}, good_robots, 5)
        if "sitemap" in url:
            return FetchResult(url, url, 200, {}, good_sitemap, 5)
        if "/llms.txt" in url:
            text = "# Example\n\n> An LLM-friendly site map.\n\n## Sections\n\n- [Home](/)\n"
            return FetchResult(url, url, 200, {}, text, 5)
        if "/llms-full.txt" in url:
            text = "# Example\n\n" + ("Lorem ipsum dolor sit amet. " * 100)
            return FetchResult(url, url, 200, {}, text, 5)
        return FetchResult(
            url, "https://example.com/", 200,
            {"strict-transport-security": "max-age=31536000"},
            good_html, 30,
        )
    return _stub


def test_e2e_no_keys(stub_fetcher, tmp_path):
    with patch("geo_audit.crawler.httpx.Client") as MC, \
         patch("geo_audit.orchestrator.fetch", side_effect=stub_fetcher), \
         patch("geo_audit.orchestrator.fetch_robots", return_value="User-agent: *\nAllow: /\n"), \
         patch("geo_audit.orchestrator.fetch_sitemap_urls", return_value=["https://example.com/", "https://example.com/about"]), \
         patch("geo_audit.modules.llmstxt.fetch", side_effect=stub_fetcher):
        report = run_audit("https://example.com/", no_cache=True)

    assert 0 < report.composite.score <= 100
    # brand-mentions skipped without keys.
    assert "brand-mentions" in report.composite.modules_skipped
    # citability/schema/llmstxt/content/technical all ran.
    for m in ["citability", "schema", "llmstxt", "content", "technical"]:
        assert m in report.composite.modules_used, f"{m} should have run"


def test_e2e_deterministic(stub_fetcher, tmp_path):
    """Same fixture twice → same score."""
    def _go():
        with patch("geo_audit.orchestrator.fetch", side_effect=stub_fetcher), \
             patch("geo_audit.orchestrator.fetch_robots", return_value="User-agent: *\nAllow: /\n"), \
             patch("geo_audit.orchestrator.fetch_sitemap_urls", return_value=["https://example.com/"]), \
             patch("geo_audit.modules.llmstxt.fetch", side_effect=stub_fetcher):
            return run_audit("https://example.com/", no_cache=True)
    r1 = _go()
    r2 = _go()
    assert r1.composite.score == r2.composite.score


def test_e2e_report_json_serializable(stub_fetcher):
    import json as _json
    with patch("geo_audit.orchestrator.fetch", side_effect=stub_fetcher), \
         patch("geo_audit.orchestrator.fetch_robots", return_value=""), \
         patch("geo_audit.orchestrator.fetch_sitemap_urls", return_value=[]), \
         patch("geo_audit.modules.llmstxt.fetch", side_effect=stub_fetcher):
        report = run_audit("https://example.com/", no_cache=True)
    s = _json.dumps(report.to_dict(), default=str)
    parsed = _json.loads(s)
    assert "composite_score" in parsed
    assert "modules" in parsed
    assert parsed["geo_audit_version"] == report.geo_audit_version
