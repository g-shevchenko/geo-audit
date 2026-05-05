"""Tests for crawler — robots, sitemap parsing, normalization."""
from __future__ import annotations

from geo_audit.crawler import (
    _parse_sitemap_xml, is_allowed_by_robots, normalize_url,
)


def test_normalize_url_adds_scheme():
    assert normalize_url("example.com") == "https://example.com/"


def test_normalize_url_lowercases_host():
    assert normalize_url("https://Example.COM/path") == "https://example.com/path"


def test_normalize_url_strips_fragment():
    assert normalize_url("https://example.com/page#x") == "https://example.com/page"


def test_normalize_url_keeps_query():
    assert normalize_url("https://example.com/?a=1") == "https://example.com/?a=1"


def test_parse_sitemap(good_sitemap):
    urls = _parse_sitemap_xml(good_sitemap)
    assert "https://example.com/" in urls
    assert "https://example.com/about" in urls
    assert "https://example.com/blog/post-1" in urls


def test_parse_sitemap_index():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap><loc>https://example.com/sitemap-pages.xml</loc></sitemap>
  <sitemap><loc>https://example.com/sitemap-posts.xml</loc></sitemap>
</sitemapindex>"""
    urls = _parse_sitemap_xml(xml)
    assert "https://example.com/sitemap-pages.xml" in urls
    assert "https://example.com/sitemap-posts.xml" in urls


def test_robots_allow():
    robots = "User-agent: *\nAllow: /\n"
    assert is_allowed_by_robots("https://x/y", robots, "GPTBot") is True


def test_robots_disallow():
    robots = "User-agent: GPTBot\nDisallow: /\n"
    assert is_allowed_by_robots("https://x/y", robots, "GPTBot") is False
