# PR Build + Diff Intelligence Pipeline

This pipeline makes PRs actionable by surfacing:

- changed files + diff stats
- language/function references inferred from patches
- optional full checks per PR branch (`lint`, `typecheck`, `build`, `test`)
- TypeScript/eslint error/warning signal extraction from outputs

## Diff-only mode (fast, no checkout)

```bash
python orchestrator/pr_build_validate.py \
  --repo openclaw/openclaw \
  --limit 8 \
  --out orchestrator/state/pr-build-report.json
```

## Full build mode (requires local repo checkout)

```bash
python orchestrator/pr_build_validate.py \
  --repo openclaw/openclaw \
  --limit 3 \
  --repo-path /path/to/openclaw \
  --out orchestrator/state/pr-build-report.json
```

## Outputs

- `orchestrator/state/pr-build-report.json`
- `docs/findings/pr-build-report.md`

## Notes

- In full mode, PR branches are checked out as `pr-<number>` and scripts are run if present.
- Script coverage currently targets package scripts: `lint`, `typecheck`, `build`, `test`.
- Error/warning extraction is heuristic and intended for triage, not final verdicts.
