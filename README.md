# geo-audit

> Open-source toolkit that scores any URL for **AI search visibility** —
> ChatGPT, Perplexity, Claude, Google AI Overviews, Bing Copilot, Yandex
> Neuro — and writes a prioritized action plan you can hand to your team.
>
> Built and maintained by [Humanswith.ai](https://humanswith.ai). Used on
> 40+ client projects in production. **MIT-licensed**.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Status: v0.2 working](https://img.shields.io/badge/Status-v0.2%20working-brightgreen.svg)](CHANGELOG.md)
[![Tests: 77 passing](https://img.shields.io/badge/tests-77%20passing-brightgreen.svg)](tests/)
[![OpenSSF Scorecard](https://img.shields.io/badge/OpenSSF-Scorecard%20pending-lightgrey.svg)](https://github.com/g-shevchenko/geo-audit/actions/workflows/scorecard.yml)

---

## What you get

```
$ geo-audit audit https://yoursite.com -o report/

==> Composite GEO Score: 73/100
    duration: 1.4s  |  modules used: 6/7
    skipped: brand-mentions

=== Per-module ===
  citability               80/100
  schema                   75/100
  llmstxt                  80/100
  crawlers                      —      (informational)
  technical                65/100
  content                  60/100
  brand-mentions                —      (degraded — no LLM key)

→ report/report.json   machine-readable, drop into CI / dashboards
→ report/report.md     full per-module breakdown with findings + actions
→ report/actions.md    prioritized P0–P3 action plan, client-shareable
→ report/report.pdf    optional, requires `pip install 'geo-audit[pdf]'`
```

**Bring your own keys (BYOK).** Every API key is OPTIONAL. Missing keys cause
specific modules to degrade gracefully with a clear hint about what they
would unlock — never a crash. Run `geo-audit doctor` to see your status.

| Module           | Scores                                                                                            | Required keys |
|------------------|---------------------------------------------------------------------------------------------------|---------------|
| `citability`     | LLM-citation likelihood: TL;DR, FAQ, numbered structure, source links, clear definitions (EN+RU)  | none          |
| `schema`         | JSON-LD validator + suggester (Article, FAQPage, HowTo, Organization, Person, Product…)           | none          |
| `llmstxt`        | Detects `/llms.txt`, `/llms-full.txt`, AI-bot access in robots.txt (GPTBot, ClaudeBot, …)         | none          |
| `crawlers`       | Full bot access map (AI / search / social) — informational                                        | none          |
| `technical`      | Indexability (HTTPS, sitemap, robots, canonical, SSR/SSG, viewport) + Core Web Vitals             | optional `PAGESPEED_API_KEY` (free) for CWV |
| `content`        | E-E-A-T signals + AI-detection (built-in heuristic) + readability (Flesch / Pushkin)              | none          |
| `brand-mentions` | Live brand mention scan in Claude / ChatGPT / Perplexity / Gemini                                 | any of `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `PERPLEXITY_API_KEY`, `GEMINI_API_KEY` |

---

## Verify before installing

This is a serious request. The repo has **no installer that runs without your
approval**. Before running anything, prove the repo matches its declared trust
profile:

### 1. Read what we promise

Plain English manifest of what we will and will not do:

- [`TRUST.md`](TRUST.md) — what's written, network calls, API keys, banned patterns
- [`trust/manifest.json`](trust/manifest.json) — same, machine-readable
- [`SECURITY.md`](SECURITY.md) — vulnerability disclosure policy
- [`PUBLIC_RELEASE_AUDIT.md`](PUBLIC_RELEASE_AUDIT.md) — what we audit before shipping

### 2. Run the trust check

```bash
git clone https://github.com/g-shevchenko/geo-audit.git
cd geo-audit
bash scripts/agent-preinstall-check.sh
```

Exit `0` means: no `curl … | bash`, no hardcoded secrets, no internal HWAI
infra references, required files present, no `sudo` in installer. Read the
script — it's 50 lines.

### 3. Inspect the installer

```bash
less scripts/install.sh        # 50 lines, explicit
less scripts/public-release-audit.sh  # 80 lines
```

### 4. Verify the tag (releases ≥ v0.2.0)

```bash
gh release download v0.2.0 -R g-shevchenko/geo-audit
sha256sum -c geo-audit-v0.2.0.sha256
gh attestation verify geo-audit-v0.2.0.tar.gz -R g-shevchenko/geo-audit
```

We never ask you to `curl … | bash`. If you see that pattern in third-party
docs about geo-audit — it's not us.

---

## Install

```bash
git clone https://github.com/g-shevchenko/geo-audit.git
cd geo-audit
bash scripts/install.sh
```

What it does, in order:

1. Re-runs `scripts/agent-preinstall-check.sh` and aborts on failure.
2. Creates a local `.venv/` (Python virtualenv). **Never** touches global pip.
3. `pip install -e .` to make the `geo-audit` CLI available inside `.venv/bin/`.
4. Creates `~/.cache/geo-audit/` for HTTP response caching (24h TTL).
5. Copies `.env.example` → `.env` if `.env` doesn't exist yet (all keys empty).
6. Prints the next-step instructions, including `geo-audit doctor`.

**No `sudo`. No PATH modification. No shell init file edits. No telemetry.**

Requirements:

- Python 3.10+
- Optional: `gh` CLI (for release verification only)
- Optional: WeasyPrint (`pip install 'geo-audit[pdf]'`) — only if you want PDFs

### Add to PATH (manual, opt-in)

```bash
echo 'export PATH="$PWD/.venv/bin:$PATH"' >> ~/.zshrc
```

We refuse to do this for you. Your shell init is yours.

---

## Quick audit

After `bash scripts/install.sh`:

```bash
# 1. See your key status & which modules will run.
.venv/bin/geo-audit doctor

# 2. Edit .env, paste any keys you have. All optional.
$EDITOR .env

# 3. Run an audit.
.venv/bin/geo-audit audit https://yoursite.com -o report/
```

You'll get four files in `report/`:

- `report.json` — machine-readable, schema-stable. Pipe into anything.
- `report.md` — full per-module breakdown.
- `actions.md` — P0–P3 action plan, client-shareable.
- `report.pdf` — optional, requires `pip install 'geo-audit[pdf]'` and `--pdf` flag.

### Pick specific modules

```bash
geo-audit audit https://yoursite.com --modules citability,schema,llmstxt -o out/
```

### Russian-language pages

```bash
geo-audit audit https://example.ru --lang ru -o out/
```

### Bypass cache (force refetch)

```bash
geo-audit audit https://yoursite.com --no-cache -o out/
```

---

## What this replaces

`geo-audit` exists because we got tired of stitching together expensive SaaS
tools to answer one question: **"will an LLM cite this page when a customer
asks about your category?"**

Below is what we replace, what we don't, and why we picked open-source.

### Direct competitors (paid SaaS we're replacing)

| Tool                                                                                       | Price (USD/mo)        | What it does (well)                                                              | What we cover                                                                  | What we don't (yet)                                       |
|--------------------------------------------------------------------------------------------|-----------------------|----------------------------------------------------------------------------------|--------------------------------------------------------------------------------|-----------------------------------------------------------|
| [Surfer SEO](https://surferseo.com)                                                        | 49 – 199              | Content briefs, NLP terms, on-page audit, content editor                         | Content audit, citability, schema, technical SEO checks                        | Real-time content editor with live NLP scoring             |
| [Frase](https://frase.io)                                                                  | 14.99 – 114.99        | Content briefs from SERP, AI writer, outline builder                             | Citability scoring, content structure analysis                                  | Inline AI writing assistant                                |
| [Profound](https://www.tryprofound.com)                                                    | 499+                  | Enterprise brand monitoring across LLMs                                          | `brand-mentions` module (when API keys are provided)                            | Multi-tenant dashboards, Slack alerts, role-based access   |
| [AI-Semantica](https://app.ai-semantica.com)                                               | 30 – 200              | AI-Visibility scanning, brand mentions in LLMs, SERP-vs-LLM gap                  | `brand-mentions` (smaller scope), `citability`                                  | Continuous monitoring, historical trend graphs             |
| [Goodie](https://goodie.app)                                                               | 99+                   | LLM citation tracking with notifications                                         | `brand-mentions` one-shot scan                                                  | Real-time webhooks                                         |
| [RankIQ](https://rankiq.com)                                                               | 49 – 199              | Content optimization for SEO bloggers                                            | `content`, `citability`, `schema`                                               | Niche-specific keyword libraries                           |
| [Lighthouse](https://developer.chrome.com/docs/lighthouse) (free)                           | 0                     | Core Web Vitals, accessibility, SEO basics                                       | `technical` module wraps Lighthouse for vitals only                            | Full Lighthouse a11y/PWA audit (use Lighthouse directly)   |
| [Schema.org Validator](https://validator.schema.org/) (free)                                | 0                     | JSON-LD validation                                                               | `schema` validates **and** suggests fixes for missing markup                    | —                                                          |

**Where we chose to be different:**

- **Open-source first.** You can read every scoring rule, fork it, prove it
  to your CTO. Surfer/Frase scoring is a black box.
- **One-shot, scriptable, CI-friendly.** No web dashboard you have to log into.
- **GEO-native, not "SEO with AI features bolted on".** Most tools above
  treat LLM visibility as an add-on. We treat it as the headline metric.
- **Composite score.** One 0–100 number for client reports + 6-module
  breakdown for engineers.

### Adjacent tools (we coexist, not replace)

| Tool                                                                                  | Role                          | Note                                                                                              |
|---------------------------------------------------------------------------------------|-------------------------------|---------------------------------------------------------------------------------------------------|
| [Ahrefs](https://ahrefs.com), [Semrush](https://semrush.com)                          | Keyword research, backlinks   | Use them for the **inputs** (which queries to audit). `geo-audit` scores the resulting pages.    |
| [Google Search Console](https://search.google.com/search-console)                     | Real impressions / clicks      | Truth source for what's actually ranking. We score *page quality*, not rank.                     |
| [Yandex Webmaster](https://webmaster.yandex.com)                                      | Russian SERP monitoring        | Required if you target RU. We don't replace it.                                                   |
| [Google Indexing API](https://developers.google.com/search/apis/indexing-api)         | Force-indexing                 | Run this **after** a `geo-audit` pass surfaces issues.                                            |
| [Pitchbox](https://pitchbox.com), [BuzzStream](https://buzzstream.com)                | Outreach pipelines             | Different category — we score the page, they handle email outreach.                              |
| [Crawl4AI](https://github.com/unclecode/crawl4ai), [Firecrawl](https://firecrawl.dev) | Generic web scraping           | We use Crawl4AI internally for the `technical` and `content` modules.                            |

---

## How it's organized

`geo-audit` is a **CLI dispatcher**. Each module is a self-contained Python
package with a documented contract; modules don't know about each other.

```
geo-audit/
├── README.md                         ← you are here
├── LICENSE                           ← MIT
├── VERSION                           ← single source of truth for version
├── CHANGELOG.md
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── SECURITY.md                       ← vuln reporting policy
├── TRUST.md                          ← human-readable trust manifest
├── PUBLIC_RELEASE_AUDIT.md           ← what we audit before each release
│
├── trust/
│   └── manifest.json                 ← machine-readable trust profile
│
├── scripts/
│   ├── install.sh                    ← local-only, no sudo
│   ├── agent-preinstall-check.sh     ← trust profile verifier (run BEFORE install)
│   └── public-release-audit.sh       ← repo-wide audit (run BEFORE git push)
│
├── geo_audit/                        ← Python package (CLI + dispatch)
│   ├── cli.py                        ← argparse, module registry
│   ├── report.py                     ← PDF/JSON/MD writer
│   └── modules/
│       ├── citability.py             ← LLM-citation scoring (open-source)
│       ├── schema.py                 ← JSON-LD validator + suggester
│       ├── llmstxt.py                ← /llms.txt detection + generation
│       ├── brand_mentions.py         ← multi-LLM brand scan (opt-in)
│       ├── technical.py              ← Lighthouse + SSR check
│       └── content.py                ← Binoculars + readability + EEAT
│
├── docs/
│   ├── methodology.md                ← how each score is computed
│   ├── modules.md                    ← per-module specs and flags
│   ├── integrations.md               ← Claude Code skill, n8n, GitHub Action
│   ├── comparison.md                 ← detailed feature matrix vs paid tools
│   └── external-services.md          ← optional API keys, what each unlocks
│
├── .github/
│   ├── workflows/
│   │   ├── preinstall-check.yml      ← runs trust profile on every PR
│   │   └── scorecard.yml             ← OpenSSF Scorecard
│   ├── dependabot.yml
│   ├── ISSUE_TEMPLATE/
│   └── PULL_REQUEST_TEMPLATE.md
│
└── tests/                            ← pytest, smoke + unit
```

### Design decisions you can argue with

1. **Python + Node split.** Python for orchestration and string-heavy work
   (schema validation, AI-detection scoring). Node for browser automation
   (Playwright, Lighthouse). Splitting beats trying to do Playwright from
   Python (`playwright-python` is fine, but Lighthouse runs better on Node).

2. **Per-module isolation.** Each module reads a URL + `Args`, returns a
   `ModuleResult`. Adding a 7th module is one file + one entry in the
   registry. No shared state, no implicit ordering.

3. **No vector DB, no embeddings.** Citability scoring uses deterministic
   rules (regex + structure heuristics) and a small open-source classifier
   (Binoculars). We considered embeddings — rejected because reproducibility
   matters more than 5% accuracy gain.

4. **Markdown-first reports.** PDF is generated from a Markdown intermediate.
   You can pipe `report.md` through your own template engine if you don't
   want our PDF style.

5. **Sharp design, dark UI.** PDF reports use a Pantheon-style design system
   (Instrument Serif italic + Inter + JetBrains Mono, sharp 2px borders,
   cyan accent). Source: [`docs/integrations.md#pdf-styling`](docs/integrations.md).

---

## External services — all optional, all opt-in

`geo-audit` works **fully offline against open-source resources** by default.
Modules that benefit from external APIs gracefully degrade if the key is
missing.

| Service                                                                             | Module           | What it unlocks                                       | Free tier?                                  |
|-------------------------------------------------------------------------------------|------------------|-------------------------------------------------------|---------------------------------------------|
| [Google PageSpeed Insights](https://developers.google.com/speed/docs/insights/v5)   | `technical`      | Higher rate limits for Core Web Vitals queries        | Yes, generous (25k/day)                     |
| [OpenAI API](https://platform.openai.com)                                           | `brand-mentions` | Live ChatGPT mention check                            | No (pay-per-token, ~$0.001/audit)           |
| [Anthropic API](https://docs.anthropic.com)                                         | `brand-mentions` | Live Claude mention check                             | No (~$0.001/audit)                           |
| [Perplexity API](https://docs.perplexity.ai)                                        | `brand-mentions` | Live Perplexity citation check                        | No (~$0.005/audit)                           |
| [Tavily Search API](https://tavily.com)                                             | `brand-mentions` | LLM-friendly web search for context expansion         | Yes, 1k searches/mo                          |
| [Serper.dev](https://serper.dev)                                                    | `brand-mentions` | Google SERP fetcher (cheaper than ScrapingBee)        | No (~$0.001/query, $50/mo for 50k)           |
| [SearXNG](https://docs.searxng.org)                                                 | `brand-mentions` | Self-hosted meta-search, alternative to Serper        | Free (self-hosted, ~$5/mo VPS)               |

**Full configuration guide:** [`docs/external-services.md`](docs/external-services.md).

The audit will tell you exactly which modules ran in degraded mode and what
key would have unlocked the full check.

---

## Open-source dependencies (bundled)

Core libraries we depend on:

- [`cheerio`](https://cheerio.js.org) — server-side HTML parsing
- [`playwright`](https://playwright.dev) — browser automation, JS rendering, CWV
- [`lighthouse`](https://github.com/GoogleChrome/lighthouse) — Web Vitals scoring
- [`jsonschema`](https://github.com/python-jsonschema/jsonschema) — JSON-LD validation
- [`textstat`](https://github.com/textstat/textstat) — readability metrics
- [`binoculars-llm`](https://github.com/AHans30/Binoculars) — open-source AI-detection (MIT)
- [`weasyprint`](https://weasyprint.org) — Markdown → PDF rendering

Full list with pinned versions: [`requirements.txt`](requirements.txt) +
[`package.json`](package.json).

We pin everything to specific versions. We do not use `latest`.

---

## Documentation

- [`docs/methodology.md`](docs/methodology.md) — how each score is computed
- [`docs/modules.md`](docs/modules.md) — per-module specs, flags, output schema
- [`docs/integrations.md`](docs/integrations.md) — Claude Code skill, n8n node, GitHub Action
- [`docs/comparison.md`](docs/comparison.md) — detailed feature matrix vs paid tools
- [`docs/external-services.md`](docs/external-services.md) — optional API keys, what each unlocks
- [`TRUST.md`](TRUST.md) — what we write, what we call, what we never do
- [`SECURITY.md`](SECURITY.md) — vulnerability disclosure
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — how to add a module or fix a score
- [`CHANGELOG.md`](CHANGELOG.md) — versioned changes

---

## Roadmap

| Version       | Status            | Highlights                                                                         |
|---------------|-------------------|------------------------------------------------------------------------------------|
| **v0.1**      | April 2026 (now)  | Skeleton, TRUST manifest, README + docs, install scaffolding, CI workflows         |
| v0.2          | May 2026          | First working modules (`citability`, `schema`, `llmstxt`), `report.json` format    |
| v0.3          | June 2026         | `technical` (Lighthouse + SSR), `content` (EEAT + AI-detection)                    |
| v0.4          | July 2026         | `brand-mentions` with all 4 LLM providers, n8n node                                |
| v0.5          | August 2026       | GitHub Action, multi-language reports (RU, EN, DE, ES, AR)                         |
| v1.0          | Q4 2026           | Stable API, semver, plugin system for custom modules                               |

This roadmap is a public commitment. Slips will be documented in
[`CHANGELOG.md`](CHANGELOG.md) with reasons.

---

## Contributing

PRs welcome. Read [`CONTRIBUTING.md`](CONTRIBUTING.md) before opening one.

Short version:
1. Open an issue describing the change first.
2. `bash scripts/agent-preinstall-check.sh` and `bash scripts/public-release-audit.sh` must pass.
3. Add a test case for any module behavior change.
4. Sign your commit (`git commit -s`).
5. Be ready to discuss — we say no to features that bloat scope.

---

## Security

Found a vulnerability? Email **security@humanswith.ai** rather than opening
a public issue. Full policy: [`SECURITY.md`](SECURITY.md).

We treat as a security issue:
- Hardcoded credentials in any commit
- Code that exfiltrates audit target data
- Privilege escalation in the installer

We do **not** treat as security issues:
- Bugs in audit accuracy (use the issue tracker)
- Performance regressions
- Requests for new modules

---

## License

MIT. See [`LICENSE`](LICENSE). Use freely, fork, modify, sell. Attribution
appreciated but not required.

If you ship a product that uses `geo-audit` internally, we'd love to hear
about it on [`@gshevchenko_humanswith_ai`](https://t.me/gshevchenko_humanswith_ai)
or via [humanswith.ai](https://humanswith.ai).

---

## Authors

[Humanswith.ai](https://humanswith.ai) — AI-marketing agency based in Dubai,
UAE. We use this on 40+ client projects daily.

Founder & maintainer: **Gregory Shevchenko**
- Telegram channel: [@gshevchenko_humanswith_ai](https://t.me/gshevchenko_humanswith_ai)
- Personal: [@gshevchenko](https://t.me/gshevchenko)

If you're hiring an AI-marketing agency: [humanswith.ai](https://humanswith.ai).
If you just want the tool to work: clone, install, audit — no sales pitch on
the way.
