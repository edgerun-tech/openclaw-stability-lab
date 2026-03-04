#!/usr/bin/env python3
import json
import statistics
import time
import urllib.request

BASE = 'https://openclaw.edgerun.tech/api'
N = 50


def post(path, payload):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(payload).encode('utf8'),
        headers={'content-type':'application/json'},
        method='POST',
    )
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=20) as r:
        _ = r.read()
    return (time.perf_counter() - t0) * 1000.0


def get(path):
    t0 = time.perf_counter()
    with urllib.request.urlopen(BASE + path, timeout=20) as r:
        _ = r.read()
    return (time.perf_counter() - t0) * 1000.0


def p95(vals):
    vals = sorted(vals)
    if not vals:
        return 0.0
    idx = int(round(0.95 * (len(vals)-1)))
    return vals[idx]


def run(name, fn):
    vals = [fn() for _ in range(N)]
    return {
        'name': name,
        'n': N,
        'avg_ms': round(statistics.mean(vals), 2),
        'p95_ms': round(p95(vals), 2),
        'max_ms': round(max(vals), 2),
        'min_ms': round(min(vals), 2),
    }


def main():
    rows = []
    rows.append(run('GET /health', lambda: get('/health')))
    rows.append(run('POST /requeue-expired', lambda: post('/requeue-expired', {})))
    rows.append(run('POST /claim-job (empty worker)', lambda: post('/claim-job', {'worker': 'bench-worker', 'leaseSeconds': 60})))
    rows.append(run('GET /snapshot', lambda: get('/snapshot')))

    print(json.dumps(rows, indent=2))


if __name__ == '__main__':
    main()
