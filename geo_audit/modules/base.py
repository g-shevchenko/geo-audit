"""Module contract for geo-audit modules.

Every module exposes:
- NAME, WEIGHT, REQUIRES_API_KEYS, DESCRIPTION
- run(args: ModuleArgs) -> ModuleResult

See docs/modules.md for the canonical contract.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Literal, Optional


@dataclass
class ModuleArgs:
    """Inputs handed to every module."""
    url: str
    depth: Literal["quick", "full"] = "full"
    cache_dir: Path = field(default_factory=lambda: Path.home() / ".cache" / "geo-audit")
    timeout_s: int = 30
    user_agent: str = "geo-audit/0.2 (+https://github.com/g-shevchenko/geo-audit)"
    api_keys: dict[str, Optional[str]] = field(default_factory=dict)
    lang: Optional[str] = None  # "en", "ru", or None for auto-detect
    no_cache: bool = False
    # crawled artifacts (set by orchestrator before module.run)
    homepage_html: Optional[str] = None
    homepage_status: Optional[int] = None
    homepage_headers: dict[str, str] = field(default_factory=dict)
    homepage_url_final: Optional[str] = None
    sitemap_urls: list[str] = field(default_factory=list)
    robots_txt: Optional[str] = None


@dataclass
class Finding:
    priority: Literal["P0", "P1", "P2", "P3"]
    title: str            # one-line, action-oriented
    evidence: str         # what we saw on the page
    fix_url: str = ""     # docs anchor or external ref

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass
class ModuleResult:
    name: str
    score: Optional[int]                    # 0–100, or None if degraded
    findings: list[Finding] = field(default_factory=list)
    actions: list[Finding] = field(default_factory=list)
    ran_in_degraded_mode: bool = False
    skip_reason: Optional[str] = None       # why score is None
    missing_keys: list[str] = field(default_factory=list)
    what_youd_get: Optional[str] = None     # hint shown when skipped
    duration_ms: int = 0
    sub_scores: dict[str, Any] = field(default_factory=dict)  # per-rubric breakdown

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


def skipped(name: str, missing_keys: list[str], what: str) -> ModuleResult:
    """Helper: build a degraded-mode result for missing keys."""
    return ModuleResult(
        name=name,
        score=None,
        ran_in_degraded_mode=True,
        skip_reason=f"missing required env vars: {', '.join(missing_keys)}",
        missing_keys=missing_keys,
        what_youd_get=what,
    )
