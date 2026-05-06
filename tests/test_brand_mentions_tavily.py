"""Tests for Tavily grounding wired into brand-mentions."""
from __future__ import annotations

from unittest.mock import patch

from geo_audit import llm
from geo_audit.modules import brand_mentions as mod
from geo_audit.modules.base import ModuleArgs


def _args(api_keys: dict) -> ModuleArgs:
    return ModuleArgs(
        url="https://acme.io/",
        homepage_html="<html><head><title>Acme — observability</title></head><body>Acme builds modern observability for cloud apps.</body></html>",
        homepage_status=200,
        api_keys=api_keys,
    )


def test_tavily_called_when_key_present():
    fake_resp = llm.LLMResponse(
        provider="anthropic", model="claude-3-5-haiku-latest",
        content="Acme is an observability vendor at acme.io",
        tokens_in=120, tokens_out=80, cost_usd=0.0001, duration_ms=50, citations=[],
    )
    fake_tavily = [
        {"title": "Acme blog", "url": "https://acme.io/blog", "content": "Acme builds observability"},
        {"title": "Acme on Hacker News", "url": "https://news.ycombinator.com/from?site=acme.io", "content": "Discussion"},
    ]
    with patch.object(mod, "_tavily_search", return_value=fake_tavily) as tavily, \
         patch.object(llm, "call_anthropic", return_value=fake_resp) as anth:
        result = mod.run(_args({"ANTHROPIC_API_KEY": "sk-x", "TAVILY_API_KEY": "tvly-x"}))
    assert tavily.called
    assert anth.called
    # System prompt should contain grounding text from Tavily.
    sys_prompt = anth.call_args.kwargs["system"]
    assert "live web search context" in sys_prompt
    assert "https://acme.io/blog" in sys_prompt
    # Sub-scores should record grounding.
    assert result.sub_scores["tavily_grounding_used"] is True
    assert result.sub_scores["tavily_results_count"] == 2


def test_tavily_skipped_for_perplexity():
    """Perplexity has built-in web search; we must not waste a Tavily lookup
    nor inject grounding into its prompt."""
    fake_resp = llm.LLMResponse(
        provider="perplexity", model="sonar",
        content="Acme is observability for cloud apps. acme.io",
        tokens_in=120, tokens_out=80, cost_usd=0.0001, duration_ms=80,
        citations=["https://acme.io/about"],
    )
    fake_tavily = [{"title": "Acme blog", "url": "https://acme.io/blog", "content": "x"}]
    with patch.object(mod, "_tavily_search", return_value=fake_tavily), \
         patch.object(llm, "call_perplexity", return_value=fake_resp) as ppl:
        mod.run(_args({"PERPLEXITY_API_KEY": "pplx-x", "TAVILY_API_KEY": "tvly-x"}))
    sys_prompt = ppl.call_args.kwargs["system"]
    # Perplexity prompt must NOT contain Tavily grounding.
    assert "live web search context" not in sys_prompt


def test_no_tavily_no_grounding():
    fake_resp = llm.LLMResponse(
        provider="anthropic", model="claude-3-5-haiku-latest",
        content="Acme is an observability vendor",
        tokens_in=120, tokens_out=80, cost_usd=0.0001, duration_ms=50, citations=[],
    )
    with patch.object(mod, "_tavily_search") as tavily, \
         patch.object(llm, "call_anthropic", return_value=fake_resp) as anth:
        result = mod.run(_args({"ANTHROPIC_API_KEY": "sk-x"}))
    assert not tavily.called
    sys_prompt = anth.call_args.kwargs["system"]
    assert "live web search context" not in sys_prompt
    assert result.sub_scores["tavily_grounding_used"] is False


def test_tavily_failure_does_not_block_provider_calls():
    """Tavily 5xx → empty results → grounding skipped, providers still called."""
    fake_resp = llm.LLMResponse(
        provider="anthropic", model="claude-3-5-haiku-latest",
        content="Acme is observability",
        tokens_in=10, tokens_out=10, cost_usd=0.0, duration_ms=10, citations=[],
    )
    with patch.object(mod, "_tavily_search", return_value=[]), \
         patch.object(llm, "call_anthropic", return_value=fake_resp) as anth:
        result = mod.run(_args({"ANTHROPIC_API_KEY": "sk-x", "TAVILY_API_KEY": "tvly-x"}))
    assert anth.called
    assert result.score is not None
