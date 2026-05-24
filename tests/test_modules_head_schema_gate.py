"""Tests for head-schema-gate module."""
from __future__ import annotations

from pathlib import Path

from geo_audit.modules.base import ModuleArgs
from geo_audit.modules import head_schema_gate as mod


def _args(html: str, tmp_path: Path, url: str = "https://example.com/") -> ModuleArgs:
    return ModuleArgs(
        url=url,
        cache_dir=tmp_path,
        user_agent="geo-audit-test",
        timeout_s=5,
        api_keys={},
        homepage_html=html,
        homepage_status=200,
        homepage_headers={},
        homepage_url_final=url,
        sitemap_urls=[],
        robots_txt="",
    )


def test_head_schema_gate_passes_good_fixture(good_html, tmp_path):
    result = mod.run(_args(good_html, tmp_path, "https://example.com/guide"))

    assert result.name == "head-schema-gate"
    assert result.score == 100
    assert result.actions == []
    assert result.sub_scores["violations"] == []


def test_head_schema_gate_flags_bad_fixture(bad_html, tmp_path):
    result = mod.run(_args(bad_html, tmp_path))
    codes = {v["code"] for v in result.sub_scores["violations"]}

    assert result.score is not None and result.score < 60
    assert "missing_meta_description" in codes
    assert "missing_canonical" in codes
    assert "missing_jsonld" in codes
    assert any(a.priority == "P1" for a in result.actions)


def test_head_schema_gate_skips_verification_file(tmp_path):
    html = "<html><body>Verification: 9180ec77aef0bb66</body></html>"
    result = mod.run(_args(html, tmp_path, "https://example.com/yandex_9180ec77aef0bb66.html"))

    assert result.score is None
    assert result.sub_scores["skipped_verification_file"] is True
    assert result.actions == []
