#!/usr/bin/env bash
set -euo pipefail

BASE=${BASE:-$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)}
CORE_REPO=${CORE_REPO:-/root/stability/openclaw}
WORKER_ID=${WORKER_ID:-$(hostname -s)}
WORKER_PROFILES=${WORKER_PROFILES:-channel-delivery,gateway-lifecycle,protocol-transport}
SLEEP_SECS=${SLEEP_SECS:-20}

CONTROL_PLANE_URL=${CONTROL_PLANE_URL:-}

post_json() {
  local path="$1"
  local payload="$2"
  if [[ -n "$CONTROL_PLANE_URL" ]]; then
    curl -sS -X POST "$CONTROL_PLANE_URL$path" -H 'content-type: application/json' -d "$payload"
  else
    case "$path" in
      /register-worker)
        python3 orchestrator/control_plane.py register-worker --worker "$WORKER_ID" --profiles "$WORKER_PROFILES" >/dev/null
        echo '{"ok":true}'
        ;;
      /claim-job)
        python3 orchestrator/control_plane.py claim-job --worker "$WORKER_ID" --lease-seconds 1800 | python3 -c 'import json,sys; print(json.dumps({"job":json.load(sys.stdin)}))'
        ;;
      /submit-result)
        # parse payload fields and call local CLI
        python3 - "$payload" <<'PY'
import json,sys,subprocess
p=json.loads(sys.argv[1])
subprocess.check_call([
  'python3','orchestrator/control_plane.py','submit-result',
  '--job-id',p['jobId'],'--worker',p['worker'],'--verdict',p['verdict'],
  '--commit',p.get('commit',''),'--report',p.get('report',''),'--logs',p.get('logs','')
])
print('{"ok":true}')
PY
        ;;
      /requeue-expired)
        python3 orchestrator/control_plane.py requeue-expired >/dev/null
        echo '{"ok":true}'
        ;;
      /render-board)
        python3 orchestrator/control_plane.py render-board >/dev/null
        echo '{"ok":true}'
        ;;
      *)
        echo '{}' ;;
    esac
  fi
}

cd "$BASE"
python3 orchestrator/control_plane.py init-db >/dev/null
post_json /register-worker "{\"worker\":\"$WORKER_ID\",\"profiles\":[\"${WORKER_PROFILES//,/\",\"}\"]}" >/dev/null

while true; do
  post_json /requeue-expired '{}' >/dev/null
  CLAIM=$(post_json /claim-job "{\"worker\":\"$WORKER_ID\",\"leaseSeconds\":1800}")
  JOB_JSON=$(python3 -c 'import json,sys; print(json.dumps(json.loads(sys.argv[1]).get("job",{})))' "$CLAIM")
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

  post_json /submit-result "{\"jobId\":\"$JOB_ID\",\"worker\":\"$WORKER_ID\",\"verdict\":\"$VERDICT\",\"commit\":\"$COMMIT\",\"report\":\"$LOG_DIR/report.json\",\"logs\":\"$LOG_DIR/worker.log\"}" >/dev/null

  post_json /render-board '{}' >/dev/null
  sleep 1
done
