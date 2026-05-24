"""Small, dependency-free HTML extraction helpers for audit modules."""
from __future__ import annotations

import json
import re
import urllib.parse
from html import unescape
from typing import Any


def strip_html_to_text(html: str) -> str:
    cleaned = re.sub(r"<script\b[^>]*>.*?</script>", " ", html or "", flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"<style\b[^>]*>.*?</style>", " ", cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"<!--.*?-->", " ", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    return unescape(re.sub(r"\s+", " ", cleaned).strip())


def word_count(html: str) -> int:
    return len(re.findall(r"[\wА-Яа-яЁё]+", strip_html_to_text(html)))


def first_match(html: str, pattern: str) -> str:
    match = re.search(pattern, html or "", re.IGNORECASE | re.DOTALL)
    if not match:
        return ""
    return unescape(re.sub(r"\s+", " ", match.group(1)).strip())


def title(html: str) -> str:
    return first_match(html, r"<title[^>]*>(.*?)</title>")


def h1(html: str) -> str:
    raw = first_match(html, r"<h1\b[^>]*>(.*?)</h1>")
    return strip_html_to_text(raw)


def attr_from_tag(tag: str, attr: str) -> str:
    match = re.search(rf"\b{re.escape(attr)}\s*=\s*([\"'])(.*?)\1", tag or "", re.IGNORECASE | re.DOTALL)
    return unescape(match.group(2).strip()) if match else ""


def meta_content(html: str, *, name: str = "", prop: str = "") -> str:
    for match in re.finditer(r"<meta\b[^>]*>", html or "", re.IGNORECASE | re.DOTALL):
        tag = match.group(0)
        if name and attr_from_tag(tag, "name").lower() == name.lower():
            return attr_from_tag(tag, "content")
        if prop and attr_from_tag(tag, "property").lower() == prop.lower():
            return attr_from_tag(tag, "content")
    return ""


def canonical(html: str) -> str:
    for match in re.finditer(r"<link\b[^>]*>", html or "", re.IGNORECASE | re.DOTALL):
        tag = match.group(0)
        rel = attr_from_tag(tag, "rel").lower()
        if "canonical" in rel.split():
            return attr_from_tag(tag, "href")
    return ""


def robots_meta(html: str) -> str:
    return meta_content(html, name="robots")


def jsonld_blocks(html: str) -> list[Any]:
    blocks: list[Any] = []
    pattern = re.compile(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', re.IGNORECASE | re.DOTALL)
    for match in pattern.finditer(html or ""):
        raw = match.group(1).strip()
        if not raw:
            continue
        try:
            blocks.append(json.loads(raw))
        except json.JSONDecodeError:
            try:
                blocks.append(json.loads(re.sub(r",(\s*[}\]])", r"\1", raw)))
            except json.JSONDecodeError:
                blocks.append({"_parse_error": True, "_raw": raw[:500]})
    return blocks


def collect_jsonld_types(node: Any, acc: set[str] | None = None) -> set[str]:
    acc = acc or set()
    if isinstance(node, dict):
        value = node.get("@type")
        values = value if isinstance(value, list) else [value]
        for item in values:
            if isinstance(item, str):
                acc.add(item)
        for child in node.values():
            collect_jsonld_types(child, acc)
    elif isinstance(node, list):
        for item in node:
            collect_jsonld_types(item, acc)
    return acc


def has_jsonld_type(blocks: list[Any], type_name: str) -> bool:
    return type_name.lower() in {t.lower() for block in blocks for t in collect_jsonld_types(block)}


def absolute_url(base_url: str, href: str) -> str:
    if not href or href.startswith(("mailto:", "tel:", "javascript:", "#")):
        return ""
    return urllib.parse.urljoin(base_url, href)


def same_host(url_a: str, url_b: str) -> bool:
    return urllib.parse.urlparse(url_a).netloc.lower() == urllib.parse.urlparse(url_b).netloc.lower()


def links(html: str, base_url: str) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for match in re.finditer(r"<a\b[^>]*>(.*?)</a>", html or "", re.IGNORECASE | re.DOTALL):
        tag = match.group(0)
        href = absolute_url(base_url, attr_from_tag(tag, "href"))
        if not href:
            continue
        out.append({"url": href, "text": strip_html_to_text(match.group(1))[:160]})
    return out


def images(html: str, base_url: str) -> list[dict[str, str | bool]]:
    out: list[dict[str, str | bool]] = []
    for match in re.finditer(r"<img\b[^>]*>", html or "", re.IGNORECASE | re.DOTALL):
        tag = match.group(0)
        src = absolute_url(base_url, attr_from_tag(tag, "src")) or attr_from_tag(tag, "src")
        alt = attr_from_tag(tag, "alt")
        out.append({"src": src, "alt": alt, "has_alt": bool(alt.strip())})
    return out


def route_snapshot(url: str, final_url: str, status: int, html: str) -> dict[str, object]:
    blocks = jsonld_blocks(html)
    all_links = links(html, final_url or url)
    internal = [item for item in all_links if same_host(final_url or url, item["url"])]
    imgs = images(html, final_url or url)
    robots = robots_meta(html).lower()
    return {
        "url": url,
        "final_url": final_url or url,
        "status": status,
        "title": title(html),
        "meta_description": meta_content(html, name="description"),
        "og_title": meta_content(html, prop="og:title"),
        "og_description": meta_content(html, prop="og:description"),
        "og_image": meta_content(html, prop="og:image"),
        "twitter_card": meta_content(html, name="twitter:card"),
        "canonical": canonical(html),
        "h1": h1(html),
        "word_count": word_count(html),
        "jsonld_count": len(blocks),
        "jsonld_parse_errors": sum(1 for block in blocks if isinstance(block, dict) and block.get("_parse_error")),
        "jsonld_types": sorted({t for block in blocks for t in collect_jsonld_types(block)}),
        "internal_links_count": len(internal),
        "outbound_links_count": len(all_links) - len(internal),
        "images_count": len(imgs),
        "images_missing_alt": sum(1 for img in imgs if not img.get("has_alt")),
        "noindex": "noindex" in robots,
    }
