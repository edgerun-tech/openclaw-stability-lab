#!/usr/bin/env bash
set -euo pipefail
PROFILE="${1:-}"; shift || true
ISSUE=""
REPO=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --issue) ISSUE="$2"; shift 2;;
    --repo) REPO="$2"; shift 2;;
    *) echo "unknown arg: $1"; exit 1;;
  esac
done
[[ -n "$PROFILE" && -n "$ISSUE" && -n "$REPO" ]] || { echo "usage: run-profile.sh <profile> --issue <id> --repo <openclaw-path>"; exit 1; }

YML="profiles/${PROFILE}.yml"
[[ -f "$YML" ]] || { echo "missing profile $YML"; exit 1; }
OUT="reports/issue-${ISSUE}-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$OUT"
START=$(date -u +%FT%TZ)
COMMIT=$(git -C "$REPO" rev-parse HEAD)

python3 - <<PY > "$OUT/commands.txt"
import yaml
cfg=yaml.safe_load(open('$YML'))
for c in cfg.get('commands',[]):
    print(c)
PY

pushd "$REPO" >/dev/null
status=0
idx=0
while IFS= read -r cmd; do
  idx=$((idx+1))
  bash -lc "$cmd" > "$OLDPWD/$OUT/cmd-${idx}.log" 2>&1 || status=1
done < "$OLDPWD/$OUT/commands.txt"
popd >/dev/null
END=$(date -u +%FT%TZ)
VERDICT=$([ $status -eq 0 ] && echo not-reproducible || echo reproducible)

cat > "$OUT/report.json" <<JSON
{"issue": $ISSUE, "repo": "openclaw/openclaw", "commit": "$COMMIT", "profile": "$PROFILE", "verdict": "$VERDICT", "startedAt": "$START", "endedAt": "$END", "artifacts": ["$OUT"]}
JSON

echo "wrote $OUT/report.json"
