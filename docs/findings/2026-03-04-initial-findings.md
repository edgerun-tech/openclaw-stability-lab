# Initial Findings — 2026-03-04

## Runs completed

- #34093 (`channel-delivery`) → harness verdict: `not-reproducible`
- #34052 (`gateway-lifecycle`) → harness verdict: `not-reproducible`
- #34090 (`protocol-transport`) → harness verdict: `not-reproducible` (2 runs)

## Important caveat

`not-reproducible` from harness means: current test profile did not fail on tested commit.
It does **not** automatically prove issue closed.

Before proposing closure upstream, require:

1. Issue-specific repro steps included in run notes
2. Tested commit SHA + environment details
3. At least two independent runs (or one run + targeted unit/e2e test)
4. Human reviewer approval for closure comment

## Recommended action lanes

### Lane A — Candidate for closure comment (needs human review)
- #34090 (proto transport check drift) — likely resolved by updated branch state + passing harness

### Lane B — Candidate for "needs reproduction details"
- #34093, #34052 (harness passes, but issue-specific repro scripts not yet encoded)

## Next step

Convert issue reports into reproducibility scripts under `profiles/` and re-run with explicit issue parameters.
