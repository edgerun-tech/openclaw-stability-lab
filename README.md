# openclaw-stability-lab

Community compute harness for validating OpenClaw issues and regressions without burdening core CI.

## Goals

- Reproduce (or falsify) issue reports with evidence
- Run heavy checks on contributor infrastructure
- Publish standardized artifacts maintainers can trust

## How it works

1. Select an issue (or batch)
2. Run harness profile (`channel-delivery`, `gateway-lifecycle`, `protocol-transport`)
3. Produce machine-readable report + logs
4. Share report URL/artifacts in issue comments

## Safety

- No upstream secrets required
- Runs in contributor-controlled environment
- Uses pinned harness commands and report schema

See `CONTRIBUTING.md` and `profiles/`.
