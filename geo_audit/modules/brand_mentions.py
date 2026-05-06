"""Module: brand-mentions — multi-platform brand visibility scan.

Per docs/methodology.md#brand-mentions:
  For each LLM provider with API access, query about the brand and count:
    - Brand appears by name (40)
    - URL/domain cited as source (40)
    - Description accurate (20 — heuristic match against homepage content)
  Final = average across providers that ran.

Each provider runs INDEPENDENTLY. Failures in one don't block others.
"""
from __future__ import annotations

import re
import time
import urllib.parse
from typing import Optional

import httpx

from geo_audit import llm
from geo_audit.modules.base import Finding, ModuleArgs, ModuleResult, skipped

NAME = "brand-mentions"
WEIGHT = 20
REQUIRES_API_KEYS: list[str] = []
DESCRIPTION = "Multi-platform brand mention scan (ChatGPT/Claude/Perplexity/Gemini)."

PROVIDERS = ["ANTHROPIC_API_KEY", "OPENAI_API_KEY", "PERPLEXITY_API_KEY", "GEMINI_API_KEY"]


def _tavily_search(api_key: str, query: str, *, timeout_s: int = 20, max_results: int = 5) -> list[dict]:
    """Call Tavily search API and return list of {title, url, content} dicts.

    Used to ground Claude/ChatGPT/Gemini brand-mention queries with live web
    search results (Perplexity has its own web search built-in, so we skip
    grounding for it).
    """
    body = {
        "api_key": api_key,
        "query": query,
        "max_results": max_results,
        "search_depth": "basic",
    }
    try:
        with httpx.Client(timeout=timeout_s) as client:
            r = client.post("https://api.tavily.com/search", json=body)
            r.raise_for_status()
            data = r.json()
    except (httpx.HTTPError, ValueError, KeyError):
        return []
    return [
        {
            "title": item.get("title", "")[:200],
            "url": item.get("url", ""),
            "content": item.get("content", "")[:500],
        }
        for item in data.get("results", [])[:max_results]
    ]


def _format_tavily_grounding(results: list[dict]) -> str:
    if not results:
        return ""
    lines = ["Here is recent live web search context (Tavily, used to ground your answer):"]
    for i, r in enumerate(results, 1):
        lines.append(f"[{i}] {r.get('title', '')}\n  URL: {r.get('url', '')}\n  Excerpt: {r.get('content', '')[:300]}")
    return "\n\n".join(lines)


def _extract_brand_from_html(html: str, url: str) -> tuple[str, str]:
    """Extract brand name and root domain. Brand from <title>/og:site_name; domain from URL."""
    parsed = urllib.parse.urlparse(url)
    netloc = parsed.netloc.lower()
    domain = ".".join(netloc.split(".")[-2:]) if "." in netloc else netloc

    # og:site_name
    m = re.search(r'<meta[^>]*property=["\']og:site_name["\'][^>]*content=["\']([^"\']+)', html, re.IGNORECASE)
    if m:
        return m.group(1).strip(), domain

    # <title>
    m = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
    if m:
        title = m.group(1).strip()
        # Clean: split on common separators, take first chunk.
        for sep in [" — ", " - ", " | ", " : ", " · "]:
            if sep in title:
                title = title.split(sep)[0].strip()
                break
        if title:
            return title, domain

    # Fallback: domain-derived.
    return domain.split(".")[0].title(), domain


def _build_query(brand: str, domain: str, lang: str = "en") -> str:
    if lang == "ru":
        return (f"Расскажи о компании {brand} ({domain}). "
                f"Что они делают, какая у них экспертиза, кто целевая аудитория, "
                f"какие источники ты использовал?")
    return (f"Tell me about {brand} ({domain}). What do they do, what's their expertise, "
            f"who is their audience, and what sources did you use?")


def _grade_response(text: str, citations: list[str], brand: str, domain: str,
                    homepage_text_lower: str) -> tuple[int, dict]:
    """Per provider, score 0–100.

    - Brand by name (40): brand string present in response
    - URL/domain cited (40): domain in citations OR in response text
    - Description heuristic-accurate (20): >=2 substantive words from homepage in response
    """
    text_lower = text.lower()
    brand_lower = brand.lower()
    domain_lower = domain.lower()

    by_name = 40 if (brand_lower and brand_lower in text_lower) else 0

    cited = 0
    if any(domain_lower in (c or "").lower() for c in citations):
        cited = 40
    elif domain_lower in text_lower:
        cited = 20  # mentioned but not in formal citations

    # Heuristic accuracy: count overlap of ≥6-letter words from homepage in response.
    homepage_words = set(re.findall(r"\b[a-zA-Zа-яА-ЯёЁ]{6,}\b", homepage_text_lower))
    response_words = set(re.findall(r"\b[a-zA-Zа-яА-ЯёЁ]{6,}\b", text_lower))
    overlap = len(homepage_words & response_words)
    if overlap >= 5:
        accurate = 20
    elif overlap >= 2:
        accurate = 10
    else:
        accurate = 0

    score = by_name + cited + accurate
    return score, {
        "brand_appears": bool(by_name),
        "domain_cited": bool(cited),
        "domain_cite_strength": cited,
        "homepage_word_overlap": overlap,
        "response_chars": len(text),
        "citations_count": len(citations),
    }


