"""Module registry — central place to register all geo-audit modules.

Order matters for default execution: cheap+offline first, network heavier last.
"""
from __future__ import annotations

from types import ModuleType
from typing import Optional

from geo_audit.modules import schema as schema_mod
from geo_audit.modules import llmstxt as llmstxt_mod
from geo_audit.modules import crawlers as crawlers_mod
from geo_audit.modules import technical as technical_mod
from geo_audit.modules import citability as citability_mod
from geo_audit.modules import content as content_mod
from geo_audit.modules import brand_mentions as brand_mod


REGISTRY: dict[str, ModuleType] = {
    schema_mod.NAME:     schema_mod,
    llmstxt_mod.NAME:    llmstxt_mod,
    crawlers_mod.NAME:   crawlers_mod,
    technical_mod.NAME:  technical_mod,
    citability_mod.NAME: citability_mod,
    content_mod.NAME:    content_mod,
    brand_mod.NAME:      brand_mod,
}


DEFAULT_ORDER = [
    "schema", "llmstxt", "crawlers", "citability", "content", "technical", "brand-mentions",
]


def get(name: str) -> Optional[ModuleType]:
    return REGISTRY.get(name)


def list_modules() -> list[ModuleType]:
    return [REGISTRY[n] for n in DEFAULT_ORDER if n in REGISTRY]
