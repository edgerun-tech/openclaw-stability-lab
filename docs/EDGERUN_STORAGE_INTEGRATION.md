# EdgeRun Storage Integration Plan

Goal: use `edgerun-storage` as durable event store for materialized views and PR build/test results.

## Why

- append-only evidence log
- queryable history for cross-referencing issues/PRs/results
- reproducible decision trail

## Event model

- `job.created`
- `job.assigned`
- `job.started`
- `job.result`
- `pr.materialized`
- `pr.build.result`
- `pr.test.result`

## Materialized views

1. `issue_latest_status`
2. `pr_latest_status`
3. `worker_capacity`
4. `failure_hotspots` (profile/path based)

## Integration steps

1. Add storage adapter process to mirror SQLite events into `edgerun-storage`.
2. Build read model updater to render dashboard from storage views.
3. Add retention/compaction policy for old raw logs.

## PR materialization pipeline

For PR jobs:

- fetch PR ref into isolated workspace
- run:
  - `pnpm check`
  - `pnpm protocol:check`
  - profile-targeted `vitest` suites
- publish artifact bundle + event records
