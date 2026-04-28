# geo-audit

> Open-source GEO (Generative Engine Optimization) audit toolkit by [Humanswith.ai](https://humanswith.ai).
> Score your site for AI search visibility (ChatGPT, Perplexity, Claude, Gemini, AI Overviews) and get a prioritized action plan.

**License:** MIT · **Status:** v0.1 (April 2026) · **Author:** [Humanswith.ai](https://humanswith.ai)

## What it does

Runs a full audit of any URL across 6 dimensions, produces a composite GEO Score (0–100), and writes a PDF + JSON report with prioritized action items (P0–P3).

| Module | Checks |
|--------|--------|
| `citability` | LLM-citation scoring: TL;DR, FAQ blocks, numbered structure, source links, clear definitions |
| `schema` | JSON-LD validator + suggester (Article, FAQPage, HowTo, Organization, Person, etc.) |
| `llmstxt` | Detects/generates `/llms.txt` and `/llms-full.txt` per [llmstxt.org](https://llmstxt.org) |
| `brand-mentions` | Scans ChatGPT, Perplexity, Claude, Gemini for current brand mentions |
| `technical` | Core Web Vitals (LCP, INP, CLS), SSR/SSG check, mobile-first, sitemap, robots, hreflang |
| `content` | EEAT signals, AI-detection, readability, uniqueness |

## Verify before installing

This repository has no installer that runs without your approval. Before running anything:

1. **Read the manifest:** [`TRUST.md`](TRUST.md) — declares expected file writes, network calls, and forbidden patterns.
2. **Run the preinstall checker:**
   ```bash
   bash scripts/agent-preinstall-check.sh
   ```
   Returns `0` if the repo matches its declared trust profile, non-zero otherwise.
3. **Inspect the install script** before sourcing:
   ```bash
   less scripts/install.sh
   ```

We never use `curl … | bash` style installers. Tagged releases include checksums and build provenance.

## Install

```bash
git clone https://github.com/g-shevchenko/geo-audit.git
cd geo-audit
bash scripts/install.sh        # creates .venv, installs deps, no sudo
```

Requirements: Python 3.10+, Node 20+, Chromium (auto-installed by Playwright).

## Quick audit

```bash
geo-audit https://yoursite.com \
  --depth full \
  --output report.pdf \
  --modules citability,schema,llmstxt,brand-mentions,technical,content
```

Output:
- `report.pdf` — client-ready PDF with composite score + breakdown
- `report.json` — machine-readable, for CI/dashboards
- `actions.md` — prioritized P0–P3 list

## Quick checks (no install)

For one-off checks without cloning:

```bash
# Citability score for a single URL (LLM-friendliness 0–100)
curl -sS https://yoursite.com | python3 -c "
import sys, re
text = sys.stdin.read()
score = 0
if re.search(r'<meta[^>]+description=', text): score += 10
if re.search(r'<h2', text, re.I): score += 10
if re.search(r'application/ld\+json', text): score += 20
print(f'Quick score: {score}/40 (full audit gives 0–100)')
"
```

For the full audit, install above.

## Documentation

- [`docs/methodology.md`](docs/methodology.md) — how scores are computed
- [`docs/modules.md`](docs/modules.md) — per-module specs
- [`docs/integrations.md`](docs/integrations.md) — Claude Code skill, n8n node, GitHub Action
- [`TRUST.md`](TRUST.md) — security and trust manifest

## Comparable paid tools

| Tool | Price | What it covers |
|------|-------|----------------|
| Surfer SEO | $49–199/mo | content briefs + technical SEO |
| Frase | $14.99–114.99/mo | content briefs + AI writer |
| AI-Semantica | $30–200/mo | brand mentions in LLMs (we recommend it as the paid path until our `brand-mentions` module reaches feature parity) |
| Profound | $499+/mo | enterprise brand monitoring |

`geo-audit` covers ~70% of these for $0 + your compute. See [`docs/comparison.md`](docs/comparison.md).

## Roadmap

- v0.2 (May 2026) — `n8n` node, GitHub Action for CI integration
- v0.3 (June 2026) — `brand-mentions` module reaches feature parity with AI-Semantica
- v0.4 (July 2026) — multi-language: RU, EN, DE, ES, AR (current: EN + RU only)

## Contributing

PRs welcome. Please:
1. Open an issue describing the change before sending PR.
2. Run `bash scripts/test.sh` locally — must pass.
3. Add a test case for any new module behavior.
4. Sign your commit (`git commit -s`).

## Security

If you find a security issue, please email **security@humanswith.ai** rather than opening a public issue. See [`SECURITY.md`](SECURITY.md).

## License

MIT — see [`LICENSE`](LICENSE). Use freely, fork, modify. Attribution appreciated but not required.

## Authors

[Humanswith.ai](https://humanswith.ai) — AI-marketing agency based in Dubai. We use this on 40+ client projects daily.

Founder: [Gregory Shevchenko](https://t.me/gshevchenko_humanswith_ai)
