"""HTTP crawler: fetch homepage, sitemap, robots.txt with timeouts and caching.

Uses httpx (sync). Respects robots.txt for crawled targets. Never bypasses
authoritative server timeouts. Caches by URL hash with TTL.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
import urllib.parse
import urllib.robotparser
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from xml.etree import ElementTree as ET

import httpx


CACHE_TTL_SEC = 24 * 3600  # 24h


@dataclass
class FetchResult:
    url: str
    final_url: str
    status: int
    headers: dict[str, str]
    text: str
    duration_ms: int
    from_cache: bool = False


def _cache_key(url: str, suffix: str = "html") -> str:
    h = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    return f"{h}.{suffix}"


def _read_cache(cache_dir: Path, url: str, suffix: str = "json") -> Optional[dict]:
    p = cache_dir / _cache_key(url, suffix)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if time.time() - data.get("_ts", 0) > CACHE_TTL_SEC:
            return None
        return data
    except Exception:
        return None


def _write_cache(cache_dir: Path, url: str, payload: dict, suffix: str = "json") -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    p = cache_dir / _cache_key(url, suffix)
    payload = dict(payload)
    payload["_ts"] = time.time()
    p.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def fetch(
    url: str,
    *,
    user_agent: str,
    timeout_s: int = 30,
    cache_dir: Optional[Path] = None,
    no_cache: bool = False,
) -> FetchResult:
    """Fetch one URL with caching."""
    if cache_dir and not no_cache:
        cached = _read_cache(cache_dir, url)
        if cached is not None:
            return FetchResult(
                url=url,
                final_url=cached.get("final_url", url),
                status=cached.get("status", 0),
                headers=cached.get("headers", {}),
                text=cached.get("text", ""),
                duration_ms=cached.get("duration_ms", 0),
                from_cache=True,
            )

    headers = {"User-Agent": user_agent, "Accept": "text/html,application/xhtml+xml,*/*;q=0.8"}
    t0 = time.time()
    try:
        with httpx.Client(follow_redirects=True, timeout=timeout_s, headers=headers) as client:
            r = client.get(url)
            duration_ms = int((time.time() - t0) * 1000)
            result = FetchResult(
                url=url,
                final_url=str(r.url),
                status=r.status_code,
                headers={k.lower(): v for k, v in r.headers.items()},
                text=r.text or "",
                duration_ms=duration_ms,
            )
    except httpx.HTTPError as e:
        duration_ms = int((time.time() - t0) * 1000)
        result = FetchResult(
            url=url, final_url=url, status=0,
            headers={"x-fetch-error": str(e)[:200]},
            text="", duration_ms=duration_ms,
        )

    if cache_dir and not no_cache and result.status > 0:
        _write_cache(cache_dir, url, {
            "final_url": result.final_url,
            "status": result.status,
            "headers": result.headers,
            "text": result.text,
            "duration_ms": result.duration_ms,
        })
    return result


def fetch_robots(
    base_url: str, *, user_agent: str, timeout_s: int = 10,
    cache_dir: Optional[Path] = None, no_cache: bool = False,
) -> Optional[str]:
    parsed = urllib.parse.urlparse(base_url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    r = fetch(robots_url, user_agent=user_agent, timeout_s=timeout_s,
              cache_dir=cache_dir, no_cache=no_cache)
    if r.status == 200 and r.text.strip():
        return r.text
    return None


def fetch_sitemap_urls(
    base_url: str, *, user_agent: str, robots_txt: Optional[str] = None,
    timeout_s: int = 15, max_urls: int = 50,
    cache_dir: Optional[Path] = None, no_cache: bool = False,
) -> list[str]:
    """Discover and parse sitemap.xml. Tries common paths + robots Sitemap: directives.

    Returns up to max_urls absolute URLs.
    """
    parsed = urllib.parse.urlparse(base_url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    candidates: list[str] = []

    if robots_txt:
        for line in robots_txt.splitlines():
            line = line.strip()
            if line.lower().startswith("sitemap:"):
                candidates.append(line.split(":", 1)[1].strip())

    candidates.extend([
        f"{base}/sitemap.xml",
        f"{base}/sitemap_index.xml",
        f"{base}/sitemap-index.xml",
    ])

    seen: set[str] = set()
    out: list[str] = []
    for sm in candidates:
        if sm in seen:
            continue
        seen.add(sm)
        r = fetch(sm, user_agent=user_agent, timeout_s=timeout_s,
                  cache_dir=cache_dir, no_cache=no_cache)
        if r.status != 200 or not r.text.strip():
            continue
        try:
            urls = _parse_sitemap_xml(r.text)
        except ET.ParseError:
            continue
        for u in urls:
            if u not in out:
                out.append(u)
                if len(out) >= max_urls:
                    return out
        # If this was a sitemap index, fetch nested sitemaps once.
        if "<sitemapindex" in r.text.lower():
            for nested in urls[:10]:
                if nested in seen:
                    continue
                seen.add(nested)
                rr = fetch(nested, user_agent=user_agent, timeout_s=timeout_s,
                           cache_dir=cache_dir, no_cache=no_cache)
                if rr.status != 200:
                    continue
                try:
                    nested_urls = _parse_sitemap_xml(rr.text)
                except ET.ParseError:
                    continue
                for nu in nested_urls:
                    if nu not in out:
                        out.append(nu)
                        if len(out) >= max_urls:
                            return out
    return out


def _parse_sitemap_xml(xml: str) -> list[str]:
    """Parse a sitemap.xml or sitemapindex into URL list."""
    out: list[str] = []
    # Strip BOM if present.
    if xml.startswith("﻿"):
        xml = xml[1:]
    root = ET.fromstring(xml)
    # Strip namespace from tags.
    ns = re.match(r"\{(.*?)\}", root.tag)
    nsstr = "{" + ns.group(1) + "}" if ns else ""
    for elem in root.iter(f"{nsstr}url" if nsstr else "url"):
        for loc in elem.iter(f"{nsstr}loc" if nsstr else "loc"):
            if loc.text:
                out.append(loc.text.strip())
                break
    # Sitemap index entries (nested sitemaps).
    if not out:
        for elem in root.iter(f"{nsstr}sitemap" if nsstr else "sitemap"):
            for loc in elem.iter(f"{nsstr}loc" if nsstr else "loc"):
                if loc.text:
                    out.append(loc.text.strip())
                    break
    return out


def is_allowed_by_robots(url: str, robots_txt: Optional[str], user_agent: str) -> bool:
    """Check if user_agent is allowed to fetch url under robots_txt."""
    if not robots_txt:
        return True  # no robots.txt = allowed by default
    rp = urllib.robotparser.RobotFileParser()
    rp.parse(robots_txt.splitlines())
    try:
        return rp.can_fetch(user_agent, url)
    except Exception:
        return True


def normalize_url(url: str) -> str:
    """Normalize URL: ensure scheme, strip fragment, lowercase host."""
    if "://" not in url:
        url = "https://" + url
    p = urllib.parse.urlparse(url)
    netloc = p.netloc.lower()
    return urllib.parse.urlunparse((p.scheme, netloc, p.path or "/", p.params, p.query, ""))
