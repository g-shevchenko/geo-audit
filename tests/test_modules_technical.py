"""Tests for technical module — indexability + CWV stub."""
from __future__ import annotations

from geo_audit.modules import technical as mod
from geo_audit.modules.base import ModuleArgs


def _args(html: str = "", **kw) -> ModuleArgs:
    args = dict(
        url="https://example.com/",
        homepage_html=html,
        homepage_status=200,
        homepage_url_final="https://example.com/",
        homepage_headers={"strict-transport-security": "max-age=31536000"},
        sitemap_urls=["https://example.com/", "https://example.com/about"],
        robots_txt="User-agent: *\nAllow: /\n",
    )
    args.update(kw)
    return ModuleArgs(**args)


def test_good_page_full_indexability(good_html):
    result = mod.run(_args(good_html))
    # Indexability should max at 50; CWV is 0 without PSI key.
    assert result.sub_scores["indexability_score"] == 50
    assert result.sub_scores["cwv_score"] == 0
    assert result.score == 50  # 50 indexability + 0 CWV


def test_lcp_scoring():
    assert mod._score_lcp(2.0) == 20
    assert mod._score_lcp(3.0) == 10
    assert mod._score_lcp(5.0) == 0
    assert mod._score_lcp(None) == 0


def test_inp_scoring():
    assert mod._score_inp(150) == 15
    assert mod._score_inp(300) == 7
    assert mod._score_inp(700) == 0


def test_cls_scoring():
    assert mod._score_cls(0.05) == 15
    assert mod._score_cls(0.15) == 7
    assert mod._score_cls(0.3) == 0


def test_blanket_disallow_robots(good_html):
    blocking = "User-agent: *\nDisallow: /\n"
    result = mod.run(_args(good_html, robots_txt=blocking))
    p0s = [a for a in result.actions if a.priority == "P0"]
    assert any("blanket Disallow" in a.title for a in p0s)


def test_no_sitemap_action(good_html):
    result = mod.run(_args(good_html, sitemap_urls=[]))
    p1s = [a for a in result.actions if a.priority == "P1"]
    assert any("sitemap" in a.title.lower() for a in p1s)


def test_empty_spa_low_indexability(empty_spa_html):
    result = mod.run(_args(empty_spa_html))
    # No content in initial HTML → P0 action.
    p0s = [a for a in result.actions if a.priority == "P0"]
    assert any("renders empty" in a.title for a in p0s)


def test_cwv_extract_from_psi_field_data():
    psi = {
        "loadingExperience": {"metrics": {
            "LARGEST_CONTENTFUL_PAINT_MS": {"percentile": 1800},
            "INTERACTION_TO_NEXT_PAINT": {"percentile": 150},
            "CUMULATIVE_LAYOUT_SHIFT_SCORE": {"percentile": 5},
        }}
    }
    cwv = mod._extract_cwv_from_psi(psi)
    assert cwv["lcp_s"] == 1.8
    assert cwv["inp_ms"] == 150.0
    assert cwv["cls"] == 0.05
