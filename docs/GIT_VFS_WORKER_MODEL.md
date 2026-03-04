# Git-backed VFS Worker Model

This model keeps workers aligned to a single canonical source while allowing many parallel build/test tracks.

## Canonical source

- Mirror repo at `/var/lib/openclaw-vfs/openclaw.git`.
- Sync from `openclaw/openclaw` including PR refs.

## Materialization

- Any SHA/ref/PR head can be materialized into isolated worktree:
  - `/var/lib/openclaw-vfs/worktrees/<ref>`

## Build/test execution

- run `pnpm check`, `pnpm protocol:check`, `pnpm test` in isolated worktree
- emit result JSON for ingest/publishing

## Commands

```bash
scripts/worker-vfs/sync-openclaw-mirror.sh
scripts/worker-vfs/materialize-ref.sh refs/pull/34090/head
scripts/worker-vfs/build-track.sh /var/lib/openclaw-vfs/worktrees/refs_pull_34090_head /tmp/result.json
```

## Why this works

- single source of truth from upstream git
- deterministic per-track state via worktrees
- safe parallelization for many PR/commit checks
- easy to keep current (mirror fetch)
