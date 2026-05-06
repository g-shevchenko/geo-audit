"""Tests for composite scoring."""
from __future__ import annotations

from geo_audit.modules.base import ModuleResult
from geo_audit.scoring import compute_composite, WEIGHTS


def test_weights_sum_to_100():
    assert sum(WEIGHTS.values()) == 100


def test_composite_weighted_average():
    results = [
        ModuleResult(name="citability", score=80),     # weight 25
        ModuleResult(name="schema", score=60),         # weight 15
        ModuleResult(name="llmstxt", score=40),        # weight 10
        ModuleResult(name="brand-mentions", score=70), # weight 20
        ModuleResult(name="technical", score=50),      # weight 15
        ModuleResult(name="content", score=90),        # weight 15
    ]
    c = compute_composite(results, methodology_version="1")
    # (80*25 + 60*15 + 40*10 + 70*20 + 50*15 + 90*15) / 100 = 67.5
    assert c.score == 68
    assert len(c.modules_used) == 6


def test_composite_excludes_skipped():
    results = [
        ModuleResult(name="citability", score=80),
        ModuleResult(name="schema", score=None, ran_in_degraded_mode=True),
        ModuleResult(name="brand-mentions", score=None, ran_in_degraded_mode=True),
    ]
    c = compute_composite(results, methodology_version="1")
    assert c.score == 80
    assert "schema" in c.modules_skipped
    assert "brand-mentions" in c.modules_skipped


def test_composite_zero_when_all_skipped():
    results = [
        ModuleResult(name="citability", score=None, ran_in_degraded_mode=True),
    ]
    c = compute_composite(results, methodology_version="1")
    assert c.score == 0


def test_crawlers_excluded_from_composite():
    """crawlers module has weight 0 — informational only."""
    results = [
        ModuleResult(name="citability", score=100),
        ModuleResult(name="crawlers", score=None),  # informational
    ]
    c = compute_composite(results, methodology_version="1")
    assert c.score == 100
    assert "crawlers" not in c.modules_used
