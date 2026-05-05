"""Orchestrator — runs modules in order, aggregates results.

Crawls homepage, sitemap, robots.txt once and shares with all modules.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from geo_audit import __version__, __methodology_version__
from geo_audit.config import Config, load_config
from geo_audit.crawler import fetch, fetch_robots, fetch_sitemap_urls, normalize_url
from geo_audit.modules.base import ModuleArgs, ModuleResult
from geo_audit.modules import registry
from geo_audit.scoring import compute_composite, CompositeScore, WEIGHTS


@dataclass
class AuditReport:
    url: str
    geo_audit_version: str
    methodology_version: str
    started_at: str
    duration_ms: int
    composite: CompositeScore
    modules: list[ModuleResult]
    config_summary: dict[str, object] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "geo_audit_version": self.geo_audit_version,
            "methodology_version": self.methodology_version,
            "started_at": self.started_at,
            "duration_ms": self.duration_ms,
            "composite_score": self.composite.score,
            "modules_used": self.composite.modules_used,
            "modules_skipped": self.composite.modules_skipped,
            "weights": self.composite.weights_used,
            "modules": [m.to_dict() for m in self.modules],
            "config": self.config_summary,
        }


def run_audit(
    url: str,
    *,
    config: Optional[Config] = None,
    modules: Optional[list[str]] = None,
    depth: str = "full",
    lang: Optional[str] = None,
    no_cache: bool = False,
) -> AuditReport:
    """Run a full audit. Returns AuditReport with all module results.

    modules=None → run default DEFAULT_ORDER. Pass list to restrict.
    """
    cfg = config or load_config()
    url = normalize_url(url)
    started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    t0 = time.time()

    cfg.cache_dir.mkdir(parents=True, exist_ok=True)

    # 1. Crawl shared artifacts.
    homepage = fetch(url, user_agent=cfg.user_agent, timeout_s=cfg.timeout_s,
                     cache_dir=cfg.cache_dir, no_cache=no_cache)
    robots_txt = fetch_robots(homepage.final_url, user_agent=cfg.user_agent,
                              timeout_s=10, cache_dir=cfg.cache_dir, no_cache=no_cache)
    sitemap_urls = fetch_sitemap_urls(homepage.final_url, user_agent=cfg.user_agent,
                                      robots_txt=robots_txt, max_urls=50,
                                      cache_dir=cfg.cache_dir, no_cache=no_cache) if depth == "full" else []

    # 2. Build ModuleArgs once; modules can read shared state.
    base_args = ModuleArgs(
        url=url,
        depth=depth,  # type: ignore[arg-type]
        cache_dir=cfg.cache_dir,
        timeout_s=cfg.timeout_s,
        user_agent=cfg.user_agent,
        api_keys=cfg.api_keys,
        lang=lang,
        no_cache=no_cache,
        homepage_html=homepage.text,
        homepage_status=homepage.status,
        homepage_headers=homepage.headers,
        homepage_url_final=homepage.final_url,
        sitemap_urls=sitemap_urls,
        robots_txt=robots_txt,
    )

    # 3. Run modules.
    if modules is None:
        mods_to_run = registry.list_modules()
    else:
        mods_to_run = [registry.get(n) for n in modules if registry.get(n)]

    results: list[ModuleResult] = []
    for mod in mods_to_run:
        if mod is None:
            continue
        try:
            r = mod.run(base_args)
        except Exception as e:
            r = ModuleResult(
                name=mod.NAME,
                score=None,
                ran_in_degraded_mode=True,
                skip_reason=f"module raised exception: {type(e).__name__}: {str(e)[:200]}",
            )
        results.append(r)

    composite = compute_composite(results, methodology_version=__methodology_version__)
    duration_ms = int((time.time() - t0) * 1000)

    config_summary = {
        "user_agent": cfg.user_agent,
        "cache_dir": str(cfg.cache_dir),
        "timeout_s": cfg.timeout_s,
        "keys_present": cfg.keys_present(),
        "homepage_status": homepage.status,
        "homepage_final_url": homepage.final_url,
        "homepage_from_cache": homepage.from_cache,
        "sitemap_url_count": len(sitemap_urls),
        "robots_present": bool(robots_txt),
    }

    return AuditReport(
        url=url,
        geo_audit_version=__version__,
        methodology_version=__methodology_version__,
        started_at=started,
        duration_ms=duration_ms,
        composite=composite,
        modules=results,
        config_summary=config_summary,
    )
