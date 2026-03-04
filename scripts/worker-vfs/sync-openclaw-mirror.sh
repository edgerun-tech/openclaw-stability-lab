#!/usr/bin/env bash
set -euo pipefail

# Canonical source mirror for worker node
# Usage: sync-openclaw-mirror.sh [mirror-dir]
MIRROR_DIR="${1:-/var/lib/openclaw-vfs/openclaw.git}"
REMOTE_URL="${OPENCLAW_REMOTE_URL:-https://github.com/openclaw/openclaw.git}"

mkdir -p "$(dirname "$MIRROR_DIR")"
if [ ! -d "$MIRROR_DIR" ]; then
  git clone --mirror "$REMOTE_URL" "$MIRROR_DIR"
fi

git --git-dir="$MIRROR_DIR" remote set-url origin "$REMOTE_URL"
git --git-dir="$MIRROR_DIR" fetch --prune origin "+refs/heads/*:refs/heads/*" "+refs/tags/*:refs/tags/*" "+refs/pull/*/head:refs/pull/*/head" || \
  git --git-dir="$MIRROR_DIR" fetch --prune origin

echo "mirror synced: $MIRROR_DIR"
