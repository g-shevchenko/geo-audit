"""Module: citability — LLM-citation likelihood scoring (heuristic).

Scoring per docs/methodology.md#citability:
  TL;DR present (25), FAQ block (20), Numbered structure (15),
  Source links (20), Clear definitions (20)

Fully offline. Pattern-based heuristic. No LLM calls in v0.2.
A future v0.3 may add an optional LLM-graded layer.
"""
from __future__ import annotations

import re
import time
import urllib.parse
from typing import Optional

from geo_audit.modules.base import Finding, ModuleArgs, ModuleResult

NAME = "citability"
WEIGHT = 25
REQUIRES_API_KEYS: list[str] = []
DESCRIPTION = "LLM-citation likelihood: TL;DR, FAQ, lists, sources, definitions."

SUB_WEIGHTS = {
    "tldr_present": 25,
    "faq_block": 20,
    "numbered_structure": 15,
    "source_links": 20,
    "clear_definitions": 20,
}

# Definition patterns by language. Detection of "X — это Y" / "X is Y".
DEFINITION_PATTERNS = {
    "ru": [
        # Cyrillic word OR Latin term — это / является / представляет
        r"(?:\b[А-ЯЁ][а-яё]{2,}|\b[A-Z][A-Za-z0-9]{1,})\s+[—–-]\s+это\s+",
        r"(?:\b[А-ЯЁ][а-яё]{2,}|\b[A-Z][A-Za-z0-9]{1,})\s+это\s+",
        r"(?:\b[А-ЯЁ][а-яё]{2,}|\b[A-Z][A-Za-z0-9]{1,})\s+(?:является|представляет\s+собой)\s+",
    ],
    "en": [
        r"\b[A-Z][a-z]{2,}(?:\s+[A-Za-z]+){0,3}\s+(?:is|are)\s+(?:a|an|the)\s+",
        r"\b[A-Z][A-Za-z]+\s+refers\s+to\s+",
    ],
}

TLDR_HEADERS = [
    "tl;dr", "tldr", "summary", "in short", "коротко", "вкратце", "резюме",
]


def _detect_lang(html: str, hint: Optional[str] = None) -> str:
    if hint in ("ru", "en"):
        return hint
    m = re.search(r'<html[^>]*lang=["\']([a-z]{2})', html or "", re.IGNORECASE)
    if m:
        code = m.group(1).lower()
        if code in ("ru", "en"):
            return code
    # Heuristic: fraction of cyrillic.
    cyr = len(re.findall(r"[А-Яа-яЁё]", html or ""))
    lat = len(re.findall(r"[A-Za-z]", html or ""))
    if cyr > lat * 0.5:
        return "ru"
    return "en"


