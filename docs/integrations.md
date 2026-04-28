# Integrations

How to wire `geo-audit` into your existing stack. All integrations are
**user-built on top of the CLI** — we don't ship any of them as required
parts of the tool.

## Claude Code skill

If you use [Claude Code](https://claude.com/claude-code), you can wrap
`geo-audit` as a Skill so the agent can run audits on demand.

`~/.claude/skills/geo-audit/SKILL.md`:

```markdown
---
name: geo-audit
description: Run a GEO/AI-visibility audit on any URL using the open-source geo-audit toolkit.
---

# geo-audit

When the user asks for a "GEO audit", "AI visibility scan", or "how does
X rank in ChatGPT/Perplexity", run:

```bash
geo-audit <url> --depth full --output report.pdf --output-format json
```

Then parse the JSON, summarize the composite score, and surface the top 3
P0 actions to the user. If `geo-audit` isn't installed, point them to
https://github.com/g-shevchenko/geo-audit and don't try to fake the audit.
```

Then in any Claude Code session: `Run a geo-audit on https://yoursite.com`.

## n8n workflow

`geo-audit` exposes JSON output, which n8n can consume directly.

```json
// n8n Execute Command node:
{
  "command": "geo-audit {{ $json.url }} --depth full --output - --output-format json",
  "executeOnce": false
}
```

A reference workflow ships in [`integrations/n8n/audit-workflow.json`](../integrations/n8n/audit-workflow.json)
(planned for v0.2). Import it into your n8n instance, set the trigger
(cron, webhook, etc.), and the workflow will:

1. Run `geo-audit` for each URL in your input
2. Parse the JSON
3. Post results to Slack, write to Google Sheets, or trigger downstream actions

## GitHub Action

Audit your site on every PR or on a schedule.

`.github/workflows/geo-audit.yml`:

```yaml
name: GEO audit
on:
  schedule:
    - cron: "0 4 * * 1"   # Monday 04:00 UTC
  workflow_dispatch:

jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
      - name: Install geo-audit
        run: |
          git clone https://github.com/g-shevchenko/geo-audit.git
          cd geo-audit
          bash scripts/agent-preinstall-check.sh
          bash scripts/install.sh
      - name: Run audit
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          ./geo-audit/.venv/bin/geo-audit https://yoursite.com \
            --depth full --output report.json --output-format json
      - uses: actions/upload-artifact@v4
        with:
          name: geo-audit-report
          path: report.json
```

A composite-action wrapper is planned for v0.5 — until then, the inline
recipe above is the canonical approach.

## CI gating (block merges on regression)

```bash
# In your CI:
geo-audit https://staging.yoursite.com --output report.json --quiet
# Exit 0 if score >= 70, else 1
[[ $? -eq 0 ]] || { echo "GEO Score regression"; exit 1; }
```

You can also gate on per-module scores:

```bash
geo-audit https://staging.yoursite.com --output report.json --quiet
score=$(jq '.modules.citability.score' report.json)
[[ $score -ge 60 ]] || { echo "citability regression"; exit 1; }
```

## Slack notification

```bash
geo-audit https://yoursite.com --output report.json
score=$(jq '.composite_score' report.json)
top_action=$(jq -r '.actions[0].title' report.json)

curl -X POST "$SLACK_WEBHOOK_URL" \
  -H 'Content-Type: application/json' \
  -d "{\"text\": \"GEO audit: $score/100. Top action: $top_action\"}"
```

## Google Sheets logging

```bash
geo-audit https://yoursite.com --output report.json
date=$(date -u +%Y-%m-%d)
score=$(jq '.composite_score' report.json)
echo "$date,https://yoursite.com,$score" | \
  gh sheet append --sheet-id "$SHEET_ID" --range "audits!A:C"
```

(`gh sheet` is hypothetical — use [`gam`](https://github.com/GAM-team/GAM)
or the Google Sheets API directly. Reference patterns ship in v0.3.)

## PDF report styling

The default PDF uses our **Pantheon** design system:

- Fonts: Instrument Serif italic + Inter + JetBrains Mono
- Colors: warm dark `#181818` background, cyan `#33ffff` accent
- Borders: sharp 2px (no rounded corners)
- Spacing: 4px base unit

To customize, override the WeasyPrint CSS:

```bash
geo-audit https://yoursite.com --output report.pdf --pdf-css custom.css
```

A reference `custom.css` for Bootstrap-style reports ships in
[`integrations/pdf-styles/`](../integrations/pdf-styles/) (planned for v0.3).

A reference Pantheon-style CSS for PDF reports will ship in
[`integrations/pdf-styles/pantheon.css`](../integrations/pdf-styles/pantheon.css)
in v0.3 (planned June 2026). Until then, the report CSS is bundled inside
the WeasyPrint template and you can override the entire stylesheet via
`--pdf-css custom.css`.

## Custom modules

`geo-audit` is plugin-friendly. To add a custom module:

1. Create a Python package matching the contract in [`docs/modules.md`](modules.md).
2. Pip-install it into the same `.venv/` as `geo-audit`.
3. Register via entry-point:

```toml
# pyproject.toml of your custom module:
[project.entry-points."geo_audit.modules"]
yourmodule = "yourpackage.yourmodule"
```

The CLI auto-discovers modules registered under this entry-point. No
geo-audit fork required.

## Roadmap

| Integration                  | Version | Status     |
|------------------------------|---------|------------|
| Claude Code skill (template) | v0.1    | ✅ this doc |
| n8n reference workflow       | v0.2    | Planned    |
| GitHub Action wrapper        | v0.5    | Planned    |
| Slack/Discord webhooks       | v0.3    | Planned    |
| Notion sync                  | v0.4    | Planned    |
| Lookerl Studio template      | v1.0    | Planned    |

If you build an integration we don't have, we'd love a PR or a link in the
issue tracker.
