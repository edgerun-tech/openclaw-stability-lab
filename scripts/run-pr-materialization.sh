#!/usr/bin/env bash
set -euo pipefail

# Usage: run-pr-materialization.sh <pr-number> <repo-path>
PR="${1:-}"
REPO="${2:-}"
[[ -n "$PR" && -n "$REPO" ]] || { echo "usage: $0 <pr-number> <repo-path>"; exit 1; }

cd "$REPO"
git fetch origin "pull/$PR/head:pr-$PR"
git checkout "pr-$PR"

pnpm install --frozen-lockfile || pnpm install
pnpm check
pnpm protocol:check
pnpm test

echo "PR $PR materialization checks complete"
