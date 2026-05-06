"""Module: content — E-E-A-T + AI-detection + readability.

Scoring per docs/methodology.md#content:
  A. EEAT signals (40)
  B. AI-detection (30) — heuristic by default, optional Binoculars/GPTZero/Originality
  C. Readability (30) — Flesch / Pushkin

Default: fully offline. AI-detection uses an internal lexical heuristic
(based on observed AI-text patterns). Heavier detectors are opt-in via
extras (binoculars) or env keys (GPTZERO_API_KEY, ORIGINALITY_API_KEY).
"""
from __future__ import annotations

import re
import time
from typing import Optional

from geo_audit.modules.base import Finding, ModuleArgs, ModuleResult
from geo_audit.modules.citability import _strip_html_to_text, _detect_lang

NAME = "content"
WEIGHT = 15
REQUIRES_API_KEYS: list[str] = []
DESCRIPTION = "E-E-A-T + AI-detection (heuristic) + readability."


# ============================================================================
# A. EEAT signals (40 points: 10 each)
# ============================================================================

def _check_eeat(html: str) -> tuple[int, list[Finding], list[Finding]]:
    score = 0
    findings: list[Finding] = []
    actions: list[Finding] = []

    # 1. Author byline with photo + bio (10)
    has_author_block = (
        bool(re.search(r'<[^>]*(?:class|id)=["\'][^"\']*author[^"\']*["\']', html, re.IGNORECASE))
        or bool(re.search(r"by\s+<a\b", html, re.IGNORECASE))
        or bool(re.search(r'"author"\s*:\s*\{', html))
    )
    has_author_image_or_bio = bool(re.search(r'<img[^>]*alt=["\'][^"\']*author', html, re.IGNORECASE))
    if has_author_block:
        score += 10 if has_author_image_or_bio else 5
        findings.append(Finding("P3", "Author byline present", f"image/bio: {has_author_image_or_bio}"))
    else:
        actions.append(Finding("P1", "Add author byline with photo + bio", "No author markup detected"))

    # 2. Date published + last updated (10)
    has_published = bool(re.search(r'<time[^>]*datetime=', html, re.IGNORECASE)) or \
                    bool(re.search(r'"datePublished"\s*:', html))
    has_updated = bool(re.search(r'"dateModified"\s*:', html)) or \
                  bool(re.search(r'(?:updated|обновл)', html, re.IGNORECASE))
    if has_published and has_updated:
        score += 10
        findings.append(Finding("P3", "Date published + updated present", ""))
    elif has_published:
        score += 5
        actions.append(Finding("P2", "Add 'Last updated' date alongside 'Published'", ""))
    else:
        actions.append(Finding("P1", "Add datePublished + dateModified", "No <time> or schema dates found"))

    # 3. Outbound links to sources (10) — covered partially by citability.source_links.
    outbound_links = len(re.findall(r'<a\b[^>]*href=["\']https?://(?!#)', html, re.IGNORECASE))
    if outbound_links >= 3:
        score += 10
        findings.append(Finding("P3", "Outbound source links present", f"{outbound_links} found"))
    elif outbound_links >= 1:
        score += 5
    else:
        actions.append(Finding("P2", "Add outbound source/citation links", "No outbound HTTP links found"))

    # 4. Contact info on page or footer (10)
    has_contact = bool(re.search(r'mailto:|tel:|/contact', html, re.IGNORECASE))
    if has_contact:
        score += 10
        findings.append(Finding("P3", "Contact info present", ""))
    else:
        actions.append(Finding("P1", "Add visible contact info (email/phone/contact page)", ""))

    return score, findings, actions


# ============================================================================
# B. AI-detection (30 points)
# ============================================================================

