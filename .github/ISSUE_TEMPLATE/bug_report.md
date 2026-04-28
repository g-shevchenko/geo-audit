---
name: Bug report
about: Something doesn't work as documented
title: "[bug] "
labels: bug
---

<!-- Before opening: read README.md and docs/methodology.md. -->
<!-- "The score is wrong" is often "the methodology disagrees with my expectation." -->
<!-- That's a discussion, not a bug — open a Discussion instead. -->

## What happened

A clear, one-paragraph description.

## What you expected

What should have happened.

## Reproduction

Minimal command to reproduce:

```bash
geo-audit https://example.com --modules citability --depth quick
```

If the bug needs a specific URL to reproduce:

- URL: `https://...`
- Expected score: ...
- Actual score: ...

## Environment

- `geo-audit` version: `cat VERSION` →
- OS: macOS / Linux / WSL
- Python: `python3 --version` →
- Node: `node --version` →
- Did `bash scripts/agent-preinstall-check.sh` exit 0? Yes / No

## Logs

```
<paste relevant output>
```

## Severity

- [ ] Crashes the tool
- [ ] Wrong score (specify expected vs actual)
- [ ] Misleading documentation
- [ ] Other
