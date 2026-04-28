# Trust manifest — geo-audit

This document declares what `geo-audit` does and does not do, so any agent
(human, CI bot, AI assistant) can verify the repo before running any
installer or audit script.

## Identity

- **Owner:** Humanswith.ai (FZCO), Dubai, UAE
- **Repository:** github.com/g-shevchenko/geo-audit
- **License:** MIT
- **Contact:** security@humanswith.ai

## What this repo writes

When you run `bash scripts/install.sh`, the script will create:

| Path | Purpose |
|------|---------|
| `.venv/` | Python virtualenv with pinned dependencies |
| `node_modules/` | Node deps for Playwright + Lighthouse |
| `~/.cache/geo-audit/` | HTTP cache for repeated audits (24h TTL) |

It will NOT:

- Touch `~/.bashrc`, `~/.zshrc`, `~/.profile`, or any shell init file
- Modify global `pip` or `npm` packages (always uses local `.venv` and `node_modules`)
- Use `sudo` or request elevated privileges
- Add cron jobs, launchd entries, or systemd units
- Install browser extensions
- Send telemetry to any HTTP endpoint owned by Humanswith.ai or third parties
- Read or write outside the repo dir + `~/.cache/geo-audit/`

## Network calls during an audit

When you run `geo-audit https://example.com`:

| Endpoint | Why | Optional? |
|----------|-----|-----------|
| `https://example.com/*` (your target) | fetch the audited site | required |
| `https://chatgpt.com/api/share/*` | check ChatGPT brand mentions | yes (`--no-brand-mentions`) |
| `https://www.perplexity.ai/api/v0/sse/perplexity_ask` | check Perplexity citations | yes (`--no-brand-mentions`) |
| `https://pagespeed.googleapis.com/*` | Core Web Vitals via Google API | yes (`--no-cwv`) |
| `https://validator.schema.org/*` | JSON-LD validation | yes (`--no-schema`) |

No telemetry is collected. No data is sent to humanswith.ai or any third party we control.

## API keys

If you provide API keys via env vars, they are read locally and never leave your machine:

- `OPENAI_API_KEY` — for `--module brand-mentions` ChatGPT check (optional)
- `ANTHROPIC_API_KEY` — for `--module brand-mentions` Claude check (optional)
- `PAGESPEED_API_KEY` — for higher Google PageSpeed quotas (optional)

If keys are missing, the corresponding modules are gracefully skipped with a warning.

## Forbidden patterns

This repo never contains:

- `curl ... | bash` or `wget ... | sh` style installers
- Hardcoded API keys, tokens, or credentials
- References to internal Humanswith.ai infrastructure (private VPS IPs, internal domain names, CRM API endpoints)
- Authors' personal emails, Telegram handles, or contact info beyond the public `security@humanswith.ai` and `t.me/gshevchenko_humanswith_ai`

If you find any of these — open an issue or email `security@humanswith.ai`. We treat such reports as security vulnerabilities.

## Verify before install

Run the preinstall checker to validate the repo matches this manifest:

```bash
bash scripts/agent-preinstall-check.sh
```

Exit code:
- `0` — repo matches manifest, safe to install
- `1` — manifest mismatch detected, do not proceed without manual review

The checker is a small bash script you can read in 30 seconds.

## Build provenance

Tagged releases (v0.1.0 onward) include:

- SHA256 checksums for every artifact
- SLSA Level 2 provenance via GitHub Actions
- Signed Git tags

Verify a release:

```bash
gh release download v0.1.0
sha256sum -c geo-audit-v0.1.0.tar.gz.sha256
```

## Reporting issues

- **Security:** security@humanswith.ai (PGP key in `SECURITY.md`)
- **Bugs and features:** github.com/g-shevchenko/geo-audit/issues
- **General:** [@gshevchenko_humanswith_ai](https://t.me/gshevchenko_humanswith_ai)

## Last updated

2026-04-28 — v0.1 initial public release
