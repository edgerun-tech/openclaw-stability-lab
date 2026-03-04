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

Control plane docs:

- `orchestrator/ARCHITECTURE.md`
- `docs/CODESPACE_CONTROL_PLANE.md`
- `docs/WORKER_ONBOARDING.md`
- `docs/EVIDENCE_POLICY.md`
- `docs/PR_INTELLIGENCE_V1.md`
- `docs/findings/issue-crossref.md`

Live artifacts (committed by control-plane tick):

- `docs/findings/control-plane-board.md`
- `docs/findings/issue-crossref.md`
