"""Tests for config loading + .env parsing."""
from __future__ import annotations

from pathlib import Path

import pytest

from geo_audit.config import load_dotenv, load_config


def test_dotenv_basic(tmp_path):
    p = tmp_path / ".env"
    p.write_text("ANTHROPIC_API_KEY=sk-test-1\n# comment\nFOO=bar\n", encoding="utf-8")
    env = load_dotenv(p)
    assert env["ANTHROPIC_API_KEY"] == "sk-test-1"
    assert env["FOO"] == "bar"


def test_dotenv_strips_quotes(tmp_path):
    p = tmp_path / ".env"
    p.write_text('OPENAI_API_KEY="sk-quoted"\n', encoding="utf-8")
    env = load_dotenv(p)
    assert env["OPENAI_API_KEY"] == "sk-quoted"


def test_dotenv_missing_returns_empty(tmp_path):
    assert load_dotenv(tmp_path / "missing.env") == {}


def test_config_no_keys(monkeypatch, tmp_path):
    cfg = load_config(env_path=tmp_path / "missing.env")
    assert cfg.keys_present() == []
    assert "ANTHROPIC_API_KEY" in cfg.keys_missing()


def test_config_env_overrides_dotenv(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("ANTHROPIC_API_KEY=from-file\n", encoding="utf-8")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "from-env")
    cfg = load_config(env_path=env_file)
    assert cfg.api_keys["ANTHROPIC_API_KEY"] == "from-env"


def test_has_any():
    from geo_audit.config import Config
    cfg = Config()
    cfg.api_keys = {"ANTHROPIC_API_KEY": "sk-x", "OPENAI_API_KEY": None}
    assert cfg.has_any(["ANTHROPIC_API_KEY", "OPENAI_API_KEY"]) is True
    assert cfg.has_any(["OPENAI_API_KEY"]) is False
