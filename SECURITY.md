# Security policy

## Reporting a vulnerability

Please email **security@humanswith.ai** rather than opening a public issue.

We aim to respond within 48 hours and patch critical issues within 7 days.

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | yes       |
| < 0.1   | no        |

## What we treat as security issues

- Hardcoded credentials, tokens, or API keys in any commit
- Internal Humanswith.ai infrastructure references (IPs, internal hostnames, private endpoints)
- Code that exfiltrates audit target data (URLs, page content) to any non-target endpoint
- Code that escalates privileges (sudo, install of system services without explicit user opt-in)
- RCE via crafted URLs or malicious response from audited site

## What we do NOT treat as security issues

- Bugs in audit accuracy (use the issue tracker)
- Performance issues
- Requests for new modules or integrations

## Scope

This policy covers:
- Code in github.com/g-shevchenko/geo-audit
- Documentation that could mislead users into unsafe configurations
- Distribution channels (GitHub Releases, npm, PyPI)

It does NOT cover:
- The websites you audit with this tool — that's between you and them
- Third-party APIs the tool calls (OpenAI, Anthropic, Google PageSpeed)

## Disclosure

We follow a coordinated disclosure model:
1. You report privately
2. We acknowledge within 48h
3. We patch + prepare CVE if needed
4. We publish disclosure 14 days after patch (or sooner if you prefer)
