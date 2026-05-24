"""Module: head-schema-gate — deterministic head, social, and JSON-LD readiness gate."""
from __future__ import annotations

import time

from geo_audit.html_extract import has_jsonld_type, jsonld_blocks, route_snapshot
from geo_audit.modules.base import Finding, ModuleArgs, ModuleResult

NAME = "head-schema-gate"
WEIGHT = 0
REQUIRES_API_KEYS: list[str] = []
DESCRIPTION = "Head/meta/social/schema consistency gate for SEO and AI citation readiness."


def _is_verification_file(url: str, html: str) -> bool:
    low = (url + " " + html[:300]).lower()
    return "verification:" in low or "yandex_" in low or "google-site-verification" in low


def _score_from_violations(violations: list[dict[str, str]]) -> int:
    weights = {"P0": 25, "P1": 12, "P2": 6, "P3": 0}
    penalty = sum(weights.get(v["priority"], 0) for v in violations)
    return max(0, min(100, 100 - penalty))


def _add(violations: list[dict[str, str]], priority: str, code: str, title: str, evidence: str) -> None:
    violations.append({"priority": priority, "code": code, "title": title, "evidence": evidence})


def run(args: ModuleArgs) -> ModuleResult:
    t0 = time.time()
    html = args.homepage_html or ""
    url = args.homepage_url_final or args.url
    snap = route_snapshot(args.url, url, args.homepage_status or 0, html)
    blocks = jsonld_blocks(html)
    violations: list[dict[str, str]] = []
    findings: list[Finding] = []
    actions: list[Finding] = []

    if _is_verification_file(url, html):
        findings.append(Finding("P3", "Verification file skipped", "Ownership verification files do not need SEO head/schema tags"))
        return ModuleResult(
            name=NAME,
            score=None,
            findings=findings,
            actions=actions,
            duration_ms=int((time.time() - t0) * 1000),
            sub_scores={"skipped_verification_file": True, "route": snap},
        )

    title = str(snap.get("title") or "")
    desc = str(snap.get("meta_description") or "")
    canonical = str(snap.get("canonical") or "")
    h1 = str(snap.get("h1") or "")

    if not title:
        _add(violations, "P1", "missing_title", "Add a title tag", "No <title> found")
    elif len(title) > 70:
        _add(violations, "P2", "long_title", "Shorten title tag", f"{len(title)} chars")
    else:
        findings.append(Finding("P3", "Title tag present", title[:120]))

    if not desc:
        _add(violations, "P1", "missing_meta_description", "Add classic meta description", "No meta name='description' found")
    elif len(desc) < 40 or len(desc) > 180:
        _add(violations, "P2", "meta_description_length", "Tune meta description length", f"{len(desc)} chars" )
    else:
        findings.append(Finding("P3", "Meta description present", desc[:120]))

    if not canonical:
        _add(violations, "P1", "missing_canonical", "Add canonical link", "No rel=canonical found")
    if not h1:
        _add(violations, "P2", "missing_h1", "Add visible H1", "No H1 found")
    if not snap.get("og_title"):
        _add(violations, "P2", "missing_og_title", "Add og:title", "No og:title found")
    if not snap.get("og_description"):
        _add(violations, "P2", "missing_og_description", "Add og:description", "No og:description found")
    if not snap.get("og_image"):
        _add(violations, "P2", "missing_og_image", "Add og:image", "No social preview image found")
    if int(snap.get("jsonld_parse_errors") or 0) > 0:
        _add(violations, "P0", "jsonld_parse_error", "Fix JSON-LD parse errors", f"{snap['jsonld_parse_errors']} parse error(s)")
    if not blocks:
        _add(violations, "P1", "missing_jsonld", "Add JSON-LD", "No JSON-LD blocks found")

    if has_jsonld_type(blocks, "Article") or has_jsonld_type(blocks, "BlogPosting"):
        if "author" in html and "sameAs" not in html:
            _add(violations, "P1", "article_author_sameas", "Add author.sameAs to Article schema", "Article schema has author but no sameAs signal")
    if "breadcrumb" in html.lower() and not has_jsonld_type(blocks, "BreadcrumbList"):
        _add(violations, "P2", "missing_breadcrumb_schema", "Add BreadcrumbList schema", "Breadcrumb-like text/markup found without BreadcrumbList JSON-LD")
    if ("<details" in html.lower() or "faq" in html.lower()) and not has_jsonld_type(blocks, "FAQPage"):
        _add(violations, "P1", "missing_faq_schema", "Add FAQPage schema", "FAQ-like content found without FAQPage JSON-LD")

    for v in violations:
        actions.append(Finding(v["priority"], v["title"], v["evidence"]))
    if not violations:
        findings.append(Finding("P3", "Head/schema gate passed", "No blocking head, social, or JSON-LD violations found"))

    return ModuleResult(
        name=NAME,
        score=_score_from_violations(violations),
        findings=findings,
        actions=actions,
        duration_ms=int((time.time() - t0) * 1000),
        sub_scores={"violations": violations, "route": snap},
    )
