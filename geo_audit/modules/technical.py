"""Module: technical — Core Web Vitals + indexability.

Scoring per docs/methodology.md#technical:
  A. CWV (50 points) via PageSpeed Insights API (optional key)
  B. Indexability (50 points) — fully offline

Without PSI key, A is reported as `degraded_no_cwv` (0 points) and module
flags this clearly so user knows what they're missing.
"""
from __future__ import annotations

import re
import time
import urllib.parse
from typing import Optional

import httpx

from geo_audit.modules.base import Finding, ModuleArgs, ModuleResult

NAME = "technical"
WEIGHT = 15
REQUIRES_API_KEYS: list[str] = []
DESCRIPTION = "Core Web Vitals (PSI) + indexability checks."

PSI_ENDPOINT = "https://pagespeed.googleapis.com/pagespeedonline/v5/runPagespeed"


def _score_lcp(seconds: Optional[float]) -> int:
    if seconds is None:
        return 0
    if seconds < 2.5:
        return 20
    if seconds < 4.0:
        return 10
    return 0


def _score_inp(ms: Optional[float]) -> int:
    if ms is None:
        return 0
    if ms < 200:
        return 15
    if ms < 500:
        return 7
    return 0


def _score_cls(value: Optional[float]) -> int:
    if value is None:
        return 0
    if value < 0.1:
        return 15
    if value < 0.25:
        return 7
    return 0


def fetch_psi(url: str, api_key: str, *, strategy: str = "mobile", timeout_s: int = 60) -> dict:
    """Call PSI v5 API and return the raw lighthouseResult subset we use."""
    params = {
        "url": url,
        "key": api_key,
        "strategy": strategy,
        "category": "performance",
    }
    qs = urllib.parse.urlencode(params)
    with httpx.Client(timeout=timeout_s) as client:
        r = client.get(f"{PSI_ENDPOINT}?{qs}")
        r.raise_for_status()
        return r.json()


def _extract_cwv_from_psi(psi: dict) -> dict[str, Optional[float]]:
    """Pull LCP (s), INP (ms), CLS from PSI response.

    Prefers field data (loadingExperience) over lab.
    """
    out: dict[str, Optional[float]] = {"lcp_s": None, "inp_ms": None, "cls": None}
    le = psi.get("loadingExperience", {}).get("metrics", {})

    if "LARGEST_CONTENTFUL_PAINT_MS" in le:
        out["lcp_s"] = le["LARGEST_CONTENTFUL_PAINT_MS"].get("percentile", 0) / 1000.0
    if "INTERACTION_TO_NEXT_PAINT" in le:
        out["inp_ms"] = float(le["INTERACTION_TO_NEXT_PAINT"].get("percentile", 0))
    if "CUMULATIVE_LAYOUT_SHIFT_SCORE" in le:
        out["cls"] = le["CUMULATIVE_LAYOUT_SHIFT_SCORE"].get("percentile", 0) / 100.0

    # Lab fallback if no field data.
    if out["lcp_s"] is None:
        audits = psi.get("lighthouseResult", {}).get("audits", {})
        lcp = audits.get("largest-contentful-paint", {}).get("numericValue")
        if lcp is not None:
            out["lcp_s"] = lcp / 1000.0
        cls = audits.get("cumulative-layout-shift", {}).get("numericValue")
        if cls is not None:
            out["cls"] = cls
        # PSI lab doesn't have INP; leave None.
    return out


