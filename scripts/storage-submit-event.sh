#!/usr/bin/env bash
set -euo pipefail

# usage: storage-submit-event.sh <json-payload>
PAYLOAD="${1:-}"
[[ -n "$PAYLOAD" ]] || { echo "usage: $0 <json-payload>"; exit 1; }

if command -v edgerun-cli >/dev/null 2>&1; then
  # Requires valid edgerun-cli auth/profile in environment.
  edgerun-cli event submit --json "$PAYLOAD"
else
  mkdir -p storage/spool
  TS=$(date +%Y%m%d-%H%M%S)
  echo "$PAYLOAD" >> "storage/spool/events-$TS.jsonl"
fi
