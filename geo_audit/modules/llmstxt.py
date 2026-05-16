"""Module: llmstxt — /llms.txt + AI-bot access scoring.

Scoring per docs/methodology.md#llmstxt. Fully offline (probes via crawler).
"""
from __future__ import annotations

import re
import time
import urllib.parse

from geo_audit.crawler import fetch
from geo_audit.modules.base import Finding, ModuleArgs, ModuleResult

NAME = "llmstxt"
WEIGHT = 10
REQUIRES_API_KEYS: list[str] = []
DESCRIPTION = "/llms.txt detection + AI-bot access in robots.txt."

# llms.txt is an inference-time content index, NOT a ranking signal. No
# major AI engine officially consumes a third-party llms.txt for answer
# generation and Google has publicly stated it does not use it. This
# module scores presence/conformance as a controlled-narrative + AI-
# readiness signal — never as predicted ranking/visibility uplift.
DOC_URL = "https://github.com/g-shevchenko/geo-audit/blob/main/docs/llmstxt-conformance.md"


# Subscores: 50 + 30 + 20 = 100
SUB_WEIGHTS = {
    "llms_txt_present_valid":   50,
    "llms_full_txt_present":    30,
    "ai_bots_allowed_in_robots":20,
}

AI_BOTS = ["GPTBot", "ClaudeBot", "PerplexityBot", "Google-Extended", "anthropic-ai", "ChatGPT-User"]


def _is_valid_llms_txt(text: str) -> bool:
    """Structural validity per the llmstxt.org spec.

    Per the spec the **H1 is the only required element**; a blockquote
    summary and ``## `` sections are recommended quality, not validity
    gates. We therefore treat a non-trivial document with an H1 as
    structurally valid and surface a missing summary/sections as quality
    findings rather than failing the file outright. (Earlier versions
    incorrectly also required an H2 or a link line.)
    """
    if not text or len(text.strip()) < 20:
        return False
    return bool(re.search(r"^# .+", text, re.MULTILINE))


def _bot_allowed_in_robots(robots: str, bot: str) -> bool:
    """Returns True if bot is NOT explicitly disallowed.

    Default-allow: if no User-agent: bot stanza, allow.
    Explicit allow: if User-agent: bot has Allow: / and no Disallow: /.
    Block: if Disallow: / under matching stanza.
    Wildcard Disallow: / under * also blocks bot unless bot has its own Allow.
    """
    if not robots:
        return True

    # Find all stanzas (User-agent: X / rules / blank line groups).
    lines = [ln.strip() for ln in robots.splitlines()]
    stanzas: list[tuple[list[str], list[tuple[str, str]]]] = []
    cur_agents: list[str] = []
    cur_rules: list[tuple[str, str]] = []
    for line in lines + [""]:
        if not line or line.startswith("#"):
            if cur_agents and cur_rules:
                stanzas.append((cur_agents[:], cur_rules[:]))
                cur_agents.clear()
                cur_rules.clear()
            continue
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        k = k.strip().lower()
        v = v.strip()
        if k == "user-agent":
            if cur_rules:
                stanzas.append((cur_agents[:], cur_rules[:]))
                cur_agents.clear()
                cur_rules.clear()
            cur_agents.append(v)
        elif k in ("allow", "disallow"):
            cur_rules.append((k, v))

    bot_lower = bot.lower()
    matching = [(agents, rules) for agents, rules in stanzas if any(a.lower() == bot_lower for a in agents)]
    if matching:
        # Bot has explicit stanza. Check disallows.
        for _, rules in matching:
            for k, v in rules:
                if k == "disallow" and v == "/":
                    return False
        return True
    # No explicit bot stanza — fall back to *.
    for agents, rules in stanzas:
        if "*" in agents:
            for k, v in rules:
                if k == "disallow" and v == "/":
                    return False
    return True


