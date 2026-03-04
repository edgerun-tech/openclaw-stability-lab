#!/usr/bin/env bash
set -euo pipefail

BASE=${BASE:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)}
CORE_REPO=${CORE_REPO:-/root/stability/openclaw}
WORKER_ID=${WORKER_ID:-$(hostname -s)}
WORKER_PROFILES=${WORKER_PROFILES:-channel-delivery,gateway-lifecycle,protocol-transport}
SLEEP_SECS=${SLEEP_SECS:-20}

cd "$BASE"
python3 orchestrator/control_plane.py init-db >/dev/null
python3 orchestrator/control_plane.py register-worker --worker "$WORKER_ID" --profiles "$WORKER_PROFILES" >/dev/null

while true; do
  python3 orchestrator/control_plane.py requeue-expired >/dev/null
  JOB_JSON=$(python3 orchestrator/control_plane.py claim-job --worker "$WORKER_ID" --lease-seconds 1800)
  JOB_ID=$(python3 -c 'import json,sys; obj=json.loads(sys.argv[1] if len(sys.argv)>1 and sys.argv[1] else "{}"); print(obj.get("id", ""))' "$JOB_JSON")

  if [[ -z "$JOB_ID" ]]; then
    sleep "$SLEEP_SECS"
    continue
  fi

  ISSUE=$(python3 -c 'import json,sys; obj=json.loads(sys.argv[1]); print(obj.get("issue_number", ""))' "$JOB_JSON")
  PROFILE=$(python3 -c 'import json,sys; obj=json.loads(sys.argv[1]); print(obj.get("profile", ""))' "$JOB_JSON")

  TS=$(date +%Y%m%d-%H%M%S)
  LOG_DIR="$BASE/reports/worker-${WORKER_ID}-${ISSUE}-${TS}"
  mkdir -p "$LOG_DIR"

  set +e
  ./scripts/run-profile.sh "$PROFILE" --issue "$ISSUE" --repo "$CORE_REPO" >"$LOG_DIR/worker.log" 2>&1
  RC=$?
  set -e

  COMMIT=$(git -C "$CORE_REPO" rev-parse HEAD)
  VERDICT="reproducible"
  [[ $RC -eq 0 ]] && VERDICT="not-reproducible"

  python3 orchestrator/control_plane.py submit-result \
    --job-id "$JOB_ID" \
    --worker "$WORKER_ID" \
    --verdict "$VERDICT" \
    --commit "$COMMIT" \
    --report "$LOG_DIR/report.json" \
    --logs "$LOG_DIR/worker.log" >/dev/null

  python3 orchestrator/control_plane.py render-board >/dev/null
  sleep 1
done
