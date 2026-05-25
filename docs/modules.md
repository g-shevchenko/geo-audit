# Modules — per-module specs

Each module is a self-contained Python package. They follow a strict
contract so the CLI dispatcher can run them independently.

## Module contract

Every module exposes:

```python
NAME: str                      # CLI flag (e.g., "citability")
WEIGHT: int                    # composite-score contribution
REQUIRES_API_KEYS: list[str]   # env vars; empty list = works offline
DESCRIPTION: str               # one-line description for --help

def run(args: ModuleArgs) -> ModuleResult: ...
```

Where:

```python
@dataclass
class ModuleArgs:
    url: str                              # the audit target
    depth: Literal["quick", "full"]       # quick = first-page only
    cache_dir: Path                       # ~/.cache/geo-audit/
    timeout_s: int                        # network timeout per request
    user_agent: str                       # canonical UA
    api_keys: dict[str, str | None]       # from env, or None if missing

@dataclass
class ModuleResult:
    name: str
    score: int | None                     # 0-100, or None if degraded
    findings: list[Finding]               # everything we observed
    actions: list[Finding]                # subset with priority + fix
    ran_in_degraded_mode: bool
    duration_ms: int

@dataclass
class Finding:
    priority: Literal["P0", "P1", "P2", "P3"]
    title: str                            # one-line, action-oriented
    evidence: str                         # what we saw on the page
    fix_url: str                          # link to docs/methodology.md anchor
```

---

## Module: `site-crawl-lite`

Small-site crawl inventory for SEO/GEO readiness.

### CLI

```bash
geo-audit audit https://yoursite.com --modules site-crawl-lite
```

### What it checks

- Fetches the homepage plus sitemap URLs (`quick` = homepage only, `full` = up to 50 URLs).
- Respects `robots.txt`.
- Records status, final URL, title, classic meta description, canonical, H1, word count, JSON-LD count/types, internal/outbound link counts, image alt counts, and `noindex`.
- Reports route-level issues without requiring any API keys.

### What it does NOT check

- Enterprise crawl scale, log-file joins, JavaScript rendering at Screaming Frog / Sitebulb / Oncrawl depth.
- Backlink authority or keyword volume.

### Required API keys

None. If `FIRECRAWL_API_KEY` is set, the normal fetcher can still use it as a fallback for hostile HTML targets.

---

## Module: `head-schema-gate`

Deterministic head/social/schema consistency gate.

### CLI

```bash
geo-audit audit https://yoursite.com --modules head-schema-gate
```

### What it checks

- `<title>` presence and reasonable length.
- Classic `<meta name="description">`.
- Canonical link.
- Visible H1.
- `og:title`, `og:description`, `og:image`.
- JSON-LD parse errors and missing JSON-LD.
- Article author `sameAs`, BreadcrumbList, and FAQPage when the page contains matching signals.
- Ownership verification files are skipped so they do not create false SEO failures.

### Required API keys

None.

---

## Module: `citability`

LLM-citation likelihood scoring.

### CLI

```bash
geo-audit https://yoursite.com --modules citability
```

### Flags

| Flag               | Default | Effect                                                |
|--------------------|---------|-------------------------------------------------------|
| `--lang ru\|en`    | auto    | Language-specific definition patterns                  |
| `--strict-tldr`    | off     | Require TL;DR within first 200 chars (vs 500)          |

### What it checks

