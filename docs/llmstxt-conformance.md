# llms.txt — conformance & honesty reference

How `geo-audit`'s `llmstxt` module interprets the `/llms.txt` proposal,
and an honest account of what the file does and does not do. This page is
self-contained — no external dependency beyond the public spec.

## What llms.txt is

`llms.txt` is a proposal by **Jeremy Howard** (co-founder, Answer.AI;
fast.ai), published 2024-09-03 at <https://llmstxt.org/> (spec repo:
<https://github.com/AnswerDotAI/llms-txt>). It is **two** proposals, not
one:

1. **`/llms.txt`** — a Markdown index at the domain root.
2. **`.md` page mirrors** — a clean Markdown copy of each useful page at
   the **same URL + `.md`** (or `index.html.md` for fileless URLs). This
   is the part coding assistants and agents most often consume; most
   sites implement only proposal 1.

### `/llms.txt` format (normative, in order)

1. An **H1** with the project/site name — **the only required element**.
2. A **blockquote** (`> …`) short summary.
3. Zero or more Markdown blocks **with no headings** (free-form context).
4. Zero or more `## ` sections, each a list of `[name](url)` links with
   an optional `: note`.

A section literally named **`## Optional`** is normative: its links may
be skipped when a shorter context is needed.

`llms.txt` is designed to coexist with `robots.txt` (access control) and
`sitemap.xml` (full index). It is for **inference-time, on-demand** use —
not training, not crawl-ranking.

### Terminology (kept distinct)

| Term | What it is |
|---|---|
| `llms.txt` | The spec'd root index file |
| `.md` page mirrors | The spec'd clean-Markdown page copies (proposal 2) |
| `llms-ctx.txt` / `llms-ctx-full.txt` | Output of the Answer.AI `llms_txt2ctx` tool that expands an `llms.txt` into a context file (full = includes `## Optional`) |
| `llms-full.txt` | A **community convention** (popularised by Mintlify) for a single concatenated dump — **not part of the spec** |

## Honesty: what llms.txt does not do

`llms.txt` is **not a ranking lever**. As of 2026:

- No major AI search/answer engine has officially confirmed consuming a
  third-party `llms.txt` for answer generation.
- Google's John Mueller stated publicly (2025) that no Google Search
  system reads or acts on `llms.txt`, comparing it to the obsolete
  `keywords` meta tag.

Where it demonstrably helps:

- **Inference-time, on demand** — when a user or agent explicitly loads
  the site (coding assistants, docs Q&A, retrieval tools).
- **Controlled narrative + citation accuracy** — *if* consulted, you
  decide the canonical pages, facts, and "how to cite" line, reducing
  hallucination about pricing/HQ/founder.
- **Early-adopter / due-diligence signal** — a present, well-formed,
  honest file reads as engineering maturity to a human or agent
  inspecting the site.

Treat the `llmstxt` score as a **controlled-narrative + AI-readiness**
signal, not as predicted ranking or traffic.

## How `geo-audit` scores it

`llmstxt` module, composite weight **10**, sub-weights:

| Sub-check | Points |
|---|---|
| `/llms.txt` present and valid | 50 |
| `/llms-full.txt` present | 30 |
| AI bots allowed in `robots.txt` | 20 |

- **Validity** follows the spec: a non-trivial document with an **H1** is
  structurally valid. A missing blockquote summary or `## ` section is a
  quality finding, not an invalidity.
- **Missing `/llms.txt`** is a **P2** suggestion (controlled-narrative /
  citability asset), never a P0/P1 visibility blocker.
- **`/llms-full.txt`** is scored for parity with common practice but
  labelled a community convention; its absence is a **P3** optional
  suggestion.
- **`.md` page mirrors** (proposal 2) are probed and reported as an
  **informational** finding only — no scoring weight.
- **Blocked AI bots** in `robots.txt` *are* a real visibility issue and
  remain a P0 action — that is crawler access, a separate concern from
  `llms.txt`.

Spec: <https://llmstxt.org/>.
