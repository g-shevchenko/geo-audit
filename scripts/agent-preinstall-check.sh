#!/usr/bin/env bash
# Preinstall trust check for geo-audit.
# Verifies the repo matches its declared trust profile in TRUST.md.
# Exit 0 if safe to install, non-zero otherwise.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> geo-audit preinstall check"
echo "    repo: $ROOT"
echo

errors=0

# 1. No curl-pipe-bash patterns in scripts (excluding audit scripts themselves)
echo "  [1/5] no curl-pipe-bash installers..."
if grep -rE 'curl.*\|.*bash|wget.*\|.*sh' scripts/ 2>/dev/null \
     | grep -vE "agent-preinstall-check\.sh|public-release-audit\.sh"; then
  echo "    FAIL: curl-pipe-bash detected"
  errors=$((errors + 1))
else
  echo "    ok"
fi

# 2. No hardcoded API keys
echo "  [2/5] no hardcoded credentials..."
if grep -rE 'sk-[a-zA-Z0-9]{20,}|ghp_[a-zA-Z0-9]{20,}|hf_[a-zA-Z0-9]{20,}|xoxb-' \
     --include="*.py" --include="*.js" --include="*.ts" --include="*.sh" \
     --include="*.md" --include="*.yaml" --include="*.json" 2>/dev/null \
     | grep -v "TRUST.md" | grep -v "OPENAI_API_KEY" | grep -v "agent-preinstall-check.sh"; then
  echo "    FAIL: possible hardcoded credential"
  errors=$((errors + 1))
else
  echo "    ok"
fi

# 3. No internal HWAI infra references
echo "  [3/5] no internal infra leaks..."
banned='hwai-ops\.xyz|humanswith-ai/(?!geo-audit|contentos-benchmark)|159\.195\.|193\.188\.|185\.217\.|tefggl@'
if grep -rEi "$banned" \
     --include="*.py" --include="*.js" --include="*.ts" --include="*.sh" \
     --include="*.md" --include="*.yaml" 2>/dev/null \
     | grep -v "agent-preinstall-check.sh"; then
  echo "    FAIL: internal HWAI reference detected"
  errors=$((errors + 1))
else
  echo "    ok"
fi

# 4. Required files exist
echo "  [4/5] required files..."
for f in README.md LICENSE TRUST.md scripts/install.sh; do
  if [[ ! -f "$f" ]]; then
    echo "    FAIL: missing $f"
    errors=$((errors + 1))
  fi
done
[[ $errors -eq 0 ]] && echo "    ok"

# 5. install.sh does not require sudo
echo "  [5/5] install.sh does not request sudo..."
if grep -E '^[^#]*sudo' scripts/install.sh 2>/dev/null; then
  echo "    FAIL: install.sh contains sudo"
  errors=$((errors + 1))
else
  echo "    ok"
fi

echo
if [[ $errors -eq 0 ]]; then
  echo "==> All checks passed. Safe to run scripts/install.sh."
  exit 0
else
  echo "==> $errors check(s) failed. DO NOT proceed without manual review."
  exit 1
fi
