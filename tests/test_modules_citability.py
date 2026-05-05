"""Tests for citability module — heuristic 5-rubric scoring."""
from __future__ import annotations

from geo_audit.modules import citability as mod
from geo_audit.modules.base import ModuleArgs


def _args(html: str, url: str = "https://example.com/") -> ModuleArgs:
    return ModuleArgs(url=url, homepage_html=html, homepage_status=200)


def test_lang_detect_en(good_html):
    assert mod._detect_lang(good_html) == "en"


def test_lang_detect_ru(fixtures_dir):
    ru = (fixtures_dir / "good_page_ru.html").read_text(encoding="utf-8")
    assert mod._detect_lang(ru) == "ru"


def test_lang_hint_overrides():
    assert mod._detect_lang("<html>...", hint="ru") == "ru"


def test_good_page_scores_high(good_html):
    result = mod.run(_args(good_html))
    assert result.score >= 80, f"good page should ≥80, got {result.score}"


def test_bad_page_scores_low(bad_html):
    result = mod.run(_args(bad_html))
    assert result.score <= 25, f"bad page should ≤25, got {result.score}"


def test_good_ru_page(fixtures_dir):
    ru = (fixtures_dir / "good_page_ru.html").read_text(encoding="utf-8")
    result = mod.run(_args(ru))
    assert result.score >= 70, f"good RU page should ≥70, got {result.score}"
    assert result.sub_scores["lang_detected"] == "ru"


def test_deterministic(good_html):
    s1 = mod.run(_args(good_html)).score
    s2 = mod.run(_args(good_html)).score
    assert s1 == s2


def test_tldr_detection():
    html = "<p>TL;DR: this is the answer.</p><p>" + "x " * 1000 + "</p>"
    text = mod._strip_html_to_text(html)
    ok, _ = mod._check_tldr(html, text)
    assert ok is True


def test_no_tldr():
    text = "x " * 200
    ok, _ = mod._check_tldr("<html><body>" + text + "</body></html>", text)
    assert ok is False


def test_definitions_en():
    text = "Generative Engine Optimization is a discipline. "
    count, _ = mod._check_definitions(text, "en")
    assert count >= 1


def test_definitions_ru():
    text = "GEO — это оптимизация. Citability — это вероятность."
    count, _ = mod._check_definitions(text, "ru")
    assert count >= 2


def test_source_links_outbound():
    html = '<a href="https://schema.org/X">x</a> <a href="https://example.com/y">y</a>'
    count, _ = mod._check_source_links(html, "https://example.com/")
    assert count == 1  # schema.org is outbound; example.com is self.


def test_handles_bad_status():
    args = ModuleArgs(url="https://x", homepage_html="", homepage_status=500)
    result = mod.run(args)
    assert result.score == 0
    assert result.ran_in_degraded_mode is True