See [`docs/methodology.md#citability`](methodology.md#citability) for scoring formulas.

### What it does NOT check

- The page's actual rank in any search engine (use Ahrefs / Semrush)
- Whether the brand appears in *current* LLM outputs (use `brand-mentions`)
- Image alt text quality (out of scope — use Lighthouse a11y)

### Required API keys

None. Fully offline.

---

## Module: `schema`

JSON-LD validator + suggester.

### Flags

| Flag                 | Default | Effect                                                |
|----------------------|---------|-------------------------------------------------------|
| `--strict`           | off     | Treat warnings as errors                               |
| `--types <list>`     | auto    | Limit to specific schema types                         |

### What it checks

- All JSON-LD blocks parse as valid JSON
- Each block validates against its declared `@type`
- Required properties for each type are present
- Suggested types based on page content (Article on blog posts, CollectionPage on hub pages, Product on /shop, etc.)

### Required API keys

None. We use a bundled Schema.org JSON Schema. Optionally hits
[validator.schema.org](https://validator.schema.org/) for cross-validation.

---

## Module: `llmstxt`

`/llms.txt` and `/llms-full.txt` detection + generation.

### Flags

| Flag             | Default | Effect                                                  |
|------------------|---------|---------------------------------------------------------|
| `--generate`     | off     | Output a suggested `/llms.txt` for this site            |
| `--also-full`    | off     | With `--generate`, also output `/llms-full.txt`          |

### What it checks

- `/llms.txt` exists and is reachable
- Content matches the [llmstxt.org](https://llmstxt.org) spec
- `robots.txt` allows GPTBot, ClaudeBot, PerplexityBot, Google-Extended

### Required API keys

None.

---

## Module: `brand-mentions`

Live scan of LLM providers for current brand mentions.

### Flags

| Flag                              | Default     | Effect                                       |
|-----------------------------------|-------------|----------------------------------------------|
| `--brand <name>`                  | (required)  | Brand name to query for                      |
| `--queries <file>`                | bundled     | Custom query list                            |
| `--providers chatgpt,claude,perplexity,gemini` | all     | Restrict to specific LLM providers           |

### What it checks

For each provider with an API key, we run controlled queries like:

- "What are the best [category]?"
- "Compare [your brand] vs [competitor]"
- "Tell me about [your brand]"

And measure:
- Does the brand name appear?
- Is your URL cited?
- Is the description correct?

### Required API keys (at least one)

| Env var                | Provider     | Free tier?              |
|------------------------|--------------|-------------------------|
| `OPENAI_API_KEY`       | ChatGPT      | No (~$0.001/audit)      |
| `ANTHROPIC_API_KEY`    | Claude       | No (~$0.001/audit)      |
| `PERPLEXITY_API_KEY`   | Perplexity   | No (~$0.005/audit)      |
| `GEMINI_API_KEY`       | Gemini       | Yes, generous           |

If no keys are provided, the module reports `score: null` and is excluded
from the composite. See [`docs/external-services.md`](external-services.md).

---

## Module: `technical`

Core Web Vitals + indexability.

### Flags

| Flag             | Default | Effect                                                    |
|------------------|---------|-----------------------------------------------------------|
| `--device mobile\|desktop\|both` | mobile | Lighthouse profile to use                       |
| `--no-cwv`       | off     | Skip Core Web Vitals (faster, less informative)            |

### What it checks

A. Core Web Vitals via Lighthouse:
- LCP, INP, CLS

B. Indexability:
- HTTPS, HSTS, sitemap.xml, robots.txt
- Canonical, hreflang
- SSR/SSG detection (content in initial HTML)
- Mobile viewport meta

### Required API keys

None required. With `PAGESPEED_API_KEY`, we use Google's hosted Lighthouse
for higher rate limits and field data when available.

---

## Module: `content`

EEAT signals, AI-detection, readability.

### Flags

| Flag                 | Default | Effect                                                  |
|----------------------|---------|---------------------------------------------------------|
| `--lang ru\|en`      | auto    | Language for readability scoring                         |
| `--no-ai-detection`  | off     | Skip Binoculars (faster)                                 |
| `--ai-threshold N`   | 25      | Max acceptable AI-likelihood %                           |

### What it checks

- EEAT: author, date, sources, contact
- AI-detection via [Binoculars](https://github.com/AHans30/Binoculars) (open-source, MIT)
- Readability:
  - English: Flesch Reading Ease (textstat)
  - Russian: adapted Pushkin formula

### Required API keys

None. Binoculars runs locally on CPU.

---

## Adding a new module

See [`CONTRIBUTING.md#adding-a-module`](../CONTRIBUTING.md#adding-a-module).
