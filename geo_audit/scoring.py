"""Composite GEO score: weighted average of module sub-scores.

Per docs/methodology.md:
  GEO Score = Σ (module_score × weight) / Σ (weight) for modules that ran

Modules in degraded mode (skip_reason set) are EXCLUDED from the composite.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from geo_audit.modules.base import ModuleResult


# Weights from docs/methodology.md. Sum = 100.
WEIGHTS: dict[str, int] = {
    "citability":     25,
    "schema":         15,
    "llmstxt":        10,
    "brand-mentions": 20,
    "technical":      15,
    "content":        15,
}


@dataclass
class CompositeScore:
    score: int                   # 0–100
    methodology_version: str     # e.g. "1"
    modules_used: list[str]
    modules_skipped: list[str]
    weights_used: dict[str, int]


def compute_composite(results: Iterable[ModuleResult], methodology_version: str) -> CompositeScore:
    used: dict[str, int] = {}
    skipped: list[str] = []
    weighted_sum = 0
    weight_total = 0

    for r in results:
        w = WEIGHTS.get(r.name, 0)
        if w == 0:
            # platform-readiness is a derived view, not part of composite.
            continue
        if r.score is None or r.ran_in_degraded_mode:
            skipped.append(r.name)
            continue
        used[r.name] = r.score
        weighted_sum += r.score * w
        weight_total += w

    composite = int(round(weighted_sum / weight_total)) if weight_total > 0 else 0
    return CompositeScore(
        score=composite,
        methodology_version=methodology_version,
        modules_used=list(used.keys()),
        modules_skipped=skipped,
        weights_used={k: WEIGHTS[k] for k in used},
    )
