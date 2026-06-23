#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export RESOLVE_PREP_DRY_RUN="${RESOLVE_PREP_DRY_RUN:-true}"

cd "$ROOT/backend"
python3 -m pip install -e ".[dev]" -q
python3 -m pytest -q

cd "$ROOT/frontend"
npm install --silent
npm run build

echo "Resolve Prep checks passed."
