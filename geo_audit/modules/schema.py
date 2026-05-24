"""Module: schema — JSON-LD schema.org validator + suggester.

Scoring per docs/methodology.md#schema. Fully offline.
"""
from __future__ import annotations

import json
import re
import time
from typing import Any

from geo_audit.html_extract import has_breadcrumb_markup
from geo_audit.modules.base import Finding, ModuleArgs, ModuleResult

NAME = "schema"
WEIGHT = 15
REQUIRES_API_KEYS: list[str] = []
DESCRIPTION = "JSON-LD schema.org validator + suggester."

# Sub-check weights (per methodology.md).
SUB_WEIGHTS = {
    "article_with_author_sameas":   15,
    "organization_with_sameas":     15,
    "faqpage_for_faq_blocks":       15,
    "howto_for_steps":              10,
    "person_with_jobtitle":         10,
    "breadcrumblist":               10,
    "product_with_aggregaterating": 15,
    "no_validation_errors":         10,
}


def extract_jsonld_blocks(html: str) -> list[Any]:
    """Extract all JSON-LD <script> blocks. Returns list of decoded JSON values."""
    out: list[Any] = []
    if not html:
        return out
    pattern = re.compile(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        re.IGNORECASE | re.DOTALL,
    )
    for m in pattern.finditer(html):
        raw = m.group(1).strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
            out.append(data)
        except json.JSONDecodeError:
            # Try a tolerant strip of trailing commas.
            cleaned = re.sub(r",(\s*[}\]])", r"\1", raw)
            try:
                out.append(json.loads(cleaned))
            except json.JSONDecodeError:
                out.append({"_parse_error": True, "_raw": raw[:500]})
    return out


def _collect_types(node: Any, acc: set[str]) -> None:
    """Walk JSON-LD and collect all @type values (handles arrays + nested @graph)."""
    if isinstance(node, dict):
        t = node.get("@type")
        if isinstance(t, str):
            acc.add(t)
        elif isinstance(t, list):
            for x in t:
                if isinstance(x, str):
                    acc.add(x)
        for v in node.values():
            _collect_types(v, acc)
    elif isinstance(node, list):
        for x in node:
            _collect_types(x, acc)


def _find_nodes_with_type(node: Any, type_name: str) -> list[dict]:
    """Find all dict nodes whose @type matches (case-insensitive, supports arrays)."""
    out: list[dict] = []
    if isinstance(node, dict):
        t = node.get("@type")
        types = [t] if isinstance(t, str) else (t if isinstance(t, list) else [])
        if any(isinstance(x, str) and x.lower() == type_name.lower() for x in types):
            out.append(node)
        for v in node.values():
            out.extend(_find_nodes_with_type(v, type_name))
    elif isinstance(node, list):
        for x in node:
            out.extend(_find_nodes_with_type(x, type_name))
    return out


def _has_html_pattern(html: str, pattern: str) -> bool:
    return bool(re.search(pattern, html, re.IGNORECASE | re.DOTALL))


