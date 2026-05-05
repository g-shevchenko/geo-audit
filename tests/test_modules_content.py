"""Tests for content module — EEAT + AI-detection heuristic + readability."""
from __future__ import annotations

from geo_audit.modules import content as mod
from geo_audit.modules.base import ModuleArgs


def _args(html: str, url: str = "https://example.com/") -> ModuleArgs:
    return ModuleArgs(url=url, homepage_html=html, homepage_status=200)


def test_good_page_scores_well(good_html):
    result = mod.run(_args(good_html))
    assert result.score >= 50, f"good page should ≥50, got {result.score}"


def test_bad_page_scores_low(bad_html):
    result = mod.run(_args(bad_html))
    # bad page has no author, no dates, no contact, no outbound, but has decent readability + low AI signal
    assert result.score < 50, result.score


def test_eeat_good_page(good_html):
    score, _findings, _actions = mod._check_eeat(good_html)
    assert score >= 30  # most signals present


def test_eeat_bad_page(bad_html):
    score, _findings, _actions = mod._check_eeat(bad_html)
    assert score == 0  # no author, no dates, no contact


def test_ai_heuristic_low_on_human_text():
    text = "GEO is a discipline. Add a TL;DR. Use FAQ blocks. Add schema. Done."
    likelihood, _hits = mod._ai_detect_heuristic(text, "en")
    assert likelihood < 0.25


def test_ai_heuristic_high_on_slop():
    text = ("In today's fast-paced digital landscape, it's important to note that we must "
            "delve into the world of cutting-edge solutions. Whether you're a startup or "
            "Fortune 500, our seamless intuitive platform unlocks the power of innovation. "
            "Not only that, but also it's a game-changer.") * 2
    likelihood, hits = mod._ai_detect_heuristic(text, "en")
    assert likelihood >= 0.5, f"got {likelihood}, hits={hits}"


def test_flesch_returns_for_long_text():
    text = ("This is a sentence. " * 30 + "Another simple line. " * 30)
    f = mod._flesch_reading_ease(text)
    assert f is not None


def test_flesch_returns_none_for_short_text():
    assert mod._flesch_reading_ease("hi") is None


def test_pushkin_for_russian():
    text = ("Это простое предложение. " * 20 + "Ещё одно короткое. " * 20)
    p = mod._pushkin_readability(text)
    assert p is not None


def test_deterministic(good_html):
    s1 = mod.run(_args(good_html)).score
    s2 = mod.run(_args(good_html)).score
    assert s1 == s2


def test_handles_bad_status():
    result = mod.run(ModuleArgs(url="https://x", homepage_html="", homepage_status=500))
    assert result.score == 0
    assert result.ran_in_degraded_mode is True
