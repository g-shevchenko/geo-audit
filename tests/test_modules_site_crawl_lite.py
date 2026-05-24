"""Tests for site-crawl-lite module."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from geo_audit.crawler import FetchResult
from geo_audit.modules.base import ModuleArgs
from geo_audit.modules import site_crawl_lite as mod


def _args(html: str, sitemap_urls: list[str], tmp_path: Path, robots: str = "User-agent: *\nAllow: /\n") -> ModuleArgs:
    return ModuleArgs(
        url="https://example.com/",
        cache_dir=tmp_path,
        user_agent="geo-audit-test",
        timeout_s=5,
        api_keys={},
        homepage_html=html,
        homepage_status=200,
        homepage_headers={},
        homepage_url_final="https://example.com/",
        sitemap_urls=sitemap_urls,
        robots_txt=robots,
    )


def test_site_crawl_lite_finds_route_head_gaps(good_html, bad_html, tmp_path):
    def stub_fetch(url: str, **_):
        if url.endswith("/bad"):
            return FetchResult(url, url, 200, {}, bad_html, 1)
        return FetchResult(url, url, 200, {}, good_html, 1)

    args = _args(good_html, ["https://example.com/", "https://example.com/bad"], tmp_path)
    with patch("geo_audit.modules.site_crawl_lite.fetch", side_effect=stub_fetch):
        result = mod.run(args)

    assert result.name == "site-crawl-lite"
    assert result.score is not None
    assert result.score < 100
    assert result.sub_scores["routes_checked"] == 2
    assert result.sub_scores["issue_counts"]["missing_meta_description"] == 1
    assert any(a.title == "Add missing meta descriptions" for a in result.actions)


def test_site_crawl_lite_respects_robots(good_html, tmp_path):
    args = _args(
        good_html,
        ["https://example.com/private"],
        tmp_path,
        robots="User-agent: *\nDisallow: /private\n",
    )
    result = mod.run(args)

    assert result.sub_scores["routes_checked"] == 1
    assert result.sub_scores["blocked_urls"] == ["https://example.com/private"]
    assert any(a.title == "Robots.txt blocked crawl-lite URLs" for a in result.actions)


def test_site_crawl_lite_good_fixture_has_no_p0_or_p1(good_html, tmp_path):
    args = _args(good_html, ["https://example.com/"], tmp_path)
    result = mod.run(args)

    severe = [a for a in result.actions if a.priority in {"P0", "P1"}]
    assert severe == []
    assert result.score and result.score >= 80
