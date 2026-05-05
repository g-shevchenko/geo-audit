"""Provider-agnostic LLM client.

Calls Anthropic, OpenAI, Perplexity, Gemini via their public HTTP APIs.
Uses httpx (no provider SDK dependency, keeps the install slim).

Each call is sync and bounded by timeout. No streaming. Temperature=0
unless overridden — citability/brand-mention scoring should be reproducible.
"""
from __future__ import annotations

import json
import time
import urllib.parse
from dataclasses import dataclass
from typing import Optional

import httpx


@dataclass
class LLMResponse:
    provider: str            # "anthropic", "openai", "perplexity", "gemini"
    model: str
    content: str             # text response
    tokens_in: int
    tokens_out: int
    cost_usd: float          # estimated
    duration_ms: int
    citations: list[str]     # URLs cited (Perplexity only) — empty for others


# Per-million-token pricing (USD). Approximate, public list prices.
# These are NOT used to charge anything — only to print "estimated cost"
# transparency before the user confirms an audit.
PRICING = {
    "anthropic:claude-haiku-4-5":         {"in": 1.0,  "out": 5.0},   # placeholder for future
    "anthropic:claude-3-5-haiku-latest":  {"in": 0.80, "out": 4.0},
    "anthropic:claude-3-5-sonnet-latest": {"in": 3.0,  "out": 15.0},
    "openai:gpt-4o-mini":                 {"in": 0.15, "out": 0.60},
    "openai:gpt-4o":                      {"in": 2.50, "out": 10.0},
    "perplexity:sonar":                   {"in": 1.0,  "out": 1.0},
    "perplexity:sonar-pro":               {"in": 3.0,  "out": 15.0},
    "gemini:gemini-1.5-flash":            {"in": 0.075, "out": 0.30},
    "gemini:gemini-2.0-flash":            {"in": 0.10, "out": 0.40},
}


def _estimate_cost(provider: str, model: str, tokens_in: int, tokens_out: int) -> float:
    p = PRICING.get(f"{provider}:{model}")
    if p is None:
        return 0.0
    return (tokens_in / 1_000_000) * p["in"] + (tokens_out / 1_000_000) * p["out"]


# ============================================================================
# Anthropic
# ============================================================================

def call_anthropic(
    api_key: str,
    *,
    system: str,
    user: str,
    model: str = "claude-3-5-haiku-latest",
    max_tokens: int = 1024,
    timeout_s: int = 60,
) -> LLMResponse:
    t0 = time.time()
    body = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": 0.0,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    with httpx.Client(timeout=timeout_s) as client:
        r = client.post("https://api.anthropic.com/v1/messages", headers=headers, json=body)
        r.raise_for_status()
        data = r.json()
    text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
    usage = data.get("usage", {})
    tokens_in = int(usage.get("input_tokens", 0))
    tokens_out = int(usage.get("output_tokens", 0))
    return LLMResponse(
        provider="anthropic",
        model=model,
        content=text,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_usd=_estimate_cost("anthropic", model, tokens_in, tokens_out),
        duration_ms=int((time.time() - t0) * 1000),
        citations=[],
    )


# ============================================================================
# OpenAI
# ============================================================================

def call_openai(
    api_key: str,
    *,
    system: str,
    user: str,
    model: str = "gpt-4o-mini",
    max_tokens: int = 1024,
    timeout_s: int = 60,
) -> LLMResponse:
    t0 = time.time()
    body = {
        "model": model,
        "temperature": 0.0,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    with httpx.Client(timeout=timeout_s) as client:
        r = client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=body)
        r.raise_for_status()
        data = r.json()
    text = data["choices"][0]["message"]["content"]
    usage = data.get("usage", {})
    tokens_in = int(usage.get("prompt_tokens", 0))
    tokens_out = int(usage.get("completion_tokens", 0))
    return LLMResponse(
        provider="openai",
        model=model,
        content=text,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_usd=_estimate_cost("openai", model, tokens_in, tokens_out),
        duration_ms=int((time.time() - t0) * 1000),
        citations=[],
    )


# ============================================================================
# Perplexity (online model with citations)
# ============================================================================

def call_perplexity(
    api_key: str,
    *,
    system: str,
    user: str,
    model: str = "sonar",
    max_tokens: int = 1024,
    timeout_s: int = 60,
) -> LLMResponse:
    t0 = time.time()
    body = {
        "model": model,
        "temperature": 0.0,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    with httpx.Client(timeout=timeout_s) as client:
        r = client.post("https://api.perplexity.ai/chat/completions", headers=headers, json=body)
        r.raise_for_status()
        data = r.json()
    text = data["choices"][0]["message"]["content"]
    citations = data.get("citations", []) or []
    usage = data.get("usage", {})
    tokens_in = int(usage.get("prompt_tokens", 0))
    tokens_out = int(usage.get("completion_tokens", 0))
    return LLMResponse(
        provider="perplexity",
        model=model,
        content=text,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_usd=_estimate_cost("perplexity", model, tokens_in, tokens_out),
        duration_ms=int((time.time() - t0) * 1000),
        citations=list(citations),
    )


# ============================================================================
# Google Gemini
# ============================================================================

def call_gemini(
    api_key: str,
    *,
    system: str,
    user: str,
    model: str = "gemini-2.0-flash",
    max_tokens: int = 1024,
    timeout_s: int = 60,
) -> LLMResponse:
    t0 = time.time()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    body = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {"temperature": 0.0, "maxOutputTokens": max_tokens},
    }
    with httpx.Client(timeout=timeout_s) as client:
        r = client.post(url, json=body)
        r.raise_for_status()
        data = r.json()
    text = ""
    for cand in data.get("candidates", []):
        for part in cand.get("content", {}).get("parts", []):
            text += part.get("text", "")
    usage = data.get("usageMetadata", {})
    tokens_in = int(usage.get("promptTokenCount", 0))
    tokens_out = int(usage.get("candidatesTokenCount", 0))
    return LLMResponse(
        provider="gemini",
        model=model,
        content=text,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        cost_usd=_estimate_cost("gemini", model, tokens_in, tokens_out),
        duration_ms=int((time.time() - t0) * 1000),
        citations=[],
    )