def run(args: ModuleArgs) -> ModuleResult:
    t0 = time.time()
    findings: list[Finding] = []
    actions: list[Finding] = []
    sub_scores: dict[str, int] = {k: 0 for k in SUB_WEIGHTS}

    parsed = urllib.parse.urlparse(args.url)
    base = f"{parsed.scheme}://{parsed.netloc}"

    # 1. /llms.txt present + valid
    r1 = fetch(f"{base}/llms.txt", user_agent=args.user_agent, timeout_s=args.timeout_s,
               cache_dir=args.cache_dir, no_cache=args.no_cache)
    has_llms = r1.status == 200 and _is_valid_llms_txt(r1.text)
    if has_llms:
        sub_scores["llms_txt_present_valid"] = SUB_WEIGHTS["llms_txt_present_valid"]
        findings.append(Finding("P3", "/llms.txt present and valid", f"{base}/llms.txt → 200, {len(r1.text)} bytes"))
    else:
        actions.append(Finding(
            "P2",
            "Publish /llms.txt — controlled-narrative + citability asset (not a ranking factor)",
            f"{base}/llms.txt → {r1.status or 'fetch error'}",
            DOC_URL,
        ))

    # 2. /llms-full.txt present
    r2 = fetch(f"{base}/llms-full.txt", user_agent=args.user_agent, timeout_s=args.timeout_s,
               cache_dir=args.cache_dir, no_cache=args.no_cache)
    has_full = r2.status == 200 and len(r2.text.strip()) >= 1000  # at least 1KB content
    if has_full:
        sub_scores["llms_full_txt_present"] = SUB_WEIGHTS["llms_full_txt_present"]
        findings.append(Finding("P3", "/llms-full.txt present", f"{base}/llms-full.txt → 200, {len(r2.text)} bytes"))
    else:
        actions.append(Finding(
            "P3",
            "Optional: /llms-full.txt (community convention — NOT part of the llms.txt spec)",
            f"{base}/llms-full.txt → {r2.status or 'fetch error'}",
            DOC_URL,
        ))

    # 2b. Markdown page mirrors (llmstxt.org spec proposal 2) — informational
    # only, no score weight. Spec: fileless URLs append index.html.md.
    try:
        rmd = fetch(f"{base}/index.html.md", user_agent=args.user_agent,
                    timeout_s=args.timeout_s, cache_dir=args.cache_dir,
                    no_cache=args.no_cache)
        md_ok = rmd.status == 200 and len(rmd.text.strip()) >= 50
    except Exception:
        rmd, md_ok = None, False
    if md_ok:
        findings.append(Finding(
            "P3", "Markdown page mirror detected (llms.txt spec proposal 2)",
            f"{base}/index.html.md → 200, {len(rmd.text)} bytes", DOC_URL))
    else:
        actions.append(Finding(
            "P3",
            "Consider Markdown page mirrors: <url>.md (llms.txt spec proposal 2, rarely implemented)",
            f"{base}/index.html.md → {(rmd.status if rmd else 'fetch error')}",
            DOC_URL))

    # 3. AI bots allowed in robots.txt
    robots = args.robots_txt or ""
    blocked_bots: list[str] = []
    allowed_bots: list[str] = []
    for bot in AI_BOTS:
        if _bot_allowed_in_robots(robots, bot):
            allowed_bots.append(bot)
        else:
            blocked_bots.append(bot)
    if not blocked_bots:
        sub_scores["ai_bots_allowed_in_robots"] = SUB_WEIGHTS["ai_bots_allowed_in_robots"]
        findings.append(Finding("P3", "All known AI bots allowed", f"Allowed: {', '.join(allowed_bots)}"))
    else:
        # Penalty proportional to blocked count.
        ratio = (len(AI_BOTS) - len(blocked_bots)) / len(AI_BOTS)
        sub_scores["ai_bots_allowed_in_robots"] = int(SUB_WEIGHTS["ai_bots_allowed_in_robots"] * ratio)
        actions.append(Finding(
            "P0", f"Unblock AI bots: {', '.join(blocked_bots)}",
            f"robots.txt has Disallow: / for {', '.join(blocked_bots)}",
            "https://platform.openai.com/docs/gptbot",
        ))

    findings.append(Finding(
        "P3",
        "Note: llms.txt is not a ranking signal",
        "No major AI engine officially consumes a third-party llms.txt for "
        "answers; Google has stated it does not use it. Value is "
        "controlled-narrative + AI-readiness at inference time, not "
        "ranking/visibility uplift.",
        DOC_URL,
    ))

    score = sum(sub_scores.values())
    duration = int((time.time() - t0) * 1000)

    return ModuleResult(
        name=NAME,
        score=score,
        findings=findings,
        actions=actions,
        duration_ms=duration,
        sub_scores={
            **sub_scores,
            "llms_txt_status": r1.status,
            "llms_full_txt_status": r2.status,
            "md_page_mirror_status": (rmd.status if rmd else None),
            "ai_bots_blocked": blocked_bots,
            "ai_bots_allowed": allowed_bots,
        },
    )
