"""Configuration: load .env, detect API keys, build key-module matrix.

The user's .env is the only source of truth for API keys at runtime.
This module never writes keys back to disk and never logs key values.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# Canonical env var names. Documented in .env.example and TRUST.md.
KEY_ENV_VARS = [
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "PAGESPEED_API_KEY",
    "PERPLEXITY_API_KEY",
    "GEMINI_API_KEY",
    "TAVILY_API_KEY",
    "SERPER_API_KEY",
    "SEARXNG_BASE_URL",
    "YANDEX_XML_USER",
    "YANDEX_XML_KEY",
    "ORIGINALITY_API_KEY",
    "GPTZERO_API_KEY",
]


# Per-key human description: what registering it unlocks.
KEY_HINTS = {
    "ANTHROPIC_API_KEY": {
        "what": "LLM-graded citability + content E-E-A-T scoring + Claude brand-mention scan",
        "register": "https://console.anthropic.com/settings/keys",
        "free_tier": "no — paid only ($5 minimum), but Haiku is ~$0.001 per audit",
    },
    "OPENAI_API_KEY": {
        "what": "LLM-graded citability + content E-E-A-T scoring + ChatGPT brand-mention scan",
        "register": "https://platform.openai.com/api-keys",
        "free_tier": "no — paid only, but gpt-4o-mini is ~$0.001 per audit",
    },
    "PAGESPEED_API_KEY": {
        "what": "Full Core Web Vitals (LCP, INP, CLS) via PageSpeed Insights",
        "register": "https://developers.google.com/speed/docs/insights/v5/get-started",
        "free_tier": "yes — 25k requests/day free",
    },
    "TAVILY_API_KEY": {
        "what": "LLM-friendly web search for brand-mention grounding",
        "register": "https://tavily.com",
        "free_tier": "yes — 1,000 searches/month free",
    },
    "SERPER_API_KEY": {
        "what": "Google SERP fetcher (alternative to SearXNG)",
        "register": "https://serper.dev",
        "free_tier": "yes — 2,500 queries free, then paid",
    },
    "SEARXNG_BASE_URL": {
        "what": "Self-hosted SearXNG endpoint for SERP queries (no auth)",
        "register": "https://docs.searxng.org/admin/installation.html",
        "free_tier": "self-hosted",
    },
    "PERPLEXITY_API_KEY": {
        "what": "Live brand-mention scan in Perplexity AI search results",
        "register": "https://www.perplexity.ai/settings/api",
        "free_tier": "yes — $5 free credits on signup",
    },
    "GEMINI_API_KEY": {
        "what": "Brand-mention scan via Google Gemini (proxy for AI Overviews readiness)",
        "register": "https://ai.google.dev/gemini-api/docs/api-key",
        "free_tier": "yes — generous free tier",
    },
    "YANDEX_XML_USER": {
        "what": "Russian-market AI search visibility (Yandex Neuro proxy via Yandex.XML)",
        "register": "https://xml.yandex.ru/",
        "free_tier": "yes — limited daily quota",
        "pair_with": "YANDEX_XML_KEY",
    },
    "YANDEX_XML_KEY": {
        "what": "(paired with YANDEX_XML_USER) Russian-market AI search visibility",
        "register": "https://xml.yandex.ru/",
        "free_tier": "yes — limited daily quota",
        "pair_with": "YANDEX_XML_USER",
    },
    "ORIGINALITY_API_KEY": {
        "what": "Paid AI-content detection (alternative to local heuristic / Binoculars)",
        "register": "https://originality.ai/",
        "free_tier": "no — pay-per-scan",
    },
    "GPTZERO_API_KEY": {
        "what": "Paid AI-content detection (alternative to local heuristic / Binoculars)",
        "register": "https://gptzero.me/",
        "free_tier": "yes — limited monthly quota",
    },
}


# Module → required keys map. Every key here is OPTIONAL: missing → graceful degrade.
MODULE_KEY_MATRIX: dict[str, dict[str, list[str]]] = {
    "citability":    {"required": [],                                            "optional_any_of": ["ANTHROPIC_API_KEY", "OPENAI_API_KEY"]},
    "schema":        {"required": [],                                            "optional_any_of": []},
    "llmstxt":       {"required": [],                                            "optional_any_of": []},
    "crawlers":      {"required": [],                                            "optional_any_of": []},
    "technical":     {"required": [],                                            "optional_any_of": ["PAGESPEED_API_KEY"]},
    "content":       {"required": [],                                            "optional_any_of": ["ANTHROPIC_API_KEY", "OPENAI_API_KEY"]},
    "brand-mentions":{"required": [],                                            "optional_any_of": ["ANTHROPIC_API_KEY", "OPENAI_API_KEY", "PERPLEXITY_API_KEY", "GEMINI_API_KEY", "YANDEX_XML_USER"]},
}


@dataclass
class Config:
    api_keys: dict[str, Optional[str]] = field(default_factory=dict)
    user_agent: str = "geo-audit/0.2 (+https://github.com/g-shevchenko/geo-audit)"
    cache_dir: Path = field(default_factory=lambda: Path.home() / ".cache" / "geo-audit")
    timeout_s: int = 30

    def has_any(self, keys: list[str]) -> bool:
        """True if at least one of the listed keys is present (non-empty)."""
        return any(self.api_keys.get(k) for k in keys)

    def has_all(self, keys: list[str]) -> bool:
        return all(self.api_keys.get(k) for k in keys)

    def keys_present(self) -> list[str]:
        return [k for k, v in self.api_keys.items() if v]

    def keys_missing(self) -> list[str]:
        return [k for k in KEY_ENV_VARS if not self.api_keys.get(k)]


def load_dotenv(path: Optional[Path] = None) -> dict[str, str]:
    """Lightweight .env loader. No third-party dep.

    Reads KEY=VALUE lines. Ignores lines starting with #. Strips quotes.
    Does not perform variable expansion.
    """
    if path is None:
        path = Path.cwd() / ".env"
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if k:
            out[k] = v
    return out


def load_config(env_path: Optional[Path] = None) -> Config:
    """Build Config from .env (if present) overlaid with os.environ.

    os.environ wins — explicit shell exports override .env.
    """
    cfg = Config()
    file_env = load_dotenv(env_path)
    for k in KEY_ENV_VARS:
        # os.environ first; fall back to .env.
        cfg.api_keys[k] = os.environ.get(k) or file_env.get(k) or None
    # Allow override of cache dir via env.
    if cache := os.environ.get("GEO_AUDIT_CACHE_DIR"):
        cfg.cache_dir = Path(cache)
    return cfg