# Lexical patterns observed in AI-generated text. Source:
#   - .claude/rules/anti-slop-v2.md (HWAI internal — generic patterns, not infra)
#   - GPTZero/Originality.ai public signal lists
# Each hit adds a point of "AI-likelihood". Threshold-based scoring below.
AI_PATTERNS_EN = [
    (r"\bdelve\s+(into|deeper)\b", 2),
    (r"\b(navigate|navigating|tapestry)\s+(?:the\s+)?landscape\b", 2),
    (r"\bunlock\s+(?:the\s+)?(?:power|potential|magic)\s+of\b", 2),
    (r"\bIt('s| is)\s+(important|worth|essential|crucial)\s+to\s+(note|mention|remember)", 2),
    (r"\bgame[- ]?changer|game[- ]?changing|revolutionary|groundbreaking|cutting[- ]?edge\b", 1),
    (r"\bnot only\b.{0,80}\bbut also\b", 1),
    (r"\bWhen it comes to\b", 1),
    (r"^\s*In (conclusion|summary|essence|short)\b", 1),
    (r"\b(seamless|robust|intuitive|comprehensive|holistic)\s+(platform|solution|tool|experience)\b", 1),
    (r"\bIn (today's|the)\s+(fast-paced|digital|modern|increasingly|complex|ever-changing)\b", 2),
]
AI_PATTERNS_RU = [
    (r"\b(?:важно|стоит|необходимо)\s+отметить,\s+что\b", 2),
    (r"\bв(?:\s+условиях)?\s+современного\s+(?:мира|общества)\b", 2),
    (r"\b(?:играет|играют)\s+(?:важную|ключевую|значимую)\s+роль\b", 2),
    (r"\bне\s+только.{0,80}\bно\s+и\b", 1),
    (r"\b(?:подведём|подводя)\s+итог", 1),
    (r"\bв\s+(?:заключение|целом|итоге)\b", 1),
]


def _ai_detect_heuristic(text: str, lang: str) -> tuple[float, list[str]]:
    """Returns (likelihood 0..1, hits)."""
    patterns = AI_PATTERNS_RU if lang == "ru" else AI_PATTERNS_EN
    hits: list[str] = []
    score = 0
    for pattern, weight in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
        if matches:
            score += weight * min(len(matches), 3)
            hits.append(f"{pattern}: {len(matches)}x")
    # Calibrate to 0..1 — assume ~10 weighted hits = 100% AI signal.
    likelihood = min(1.0, score / 10.0)
    return likelihood, hits


def _ai_detect_score(likelihood: float) -> int:
    if likelihood < 0.25:
        return 30
    if likelihood < 0.5:
        return 15
    if likelihood < 0.75:
        return 5
    return 0


# ============================================================================
# C. Readability (30 points)
# ============================================================================

def _flesch_reading_ease(text: str) -> Optional[float]:
    """Compute Flesch Reading Ease without third-party dep.

    Formula: 206.835 − 1.015×(words/sentences) − 84.6×(syllables/words)
    """
    if not text or len(text) < 100:
        return None
    sentences = re.split(r"[.!?]+", text)
    sentences = [s for s in sentences if s.strip()]
    if not sentences:
        return None
    words = re.findall(r"[A-Za-z']+", text)
    if not words:
        return None
    syll = sum(_count_syllables_en(w) for w in words)
    return 206.835 - 1.015 * (len(words) / len(sentences)) - 84.6 * (syll / len(words))


def _count_syllables_en(word: str) -> int:
    word = word.lower()
    if not word:
        return 0
    vowels = "aeiouy"
    count = 0
    prev_vowel = False
    for ch in word:
        is_vowel = ch in vowels
        if is_vowel and not prev_vowel:
            count += 1
        prev_vowel = is_vowel
    if word.endswith("e") and count > 1:
        count -= 1
    return max(1, count)


