"""Pluggable page fetcher with Firecrawl fallback.

By default, geo-audit uses direct httpx (no key, no third-party dep).
This works for ~70% of sites. The remaining ~30% — Cloudflare-protected,
DataDome, JS-heavy SPAs, geo-blocked — return empty or challenge HTML.

If `FIRECRAWL_API_KEY` is set, this module activates Firecrawl as a
fallback: when direct httpx returns a non-200 OR HTML that looks like a
challenge page OR has no readable content, we retry through Firecrawl.

The user can also force Firecrawl unconditionally via
`FIRECRAWL_FORCE=1` in the environment (useful when auditing a known
hostile target — saves the wasted httpx attempt).
"""
from __future__ import annotations

import os
import re
import time
from typing import Optional

import httpx


FIRECRAWL_ENDPOINT = "https://api.firecrawl.dev/v1/scrape"


def _looks_like_challenge_html(text: str) -> bool:
    """Heuristic: is the response a Cloudflare/DataDome/PerimeterX challenge?"""
    if not text:
        return True
    if len(text) < 500:
        # Too short to be a real homepage; likely an interstitial.
        return True
    head = text[:4000].lower()
    markers = [
        "cf-browser-verification",
        "cloudflare ray id",
        "checking your browser",
        "just a moment",
        "/cdn-cgi/challenge-platform",
        "datadome",
        "perimeterx",
        "_pxhd",
        "captcha",
        "px-captcha",
        "please enable javascript",
        "you need to enable javascript to run this app",
    ]
    return any(m in head for m in markers)


def _visible_text_len(html: str) -> int:
    """Quick estimate of visible content length (mirror of technical module)."""
    if not html:
        return 0
    cleaned = re.sub(r"<script\b[^>]*>.*?</script>|<style\b[^>]*>.*?</style>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    return len(re.sub(r"\s+", " ", cleaned).strip())


def should_try_fallback(status: int, text: str) -> bool:
    """Decide whether the direct fetch result warrants a fallback attempt.

    True when:
    - status >= 400 (server error or block), OR
    - status == 0 (network error), OR
    - HTML looks like a challenge / interstitial, OR
    - HTML has very little visible content (<200 chars) — likely CSR-only.
    """
    if status == 0 or status >= 400:
        return True
    if _looks_like_challenge_html(text):
        return True
    if _visible_text_len(text) < 200:
        return True
    return False


def fetch_via_firecrawl(
    url: str,
    api_key: str,
    *,
    timeout_s: int = 60,
    user_agent: Optional[str] = None,
) -> tuple[int, dict[str, str], str]:
    """Fetch a URL via Firecrawl /v1/scrape and return (status, headers, html).

    Firecrawl returns rendered HTML (after JS execution) and bypasses common
    bot-protection. Costs apply per their pricing — caller already opted in
    by setting FIRECRAWL_API_KEY.

    Returns (status, headers, html). On Firecrawl failure raises httpx.HTTPError.
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body: dict = {
        "url": url,
        "formats": ["html"],
        "onlyMainContent": False,  # we want full HTML for schema/llmstxt parsing
    }
    if user_agent:
        body["headers"] = {"User-Agent": user_agent}

    with httpx.Client(timeout=timeout_s) as client:
        r = client.post(FIRECRAWL_ENDPOINT, headers=headers, json=body)
        r.raise_for_status()
        data = r.json()

    if not data.get("success"):
        raise httpx.HTTPError(f"Firecrawl: success=false, error={data.get('error', 'unknown')[:200]}")

    payload = data.get("data", {})
    html = payload.get("html") or payload.get("rawHtml") or ""
    metadata = payload.get("metadata", {})
    out_status = int(metadata.get("statusCode", 200))
    out_headers = {"x-fetched-via": "firecrawl"}
    if metadata.get("contentType"):
        out_headers["content-type"] = metadata["contentType"]
    return out_status, out_headers, html


def firecrawl_force_enabled() -> bool:
    return os.environ.get("FIRECRAWL_FORCE", "").strip() in ("1", "true", "yes")
