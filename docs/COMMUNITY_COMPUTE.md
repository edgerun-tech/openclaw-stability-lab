# Community Compute Playbook

Goal: distribute issue verification workload across community machines/runners.

## Work scheduling

1. Curate issue batches in `manifests/issue-batches.json`
2. Generate queue: `python3 scripts/gen-work-queue.py`
3. Split into shards: `python3 scripts/split-work-queue.py --shards N --index I`

## Execution modes

- Local/self-hosted: run `scripts/run-profile.sh` against local OpenClaw checkout.
- GitHub Actions: trigger `community-sweep` workflow with shard inputs.

## Evidence policy

Each run must publish:
- report JSON
- logs
- tested OpenClaw commit SHA
- explicit verdict (`reproducible`/`not-reproducible`/etc)

## Governance

- No direct upstream auto-commenting by default.
- Human review before posting issue conclusions.
