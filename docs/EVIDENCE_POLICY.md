# Evidence & Cross-Reference Policy

Goal: produce high-confidence, reviewable outputs for upstream issue triage.

## Required fields per result

- issue number
- tested repo + commit SHA
- profile used
- verdict (`reproducible` / `not-reproducible` / `needs-more-info` / `duplicate/superseded`)
- artifact paths (logs/report)
- run timestamps

## Confidence tiers

### Tier 0 (insufficient)
- Single run with no clear repro steps
- Missing commit SHA or logs

### Tier 1 (candidate)
- At least one clean harness run with artifacts
- Repro/no-repro signal is clear

### Tier 2 (actionable)
- Two+ independent runs or one run + targeted test reference
- Environment + SHA pinned
- Suggested upstream comment draft prepared

### Tier 3 (closure-ready)
- Stable non-repro across recent main commits OR confirmed fix commit
- No conflicting recent reports
- Human reviewer signs off

## Upstream comment policy

- Never auto-close from raw harness output.
- Post evidence comment first.
- Ask maintainers/reporters to confirm environment parity when needed.

## Cross-reference output

Use generated triage board/docs to map:
- issue -> profile -> latest verdict -> confidence tier -> artifact links
