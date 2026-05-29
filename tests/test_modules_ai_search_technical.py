"""Tests for ai-search-technical gate."""
from __future__ import annotations

from geo_audit.modules import ai_search_technical as mod
from geo_audit.modules.base import ModuleArgs


def _args(html: str, robots: str, **kw) -> ModuleArgs:
    args = dict(
        url="https://example.com/",
        homepage_html=html,
        homepage_status=200,
        homepage_url_final="https://example.com/",
        homepage_headers={},
        sitemap_urls=["https://example.com/", "https://example.com/about"],
        robots_txt=robots,
    )
    args.update(kw)
    return ModuleArgs(**args)


GOOD_ROBOTS = """User-agent: *
Allow: /

User-agent: Googlebot
Allow: /

User-agent: Bingbot
Allow: /

User-agent: OAI-SearchBot
Allow: /

User-agent: Claude-SearchBot
Allow: /

User-agent: PerplexityBot
Allow: /
"""


def test_good_page_passes_gate(good_html):
    result = mod.run(_args(good_html, GOOD_ROBOTS))

    assert result.score >= 90
    assert result.sub_scores["gate_verdict"] == "pass"
    assert result.sub_scores["blocked_crawlers"] == []
    assert not [a for a in result.actions if a.priority == "P0"]


def test_blocks_googlebot_and_oai_searchbot(good_html):
    robots = """User-agent: *
Allow: /

User-agent: Googlebot
Disallow: /

User-agent: OAI-SearchBot
Disallow: /
"""
    result = mod.run(_args(good_html, robots))

    assert result.sub_scores["gate_verdict"] == "fail"
    assert "Googlebot" in result.sub_scores["blocked_crawlers"]
    assert "OAI-SearchBot" in result.sub_scores["blocked_crawlers"]
    titles = [a.title for a in result.actions]
    assert any("Googlebot" in title for title in titles)


def test_js_only_page_fails_parseability(empty_spa_html):
    result = mod.run(_args(empty_spa_html, GOOD_ROBOTS))

    assert result.sub_scores["main_content_parseable"] is False
    assert result.sub_scores["gate_verdict"] == "fail"
    assert any("initial HTML" in a.title for a in result.actions)


def test_noindex_blocks_google_ai_eligibility(good_html):
    html = good_html.replace("</head>", '<meta name="robots" content="noindex"></head>')
    result = mod.run(_args(html, GOOD_ROBOTS))

    assert result.sub_scores["noindex_detected"] is True
    assert result.sub_scores["gate_verdict"] == "fail"
    assert any("noindex" in a.title.lower() for a in result.actions)


def test_missing_sitemap_warns_but_does_not_fail(good_html):
    result = mod.run(_args(good_html, GOOD_ROBOTS, sitemap_urls=[]))

    assert result.sub_scores["gate_verdict"] == "warn"
    assert any("sitemap" in a.title.lower() for a in result.actions)
