"""Shared pytest fixtures."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Ensure local package imports without install for CI ergonomics.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture(autouse=True)
def _scrub_env(monkeypatch):
    """Strip all geo-audit env vars so tests are deterministic.

    Tests opt back into specific keys via monkeypatch.setenv.
    """
    for k in [
        "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "PAGESPEED_API_KEY",
        "PERPLEXITY_API_KEY", "GEMINI_API_KEY", "TAVILY_API_KEY",
        "SERPER_API_KEY", "SEARXNG_BASE_URL",
        "YANDEX_XML_USER", "YANDEX_XML_KEY",
        "ORIGINALITY_API_KEY", "GPTZERO_API_KEY",
        "GEO_AUDIT_CACHE_DIR",
    ]:
        monkeypatch.delenv(k, raising=False)


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def good_html(fixtures_dir) -> str:
    return (fixtures_dir / "good_page.html").read_text(encoding="utf-8")


@pytest.fixture
def bad_html(fixtures_dir) -> str:
    return (fixtures_dir / "bad_page.html").read_text(encoding="utf-8")


@pytest.fixture
def empty_spa_html(fixtures_dir) -> str:
    return (fixtures_dir / "empty_spa.html").read_text(encoding="utf-8")


@pytest.fixture
def good_robots() -> str:
    return """User-agent: *
Allow: /

User-agent: Googlebot
Allow: /

Sitemap: https://example.com/sitemap.xml
"""


@pytest.fixture
def blocking_robots() -> str:
    return """User-agent: *
Disallow: /

User-agent: GPTBot
Disallow: /

User-agent: ClaudeBot
Disallow: /
"""


@pytest.fixture
def good_sitemap() -> str:
    return """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/</loc></url>
  <url><loc>https://example.com/about</loc></url>
  <url><loc>https://example.com/blog/post-1</loc></url>
</urlset>
"""
