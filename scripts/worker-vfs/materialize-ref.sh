#!/usr/bin/env bash
set -euo pipefail

# Materialize any ref/SHA/PR ref into isolated worktree from mirror.
# Usage: materialize-ref.sh <ref> [mirror-dir] [work-root]
REF="${1:-}"
MIRROR_DIR="${2:-/var/lib/openclaw-vfs/openclaw.git}"
WORK_ROOT="${3:-/var/lib/openclaw-vfs/worktrees}"
[[ -n "$REF" ]] || { echo "usage: $0 <ref> [mirror-dir] [work-root]"; exit 1; }

mkdir -p "$WORK_ROOT"
SAFE_REF=$(echo "$REF" | sed 's#[^a-zA-Z0-9._-]#_#g')
WT="$WORK_ROOT/$SAFE_REF"

# resolve ref against mirror
SHA=$(git --git-dir="$MIRROR_DIR" rev-parse "$REF" 2>/dev/null || true)
if [[ -z "$SHA" ]]; then
  echo "ref not found in mirror: $REF"
  exit 2
fi

# recreate worktree for deterministic state
if [ -d "$WT" ]; then
  git --git-dir="$MIRROR_DIR" worktree remove "$WT" --force || true
  rm -rf "$WT"
fi

git --git-dir="$MIRROR_DIR" worktree add --detach "$WT" "$SHA"

echo "$WT"