def _strip_html_to_text(html: str) -> str:
    """Strip scripts/styles/tags, return visible text. Tolerant — no parser dep."""
    cleaned = re.sub(r"<script\b[^>]*>.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"<style\b[^>]*>.*?</style>", " ", cleaned, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"<!--.*?-->", " ", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _check_tldr(html: str, text: str, strict: bool = False) -> tuple[bool, str]:
    """TL;DR present in first ~200 (strict) or ~500 (default) chars."""
    window = 200 if strict else 500
    head = text[:window]
    head_low = head.lower()
    for marker in TLDR_HEADERS:
        if marker in head_low:
            return True, f"Found '{marker}' in first {window} chars"
    # Also check for explicit <p> with summary class or div role=doc-abstract.
    if re.search(r'<(?:p|div)[^>]*(class|id)=["\'][^"\']*(summary|abstract|tldr|excerpt)', html, re.IGNORECASE):
        return True, "Found summary/abstract/tldr container"
    return False, f"No TL;DR / summary marker in first {window} chars"


def _check_faq(html: str) -> tuple[int, str]:
    """At least 5 question-answer pairs in semantic markup. Returns (count, evidence)."""
    # 1. <details><summary> pairs.
    details = re.findall(r"<details\b[^>]*>", html, re.IGNORECASE)
    # 2. FAQPage JSON-LD with mainEntity array.
    qa_count = len(details)
    faqpage_match = re.search(r'"@type"\s*:\s*"FAQPage"', html, re.IGNORECASE)
    if faqpage_match:
        # count Question entries
        q_count = len(re.findall(r'"@type"\s*:\s*"Question"', html, re.IGNORECASE))
        qa_count = max(qa_count, q_count)
    # 3. Heading + ? pattern (h2/h3 ending in ?).
    h_questions = len(re.findall(r"<h[23][^>]*>[^<]*\?\s*</h[23]>", html, re.IGNORECASE))
    qa_count = max(qa_count, h_questions)
    return qa_count, f"{qa_count} Q&A pair(s) detected (details/FAQPage/h?)"


def _check_numbered(html: str, text: str) -> tuple[bool, str]:
    """Numbered lists or steps."""
    ol_count = len(re.findall(r"<ol\b[^>]*>", html, re.IGNORECASE))
    inline_steps = len(re.findall(r"\b(?:step|шаг)\s+\d+\b", text, re.IGNORECASE))
    if ol_count >= 1 or inline_steps >= 3:
        return True, f"<ol> blocks: {ol_count}, inline 'Step N': {inline_steps}"
    return False, f"<ol> blocks: {ol_count}, inline 'Step N': {inline_steps} (need ≥1 ol or ≥3 inline steps)"


def _check_source_links(html: str, base_url: str) -> tuple[int, str]:
    """Count outbound links to authoritative sources (non-self domain)."""
    parsed = urllib.parse.urlparse(base_url)
    self_host = parsed.netloc.lower()
    self_root = ".".join(self_host.split(".")[-2:]) if "." in self_host else self_host
    outbound = 0
    seen: set[str] = set()
    for m in re.finditer(r'<a\b[^>]*href=["\'](https?://[^"\']+)["\']', html, re.IGNORECASE):
        href = m.group(1)
        try:
            host = urllib.parse.urlparse(href).netloc.lower()
        except Exception:
            continue
        if not host or host in seen:
            continue
        if host.endswith(self_root):
            continue
        # Skip social/share helpers.
        if any(s in host for s in ("twitter.com", "x.com", "facebook.com", "linkedin.com", "telegram.me", "t.me", "whatsapp.com", "vk.com")):
            continue
        seen.add(host)
        outbound += 1
    return outbound, f"{outbound} outbound link host(s) to non-self domains"


def _check_definitions(text: str, lang: str) -> tuple[int, str]:
    """Count definition-like patterns in first 500 words."""
    words = text.split()[:500]
    sample = " ".join(words)
    patterns = DEFINITION_PATTERNS.get(lang, DEFINITION_PATTERNS["en"])
    matches = 0
    for p in patterns:
        matches += len(re.findall(p, sample))
    return matches, f"{matches} definition pattern match(es) in first 500 words ({lang})"


def run(args: ModuleArgs) -> ModuleResult:
    t0 = time.time()
    html = args.homepage_html or ""
    if not html or args.homepage_status != 200:
        return ModuleResult(
            name=NAME, score=0,
            ran_in_degraded_mode=True,
            skip_reason=f"homepage status {args.homepage_status}",
            findings=[Finding("P0", "Cannot score citability — homepage failed to fetch",
                              f"Status: {args.homepage_status}")],
            duration_ms=int((time.time() - t0) * 1000),
        )

    text = _strip_html_to_text(html)
    lang = _detect_lang(html, args.lang)
    findings: list[Finding] = []
    actions: list[Finding] = []
    sub_scores: dict[str, int] = {k: 0 for k in SUB_WEIGHTS}

    # 1. TL;DR
    tldr_ok, tldr_evidence = _check_tldr(html, text)
    if tldr_ok:
        sub_scores["tldr_present"] = SUB_WEIGHTS["tldr_present"]
        findings.append(Finding("P3", "TL;DR present", tldr_evidence))
    else:
        actions.append(Finding(
            "P0", "Add TL;DR / summary in first 500 chars",
            tldr_evidence,
            "https://github.com/g-shevchenko/geo-audit/blob/main/docs/methodology.md#citability",
        ))

    # 2. FAQ block (≥5)
    faq_count, faq_evidence = _check_faq(html)
    if faq_count >= 5:
        sub_scores["faq_block"] = SUB_WEIGHTS["faq_block"]
        findings.append(Finding("P3", "FAQ block present", faq_evidence))
    elif faq_count >= 2:
        sub_scores["faq_block"] = SUB_WEIGHTS["faq_block"] // 2
        actions.append(Finding("P2", f"Expand FAQ: {faq_count}/5 pairs detected", faq_evidence))
    else:
        actions.append(Finding(
            "P1", "Add an FAQ block with ≥5 question-answer pairs",
            faq_evidence,
            "https://schema.org/FAQPage",
        ))

    # 3. Numbered structure
    num_ok, num_evidence = _check_numbered(html, text)
    if num_ok:
        sub_scores["numbered_structure"] = SUB_WEIGHTS["numbered_structure"]
        findings.append(Finding("P3", "Numbered structure present", num_evidence))
    else:
        actions.append(Finding(
            "P2", "Add numbered/ordered lists (steps, top-N)",
            num_evidence,
        ))

    # 4. Source links
    src_count, src_evidence = _check_source_links(html, args.url)
    if src_count >= 2:
        sub_scores["source_links"] = SUB_WEIGHTS["source_links"]
        findings.append(Finding("P3", "Outbound source links present", src_evidence))
    elif src_count == 1:
        sub_scores["source_links"] = SUB_WEIGHTS["source_links"] // 2
        actions.append(Finding("P2", "Add at least one more outbound source link", src_evidence))
    else:
        actions.append(Finding(
            "P1", "Add ≥2 outbound links to authoritative sources",
            src_evidence,
        ))

    # 5. Clear definitions
    def_count, def_evidence = _check_definitions(text, lang)
    if def_count >= 2:
        sub_scores["clear_definitions"] = SUB_WEIGHTS["clear_definitions"]
        findings.append(Finding("P3", "Clear definitions present", def_evidence))
    elif def_count == 1:
        sub_scores["clear_definitions"] = SUB_WEIGHTS["clear_definitions"] // 2
        actions.append(Finding("P2", "Add another 'X is Y' / 'X — это Y' definition", def_evidence))
    else:
        actions.append(Finding(
            "P1", f"Add a clear definition pattern in first 500 words ({lang})",
            def_evidence,
        ))

    score = sum(sub_scores.values())
    return ModuleResult(
        name=NAME,
        score=score,
        findings=findings,
        actions=actions,
        duration_ms=int((time.time() - t0) * 1000),
        sub_scores={**sub_scores, "lang_detected": lang},
    )
