"""Tests for the page fetcher fallback layer (Firecrawl)."""
from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest

from geo_audit import fetcher
from geo_audit.crawler import fetch, FetchResult


# ── Heuristic: should we trigger fallback? ─────────────────────────

def test_fallback_on_status_403():
    assert fetcher.should_try_fallback(403, "<html>...</html>") is True


def test_fallback_on_status_500():
    assert fetcher.should_try_fallback(500, "<html>...</html>") is True


def test_fallback_on_network_error():
    assert fetcher.should_try_fallback(0, "") is True


def test_fallback_on_cloudflare_challenge():
    cf_html = "<html><head><title>Just a moment...</title></head><body>cf-browser-verification</body></html>"
    assert fetcher.should_try_fallback(200, cf_html) is True


def test_fallback_on_datadome():
    dd_html = "<html><body>Please enable JavaScript and Cookies, _pxhd...</body></html>"
    assert fetcher.should_try_fallback(200, dd_html) is True


def test_fallback_on_empty_spa_shell():
    spa = '<!DOCTYPE html><html><head><title>App</title></head><body><div id="root"></div><script src="/bundle.js"></script></body></html>'
    assert fetcher.should_try_fallback(200, spa) is True


def test_no_fallback_on_real_html():
    real = "<html><body>" + ("Real content here. " * 100) + "</body></html>"
    assert fetcher.should_try_fallback(200, real) is False


# ── Firecrawl client ───────────────────────────────────────────────

def test_firecrawl_returns_html(monkeypatch):
    fake_response = {
        "success": True,
        "data": {
            "html": "<html><body>Rendered by Firecrawl</body></html>",
            "metadata": {"statusCode": 200, "contentType": "text/html"},
        },
    }

    class _StubResponse:
        def raise_for_status(self): pass
        def json(self): return fake_response

    class _StubClient:
        def __init__(self, *a, **kw): pass
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def post(self, *a, **kw): return _StubResponse()

    monkeypatch.setattr(fetcher, "httpx", type("X", (), {"Client": _StubClient}))
    status, headers, html = fetcher.fetch_via_firecrawl("https://x", "fc-test")
    assert status == 200
    assert "Rendered by Firecrawl" in html
    assert headers["x-fetched-via"] == "firecrawl"


def test_firecrawl_failure_raises(monkeypatch):
    fake_response = {"success": False, "error": "rate limited"}

    class _StubResponse:
        def raise_for_status(self): pass
        def json(self): return fake_response

    class _StubClient:
        def __init__(self, *a, **kw): pass
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def post(self, *a, **kw): return _StubResponse()

    monkeypatch.setattr(fetcher, "httpx", type("X", (), {"Client": _StubClient, "HTTPError": httpx.HTTPError}))
    with pytest.raises(httpx.HTTPError):
        fetcher.fetch_via_firecrawl("https://x", "fc-test")


# ── End-to-end: crawler.fetch with fallback ────────────────────────

def test_fetch_skips_fallback_when_no_key(tmp_path):
    """If FIRECRAWL_API_KEY not set, only direct httpx is attempted."""
    bad_result = FetchResult("https://x", "https://x", 403, {}, "<html>blocked</html>", 50)
    with patch("geo_audit.crawler._direct_httpx_fetch", return_value=(bad_result, None)) as direct, \
         patch("geo_audit.crawler._fetch_via_firecrawl_wrap") as fc:
        result = fetch("https://x", user_agent="ua", cache_dir=tmp_path, no_cache=True)
    assert direct.called
    assert not fc.called
    assert result.status == 403


def test_fetch_uses_fallback_on_403(tmp_path):
    bad_result = FetchResult("https://x", "https://x", 403, {}, "<html>blocked</html>", 50)
    good_result = FetchResult("https://x", "https://x", 200, {"x-fetched-via": "firecrawl"},
                              "<html><body>" + ("Rendered fine. " * 100) + "</body></html>", 800)
    with patch("geo_audit.crawler._direct_httpx_fetch", return_value=(bad_result, None)), \
         patch("geo_audit.crawler._fetch_via_firecrawl_wrap", return_value=good_result) as fc:
        result = fetch("https://x", user_agent="ua", cache_dir=tmp_path, no_cache=True,
                       firecrawl_api_key="fc-test")
    assert fc.called
    assert result.status == 200
    assert result.headers.get("x-fetched-via") == "firecrawl"


def test_fetch_keeps_direct_when_good(tmp_path):
    """Good direct fetch — Firecrawl NOT called, even if key present."""
    good_html = "<html><body>" + ("Real content. " * 100) + "</body></html>"
    good_result = FetchResult("https://x", "https://x", 200, {}, good_html, 100)
    with patch("geo_audit.crawler._direct_httpx_fetch", return_value=(good_result, None)), \
         patch("geo_audit.crawler._fetch_via_firecrawl_wrap") as fc:
        result = fetch("https://x", user_agent="ua", cache_dir=tmp_path, no_cache=True,
                       firecrawl_api_key="fc-test")
    assert not fc.called
    assert result.status == 200


def test_fetch_force_firecrawl_skips_httpx(monkeypatch, tmp_path):
    """FIRECRAWL_FORCE=1 → skip direct httpx entirely."""
    monkeypatch.setenv("FIRECRAWL_FORCE", "1")
    good_html = "<html><body>" + ("Forced via Firecrawl. " * 50) + "</body></html>"
    fc_result = FetchResult("https://x", "https://x", 200, {"x-fetched-via": "firecrawl"}, good_html, 600)
    with patch("geo_audit.crawler._direct_httpx_fetch") as direct, \
         patch("geo_audit.crawler._fetch_via_firecrawl_wrap", return_value=fc_result):
        result = fetch("https://x", user_agent="ua", cache_dir=tmp_path, no_cache=True,
                       firecrawl_api_key="fc-test")
    assert not direct.called
    assert result.headers.get("x-fetched-via") == "firecrawl"


def test_fetch_skips_fallback_on_robots_txt(tmp_path):
    """Non-HTML resources (robots.txt, sitemap.xml) never use Firecrawl."""
    bad_result = FetchResult("https://x/robots.txt", "https://x/robots.txt", 404, {}, "", 30)
    with patch("geo_audit.crawler._direct_httpx_fetch", return_value=(bad_result, None)), \
         patch("geo_audit.crawler._fetch_via_firecrawl_wrap") as fc:
        result = fetch("https://x/robots.txt", user_agent="ua", cache_dir=tmp_path, no_cache=True,
                       firecrawl_api_key="fc-test")
    assert not fc.called
    assert result.status == 404
