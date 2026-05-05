"""Tests for llmstxt module — robots parsing + bot allow-check.

Network calls (llms.txt fetch) are mocked.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from geo_audit.crawler import FetchResult
from geo_audit.modules import llmstxt as mod
from geo_audit.modules.base import ModuleArgs


def _args(robots: str = "", url: str = "https://example.com/") -> ModuleArgs:
    return ModuleArgs(url=url, homepage_html="", homepage_status=200, robots_txt=robots)


def test_bot_allowed_when_no_robots():
    assert mod._bot_allowed_in_robots("", "GPTBot") is True


def test_bot_blocked_when_explicit_disallow(blocking_robots):
    assert mod._bot_allowed_in_robots(blocking_robots, "GPTBot") is False
    assert mod._bot_allowed_in_robots(blocking_robots, "ClaudeBot") is False


def test_bot_allowed_when_other_bot_blocked():
    robots = """User-agent: BadBot
Disallow: /

User-agent: *
Allow: /
"""
    assert mod._bot_allowed_in_robots(robots, "GPTBot") is True


def test_bot_allowed_with_wildcard_allow(good_robots):
    for bot in mod.AI_BOTS:
        assert mod._bot_allowed_in_robots(good_robots, bot) is True


def test_valid_llms_txt():
    valid = "# My Site\n\n> An LLM-friendly site map.\n\n## Sections\n\n- [Home](/)\n"
    assert mod._is_valid_llms_txt(valid) is True


def test_invalid_llms_txt_too_short():
    assert mod._is_valid_llms_txt("") is False
    assert mod._is_valid_llms_txt("# X") is False


def test_run_with_blocking_robots_scores_partial(blocking_robots):
    """Module probes /llms.txt and /llms-full.txt — mock them to 404."""
    args = _args(robots=blocking_robots)
    with patch("geo_audit.modules.llmstxt.fetch") as m_fetch:
        m_fetch.return_value = FetchResult(
            url="x", final_url="x", status=404, headers={}, text="", duration_ms=10,
        )
        result = mod.run(args)
    # No llms.txt + no llms-full + bots blocked = very low score.
    assert result.score <= 20, result.score
    p0s = [a for a in result.actions if a.priority == "P0"]
    titles = [a.title for a in p0s]
    assert any("Unblock AI bots" in t for t in titles) or any("Publish /llms.txt" in t for t in titles)


def test_run_with_good_robots_full_score(good_robots):
    """Mock llms.txt + llms-full.txt to 200."""
    valid_llms = "# Example\n\n> An LLM-friendly site map.\n\n## Sections\n\n- [Home](/)\n"
    big_full = "# Example\n\n" + ("Lorem ipsum dolor sit amet. " * 100)

    def _stub(url, **_):
        if url.endswith("/llms.txt"):
            text = valid_llms
        elif url.endswith("/llms-full.txt"):
            text = big_full
        else:
            text = ""
        return FetchResult(url=url, final_url=url, status=200, headers={}, text=text, duration_ms=10)

    with patch("geo_audit.modules.llmstxt.fetch", side_effect=_stub):
        result = mod.run(_args(robots=good_robots))
    assert result.score == 100, result.score
