# PR Tracks & Parallel Builds

This workflow allows many PR tracks to build/test concurrently.

## Materialize PR into isolated track

```bash
./scripts/import-pr-to-track.sh <pr-number> /path/to/openclaw
```

This creates:

- `tracks/pr-<N>/track.json`
- an isolated git worktree under `.worktrees/pr-<N>`

## Run checks in each track

Inside each worktree:

```bash
pnpm install --frozen-lockfile || pnpm install
pnpm check
pnpm protocol:check
pnpm test
```

## Publish result event to EdgeRun storage

```bash
./scripts/storage-submit-event.sh '{"kind":"pr.test.result","pr":123,"commit":"abc","verdict":"pass","timestamp":"2026-03-04T00:00:00Z"}'
```

## Build materialized views

```bash
python3 scripts/materialize-views.py
```

Output:

- `docs/findings/materialized-views.json`