def run(args: ModuleArgs) -> ModuleResult:
    t0 = time.time()
    html = args.homepage_html or ""
    findings: list[Finding] = []
    actions: list[Finding] = []
    sub_scores: dict[str, int] = {k: 0 for k in SUB_WEIGHTS}

    blocks = extract_jsonld_blocks(html)
    all_types: set[str] = set()
    for b in blocks:
        _collect_types(b, all_types)

    parse_errors = sum(1 for b in blocks if isinstance(b, dict) and b.get("_parse_error"))

    # 1. Article / BlogPosting with author.sameAs
    articles = _find_nodes_with_type(blocks, "Article") + _find_nodes_with_type(blocks, "BlogPosting") + _find_nodes_with_type(blocks, "NewsArticle")
    if articles:
        for a in articles:
            author = a.get("author")
            authors = [author] if isinstance(author, dict) else (author if isinstance(author, list) else [])
            if any(isinstance(x, dict) and x.get("sameAs") for x in authors):
                sub_scores["article_with_author_sameas"] = SUB_WEIGHTS["article_with_author_sameas"]
                findings.append(Finding("P3", "Article schema with author.sameAs found", f"@type: Article + author.sameAs present"))
                break
        else:
            actions.append(Finding(
                "P1", "Add author.sameAs to Article schema",
                f"Found {len(articles)} Article/BlogPosting blocks but none have author.sameAs",
                "https://schema.org/author",
            ))
    else:
        # Article schema is optional — only an action if the page LOOKS like an article.
        looks_like_article = bool(re.search(r"<article\b|<h1\b.{0,500}<time\b", html, re.IGNORECASE | re.DOTALL))
        if looks_like_article:
            actions.append(Finding(
                "P1", "Add Article schema to article-like pages",
                "Page has <article> / <h1>+<time> but no Article JSON-LD",
                "https://schema.org/Article",
            ))

    # 2. Organization with sameAs (homepage)
    orgs = _find_nodes_with_type(blocks, "Organization")
    if any(o.get("sameAs") for o in orgs):
        sub_scores["organization_with_sameas"] = SUB_WEIGHTS["organization_with_sameas"]
        findings.append(Finding("P3", "Organization schema with sameAs found", "Organization + sameAs present"))
    else:
        actions.append(Finding(
            "P1", "Add Organization schema with sameAs to social profiles",
            f"Found {len(orgs)} Organization blocks (none with sameAs)" if orgs else "No Organization JSON-LD on homepage",
            "https://schema.org/Organization",
        ))

    # 3. FAQPage for FAQ-looking blocks
    has_faq_html = _has_html_pattern(html, r"<h\d[^>]*>\s*(?:FAQ|Часто задаваемые|Frequently Asked)") or \
                   _has_html_pattern(html, r"<details\b")
    has_faq_schema = bool(_find_nodes_with_type(blocks, "FAQPage"))
    if has_faq_schema:
        sub_scores["faqpage_for_faq_blocks"] = SUB_WEIGHTS["faqpage_for_faq_blocks"]
        findings.append(Finding("P3", "FAQPage schema present", "FAQPage @type detected"))
    elif has_faq_html:
        actions.append(Finding(
            "P1", "Add FAQPage schema to FAQ blocks",
            "FAQ-like content detected (heading, <details>, or Q&A) but no FAQPage @type",
            "https://schema.org/FAQPage",
        ))

    # 4. HowTo for stepped instructions
    has_howto_html = _has_html_pattern(html, r"<ol\b") or _has_html_pattern(html, r"step[- ]\d|шаг \d")
    if _find_nodes_with_type(blocks, "HowTo"):
        sub_scores["howto_for_steps"] = SUB_WEIGHTS["howto_for_steps"]
        findings.append(Finding("P3", "HowTo schema present", "HowTo @type detected"))
    elif has_howto_html and re.search(r"\bhow\s+to\b|\bкак\s+", html, re.IGNORECASE):
        actions.append(Finding(
            "P2", "Consider HowTo schema for instructional content",
            "Page has 'how to' / 'как ' patterns but no HowTo @type",
            "https://schema.org/HowTo",
        ))

    # 5. Person with jobTitle, worksFor (author pages)
    persons = _find_nodes_with_type(blocks, "Person")
    if any(p.get("jobTitle") and p.get("worksFor") for p in persons):
        sub_scores["person_with_jobtitle"] = SUB_WEIGHTS["person_with_jobtitle"]
        findings.append(Finding("P3", "Person schema with jobTitle + worksFor found", ""))
    elif persons:
        actions.append(Finding(
            "P2", "Enrich Person schema with jobTitle + worksFor",
            f"Person schema present but missing jobTitle/worksFor",
            "https://schema.org/Person",
        ))

    # 6. BreadcrumbList
    if _find_nodes_with_type(blocks, "BreadcrumbList"):
        sub_scores["breadcrumblist"] = SUB_WEIGHTS["breadcrumblist"]
        findings.append(Finding("P3", "BreadcrumbList schema present", ""))
    elif has_breadcrumb_markup(html):
        actions.append(Finding(
            "P2", "Add BreadcrumbList schema",
            "Breadcrumb-like markup detected but no BreadcrumbList @type",
            "https://schema.org/BreadcrumbList",
        ))

    # 7. Product + AggregateRating
    products = _find_nodes_with_type(blocks, "Product")
    has_rating = any(p.get("aggregateRating") for p in products)
    if has_rating:
        sub_scores["product_with_aggregaterating"] = SUB_WEIGHTS["product_with_aggregaterating"]
        findings.append(Finding("P3", "Product with aggregateRating found", ""))
    elif products:
        actions.append(Finding(
            "P1", "Add aggregateRating to Product schema",
            f"Found {len(products)} Product blocks but none have aggregateRating",
            "https://schema.org/aggregateRating",
        ))

    # 8. No parse errors
    if parse_errors == 0 and blocks:
        sub_scores["no_validation_errors"] = SUB_WEIGHTS["no_validation_errors"]
    elif parse_errors > 0:
        actions.append(Finding(
            "P0", f"Fix {parse_errors} JSON-LD parse error(s)",
            f"{parse_errors} <script type='application/ld+json'> block(s) failed to parse",
            "https://validator.schema.org/",
        ))
    elif not blocks:
        actions.append(Finding(
            "P0", "Add JSON-LD schema markup",
            "No <script type='application/ld+json'> blocks found in HTML",
            "https://schema.org/",
        ))

    score = sum(sub_scores.values())
    duration = int((time.time() - t0) * 1000)

    return ModuleResult(
        name=NAME,
        score=score,
        findings=findings,
        actions=actions,
        ran_in_degraded_mode=False,
        duration_ms=duration,
        sub_scores={**sub_scores, "types_found": sorted(all_types), "blocks_count": len(blocks)},
    )
