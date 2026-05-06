#!/usr/bin/env bash
# geo-audit installer — sets up a local Python venv with the geo-audit CLI.
# Does NOT require sudo. Does NOT touch global pip. Does NOT modify shell init.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> geo-audit installer"
echo "    install dir: $ROOT"
echo "    cache dir:   ~/.cache/geo-audit/"
echo

# 1. Verify trust profile first.
if [[ -f scripts/agent-preinstall-check.sh ]]; then
  echo "==> Running preinstall check..."
  bash scripts/agent-preinstall-check.sh || {
    echo "Preinstall check failed. Aborting." >&2
    exit 1
  }
  echo
fi

# 2. Python venv.
if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 not found. Install Python 3.10 or newer first." >&2
  exit 1
fi

echo "==> Creating Python venv (.venv/)"
python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
python3 -m pip install --quiet --upgrade pip

# 3. Install geo-audit + runtime deps.
echo "==> Installing geo-audit and dependencies"
pip install --quiet -e .

# 4. Cache dir.
mkdir -p "$HOME/.cache/geo-audit"

echo
echo "==> Installation complete."
echo
echo "==> Verifying:"
"$ROOT/.venv/bin/geo-audit" --version
echo

# 5. If no .env yet, copy from .env.example and run doctor.
if [[ ! -f .env && -f .env.example ]]; then
  cp .env.example .env
  echo "==> Created .env from .env.example (all keys empty)."
  echo
fi

echo "==> Next steps:"
echo "  1. Edit .env and paste the API keys you have. All are OPTIONAL — missing keys"
echo "     just degrade specific modules with a clear hint about what they would unlock."
echo "  2. Run: .venv/bin/geo-audit doctor"
echo "  3. Run: .venv/bin/geo-audit audit https://yoursite.com -o report/"
echo
echo "Optional: add to PATH"
echo "  echo 'export PATH=\"$ROOT/.venv/bin:\$PATH\"' >> ~/.zshrc"
echo
