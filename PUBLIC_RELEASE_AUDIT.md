# Public release audit

This document specifies what we audit before publishing any public release
(tag, GitHub Release, npm/PyPI publish). The automation lives in
[`scripts/public-release-audit.sh`](scripts/public-release-audit.sh).

## Why this exists

Open-source releases are public forever. Once a token, internal hostname, or
private path lands in `git log`, it's effectively unrecoverable without a
force-push history rewrite — which breaks every fork.

This audit is the gate. Failures block release.

## Checks performed

### 1. Working tree is clean

```bash
git status --short --branch
git diff --check
```

No uncommitted changes, no whitespace errors. Releases are reproducible only
if the commit hash matches the tree.

### 2. No secret-shaped strings

```bash
rg -nE '(github_pat_|gh[pousr]_|x-access-token|authorization: bearer|api[_-]?key\s*[:=]|secret\s*[:=]|password\s*[:=]|notion_token|telegram.*token|sk-[a-zA-Z0-9]{20,}|hf_[a-zA-Z0-9]{20,})' .
```

Failure means a real token. Stop, rotate the token (assume leaked), then
strip and rewrite history.

### 3. No internal HWAI infrastructure references

```bash
rg -nE '(greg-personal-claude|hwai-internal|claude/CREDENTIALS|hwai-ops\.xyz|172\.245\.|159\.195\.|193\.188\.|185\.217\.|tefggl@|r2-?d2|requests\.jsonl|feedback\.jsonl)' .
```

We sanitize. Public examples use `localhost`, `example.com`, RFC 5737 IPs.

### 4. Required files present

- `README.md` with verify-first section
- `LICENSE`
- `TRUST.md`
- `trust/manifest.json`
- `SECURITY.md`
- `CHANGELOG.md`
- `VERSION`
- `scripts/install.sh`
- `scripts/agent-preinstall-check.sh`
- `scripts/public-release-audit.sh` (this file's automation)

### 5. Trust profile passes

```bash
bash scripts/agent-preinstall-check.sh
```

The same check we ask users to run before installing. If it fails for us,
we can't ship.

### 6. Installer is non-destructive

```bash
grep -E '^[^#]*sudo' scripts/install.sh && exit 1
grep -rE 'curl.*\|.*bash|wget.*\|.*sh' scripts/ | grep -v "agent-preinstall-check.sh\|public-release-audit.sh" && exit 1
```

No `sudo`. No `curl | bash` patterns (we accept inspect-first only).

### 7. Version consistency

```bash
test "$(cat VERSION)" = "$(grep '## \[' CHANGELOG.md | head -1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')"
```

`VERSION` file matches the latest `CHANGELOG.md` entry. Tag will match too.

### 8. No private contact info

Personal email addresses and personal Telegram handles are blocked.
Only the documented public surfaces are allowed:
- `security@humanswith.ai`
- `conduct@humanswith.ai`
- `https://humanswith.ai`

## Automation

```bash
bash scripts/public-release-audit.sh
```

Exit code:
- `0` — all checks passed, safe to tag and push
- non-zero — at least one check failed, see stderr for details

## Manual checks

Some things automation can't do well:

- **Did we update the screenshot in the talk deck?** If a release changes
  the README in a visible way, refresh the GitHub screenshot used in any
  external materials.
- **Does `docs/integrations.md` still match real integration code?** Check
  links manually after big refactors.
- **Are roadmap dates honest?** Don't ship a version that promises May 2026
  if you know the team is on holiday until June.

These belong in the PR review, not in the audit script.

## Release procedure

```bash
# 1. Pre-flight
bash scripts/public-release-audit.sh

# 2. Update VERSION + CHANGELOG.md (move [Unreleased] entries to new section)

# 3. Commit, tag, push
git commit -am "Release vX.Y.Z"
git tag -s "vX.Y.Z" -m "vX.Y.Z — <one-line summary>"
git push origin main --follow-tags

# 4. Create GitHub Release with checksums
make release-artifacts        # builds tarball + computes sha256
gh release create "vX.Y.Z" \
  --title "vX.Y.Z — <summary>" \
  --notes-file release-notes.md \
  geo-audit-vX.Y.Z.tar.gz \
  geo-audit-vX.Y.Z.sha256

# 5. Post-flight
gh release view "vX.Y.Z" -R g-shevchenko/geo-audit
gh attestation verify geo-audit-vX.Y.Z.tar.gz -R g-shevchenko/geo-audit
```

Checksums and attestation are how outsiders know they got our bytes, not
someone else's.
