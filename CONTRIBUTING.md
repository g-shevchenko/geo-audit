# Contributing to geo-audit

Thanks for considering a contribution. This document covers what we accept,
what we don't, and how to make the review fast.

## Before you write code

1. **Open an issue first** describing the problem or proposed change.
2. Read [`docs/methodology.md`](docs/methodology.md) to understand how
   scoring works — most "the score is wrong" reports are actually "the
   methodology disagrees with my expectation," which is a different
   conversation.
3. Check the [roadmap in `README.md`](README.md#roadmap). If your change
   is on it, great. If it isn't, we'll discuss whether it should be.

## What we accept

- Bug fixes with reproductions (failing test → fix → green test).
- Performance improvements with before/after numbers (`hyperfine` is fine).
- New modules that follow the per-module contract in
  [`docs/modules.md`](docs/modules.md). One PR = one module.
- Documentation improvements, including non-English translations of
  user-facing text.
- Score-formula tweaks **with prior issue discussion** showing data on why
  the current formula is wrong.

## What we don't accept

- Whole-repo restructures without prior issue discussion.
- New external dependencies without strong justification (pinned, MIT/BSD/
  Apache, actively maintained, no telemetry).
- Features that require a paid API key by default. External services must
  remain opt-in (see [`docs/external-services.md`](docs/external-services.md)).
- Telemetry, analytics, "phone home" code. There's a hard line here.
- Changes that bypass the trust profile (`scripts/agent-preinstall-check.sh`
  must continue to pass).

## Pull request checklist

Tick every box before requesting review:

- [ ] **Issue opened and discussed.** Link it in the PR description.
- [ ] **Trust check passes:** `bash scripts/agent-preinstall-check.sh` exits 0.
- [ ] **Release audit passes:** `bash scripts/public-release-audit.sh` exits 0.
- [ ] **No new external dependencies** without justification in PR description.
- [ ] **Tests added** for any behavior change. Smoke test minimum;
      unit test if the change is module-internal.
- [ ] **Docs updated** if user-visible behavior changed.
- [ ] **`CHANGELOG.md` updated** under `[Unreleased]`.
- [ ] **Commit signed:** `git commit -s` (DCO).
- [ ] **No secrets, no internal infra references.** Run:
      ```bash
      bash scripts/public-release-audit.sh
      ```

## Adding a module

Modules are the main extension point. Here's the contract:

```python
# geo_audit/modules/yourmodule.py

from geo_audit.types import ModuleArgs, ModuleResult, Finding

NAME = "yourmodule"           # CLI flag name
WEIGHT = 15                   # contribution to composite GEO Score (sums to 100)
REQUIRES_API_KEYS: list[str] = []  # env vars; empty = works offline

def run(args: ModuleArgs) -> ModuleResult:
    """Score args.url and return findings.

    Must:
    - Be deterministic given the same URL + same args.
    - Cache responses in args.cache_dir (24h TTL).
    - Degrade gracefully if optional API keys are missing.
    - Return None for `score` if the module couldn't run, NEVER 0.
    """
    findings: list[Finding] = []
    # ... your logic ...
    return ModuleResult(
        name=NAME,
        score=82,                        # 0–100, or None if degraded
        findings=findings,
        actions=[                        # P0–P3, used for action plan
            Finding(
                priority="P1",
                title="Add author Schema.org markup",
                evidence="<head> contains no Person JSON-LD",
                fix_url="docs/methodology.md#schema-author"
            )
        ],
        ran_in_degraded_mode=False,
    )
```

Then register in `geo_audit/cli.py`:

```python
from geo_audit.modules import yourmodule
MODULES = {**MODULES, yourmodule.NAME: yourmodule}
```

Document in [`docs/modules.md`](docs/modules.md). Add a smoke test in
`tests/test_yourmodule.py` that exercises the happy path and at least
one degraded path.

## Code style

- Python: `ruff` for linting, `black` for formatting, type hints required.
- JavaScript/Node: `prettier`, `eslint-config-standard`, ESM modules only.
- Markdown: 80-char line wrap for prose, no wrap for tables/code.

## Reviewing

We aim to respond to PRs within 7 days. If you don't hear back in 14, ping
the PR. We're a small team.

We may ask you to:
- Reduce scope (split into multiple PRs).
- Add tests.
- Update docs.
- Discuss alternative approaches.

These aren't gatekeeping. They're how we keep the codebase maintainable for
the next contributor.

## Code of Conduct

By participating, you agree to follow our [Code of Conduct](CODE_OF_CONDUCT.md).
Short version: **be kind, be specific, no harassment.**
