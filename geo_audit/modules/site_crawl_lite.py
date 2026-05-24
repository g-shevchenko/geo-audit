"""Module: site-crawl-lite — small-site crawl inventory for SEO/GEO audits."""
from __future__ import annotations

import time
import urllib.parse
import urllib.robotparser

from geo_audit.crawler import fetch
from geo_audit.html_extract import route_snapshot
from geo_audit.modules.base import Finding, ModuleArgs, ModuleResult

NAME = "site-crawl-lite"
WEIGHT = 0
REQUIRES_API_KEYS: list[str] = []
DESCRIPTION = "Sitemap-first crawl inventory: status, head tags, schema, links, images."

MAX_FULL_URLS = 50
MAX_QUICK_URLS = 1


def _same_url(a: str, b: str) -> bool:
    def norm(u: str) -> str:
        p = urllib.parse.urlparse(u)
        path = p.path.rstrip("/") or "/"
        return urllib.parse.urlunparse((p.scheme.lower(), p.netloc.lower(), path, "", "", ""))
    return norm(a) == norm(b)


def _robots_allows(robots_txt: str | None, user_agent: str, url: str) -> bool:
    if not robots_txt:
        return True
    parser = urllib.robotparser.RobotFileParser()
    parser.parse(robots_txt.splitlines())
    return parser.can_fetch(user_agent, url)


def _candidate_urls(args: ModuleArgs) -> list[str]:
    max_urls = MAX_QUICK_URLS if args.depth == "quick" else MAX_FULL_URLS
    urls: list[str] = []
    for url in [args.homepage_url_final or args.url, args.url, *args.sitemap_urls]:
        if url and url not in urls:
            urls.append(url)
        if len(urls) >= max_urls:
            break
    return urls


def _route_issues(route: dict[str, object]) -> list[str]:
    issues: list[str] = []
    status = int(route.get("status") or 0)
    if status < 200 or status >= 400:
        issues.append("bad_status")
    if not route.get("title"):
        issues.append("missing_title")
    if not route.get("meta_description"):
        issues.append("missing_meta_description")
    if not route.get("canonical"):
        issues.append("missing_canonical")
    if not route.get("h1"):
        issues.append("missing_h1")
    if int(route.get("jsonld_parse_errors") or 0) > 0:
        issues.append("jsonld_parse_error")
    if int(route.get("jsonld_count") or 0) == 0:
        issues.append("missing_jsonld")
    if route.get("noindex"):
        issues.append("noindex")
    return issues


def _score(routes: list[dict[str, object]], blocked_count: int) -> int:
    if not routes:
        return 0
    total_checks = len(routes) * 8
    failures = blocked_count
    for route in routes:
        issues = set(_route_issues(route))
        for key in [
            "bad_status", "missing_title", "missing_meta_description", "missing_canonical",
            "missing_h1", "jsonld_parse_error", "missing_jsonld", "noindex",
        ]:
            if key in issues:
                failures += 1
    return max(0, min(100, round(100 * (1 - failures / max(total_checks, 1)))))


def run(args: ModuleArgs) -> ModuleResult:
    t0 = time.time()
    findings: list[Finding] = []
    actions: list[Finding] = []
    routes: list[dict[str, object]] = []
    blocked_urls: list[str] = []
    firecrawl_key = args.api_keys.get("FIRECRAWL_API_KEY")

    for url in _candidate_urls(args):
        if not _robots_allows(args.robots_txt, args.user_agent, url):
            blocked_urls.append(url)
            continue

        if args.homepage_html and (_same_url(url, args.url) or _same_url(url, args.homepage_url_final or args.url)):
            routes.append(route_snapshot(url, args.homepage_url_final or url, args.homepage_status or 0, args.homepage_html))
            continue

        response = fetch(
            url,
            user_agent=args.user_agent,
            timeout_s=args.timeout_s,
            cache_dir=args.cache_dir,
            no_cache=args.no_cache,
            firecrawl_api_key=firecrawl_key,
        )
        routes.append(route_snapshot(url, response.final_url, response.status, response.text))

    issue_counts: dict[str, int] = {}
    for route in routes:
        for issue in _route_issues(route):
            issue_counts[issue] = issue_counts.get(issue, 0) + 1

    if routes:
        findings.append(Finding("P3", "Crawl-lite route inventory complete", f"{len(routes)} route(s) analyzed"))
    else:
        actions.append(Finding("P0", "No crawlable routes found", "No homepage or sitemap routes could be analyzed"))

    if blocked_urls:
        actions.append(Finding("P1", "Robots.txt blocked crawl-lite URLs", f"{len(blocked_urls)} URL(s) blocked"))
    if issue_counts.get("bad_status"):
        actions.append(Finding("P0", "Fix non-200 crawl routes", f"{issue_counts['bad_status']} route(s) returned non-2xx/3xx status"))
    if issue_counts.get("missing_title"):
        actions.append(Finding("P1", "Add missing title tags", f"{issue_counts['missing_title']} route(s) missing <title>"))
    if issue_counts.get("missing_meta_description"):
        actions.append(Finding("P1", "Add missing meta descriptions", f"{issue_counts['missing_meta_description']} route(s) missing meta description"))
    if issue_counts.get("missing_canonical"):
        actions.append(Finding("P1", "Add canonical links", f"{issue_counts['missing_canonical']} route(s) missing canonical"))
    if issue_counts.get("missing_h1"):
        actions.append(Finding("P2", "Add missing H1 headings", f"{issue_counts['missing_h1']} route(s) missing H1"))
    if issue_counts.get("jsonld_parse_error"):
        actions.append(Finding("P0", "Fix JSON-LD parse errors", f"{issue_counts['jsonld_parse_error']} route(s) have invalid JSON-LD"))
    if issue_counts.get("missing_jsonld"):
        actions.append(Finding("P2", "Add JSON-LD to key routes", f"{issue_counts['missing_jsonld']} route(s) have no JSON-LD"))
    if issue_counts.get("noindex"):
        actions.append(Finding("P0", "Remove accidental noindex", f"{issue_counts['noindex']} route(s) have robots noindex"))

    return ModuleResult(
        name=NAME,
        score=_score(routes, len(blocked_urls)),
        findings=findings,
        actions=actions,
        duration_ms=int((time.time() - t0) * 1000),
        sub_scores={
            "routes_checked": len(routes),
            "blocked_urls": blocked_urls,
            "issue_counts": issue_counts,
            "routes": routes,
        },
    )
