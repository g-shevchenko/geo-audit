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
    "FIRECRAWL_API_KEY",
    "TAVILY_API_KEY",
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
    "FIRECRAWL_API_KEY": {
        "what": "Auto-fallback fetcher for Cloudflare-protected / JS-heavy / geo-blocked sites — without it, ~30% of targets return empty HTML",
        "register": "https://www.firecrawl.dev/app/api-keys",
        "free_tier": "yes — 500 requests/month free",
    },
    "TAVILY_API_KEY": {
        "what": "Grounds Claude / ChatGPT / Gemini brand-mention queries with live web search results — significantly improves brand-mentions accuracy for non-Perplexity providers",
        "register": "https://app.tavily.com/home",
        "free_tier": "yes — 1,000 searches/month free",
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
}


# Module → required keys map. Every key here is OPTIONAL: missing → graceful degrade.
MODULE_KEY_MATRIX: dict[str, dict[str, list[str]]] = {
    "site-crawl-lite": {"required": [], "optional_any_of": []},
    "head-schema-gate": {"required": [], "optional_any_of": []},
    "citability":    {"required": [], "optional_any_of": []},
    "schema":        {"required": [], "optional_any_of": []},
    "llmstxt":       {"required": [], "optional_any_of": []},
    "crawlers":      {"required": [], "optional_any_of": []},
    "technical":     {"required": [], "optional_any_of": ["PAGESPEED_API_KEY"]},
    "content":       {"required": [], "optional_any_of": []},
    "brand-mentions":{"required": [], "optional_any_of": ["ANTHROPIC_API_KEY", "OPENAI_API_KEY", "PERPLEXITY_API_KEY", "GEMINI_API_KEY"]},
}


# Cross-cutting helpers that improve any module by being available.
# Listed separately so `doctor` can suggest them as universal upgrades.
CROSS_CUTTING_KEYS = {
    "FIRECRAWL_API_KEY": "Better fetcher (Cloudflare / SPA / geo-blocked sites)",
    "TAVILY_API_KEY":    "Better brand-mention grounding (improves Claude/ChatGPT/Gemini accuracy)",
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
