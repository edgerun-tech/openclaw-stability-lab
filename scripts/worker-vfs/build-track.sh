#!/usr/bin/env bash
set -euo pipefail

# Build/test a materialized worktree and emit structured result JSON.
# Usage: build-track.sh <worktree> <out-json>
WT="${1:-}"
OUT="${2:-}"
[[ -n "$WT" && -n "$OUT" ]] || { echo "usage: $0 <worktree> <out-json>"; exit 1; }

START=$(date -u +%FT%TZ)
SHA=$(git -C "$WT" rev-parse HEAD)

corepack enable >/dev/null 2>&1 || true
corepack prepare pnpm@10.23.0 --activate >/dev/null 2>&1 || true

set +e
(
  cd "$WT"
  CI=true pnpm install --frozen-lockfile || CI=true pnpm install
  pnpm check
  pnpm protocol:check
  pnpm test
)
RC=$?
set -e

END=$(date -u +%FT%TZ)
VERDICT="pass"
[[ $RC -ne 0 ]] && VERDICT="fail"

mkdir -p "$(dirname "$OUT")"
cat > "$OUT" <<JSON
{
  "commit": "$SHA",
  "startedAt": "$START",
  "endedAt": "$END",
  "verdict": "$VERDICT",
  "exitCode": $RC,
  "worktree": "$WT"
}
JSON

echo "result: $OUT"
exit $RC
