"""Module: crawlers — robots.txt + AI-bot access map.

Pure observability: lists which crawlers can/cannot access the site.
Does NOT contribute to the composite score (informational module).
The llmstxt module owns the AI-bot scoring sub-check.
"""
from __future__ import annotations

import time

from geo_audit.modules.base import Finding, ModuleArgs, ModuleResult
from geo_audit.modules.llmstxt import _bot_allowed_in_robots

NAME = "crawlers"
WEIGHT = 0  # informational only — not in composite
REQUIRES_API_KEYS: list[str] = []
DESCRIPTION = "robots.txt parser + AI/search/social bot access map."

CRAWLERS = {
    "AI assistants": [
        "GPTBot", "ChatGPT-User", "OAI-SearchBot", "anthropic-ai",
        "ClaudeBot", "Claude-SearchBot", "PerplexityBot",
        "Google-Extended", "Applebot-Extended",
        "Bytespider", "Yandex-Neuro",
    ],
    "Search engines": [
        "Googlebot", "Bingbot", "YandexBot", "DuckDuckBot", "Baiduspider",
    ],
    "Social previews": [
        "facebookexternalhit", "Twitterbot", "LinkedInBot",
        "Slackbot", "TelegramBot", "WhatsApp",
    ],
}


def run(args: ModuleArgs) -> ModuleResult:
    t0 = time.time()
    findings: list[Finding] = []
    actions: list[Finding] = []
    robots = args.robots_txt or ""

    has_robots = bool(robots)
    if not has_robots:
        findings.append(Finding(
            "P3", "No robots.txt found",
            "All crawlers default-allowed. Consider adding robots.txt for explicit control.",
        ))

    access_map: dict[str, dict[str, bool]] = {}
    blocked_summary: list[str] = []

    for category, bots in CRAWLERS.items():
        access_map[category] = {}
        for bot in bots:
            allowed = _bot_allowed_in_robots(robots, bot)
            access_map[category][bot] = allowed
            if not allowed and category == "AI assistants":
                blocked_summary.append(bot)

    if blocked_summary:
        actions.append(Finding(
            "P0", f"AI assistants blocked: {', '.join(blocked_summary)}",
            f"robots.txt blocks {len(blocked_summary)} AI bot(s) — they cannot index your content for citation",
            "https://llmstxt.org/",
        ))

    findings.append(Finding(
        "P3", "Bot access map computed",
        f"AI: {sum(1 for v in access_map['AI assistants'].values() if v)}/{len(CRAWLERS['AI assistants'])} allowed | "
        f"Search: {sum(1 for v in access_map['Search engines'].values() if v)}/{len(CRAWLERS['Search engines'])} allowed | "
        f"Social: {sum(1 for v in access_map['Social previews'].values() if v)}/{len(CRAWLERS['Social previews'])} allowed",
    ))

    return ModuleResult(
        name=NAME,
        score=None,  # informational, no score
        findings=findings,
        actions=actions,
        duration_ms=int((time.time() - t0) * 1000),
        sub_scores={"access_map": access_map, "robots_present": has_robots},
    )
