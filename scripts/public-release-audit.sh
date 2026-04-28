#!/usr/bin/env bash
# Public release audit for geo-audit.
# Run this BEFORE every git push, tag, or GitHub Release publish.
# Spec: PUBLIC_RELEASE_AUDIT.md

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

errors=0
fail() { echo "  FAIL: $1" >&2; errors=$((errors + 1)); }
pass() { echo "  ok"; }
section() { echo; echo "==> $1"; }

echo "geo-audit public release audit"
echo "  repo: $ROOT"
echo "  ref:  $(git rev-parse --short HEAD 2>/dev/null || echo 'no-git')"

# ── 1. Working tree is clean ─────────────────────────────────────────
section "[1/8] working tree is clean"
if [[ -n "$(git status --short 2>/dev/null)" ]]; then
  fail "uncommitted changes (run 'git status --short')"
else
  pass
fi
if ! git diff --check 2>/dev/null; then
  fail "whitespace errors (run 'git diff --check')"
fi

# ── 2. No secret-shaped strings ──────────────────────────────────────
section "[2/8] no secret-shaped strings"
SECRET_PATTERN='github_pat_|gh[pousr]_[a-zA-Z0-9]{20,}|x-access-token|authorization: bearer [^*]|api[_-]?key\s*[:=]\s*["'\'']?[a-zA-Z0-9]|secret\s*[:=]\s*["'\'']?[a-zA-Z0-9]|password\s*[:=]\s*["'\'']?[a-zA-Z0-9]|notion_token|sk-[a-zA-Z0-9]{20,}|hf_[a-zA-Z0-9]{20,}'
hits=$(grep -rEn "$SECRET_PATTERN" \
       --include='*.py' --include='*.js' --include='*.ts' --include='*.sh' \
       --include='*.md' --include='*.yaml' --include='*.yml' --include='*.json' \
       --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=.venv \
       . 2>/dev/null \
       | grep -vE 'PUBLIC_RELEASE_AUDIT|TRUST\.md|trust/manifest|public-release-audit\.sh|agent-preinstall-check\.sh|README\.md|SECURITY\.md|external-services\.md' \
       || true)
if [[ -n "$hits" ]]; then
  fail "secret-shaped string detected:"
  echo "$hits" | head -5 >&2
else
  pass
fi

# ── 3. No internal HWAI infrastructure references ────────────────────
section "[3/8] no internal HWAI infra references"
INTERNAL_PATTERN='greg-personal-claude|hwai-internal|claude/CREDENTIALS|hwai-ops\.xyz|172\.245\.|159\.195\.|193\.188\.|185\.217\.|tefggl@|r2-d2|r2_d2|requests\.jsonl|feedback\.jsonl'
hits=$(grep -rEn "$INTERNAL_PATTERN" \
       --include='*.py' --include='*.js' --include='*.ts' --include='*.sh' \
       --include='*.md' --include='*.yaml' --include='*.yml' --include='*.json' \
       --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=.venv \
       . 2>/dev/null \
       | grep -vE 'PUBLIC_RELEASE_AUDIT|TRUST\.md|trust/manifest|public-release-audit\.sh|agent-preinstall-check\.sh' \
       || true)
if [[ -n "$hits" ]]; then
  fail "internal infrastructure reference:"
  echo "$hits" | head -5 >&2
else
  pass
fi

# ── 4. Required files present ────────────────────────────────────────
section "[4/8] required files present"
required=(
  README.md LICENSE TRUST.md SECURITY.md CHANGELOG.md VERSION
  CONTRIBUTING.md CODE_OF_CONDUCT.md PUBLIC_RELEASE_AUDIT.md
  trust/manifest.json
  scripts/install.sh
  scripts/agent-preinstall-check.sh
  scripts/public-release-audit.sh
  .github/workflows/preinstall-check.yml
  .github/dependabot.yml
)
missing=0
for f in "${required[@]}"; do
  [[ -f "$f" ]] || { fail "missing $f"; missing=$((missing + 1)); }
done
[[ $missing -eq 0 ]] && pass

# ── 5. Trust profile passes ──────────────────────────────────────────
section "[5/8] trust profile (agent-preinstall-check)"
if bash scripts/agent-preinstall-check.sh >/dev/null 2>&1; then
  pass
else
  fail "agent-preinstall-check.sh exited non-zero"
fi

# ── 6. Installer is non-destructive ──────────────────────────────────
section "[6/8] installer non-destructive"
if grep -E '^[^#]*sudo' scripts/install.sh >/dev/null 2>&1; then
  fail "scripts/install.sh contains 'sudo'"
elif grep -rE 'curl[^|]*\|[^|]*bash|wget[^|]*\|[^|]*sh' scripts/ 2>/dev/null \
     | grep -vE 'agent-preinstall-check|public-release-audit' >/dev/null; then
  fail "curl-pipe-bash pattern in scripts/"
else
  pass
fi

# ── 7. Version consistency ───────────────────────────────────────────
section "[7/8] VERSION ↔ CHANGELOG.md"
if [[ -f VERSION ]] && [[ -f CHANGELOG.md ]]; then
  v=$(tr -d '[:space:]' < VERSION)
  cv=$(grep -oE '\[[0-9]+\.[0-9]+\.[0-9]+\]' CHANGELOG.md | head -1 | tr -d '[]')
  if [[ "$v" = "$cv" ]]; then
    pass
  else
    fail "VERSION=$v but latest CHANGELOG entry=$cv"
  fi
else
  fail "VERSION or CHANGELOG.md missing"
fi

# ── 8. No private contact info beyond documented public ones ────────
section "[8/8] no private contact info"
allowed_emails='security@humanswith.ai|conduct@humanswith.ai|noreply@'
hits=$(grep -rEn '[a-zA-Z0-9._-]+@[a-zA-Z0-9-]+\.(com|ai|io|me|org|net)' \
       --include='*.py' --include='*.js' --include='*.ts' --include='*.sh' \
       --include='*.md' --include='*.yaml' --include='*.yml' --include='*.json' \
       --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=.venv \
       . 2>/dev/null \
       | grep -vE "$allowed_emails" \
       | grep -vE 'example\.com|example\.org|user@|noreply@anthropic|public-release-audit\.sh' \
       || true)
if [[ -n "$hits" ]]; then
  fail "private email detected:"
  echo "$hits" | head -5 >&2
else
  pass
fi

echo
if [[ $errors -eq 0 ]]; then
  echo "==> All 8 checks passed. Safe to tag and push."
  exit 0
else
  echo "==> $errors check(s) failed. DO NOT publish without resolving."
  exit 1
fi
