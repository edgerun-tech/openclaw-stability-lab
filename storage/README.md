# EdgeRun Storage Integration

This folder contains integration helpers to mirror control-plane events into `edgerun-storage`.

## Event contract

Each event is emitted as JSON:

- `kind`: `job.created|job.assigned|job.started|job.result|pr.materialized|pr.build.result|pr.test.result`
- `source`: `openclaw-stability-lab`
- `jobId`
- `issue` / `pr`
- `profile`
- `workerAlias`
- `verdict` (for result events)
- `commit`
- `timestamp`

## Transport

Default submit path uses `edgerun-cli event submit` when available.
Fallback writes JSONL spool for later replay.
