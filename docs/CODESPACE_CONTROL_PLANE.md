# Codespace Control Plane Setup

Run the orchestrator in GitHub Codespaces with persistent storage.

## 1) Bootstrap

```bash
python3 orchestrator/control_plane.py init-db
python3 orchestrator/control_plane.py ingest-openclaw --limit 500
python3 orchestrator/control_plane.py render-board
```

## 2) Register worker process

```bash
WORKER_ID=codespace-1 \
WORKER_PROFILES=channel-delivery,gateway-lifecycle,protocol-transport \
CORE_REPO=/workspaces/openclaw \
./scripts/worker-loop.sh
```

## 3) Run scheduler tick periodically

```bash
python3 orchestrator/control_plane.py requeue-expired
python3 orchestrator/control_plane.py render-board
```

## 4) Persist and publish results

Commit these files back to repo:

- `orchestrator/state/controlplane.db`
- `docs/findings/control-plane-board.md`
- `reports/*` (optional, if not ignored)

## Notes

- The default architecture is single-control-plane SQLite.
- Worker leases are time-bound; expired jobs are re-queued.
- Result ingestion is done via `submit-result` from worker loop.
