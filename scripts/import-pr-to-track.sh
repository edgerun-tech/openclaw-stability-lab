#!/usr/bin/env bash
set -euo pipefail

# Materialize PR branch into isolated workdir and enqueue job track.
# usage: import-pr-to-track.sh <pr-number> <openclaw-repo-path>
PR="${1:-}"
REPO="${2:-}"
[[ -n "$PR" && -n "$REPO" ]] || { echo "usage: $0 <pr-number> <openclaw-repo-path>"; exit 1; }

TRACK_DIR="tracks/pr-$PR"
mkdir -p "$TRACK_DIR"

cd "$REPO"
git fetch origin "pull/$PR/head:pr-$PR"
SHA=$(git rev-parse "pr-$PR")
WORKTREE="$(pwd)/.worktrees/pr-$PR"
mkdir -p .worktrees
if [ ! -d "$WORKTREE/.git" ]; then
  git worktree add "$WORKTREE" "pr-$PR"
fi

cat > "$TRACK_DIR/track.json" <<JSON
{
  "kind": "pr.materialized",
  "pr": $PR,
  "commit": "$SHA",
  "worktree": "$WORKTREE",
  "createdAt": "$(date -u +%FT%TZ)"
}
JSON

echo "materialized pr=$PR sha=$SHA worktree=$WORKTREE"