def _pushkin_readability(text: str) -> Optional[float]:
    """Pushkin readability index for Russian.

    Formula approximation:
      score = 208.7 − 1.52 × ASL − 65.14 × ASW
    where ASL = avg sentence length (words), ASW = avg syllables per word.
    Higher = easier.
    """
    if not text or len(text) < 100:
        return None
    sentences = re.split(r"[.!?…]+", text)
    sentences = [s for s in sentences if s.strip()]
    if not sentences:
        return None
    words = re.findall(r"[А-Яа-яЁё]+", text)
    if not words:
        return None
    syll = sum(len(re.findall(r"[аеёиоуыэюяАЕЁИОУЫЭЮЯ]", w)) for w in words)
    return 208.7 - 1.52 * (len(words) / len(sentences)) - 65.14 * (syll / len(words))


def _readability_score(value: Optional[float]) -> int:
    if value is None:
        return 0
    if value >= 60:
        return 30
    if value >= 40:
        return 20
    if value >= 20:
        return 10
    return 0


# ============================================================================
# Module entry
# ============================================================================

def run(args: ModuleArgs) -> ModuleResult:
    t0 = time.time()
    html = args.homepage_html or ""
    if not html or args.homepage_status != 200:
        return ModuleResult(
            name=NAME, score=0,
            ran_in_degraded_mode=True,
            skip_reason=f"homepage status {args.homepage_status}",
            duration_ms=int((time.time() - t0) * 1000),
        )

    text = _strip_html_to_text(html)
    lang = _detect_lang(html, args.lang)
    findings: list[Finding] = []
    actions: list[Finding] = []

    # A. EEAT
    eeat_score, eeat_findings, eeat_actions = _check_eeat(html)
    findings.extend(eeat_findings)
    actions.extend(eeat_actions)

    # B. AI-detection (heuristic by default).
    likelihood, hits = _ai_detect_heuristic(text, lang)
    ai_pts = _ai_detect_score(likelihood)
    if likelihood >= 0.5:
        actions.append(Finding(
            "P1", f"High AI-text signal ({int(likelihood * 100)}%)",
            f"Hits: {', '.join(hits[:5])}",
            "https://github.com/g-shevchenko/geo-audit/blob/main/docs/methodology.md#content",
        ))
    elif likelihood >= 0.25:
        actions.append(Finding(
            "P2", f"Moderate AI-text signal ({int(likelihood * 100)}%)",
            f"Hits: {', '.join(hits[:5])}",
        ))
    else:
        findings.append(Finding(
            "P3", f"Low AI-text signal ({int(likelihood * 100)}%)",
            f"Hits: {len(hits)}",
        ))

    # C. Readability.
    if lang == "ru":
        readability = _pushkin_readability(text)
        readability_label = "Pushkin"
    else:
        readability = _flesch_reading_ease(text)
        readability_label = "Flesch Reading Ease"
    read_pts = _readability_score(readability)
    if readability is not None:
        if read_pts >= 30:
            findings.append(Finding("P3", f"Good readability ({readability_label})", f"{readability:.1f}"))
        elif read_pts >= 10:
            actions.append(Finding("P2", f"Moderate readability — aim for ≥60 ({readability_label})", f"{readability:.1f}"))
        else:
            actions.append(Finding("P1", f"Low readability — aim for ≥60 ({readability_label})", f"{readability:.1f}"))
    else:
        actions.append(Finding("P2", "Readability could not be computed", "Not enough text content"))

    score = eeat_score + ai_pts + read_pts

    return ModuleResult(
        name=NAME,
        score=score,
        findings=findings,
        actions=actions,
        what_youd_get="Adding ANTHROPIC_API_KEY or OPENAI_API_KEY would unlock LLM-graded E-E-A-T (richer rubric)",
        duration_ms=int((time.time() - t0) * 1000),
        sub_scores={
            "eeat_score": eeat_score,
            "ai_detection_score": ai_pts,
            "ai_likelihood": round(likelihood, 3),
            "ai_hits_count": len(hits),
            "readability_score": read_pts,
            "readability_metric": readability_label,
            "readability_value": round(readability, 1) if readability is not None else None,
            "lang_detected": lang,
        },
    )
