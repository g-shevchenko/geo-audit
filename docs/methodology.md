# Scoring methodology

How `geo-audit` computes the composite GEO Score (0–100) and per-module
sub-scores. Open-source, deterministic, replicable.

> **Status:** v0.1 specifies the methodology. v0.2 ships the implementation.
> The numbers below are what we'll implement. If we deviate, we'll update
> this doc and the [`CHANGELOG.md`](../CHANGELOG.md).

## Composite GEO Score

```
GEO Score = Σ (module_score × module_weight) for each module that ran
            ÷ Σ (module_weight) for each module that ran
```

If a module ran in degraded mode (missing API key, network failure), it's
**excluded from the composite** — not scored as zero. The report flags
which modules were excluded.

### Weights

| Module           | Weight | Rationale                                                  |
|------------------|--------|------------------------------------------------------------|
| `citability`     | 25     | The headline metric. If LLMs won't cite the page, GEO fails. |
| `schema`         | 15     | High-signal, automatable, often the cheapest fix.          |
| `llmstxt`        | 10     | Emerging standard, low cost to implement, growing impact.  |
| `brand-mentions` | 20     | Real-world proof of GEO outcomes.                          |
| `technical`      | 15     | Required floor — slow/uncrawlable pages don't get cited.   |
| `content`        | 15     | EEAT signals + AI-detection. Without these, traffic is fragile. |

Weights sum to 100. Reweighting requires a methodology RFC and a major
version bump.

## Per-module scoring

### `citability` (0–100)

Five sub-checks, each contributing equal weight:

| Sub-check         | What we score                                                     | Max |
|-------------------|-------------------------------------------------------------------|-----|
| TL;DR present     | First paragraph contains a direct answer to the page's main query | 25  |
| FAQ block         | At least 5 question-answer pairs in semantic markup               | 20  |
| Numbered structure| Lists/steps with explicit numbering                               | 15  |
| Source links      | At least 2 outbound links to authoritative sources                | 20  |
| Clear definitions | "X — это Y" / "X is Y" pattern in the first 500 words             | 20  |

**Why these five:** they're what we observed actually gets cited in
ChatGPT/Perplexity outputs across 2,000+ pages we audited at Humanswith.ai
in 2025–2026.

### `schema` (0–100)

JSON-LD validation + suggestion. Score = (passing checks ÷ applicable checks) × 100.

- Primary page schema (15):
  - article pages: `Article` or `BlogPosting` with `author.sameAs`
  - hub/index pages: `CollectionPage` with `hasPart`, `mainEntity`, `about`, or `mentions`
- `Organization` on homepage with `sameAs` to social profiles (15)
- `FAQPage` for FAQ blocks (15)
- `HowTo` for stepped instructions (10)
- `Person` with `jobTitle, worksFor` for author pages (10)
- `BreadcrumbList` on nested pages (10)
- `Product` + `AggregateRating` for product cards (15)
- No `errors` from schema.org validator (10)

We validate against the canonical [Schema.org](https://schema.org) types,
not Google-specific extensions. Unrecognized types are warnings, not errors.

### `llmstxt` (0–100)

- `/llms.txt` present and valid (50)
- `/llms-full.txt` present and ≥50% of indexable content (30)
- AI-bot access in `robots.txt` (GPTBot, ClaudeBot, PerplexityBot, Google-Extended) (20)

Spec: [llmstxt.org](https://llmstxt.org). Honesty: `llms.txt` is an
inference-time content index, **not** a ranking signal — no major AI
engine officially consumes a third-party `llms.txt` and Google has
stated it does not use it. Scored as a controlled-narrative +
AI-readiness signal, not predicted ranking. `/llms-full.txt` is a
community convention (not in the spec). Validity follows the spec — the
H1 is the only required element. See
[docs/llmstxt-conformance.md](llmstxt-conformance.md).

### `brand-mentions` (0–100)

For each LLM provider you have API access to (ChatGPT, Claude, Perplexity,
Gemini), we run a controlled query about the brand and count:

- Does the brand appear by name? (40 each provider, normalized)
- Is your URL cited as a source? (40 each provider, normalized)
- Is the description accurate? (20 each provider, normalized — humans verify)

Final score = average across providers that ran.

If no API keys are provided, this module reports `score: null` and is
excluded from the composite.

### `technical` (0–100)

Two halves:

**A. Core Web Vitals (50 points)**, via Lighthouse:
- LCP < 2.5s (mobile) → 20 / LCP < 4s → 10 / else 0
- INP < 200ms → 15 / INP < 500ms → 7 / else 0
- CLS < 0.1 → 15 / CLS < 0.25 → 7 / else 0

**B. Indexability (50 points)**:
- HTTPS + HSTS (10)
- Valid `sitemap.xml` (10)
- Valid `robots.txt` with no blanket disallow (10)
- Canonical present and valid (5)
- SSR/SSG: content present in initial HTML (10)
- Mobile viewport meta (5)

### `content` (0–100)

Three sub-checks:

**A. EEAT signals (40 points)**:
- Author byline with photo + bio (10)
- Date published + last updated (10)
- Outbound links to sources (10)
- Contact info on the page or in footer (10)

**B. AI-detection (30 points)** via [Binoculars](https://github.com/AHans30/Binoculars):
- AI-likelihood < 25% → 30
- 25–50% → 15
- 50–75% → 5
- 75–100% → 0

**C. Readability (30 points)** via `textstat`:
- Flesch Reading Ease ≥ 60 → 30
- 40–60 → 20
- 20–40 → 10
- < 20 → 0

(For Russian-language pages, we use Pushkin readability adapted for Cyrillic
instead of Flesch — see `docs/modules.md#content` for details.)

## Why deterministic, not embeddings-based

We considered embedding-based citability scoring. Rejected:

1. **Reproducibility.** A score must reproduce on the same input one year
   later. Embedding model versions change.
2. **Auditability.** A client asks "why is this page 67/100?" — we can
   answer by listing the 5 sub-checks. Embedding similarity to "good
   citable content" is not a defensible answer.
3. **Cost.** Free-tier embeddings have rate limits. Self-hosted requires
   GPUs. Deterministic scoring runs on a CPU in milliseconds.

If you want to extend with embeddings as a v2 module, the contract in
`docs/modules.md` allows it. We'll keep the deterministic core as the default.

## Validation against ground truth

We're building a reference dataset of 200 manually-scored pages across:

- Russian (50)
- English (50)
- Spanish (50)
- Mixed-language (50)

Public release of the dataset and our scoring vs. human agreement is
planned for v0.5 (August 2026). Until then, take the absolute scores with
a grain of salt — focus on the **action plan** (which sub-checks failed,
how to fix them) rather than the raw number.

## Versioning the methodology

Score formulas may change. The version is recorded in every report:

```json
{
  "geo_audit_version": "0.1.0",
  "methodology_version": "1",
  "composite_score": 67
}
```

Methodology version bumps on any weight or sub-check change. Reports from
methodology v1 are not directly comparable to v2 — we'll provide a
migration table in [`CHANGELOG.md`](../CHANGELOG.md) when this happens.
