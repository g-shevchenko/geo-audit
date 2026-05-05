# Changelog

All notable changes to `geo-audit` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.2.0] — 2026-05-05

First working release. Implements the full v0.1 methodology spec with seven
modules and end-to-end CLI.

### Added

- **`geo_audit/` Python package** — installable via `pip install -e .` after
  cloning. Entry points: `geo-audit audit URL`, `geo-audit doctor`, `geo-audit version`.
- **Seven modules** covering the methodology in `docs/methodology.md`:
  - `citability` (weight 25) — fully offline 5-rubric heuristic: TL;DR, FAQ,
    numbered structure, source links, clear definitions. EN + RU.
  - `schema` (weight 15) — JSON-LD parse + 8 sub-checks (Article, Organization,
    FAQPage, HowTo, Person, BreadcrumbList, Product+rating, no parse errors).
  - `llmstxt` (weight 10) — probes `/llms.txt` and `/llms-full.txt`, parses
    robots.txt for AI-bot allow status (GPTBot, ClaudeBot, PerplexityBot,
    Google-Extended, etc.).
  - `crawlers` (informational, weight 0) — full bot access map (AI assistants,
    search engines, social previews) from a single robots.txt.
  - `technical` (weight 15) — indexability (50pt: HTTPS+HSTS, sitemap, robots,
    canonical, SSR/SSG, mobile viewport) + Core Web Vitals via PageSpeed
    Insights (50pt; gracefully reports 0 without `PAGESPEED_API_KEY`).
  - `content` (weight 15) — E-E-A-T (40pt: author, dates, outbound links,
    contact), AI-detection (30pt: built-in lexical heuristic — no heavy ML
    dep), readability (30pt: Flesch for EN, Pushkin for RU).
  - `brand-mentions` (weight 20) — live multi-platform scan via Anthropic
    Claude / OpenAI ChatGPT / Perplexity Sonar / Google Gemini. Each provider
    is independent — failure in one does not block the others.
- **BYOK pattern** — every API key is OPTIONAL. Missing keys cause modules to
  degrade gracefully with a `what_youd_get` hint. Run `geo-audit doctor` to
  see which modules become active for the keys you have.
- **Provider-agnostic LLM client** (`geo_audit/llm.py`) — direct HTTP, no
  third-party SDK dependency. Supports Anthropic, OpenAI, Perplexity, Gemini.
- **Composite scoring** per the published methodology (sum to 100, modules in
  degraded mode are excluded).
- **Three output formats** in every audit run:
  - `report.json` — canonical, schema-stable, machine-readable.
  - `report.md` — full per-module breakdown with findings + actions.
  - `actions.md` — P0–P3 prioritized action plan, client-shareable.
  - `report.pdf` — optional, requires `pip install 'geo-audit[pdf]'`.
- **Cache layer** — homepage / robots / sitemap fetches cached 24h in
  `~/.cache/geo-audit/`. Bypass with `--no-cache`.
- **Test suite** — 77 tests covering each module + scoring + crawler + e2e
  orchestrator with mocked HTTP. Bilingual EN+RU fixtures.
- **Updated `.env.example`** — every key now documents what it unlocks, where
  to register, and free-tier availability.
- **Updated `install.sh`** — runs the preinstall trust check, creates venv,
  copies `.env.example` → `.env`, prints next steps.

### Changed

- `VERSION` bumped to `0.2.0`.
- `trust/manifest.json` updated to v0.2 — added Gemini, Tavily, Yandex.XML;
  reflects the new provider-agnostic LLM client surface.
- README rewritten to show realistic example output and accurate "Quick start"
  flow that matches the shipping CLI.

### Notes

- Methodology version remains **`1`** — formulas are unchanged from v0.1's
  published spec. Only the implementation arrived.
- Score reproducibility guarantee: same URL × same keys × same version → score
  within ±2 points (verified by `tests/test_orchestrator.py::test_e2e_deterministic`).
- Cost transparency: each LLM call is metered against published list pricing
  in `geo_audit/llm.py::PRICING` and surfaced in
  `report.json.modules[].sub_scores.estimated_cost_usd`.

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

[Unreleased]: https://github.com/g-shevchenko/geo-audit/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/g-shevchenko/geo-audit/releases/tag/v0.2.0
[0.1.0]: https://github.com/g-shevchenko/geo-audit/releases/tag/v0.1.0
