# Comparison vs. paid SaaS tools

A more detailed feature matrix than the one in `README.md`. Use this when
your manager asks "why not just buy Surfer?".

> **Honest disclaimer.** We picked these because they're the actual tools
> our clients ask about. If you think we mischaracterized a competitor,
> open an issue with evidence and we'll update.

## Direct competitors (we replace)

### vs. [Surfer SEO](https://surferseo.com)

|                              | Surfer SEO            | geo-audit                                 |
|------------------------------|-----------------------|-------------------------------------------|
| Price                        | $49 – $199 / month    | $0 (MIT)                                  |
| Open-source                  | No                    | Yes                                       |
| LLM citability scoring       | Limited               | First-class (`citability` module)          |
| Schema.org validation        | Yes                   | Yes (`schema` module)                     |
| Content brief generation     | **Yes (signature feature)** | No (use Frase or write the brief manually) |
| AI-Visibility tracking       | No                    | Yes (`brand-mentions` module)             |
| Inline NLP editor            | **Yes (signature feature)** | No (out of scope)                         |
| API access                   | Higher tiers only     | Always (it's a CLI)                       |
| CI/CD friendly               | No                    | Yes (JSON output, exit codes)             |
| Multi-language               | EN-strong             | EN + RU (more in roadmap)                 |
| **When to choose Surfer**    | You write content full-time and need the inline editor + content brief workflow | |
| **When to choose geo-audit** | You already have a writer; you need to *audit* and *act*, not write |  |

### vs. [Frase](https://frase.io)

|                              | Frase                 | geo-audit                                 |
|------------------------------|-----------------------|-------------------------------------------|
| Price                        | $14.99 – $114.99      | $0                                        |
| Open-source                  | No                    | Yes                                       |
| AI writer                    | **Yes**               | No                                        |
| Content brief from SERP      | **Yes**               | No                                        |
| Question discovery           | Yes                   | Indirectly (via `brand-mentions` queries) |
| Schema validation            | No                    | Yes                                       |
| Technical SEO audit          | No                    | Yes                                       |
| Multi-LLM brand monitoring   | No                    | Yes                                       |
| **When to choose Frase**     | You're a content writer / agency content team | |
| **When to choose geo-audit** | You're an SEO/devops auditing existing pages |  |

### vs. [Profound](https://www.tryprofound.com)

|                              | Profound              | geo-audit                                 |
|------------------------------|-----------------------|-------------------------------------------|
| Price                        | $499+ / month         | $0 (+ ~$10–$40 in API costs)              |
| Multi-LLM mention monitoring | **Yes (signature)**   | Yes, but one-shot (not continuous)        |
| Continuous tracking          | **Yes**               | No (run on cron)                          |
| Slack/email alerts           | **Yes**               | No (output to JSON; wire your own)        |
| Multi-tenant                 | **Yes**               | No (CLI per project)                      |
| Historical trends            | **Yes**               | No (you'd store JSON outputs over time)   |
| Open-source                  | No                    | Yes                                       |
| **When to choose Profound**  | Enterprise; need real-time alerting, RBAC, dashboards | |
| **When to choose geo-audit** | Single brand, willing to wire alerting yourself, want auditable scoring |  |

### vs. [AI-Semantica](https://app.ai-semantica.com)

|                              | AI-Semantica          | geo-audit                                 |
|------------------------------|-----------------------|-------------------------------------------|
| Price                        | $30 – $200 / month    | $0                                        |
| Brand mentions in LLMs       | Yes                   | Yes (`brand-mentions`)                    |
| SERP-vs-LLM gap              | **Yes**               | Partial (planned for v0.4)                |
| Multi-language (RU strong)   | Yes                   | RU + EN, more later                       |
| Citability scoring           | Limited               | First-class                               |
| Schema validation            | No                    | Yes                                       |
| Open-source                  | No                    | Yes                                       |
| **When to choose AI-Semantica** | You want a managed UI with continuous tracking, RU-focused | |
| **When to choose geo-audit** | You want auditable scoring + on-demand audits + multi-purpose toolkit |  |

### vs. [Goodie](https://goodie.app)

|                              | Goodie                | geo-audit                                 |
|------------------------------|-----------------------|-------------------------------------------|
| Price                        | $99+ / month          | $0                                        |
| LLM citation tracking        | Yes                   | Yes (one-shot)                            |
| Real-time webhooks           | **Yes**               | No                                        |
| Citability scoring           | No                    | Yes                                       |
| Open-source                  | No                    | Yes                                       |
| **When to choose Goodie**    | You need real-time alerts on citation events | |
| **When to choose geo-audit** | You want a complete audit suite, not just citation tracking |  |

---

## Adjacent tools (we coexist)

These solve different problems. Use them alongside `geo-audit`, not instead.

### [Ahrefs](https://ahrefs.com), [Semrush](https://semrush.com)

- **Their job:** keyword research, backlink analysis, rank tracking
- **Our job:** scoring page quality for AI search
- **Use both:** Ahrefs tells you which queries to target; `geo-audit` tells
  you whether your page is good enough to be cited for those queries.

### [Google Search Console](https://search.google.com/search-console)

- **Their job:** real impressions/clicks from Google Search
- **Our job:** scoring pages independent of current rank
- **Use both:** GSC shows what's actually working; `geo-audit` shows what
  *should* work after fixes.

### [Yandex Webmaster](https://webmaster.yandex.com)

- **Their job:** Russian SERP visibility
- **Our job:** content quality scoring
- **Use both:** if you target RU. We don't replace Yandex's analytics.

### [Google Indexing API](https://developers.google.com/search/apis/indexing-api), [IndexNow](https://www.indexnow.org)

- **Their job:** force-index URL submissions
- **Our job:** identify what should be indexed first
- **Use both:** run `geo-audit` → fix the P0 items → submit via Indexing API.

### [Pitchbox](https://pitchbox.com), [BuzzStream](https://buzzstream.com), [Respona](https://respona.com)

- **Their job:** outreach pipelines (find contacts, send pitches, track replies)
- **Our job:** score the pages you're pitching about
- **Use both:** for SEO outreach, you score the donor's site with `geo-audit`,
  then use Pitchbox to actually email them.

### [Crawl4AI](https://github.com/unclecode/crawl4ai), [Firecrawl](https://firecrawl.dev)

- **Their job:** web crawling, structure extraction
- **Our job:** scoring (we use Crawl4AI internally)
- **Use both:** for ad-hoc crawling, use Crawl4AI directly. For "is this
  page LLM-friendly", use `geo-audit`.

---

## Pricing comparison summary

For a small agency with ~50 audits/month:

| Stack option                                         | Monthly cost (USD) |
|------------------------------------------------------|--------------------|
| Surfer SEO Pro + AI-Semantica Mid                    | ~$100              |
| Frase Pro + Goodie + Lighthouse (free)               | ~$215              |
| Profound + Surfer + Frase                            | ~$650              |
| **geo-audit + free Lighthouse + Tavily free tier**   | **~$0.50** (just API costs) |
| **geo-audit + ChatGPT + Claude + Perplexity APIs**   | **~$10–20**         |

For 1,000 audits/month, the savings are larger because most paid SaaS
charges per-audit while open-source scales with API costs only.

---

## What we're NOT replacing

We deliberately don't compete with:

- **Lighthouse** — we wrap it for the `technical` module. Use it directly
  for full a11y/PWA audits.
- **Schema.org Validator** — official Google validator, free. We complement
  it with suggestions (what's missing), not just validation (what's wrong).
- **GSC / Yandex Webmaster** — they're truth sources for impressions and
  clicks. We score page quality, which is a different signal.

If you want one of those, use them directly. If you want a single tool that
combines content quality + technical + LLM-visibility scoring, that's us.

---

## How accurate is the comparison?

We tested feature parity in April 2026 against the marketing pages and
trial accounts of each tool. If a tool changes, this doc may lag. PRs
welcome — open an issue first with evidence (screenshots, pricing pages).
