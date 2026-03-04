# Benchmarks

This document tracks control-plane performance baselines.

## API micro-benchmark harness

Run:

```bash
python3 scripts/benchmark-control-plane.py
```

Endpoints measured:

- `GET /health`
- `POST /requeue-expired`
- `POST /claim-job`
- `GET /snapshot`

Metrics:

- average latency (ms)
- p95 latency (ms)
- min/max latency

## Worker throughput benchmark (manual)

Measure completed jobs/hour from snapshot delta:

1. record `done` count at `t0`
2. record `done` count at `t1`
3. throughput = `(done_t1 - done_t0) / hours`

## Future benchmark expansion

- per-profile job runtime distribution
- queue drain rate under N workers
- SQLite write contention under concurrent workers
