# Changelog

All notable changes to `geo-audit` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

Working toward v0.2 — see [README roadmap](README.md#roadmap).

---

## [0.1.0] — 2026-04-28

Initial public release. Skeleton + documentation + trust scaffolding.

### Added

- Repository skeleton with verify-first README.
- Trust posture documentation:
  - `TRUST.md` — human-readable trust manifest
  - `trust/manifest.json` — machine-readable trust profile
  - `scripts/agent-preinstall-check.sh` — automated trust verifier
  - `SECURITY.md` — vulnerability disclosure policy
  - `PUBLIC_RELEASE_AUDIT.md` + `scripts/public-release-audit.sh` — pre-publish audit
- Installer scaffolding (`scripts/install.sh`):
  - Local-only `.venv/` and `node_modules/`
  - No `sudo`, no PATH modification, no shell init edits
  - Re-runs trust check before any install action
- Documentation:
  - `docs/methodology.md` — score computation specs
  - `docs/modules.md` — per-module contract
  - `docs/integrations.md` — Claude Code skill, n8n, GitHub Action
  - `docs/comparison.md` — detailed feature matrix vs Surfer SEO, Frase, Profound, etc.
  - `docs/external-services.md` — optional API key configuration
- Repository hygiene:
  - `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`
  - `.gitignore`, `VERSION`, `CHANGELOG.md`
  - Issue templates, PR template, CODEOWNERS
  - Dependabot configuration
  - GitHub Actions workflows: trust check on PRs, OpenSSF Scorecard

### Not yet implemented (coming v0.2)

- `geo_audit/` Python package (CLI + module dispatch)
- `modules/citability.py` — LLM-citation scoring
- `modules/schema.py` — JSON-LD validator + suggester
- `modules/llmstxt.py` — `/llms.txt` generator
- `modules/brand-mentions.py` — multi-LLM brand scan
- `modules/technical.py` — Core Web Vitals + SSR check
- `modules/content.py` — EEAT + AI-detection + readability
- `requirements.txt` + `package.json` with pinned versions
- `tests/` — pytest smoke + unit tests

### Why ship a skeleton

Two reasons:

1. **Trust posture comes first.** A repo with a strong `TRUST.md`, machine-readable
   manifest, and automated preinstall check teaches users to expect this from
   any installable open-source tool — including ours. Shipping the
   verification surface before the implementation forces us to never break it.

2. **Public commitment.** Tagging v0.1.0 with a public roadmap forces honesty.
   If we slip v0.2, it's visible. If we change direction, the changelog says
   so. This is harder than shipping silently and easier than shipping
   without accountability.

Star/watch the repo to track v0.2.

[Unreleased]: https://github.com/g-shevchenko/geo-audit/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/g-shevchenko/geo-audit/releases/tag/v0.1.0
