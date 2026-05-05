"""Tests for brand-mentions module — wired with mocked LLM clients."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from geo_audit import llm
from geo_audit.modules import brand_mentions as mod
from geo_audit.modules.base import ModuleArgs


def _args(html: str = "<html><head><title>Acme — modern stuff</title></head><body>Acme builds modern observability for cloud apps. Contact us.</body></html>",
          url: str = "https://acme.io/", api_keys: dict | None = None) -> ModuleArgs:
    return ModuleArgs(
        url=url, homepage_html=html, homepage_status=200,
        api_keys=api_keys or {},
    )


def test_skipped_with_no_keys():
    result = mod.run(_args())
    assert result.score is None
    assert result.ran_in_degraded_mode is True
    assert "ANTHROPIC_API_KEY" in result.missing_keys


def test_extract_brand_from_title():
    html = "<title>Acme — observability platform</title>"
    brand, domain = mod._extract_brand_from_html(html, "https://acme.io/")
    assert brand == "Acme"
    assert domain == "acme.io"


def test_extract_brand_from_og_site_name():
    html = '<meta property="og:site_name" content="Acme Corp">'
    brand, _ = mod._extract_brand_from_html(html, "https://acme.io/")
    assert brand == "Acme Corp"


def test_extract_brand_fallback_to_domain():
    brand, domain = mod._extract_brand_from_html("", "https://example.com/")
    assert brand == "Example"
    assert domain == "example.com"


def test_grade_strong_response():
    response = "Acme is a cloud observability vendor. They build modern observability tooling. See https://acme.io/about."
    homepage = "acme builds modern observability for cloud apps"
    score, b = mod._grade_response(response, ["https://acme.io/docs"], "Acme", "acme.io", homepage)
    assert score >= 80, b


def test_grade_no_brand_no_citation():
    response = "I am not aware of any company by that name."
    score, b = mod._grade_response(response, [], "Acme", "acme.io", "acme builds")
    assert score == 0
    assert b["brand_appears"] is False
    assert b["domain_cited"] is False


def test_brand_mentions_runs_with_anthropic_key():
    """Mock anthropic client and verify scoring loop."""
    fake_resp = llm.LLMResponse(
        provider="anthropic", model="claude-3-5-haiku-latest",
        content="Acme is a modern observability vendor. acme.io provides cloud monitoring.",
        tokens_in=120, tokens_out=80, cost_usd=0.0001, duration_ms=50, citations=[],
    )
    with patch.object(llm, "call_anthropic", return_value=fake_resp) as m:
        result = mod.run(_args(api_keys={"ANTHROPIC_API_KEY": "sk-test"}))
    assert m.called
    assert result.score is not None
    assert "Claude" in result.sub_scores["providers_called"]
    assert result.sub_scores["per_provider"]["Claude"]["score"] is not None


def test_brand_mentions_failures_dont_block_others():
    import httpx as _httpx

    def _bad_anthropic(*a, **kw):
        raise _httpx.HTTPError("simulated")

    fake_openai = llm.LLMResponse(
        provider="openai", model="gpt-4o-mini",
        content="Acme is a modern observability platform built for cloud applications.",
        tokens_in=120, tokens_out=80, cost_usd=0.0001, duration_ms=50, citations=[],
    )
    with patch.object(llm, "call_anthropic", side_effect=_bad_anthropic), \
         patch.object(llm, "call_openai", return_value=fake_openai):
        result = mod.run(_args(api_keys={
            "ANTHROPIC_API_KEY": "sk-test",
            "OPENAI_API_KEY": "sk-test",
        }))
    # OpenAI scored; Anthropic failed — composite from OpenAI only.
    assert result.score is not None
    assert "ChatGPT" in result.sub_scores["providers_called"]
    assert "Claude" in result.sub_scores["providers_failed"]
    # Estimated cost should still be reported.
    assert result.sub_scores["estimated_cost_usd"] >= 0
