# External services

`geo-audit` is **fully usable offline** with the modules that don't require
external APIs. This document lists every external service the tool can
optionally talk to, what it unlocks, and how to configure access.

## Default behavior

If no API keys are configured, `geo-audit` runs:
- ✅ `citability` — works fully (deterministic, no APIs)
- ✅ `schema` — works fully (bundled JSON Schema)
- ✅ `llmstxt` — works fully (HTTP fetches against the audit target only)
- ⚠️ `brand-mentions` — reports `score: null`, excluded from composite
- ✅ `technical` — works (Lighthouse runs locally), but rate-limited
- ✅ `content` — works fully (Binoculars runs locally)

Adding API keys unlocks the rest. Each is opt-in. None are sent in
unencrypted form. None are stored beyond the `~/.cache/geo-audit/` HTTP
response cache (24h TTL, never includes auth headers).

---

## How to configure

`geo-audit` reads keys from environment variables. Two ways to set them:

### Option A: shell env (per-invocation)

```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
geo-audit https://yoursite.com --depth full
```

### Option B: `.env` file (persistent, gitignored)

```bash
cp .env.example .env
$EDITOR .env       # add your keys
geo-audit https://yoursite.com --depth full
# (geo-audit auto-loads .env from the current directory)
```

The `.env.example` file ships with the repo. It contains placeholder
values, never real keys. The `.gitignore` excludes `.env` so you can't
accidentally commit secrets.

---

## Service catalog

### Google PageSpeed Insights

- **Module:** `technical`
- **Required:** No (Lighthouse runs locally without it)
- **What it unlocks:** Higher rate limits, field data (real-user CrUX) when available
- **Free tier:** Yes — 25,000 queries/day
- **Sign up:** [console.cloud.google.com](https://console.cloud.google.com/apis/library/pagespeedonline.googleapis.com)
- **Env var:** `PAGESPEED_API_KEY`

### OpenAI API

- **Module:** `brand-mentions` (ChatGPT check)
- **Required:** No (gracefully degrades if missing)
- **What it unlocks:** Live ChatGPT brand mention scan
- **Cost:** ~$0.001 per audit (single GPT-4o-mini query)
- **Free tier:** No (pay-per-token)
- **Sign up:** [platform.openai.com](https://platform.openai.com)
- **Env var:** `OPENAI_API_KEY`

### Anthropic API

- **Module:** `brand-mentions` (Claude check)
- **Required:** No
- **What it unlocks:** Live Claude brand mention scan
- **Cost:** ~$0.001 per audit (Haiku 3.5)
- **Free tier:** Limited (try-it credits on signup)
- **Sign up:** [console.anthropic.com](https://console.anthropic.com)
- **Env var:** `ANTHROPIC_API_KEY`

### Perplexity API

- **Module:** `brand-mentions` (Perplexity check)
- **Required:** No
- **What it unlocks:** Live Perplexity citation check (most LLM-search-native)
- **Cost:** ~$0.005 per audit (Sonar model)
- **Free tier:** No
- **Sign up:** [docs.perplexity.ai](https://docs.perplexity.ai)
- **Env var:** `PERPLEXITY_API_KEY`

### Google Gemini API

- **Module:** `brand-mentions` (Gemini check)
- **Required:** No
- **What it unlocks:** Live Gemini brand mention scan
- **Cost:** Free tier is generous
- **Sign up:** [aistudio.google.com](https://aistudio.google.com)
- **Env var:** `GEMINI_API_KEY`

### Tavily Search API

- **Module:** `brand-mentions` (web context expansion)
- **Required:** No
- **What it unlocks:** LLM-friendly web search to compare LLM-mentioned facts vs. live web
- **Cost:** 1,000 searches/month free, then $0.005/search
- **Sign up:** [tavily.com](https://tavily.com)
- **Env var:** `TAVILY_API_KEY`

### Serper.dev (Google SERP)

- **Module:** `brand-mentions` (SERP-vs-LLM gap analysis)
- **Required:** No
- **What it unlocks:** Compare your SERP rank vs. your LLM mention rate (the "GEO gap")
- **Cost:** $50/month for 50,000 queries (~$0.001/query)
- **Sign up:** [serper.dev](https://serper.dev)
- **Env var:** `SERPER_API_KEY`

### SearXNG (self-hosted SERP, alternative to Serper)

- **Module:** `brand-mentions`
- **Required:** No
- **What it unlocks:** Same as Serper, but self-hosted (privacy + no per-query cost)
- **Cost:** ~$5/month for a small VPS
- **Setup:** [docs.searxng.org/admin/installation.html](https://docs.searxng.org/admin/installation.html)
- **Env var:** `SEARXNG_BASE_URL` (e.g., `https://searx.yourdomain.com`)

### Schema.org Validator

- **Module:** `schema`
- **Required:** No (we have a bundled validator)
- **What it unlocks:** Cross-validation against the canonical online validator
- **Cost:** Free, no auth
- **Endpoint:** [validator.schema.org](https://validator.schema.org)
- **Env var:** None (no auth needed)

---

## Cost estimation

For a single full audit with all keys configured:

| Service              | Cost per audit |
|----------------------|----------------|
| Google PageSpeed     | $0 (free tier) |
| OpenAI (ChatGPT)     | $0.001         |
| Anthropic (Claude)   | $0.001         |
| Perplexity           | $0.005         |
| Gemini               | $0 (free tier) |
| Tavily (5 searches)  | $0 – $0.025    |
| Serper (3 queries)   | $0.003         |
| **Total**            | **~$0.01–$0.04** |

For 1,000 audits/month: ~$10–$40/month in API costs.

For comparison:
- Surfer SEO: $49–199/month
- Profound: $499+/month
- AI-Semantica: $30–200/month

---

## Privacy and security

All external API calls are documented in [`TRUST.md`](../TRUST.md) and the
[`trust/manifest.json`](../trust/manifest.json) file. Specifically:

- **No telemetry to Humanswith.ai.** We don't run our own backend.
- **API keys never leave your machine** except in the request to the
  intended endpoint.
- **No third-party analytics** (no GA, Mixpanel, etc.) in the tool.
- **Cache contains response bodies but not auth headers.** Rotate the cache
  if you change a key for an unrelated reason.

If you find a privacy issue, report to **security@humanswith.ai** —
see [`SECURITY.md`](../SECURITY.md).

---

## Recommended starter configuration

If you're trying `geo-audit` for the first time:

```bash
# Minimum useful config (no paid keys):
export GEMINI_API_KEY="..."        # free
export PAGESPEED_API_KEY="..."     # free

# Adds ChatGPT + Claude for brand-mentions (~$0.002/audit):
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."

# Now you're getting:
# - 6/6 modules running
# - 2/4 LLM providers in brand-mentions
# - High-quality Core Web Vitals
# Cost: ~$0.002/audit. For 100 audits/month: $0.20.
```

This is enough for a small SEO consultancy. Scale up to all providers as
your budget allows.
