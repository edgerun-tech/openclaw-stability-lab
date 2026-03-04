#!/usr/bin/env bash
set -euo pipefail

REPO_NAME=${1:-openclaw/openclaw}
REPO_PATH=${2:-/tmp/openclaw}

python3 orchestrator/code_analysis.py init-db
python3 orchestrator/code_analysis.py ingest-repo --repo-name "$REPO_NAME" --repo-path "$REPO_PATH"
python3 orchestrator/code_analysis.py analyze-dead --repo-name "$REPO_NAME"
python3 orchestrator/code_analysis.py analyze-dup --repo-name "$REPO_NAME" --repo-path "$REPO_PATH"
python3 orchestrator/code_analysis.py render-summary --repo-name "$REPO_NAME"

echo "Code analysis complete: docs/findings/code-analysis-summary.md"