def _strip_html(html: str) -> str:
    text = re.sub(r"<script\b[^>]*>.*?</script>|<style\b[^>]*>.*?</style>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip().lower()


def run(args: ModuleArgs) -> ModuleResult:
    t0 = time.time()
    keys = args.api_keys
    active_providers: list[tuple[str, str]] = []  # (label, env_key)
    if keys.get("ANTHROPIC_API_KEY"):
        active_providers.append(("Claude", "ANTHROPIC_API_KEY"))
    if keys.get("OPENAI_API_KEY"):
        active_providers.append(("ChatGPT", "OPENAI_API_KEY"))
    if keys.get("PERPLEXITY_API_KEY"):
        active_providers.append(("Perplexity", "PERPLEXITY_API_KEY"))
    if keys.get("GEMINI_API_KEY"):
        active_providers.append(("Gemini", "GEMINI_API_KEY"))

    if not active_providers:
        return skipped(
            NAME,
            missing_keys=PROVIDERS,
            what="Add at least one of ANTHROPIC_API_KEY, OPENAI_API_KEY, PERPLEXITY_API_KEY, "
                 "or GEMINI_API_KEY → enables live brand-mention scan.",
        )

    html = args.homepage_html or ""
    brand, domain = _extract_brand_from_html(html, args.url)
    homepage_text = _strip_html(html)
    lang = args.lang or "en"
    if not lang or lang == "auto":
        lang = "ru" if len(re.findall(r"[А-Яа-яЁё]", html)) > len(re.findall(r"[A-Za-z]", html)) * 0.5 else "en"
    query = _build_query(brand, domain, lang)

    base_sys_prompt = ("You are an expert research assistant. Answer the user's question concisely. "
                       "If you don't know the company, say so explicitly. Always include 1-3 source URLs "
                       "if you can. Keep responses under 200 words.")

    # Optional Tavily grounding for non-Perplexity providers.
    tavily_key = keys.get("TAVILY_API_KEY")
    tavily_grounding = ""
    tavily_results: list[dict] = []
    if tavily_key:
        tavily_results = _tavily_search(tavily_key, f"{brand} {domain}", timeout_s=args.timeout_s)
        tavily_grounding = _format_tavily_grounding(tavily_results)

    per_provider: dict[str, dict] = {}
    findings: list[Finding] = []
    actions: list[Finding] = []
    failures: list[str] = []

    for label, env_key in active_providers:
        api_key = keys[env_key]
        # Perplexity has built-in web search — skip Tavily grounding for it.
        if env_key == "PERPLEXITY_API_KEY" or not tavily_grounding:
            sys_prompt = base_sys_prompt
        else:
            sys_prompt = base_sys_prompt + "\n\n" + tavily_grounding
        try:
            if env_key == "ANTHROPIC_API_KEY":
                resp = llm.call_anthropic(api_key, system=sys_prompt, user=query, max_tokens=400, timeout_s=args.timeout_s + 30)
            elif env_key == "OPENAI_API_KEY":
                resp = llm.call_openai(api_key, system=sys_prompt, user=query, max_tokens=400, timeout_s=args.timeout_s + 30)
            elif env_key == "PERPLEXITY_API_KEY":
                resp = llm.call_perplexity(api_key, system=sys_prompt, user=query, max_tokens=400, timeout_s=args.timeout_s + 30)
            elif env_key == "GEMINI_API_KEY":
                resp = llm.call_gemini(api_key, system=sys_prompt, user=query, max_tokens=400, timeout_s=args.timeout_s + 30)
            else:
                continue
        except (httpx.HTTPError, httpx.TimeoutException, KeyError, ValueError) as e:
            failures.append(f"{label}: {type(e).__name__}: {str(e)[:120]}")
            per_provider[label] = {"error": str(e)[:200], "score": None}
            continue

        score, breakdown = _grade_response(
            resp.content, resp.citations, brand, domain, homepage_text,
        )
        per_provider[label] = {
            "score": score,
            "model": resp.model,
            "tokens_in": resp.tokens_in,
            "tokens_out": resp.tokens_out,
            "cost_usd_est": round(resp.cost_usd, 6),
            "duration_ms": resp.duration_ms,
            **breakdown,
        }
        if score >= 80:
            findings.append(Finding("P3", f"{label}: strong brand mention ({score}/100)", f"brand_appears={breakdown['brand_appears']}, domain_cited={breakdown['domain_cited']}"))
        elif score >= 40:
            actions.append(Finding(
                "P2", f"{label}: weak brand mention ({score}/100)",
                f"brand_appears={breakdown['brand_appears']}, domain_cited={breakdown['domain_cited']} — "
                f"increase outbound presence (Wikipedia, GitHub, industry directories)",
            ))
        else:
            actions.append(Finding(
                "P1", f"{label}: brand not recognized ({score}/100)",
                f"Response mentioned brand: {breakdown['brand_appears']}; cited domain: {breakdown['domain_cited']}",
                "https://github.com/g-shevchenko/geo-audit/blob/main/docs/methodology.md#brand-mentions",
            ))

    scored = [v["score"] for v in per_provider.values() if v.get("score") is not None]
    composite = int(round(sum(scored) / len(scored))) if scored else None

    if failures:
        actions.append(Finding(
            "P2", f"{len(failures)} provider call(s) failed",
            "; ".join(failures[:3]),
        ))

    total_cost = round(sum(v.get("cost_usd_est", 0) for v in per_provider.values()), 6)

    return ModuleResult(
        name=NAME,
        score=composite if composite is not None else 0,
        findings=findings,
        actions=actions,
        ran_in_degraded_mode=composite is None,
        skip_reason=None if composite is not None else "all provider calls failed",
        what_youd_get=None,
        duration_ms=int((time.time() - t0) * 1000),
        sub_scores={
            "brand": brand,
            "domain": domain,
            "providers_called": [p for p in per_provider],
            "providers_failed": [p for p, v in per_provider.items() if v.get("score") is None],
            "per_provider": per_provider,
            "estimated_cost_usd": total_cost,
            "tavily_grounding_used": bool(tavily_grounding),
            "tavily_results_count": len(tavily_results),
        },
    )
