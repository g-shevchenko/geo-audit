"""Module: ai-search-technical — Google AI technical eligibility gate.

Public-safe deterministic checks only. This module does not bypass WAFs,
execute JS, or call private crawler infrastructure. It turns the technical
parts of Google's AI optimization guidance into an explicit page-level gate.
"""
from __future__ import annotations

import re
import time

from geo_audit.modules.base import Finding, ModuleArgs, ModuleResult
from geo_audit.modules.llmstxt import _bot_allowed_in_robots

NAME = "ai-search-technical"
WEIGHT = 0
REQUIRES_API_KEYS: list[str] = []
DESCRIPTION = "Google AI technical eligibility gate: crawlers, noindex, parseable HTML, sitemap."

GOOGLE_AI_GUIDE = "https://developers.google.com/search/docs/fundamentals/ai-optimization-guide"
GOOGLE_ROBOTS = "https://developers.google.com/search/docs/crawling-indexing/robots/intro"
GOOGLE_JS_SEO = "https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics"
OPENAI_BOTS = "https://developers.openai.com/api/docs/bots"
ANTHROPIC_BOTS = "https://support.claude.com/en/articles/8896518-does-anthropic-crawl-data-from-the-web-and-how-can-site-owners-block-the-crawler"
PERPLEXITY_BOTS = "https://docs.perplexity.ai/docs/resources/perplexity-crawlers"
BING_GUIDELINES = "https://www.bing.com/webmasters/help/bing-webmaster-guidelines-30fba23a"

CRAWLER_REFS = {
    "Googlebot": ("P0", GOOGLE_ROBOTS),
    "Bingbot": ("P1", BING_GUIDELINES),
    "OAI-SearchBot": ("P1", OPENAI_BOTS),
    "Claude-SearchBot": ("P1", ANTHROPIC_BOTS),
    "ClaudeBot": ("P2", ANTHROPIC_BOTS),
    "PerplexityBot": ("P1", PERPLEXITY_BOTS),
}


def _visible_text_chars(html: str) -> int:
    text = re.sub(
        r"<script\b[^>]*>.*?</script>|<style\b[^>]*>.*?</style>",
        "",
        html or "",
        flags=re.DOTALL | re.IGNORECASE,
    )
    text = re.sub(r"<[^>]+>", " ", text)
    return len(re.sub(r"\s+", " ", text).strip())


def _has_noindex(html: str, headers: dict[str, str]) -> bool:
    x_robots = " ".join(
        str(v) for k, v in headers.items() if k.lower() == "x-robots-tag"
    ).lower()
    if "noindex" in x_robots:
        return True
    return bool(re.search(
        r"<meta[^>]+name=[\"']robots[\"'][^>]+content=[\"'][^\"']*noindex",
        html or "",
        re.IGNORECASE,
    ))


def _has_canonical(html: str) -> bool:
    return bool(re.search(
        r"<link[^>]+rel=[\"']canonical[\"'][^>]+href=[\"'][^\"']+",
        html or "",
        re.IGNORECASE,
    ))


def _score(actions: list[Finding], findings: list[Finding]) -> int:
    penalties = {"P0": 35, "P1": 15, "P2": 7, "P3": 0}
    score = 100 - sum(penalties.get(a.priority, 0) for a in actions)
    if not findings:
        score -= 5
    return max(0, min(100, score))


def _gate_verdict(actions: list[Finding]) -> str:
    if any(a.priority == "P0" for a in actions):
        return "fail"
    if any(a.priority in ("P1", "P2") for a in actions):
        return "warn"
    return "pass"


def run(args: ModuleArgs) -> ModuleResult:
    t0 = time.time()
    html = args.homepage_html or ""
    headers = args.homepage_headers or {}
    robots = args.robots_txt or ""
    findings: list[Finding] = []
    actions: list[Finding] = []
    blocked: list[str] = []

    if _has_noindex(html, headers):
        actions.append(Finding(
            "P0",
            "Remove noindex before expecting Google AI visibility",
            "Homepage has meta robots or X-Robots-Tag noindex.",
            GOOGLE_AI_GUIDE,
        ))
    else:
        findings.append(Finding("P3", "No noindex detected", "Homepage is not explicitly noindexed."))

    for bot, (priority, ref) in CRAWLER_REFS.items():
        allowed = _bot_allowed_in_robots(robots, bot)
        if allowed:
            findings.append(Finding("P3", f"{bot} allowed", "robots.txt does not block this crawler."))
        else:
            blocked.append(bot)
            actions.append(Finding(
                priority, f"Allow {bot} when AI search visibility is intended",
                f"robots.txt blocks {bot}.",
                ref,
            ))

    visible_chars = _visible_text_chars(html)
    main_content_parseable = visible_chars >= 300
    if visible_chars >= 1000:
        findings.append(Finding(
            "P3", "Main content is present in initial HTML",
            f"~{visible_chars} visible chars without executing JavaScript.",
            GOOGLE_JS_SEO,
        ))
    elif visible_chars >= 300:
        actions.append(Finding(
            "P1", "Increase main content available in initial HTML",
            f"Only ~{visible_chars} visible chars; page may be too CSR-heavy.",
            GOOGLE_JS_SEO,
        ))
    else:
        actions.append(Finding(
            "P0", "Expose main content in initial HTML",
            f"Only ~{visible_chars} visible chars without JavaScript.",
            GOOGLE_JS_SEO,
        ))

    if _has_canonical(html):
        findings.append(Finding("P3", "Canonical link present", "Homepage HTML includes rel=canonical."))
    else:
        actions.append(Finding(
            "P1", "Add canonical link",
            "No rel=canonical found in homepage HTML.",
            GOOGLE_AI_GUIDE,
        ))

    if args.sitemap_urls:
        findings.append(Finding(
            "P3", "Sitemap discovered",
            f"{len(args.sitemap_urls)} URL(s) found via sitemap discovery.",
        ))
    else:
        actions.append(Finding(
            "P1", "Publish and reference a sitemap",
            "No sitemap URLs found via robots.txt or common sitemap paths.",
            "https://www.sitemaps.org/protocol.html",
        ))

    score = _score(actions, findings)
    verdict = _gate_verdict(actions)
    return ModuleResult(
        name=NAME,
        score=score,
        findings=findings,
        actions=actions,
        duration_ms=int((time.time() - t0) * 1000),
        sub_scores={
            "gate_verdict": verdict,
            "blocked_crawlers": blocked,
            "main_content_parseable": main_content_parseable,
            "visible_text_chars": visible_chars,
            "noindex_detected": _has_noindex(html, headers),
            "canonical_present": _has_canonical(html),
            "sitemap_present": bool(args.sitemap_urls),
            "playbook_source": GOOGLE_AI_GUIDE,
            "scope": "public_generic_technical_gate",
        },
    )
