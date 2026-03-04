# Code Analysis Pipeline (Phase 1)

This pipeline adds deep code intelligence to Stability Lab:

- codebase indexing (files + symbols)
- dead-code candidates
- duplicate-code candidates
- summary artifact for dashboard consumption

## Commands

```bash
python orchestrator/code_analysis.py init-db
python orchestrator/code_analysis.py ingest-repo --repo-name openclaw/openclaw --repo-path /path/to/openclaw
python orchestrator/code_analysis.py analyze-dead --repo-name openclaw/openclaw
python orchestrator/code_analysis.py analyze-dup --repo-name openclaw/openclaw --repo-path /path/to/openclaw
python orchestrator/code_analysis.py render-summary --repo-name openclaw/openclaw
```

## Outputs

- DB: `orchestrator/state/analysis.db`
- JSON summary: `orchestrator/state/code-analysis.json`
- Markdown summary: `docs/findings/code-analysis-summary.md`

## Phase 2 (next)

- add TypeScript symbol graph (tree-sitter/ts-morph)
- call graph + execution graph from test traces
- PR impact radius per changed symbol
- issue-fix likelihood scoring with explainable signals
- automated draft PR generation for high-confidence batches
