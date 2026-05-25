"""Tests for the schema module."""
from __future__ import annotations

from pathlib import Path

from geo_audit.modules import schema as schema_mod
from geo_audit.modules.base import ModuleArgs


def _args(html: str, url: str = "https://example.com") -> ModuleArgs:
    return ModuleArgs(url=url, homepage_html=html, homepage_status=200)


def test_extract_jsonld_blocks(good_html):
    blocks = schema_mod.extract_jsonld_blocks(good_html)
    assert len(blocks) == 4  # Article, Organization, FAQPage, BreadcrumbList


def test_good_page_scores_high(good_html):
    result = schema_mod.run(_args(good_html))
    assert result.score >= 70, f"good_html should score ≥70, got {result.score}"
    assert result.score <= 100
    assert not result.ran_in_degraded_mode


def test_bad_page_scores_low(bad_html):
    result = schema_mod.run(_args(bad_html))
    assert result.score <= 30, f"bad_html should score ≤30, got {result.score}"
    # Should produce P0 action: no JSON-LD at all.
    p0s = [a for a in result.actions if a.priority == "P0"]
    assert any("JSON-LD" in a.title for a in p0s)


def test_no_jsonld_actions(bad_html):
    result = schema_mod.run(_args(bad_html))
    titles = [a.title for a in result.actions]
    assert any("Add JSON-LD" in t for t in titles)


def test_parse_error_detected():
    html = '<html><script type="application/ld+json">{"@type":"Article", malformed}</script></html>'
    blocks = schema_mod.extract_jsonld_blocks(html)
    assert len(blocks) == 1
    assert blocks[0].get("_parse_error") is True


def test_score_deterministic(good_html):
    s1 = schema_mod.run(_args(good_html)).score
    s2 = schema_mod.run(_args(good_html)).score
    s3 = schema_mod.run(_args(good_html)).score
    assert s1 == s2 == s3


def test_handles_empty_html():
    result = schema_mod.run(_args(""))
    assert result.score == 0
    assert result.ran_in_degraded_mode is False  # Returns 0, not skipped — but with actions.
    titles = [a.title for a in result.actions]
    assert any("Add JSON-LD" in t for t in titles)


def test_schema_ignores_breadcrumb_css_without_markup():
    html = """
    <html>
      <head>
        <style>
          .breadcrumbs { display: inline-flex; }
          .breadcrumbs a:hover { color: teal; }
        </style>
        <script type="application/ld+json">
        {
          "@context": "https://schema.org",
          "@type": "WebSite",
          "url": "https://example.com/"
        }
        </script>
      </head>
      <body>
        <h1>Homepage</h1>
        <nav aria-label="Primary"><a href="/research/">Research</a></nav>
      </body>
    </html>
    """
    result = schema_mod.run(_args(html))
    titles = [a.title for a in result.actions]

    assert "Add BreadcrumbList schema" not in titles


def test_collectionpage_hub_scores_without_article_action():
    html = """
    <html>
      <head>
        <script type="application/ld+json">
        {
          "@context": "https://schema.org",
          "@graph": [
            {
              "@type": "CollectionPage",
              "name": "Research archive",
              "url": "https://example.com/research/",
              "about": "AI Search visibility research",
              "hasPart": [
                {
                  "@type": "Article",
                  "name": "What AI systems cite",
                  "url": "https://example.com/research/what-ai-systems-cite/"
                }
              ]
            },
            {
              "@type": "Organization",
              "name": "Humanswith.ai",
              "sameAs": ["https://www.linkedin.com/company/humanswith-ai"]
            },
            {
              "@type": "Person",
              "name": "Gregory Shevchenko",
              "jobTitle": "Founder",
              "worksFor": {"@type": "Organization", "name": "Humanswith.ai"}
            },
            {
              "@type": "FAQPage",
              "mainEntity": [
                {
                  "@type": "Question",
                  "name": "What should I cite?",
                  "acceptedAnswer": {"@type": "Answer", "text": "Cite the canonical research."}
                }
              ]
            },
            {
              "@type": "BreadcrumbList",
              "itemListElement": []
            }
          ]
        }
        </script>
      </head>
      <body>
        <h1>Research</h1>
        <article class="essay"><h2>What AI systems cite</h2></article>
        <article class="essay"><h2>AI visibility case studies</h2></article>
      </body>
    </html>
    """
    result = schema_mod.run(_args(html, url="https://example.com/research/"))
    action_titles = [a.title for a in result.actions]
    finding_titles = [f.title for f in result.findings]

    assert result.sub_scores["collectionpage_for_hub"] == 15
    assert result.score >= 75
    assert "Add Article schema to article-like pages" not in action_titles
    assert "CollectionPage schema for hub page found" in finding_titles


def test_article_like_page_without_collectionpage_still_requests_article_schema():
    html = """
    <html>
      <head>
        <script type="application/ld+json">
        {
          "@context": "https://schema.org",
          "@type": "Organization",
          "name": "Example",
          "sameAs": ["https://www.linkedin.com/company/example"]
        }
        </script>
      </head>
      <body>
        <article>
          <h1>Article without JSON-LD</h1>
          <time datetime="2026-05-25">25 May 2026</time>
        </article>
      </body>
    </html>
    """
    result = schema_mod.run(_args(html, url="https://example.com/blog/post/"))
    titles = [a.title for a in result.actions]

    assert "Add Article schema to article-like pages" in titles
