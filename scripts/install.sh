#!/usr/bin/env bash
# geo-audit installer — sets up local Python venv + Node modules.
# Does NOT require sudo. Does NOT touch global pip/npm.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> geo-audit installer (v0.1)"
echo "    install dir: $ROOT"
echo "    cache dir:   ~/.cache/geo-audit/"
echo

# 1. Verify trust profile first
if [[ -f scripts/agent-preinstall-check.sh ]]; then
  echo "==> Running preinstall check..."
  bash scripts/agent-preinstall-check.sh || {
    echo "Preinstall check failed. Aborting." >&2
    exit 1
  }
  echo
fi

# 2. Python venv
echo "==> Creating Python venv..."
python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt 2>/dev/null || echo "    (no requirements.txt yet — v0.1 in progress)"

# 3. Node modules
echo "==> Installing Node modules (Playwright, Lighthouse)..."
npm install --no-fund --no-audit --silent 2>/dev/null || echo "    (no package.json yet — v0.1 in progress)"

# 4. Cache dir
mkdir -p "$HOME/.cache/geo-audit"

# 5. Install CLI to .venv/bin/geo-audit
mkdir -p .venv/bin
cat > .venv/bin/geo-audit <<EOF
#!/usr/bin/env bash
exec "$ROOT/.venv/bin/python" -m geo_audit.cli "\$@"
EOF
chmod +x .venv/bin/geo-audit

echo
echo "==> Installation complete."
echo
echo "Next steps:"
echo "  1. source .venv/bin/activate"
echo "  2. geo-audit https://yoursite.com --depth full --output report.pdf"
echo
echo "Or add to your PATH:"
echo "  echo 'export PATH=\"$ROOT/.venv/bin:\$PATH\"' >> ~/.zshrc"