def _check_indexability(html: str, headers: dict[str, str], final_url: str) -> tuple[int, list[Finding], list[Finding]]:
    """Compute indexability sub-score (0–50) per methodology.

    Returns (score, findings, actions). P3 → findings; P0/P1/P2 → actions.
    """
    score = 0
    findings: list[Finding] = []
    actions: list[Finding] = []

    # 1. HTTPS + HSTS (10)
    if final_url.startswith("https://"):
        if "strict-transport-security" in headers:
            score += 10
            findings.append(Finding("P3", "HTTPS + HSTS", f"HSTS: {headers['strict-transport-security'][:80]}"))
        else:
            score += 5
            actions.append(Finding("P2", "HTTPS but no HSTS", "Add Strict-Transport-Security header for full credit"))
    else:
        actions.append(Finding("P0", "Site not on HTTPS", f"Final URL: {final_url}"))

    # 4. Canonical (5)
    canonical_match = re.search(r'<link[^>]*rel=["\']canonical["\'][^>]*href=["\']([^"\']+)["\']', html, re.IGNORECASE)
    if canonical_match:
        score += 5
        findings.append(Finding("P3", "Canonical link present", f"canonical: {canonical_match.group(1)[:100]}"))
    else:
        actions.append(Finding("P1", "Add <link rel='canonical'>", "No canonical link found in homepage HTML"))

    # 5. SSR/SSG: content present in initial HTML (10)
    text_only = re.sub(r"<script\b[^>]*>.*?</script>|<style\b[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text_only = re.sub(r"<[^>]+>", " ", text_only)
    visible_chars = len(re.sub(r"\s+", " ", text_only).strip())
    if visible_chars >= 1000:
        score += 10
        findings.append(Finding("P3", "Content rendered in initial HTML (SSR/SSG)", f"~{visible_chars} visible chars"))
    elif visible_chars >= 300:
        score += 5
        actions.append(Finding("P1", "Limited content in initial HTML", f"Only ~{visible_chars} visible chars — possible CSR-heavy"))
    else:
        actions.append(Finding(
            "P0", "Page renders empty without JS",
            f"Only ~{visible_chars} visible chars in initial HTML — AI crawlers likely see nothing",
            "https://web.dev/learn/javascript-as-it-relates-to-seo/",
        ))

    # 6. Mobile viewport meta (5)
    if re.search(r'<meta[^>]*name=["\']viewport["\']', html, re.IGNORECASE):
        score += 5
        findings.append(Finding("P3", "Mobile viewport meta present", ""))
    else:
        actions.append(Finding("P1", "Add <meta name='viewport'>", "Missing mobile viewport meta — bad mobile UX = ranking penalty"))

    return score, findings, actions


def run(args: ModuleArgs) -> ModuleResult:
    t0 = time.time()
    findings: list[Finding] = []
    actions: list[Finding] = []
    sub: dict[str, object] = {}

    html = args.homepage_html or ""
    headers = args.homepage_headers or {}
    final_url = args.homepage_url_final or args.url

    # 2. Sitemap valid (10)
    sitemap_score = 10 if args.sitemap_urls else 0
    if not args.sitemap_urls:
        actions.append(Finding(
            "P1", "Publish a valid sitemap.xml",
            "No sitemap.xml found at common paths or via robots.txt",
            "https://www.sitemaps.org/protocol.html",
        ))

    # 3. robots.txt valid + no blanket disallow (10)
    robots = args.robots_txt or ""
    robots_score = 0
    if robots:
        if re.search(r"^User-agent:\s*\*\s*\nDisallow:\s*/\s*$", robots, re.IGNORECASE | re.MULTILINE):
            actions.append(Finding(
                "P0", "robots.txt has blanket Disallow: /",
                "User-agent: * has Disallow: / — site is uncrawlable",
                "https://developers.google.com/search/docs/crawling-indexing/robots/intro",
            ))
        else:
            robots_score = 10

    indexability_partial, indexability_findings, indexability_actions = _check_indexability(html, headers, final_url)
    findings.extend(indexability_findings)
    actions.extend(indexability_actions)
    indexability_score = indexability_partial + sitemap_score + robots_score
    indexability_score = min(50, indexability_score)
    sub["indexability_score"] = indexability_score

    # CWV via PSI (optional)
    psi_key = args.api_keys.get("PAGESPEED_API_KEY")
    cwv_score = 0
    cwv_metrics: dict[str, Optional[float]] = {"lcp_s": None, "inp_ms": None, "cls": None}
    cwv_unavailable = False  # only True if PSI was needed but failed; not "no key supplied"

    if psi_key:
        try:
            psi_resp = fetch_psi(args.url, psi_key, timeout_s=args.timeout_s + 30)
            cwv_metrics = _extract_cwv_from_psi(psi_resp)
            lcp_pts = _score_lcp(cwv_metrics["lcp_s"])
            inp_pts = _score_inp(cwv_metrics["inp_ms"])
            cls_pts = _score_cls(cwv_metrics["cls"])
            cwv_score = lcp_pts + inp_pts + cls_pts
            sub["cwv_metrics"] = cwv_metrics
            sub["cwv_breakdown"] = {"lcp_pts": lcp_pts, "inp_pts": inp_pts, "cls_pts": cls_pts}
            findings.append(Finding(
                "P3", "Core Web Vitals measured",
                f"LCP: {cwv_metrics['lcp_s']}s, INP: {cwv_metrics['inp_ms']}ms, CLS: {cwv_metrics['cls']}",
            ))
            for label, val, threshold, p in [
                ("LCP", cwv_metrics["lcp_s"], 2.5, "P0" if (cwv_metrics["lcp_s"] or 0) >= 4.0 else "P1"),
                ("INP", cwv_metrics["inp_ms"], 200, "P0" if (cwv_metrics["inp_ms"] or 0) >= 500 else "P1"),
                ("CLS", cwv_metrics["cls"], 0.1, "P0" if (cwv_metrics["cls"] or 0) >= 0.25 else "P1"),
            ]:
                if val is not None and val >= threshold:
                    actions.append(Finding(p, f"Improve {label}", f"{label} = {val} (target: <{threshold})", "https://web.dev/vitals/"))
        except (httpx.HTTPError, httpx.TimeoutException, ValueError, KeyError) as e:
            cwv_unavailable = True
            findings.append(Finding("P2", "PSI fetch failed", f"PSI API error: {str(e)[:200]}"))
    else:
        cwv_unavailable = True
        actions.append(Finding(
            "P2", "Add PAGESPEED_API_KEY for full Core Web Vitals scoring",
            "Without PSI, CWV (50pt) defaults to 0 — Indexability (50pt) still scored",
            "https://developers.google.com/speed/docs/insights/v5/get-started",
        ))

    score = indexability_score + cwv_score

    return ModuleResult(
        name=NAME,
        score=score,
        findings=findings,
        actions=actions,
        ran_in_degraded_mode=False,
        skip_reason=None,  # we still score (indexability portion); not fully skipped
        what_youd_get="Adding PAGESPEED_API_KEY unlocks Core Web Vitals scoring (LCP/INP/CLS, 50pt portion)",
        duration_ms=int((time.time() - t0) * 1000),
        sub_scores={
            **sub,
            "indexability_score": indexability_score,
            "cwv_score": cwv_score,
            "sitemap_present": bool(args.sitemap_urls),
            "robots_present": bool(robots),
            "psi_used": bool(psi_key) and not cwv_unavailable,
        },
    )
