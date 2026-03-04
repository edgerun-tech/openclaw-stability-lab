# PR Intelligence v1.1 (Operational)

This module extends Stability Lab from "run checks" to "understand PR context":

- Find other PRs touching the same code paths
- Suggest issue links with confidence scores
- Produce machine-readable output for dashboards and bot comments

## Scope (v1.1)

1. **Code-path overlap (PR ↔ PR)**
   - Input: changed file list from GitHub API
   - Output: top related PRs by overlap count and overlap %
   - Includes tiering (`high|medium|low`) by overlap strength

2. **Issue candidates (PR ↔ issue)**
   - Signals:
     - explicit references in PR body (`fixes #123` / `closes #123`)
     - token overlap (title/body/labels/files)
   - Output: top candidate issues with score, reason, tier, and policy action

3. **Categorization**
   - Heuristic categories: `bug`, `ci`, `flaky`, `performance`, `security`, `docs`, `infra`, `uncategorized`
   - Applied to both PRs and issues with confidence-ish scores

4. **Closure campaigns**
   - Group issues by top category
   - Generate draft campaign bundles with:
     - issue set
     - confidence/tier
     - suggested policy (`auto-draft`, `suggest`, `report`)
     - draft PR title/body template

5. **Artifact output**
   - `orchestrator/state/pr-intel.json`
   - optional board render: `docs/findings/pr-intel-board.md`

## Run

```bash
python orchestrator/pr_intel.py --repo openclaw/openclaw --out orchestrator/state/pr-intel.json
python scripts/render-pr-intel-board.py
```

## Output shape

```json
{
  "repo": "openclaw/openclaw",
  "openPulls": 0,
  "openIssues": 0,
  "relatedPulls": {"123": [{"number": 456, "overlapFiles": 7, "overlapPct": 0.41, "tier": "medium"}]},
  "issueCandidates": {"123": [{"number": 5799, "score": 10.0, "reason": "explicit-reference", "tier": "high", "policy": "auto-draft"}]},
  "categories": {"pulls": {}, "issues": {}},
  "campaigns": [{"campaignId": "bug-batch-4", "issues": [1, 2], "tier": "medium", "policy": "suggest"}],
  "tierPolicy": {"high": "auto-draft", "medium": "suggest", "low": "report"}
}
```

## Next (v1.1)

- Add symbol-level overlap (tree-sitter / LSP) instead of file-only
- Add recency/conflict weighting to PR overlap score
- Add confidence tiers:
  - High: auto-open draft fix PR allowed
  - Medium: suggest only
  - Low: report only
- Feed results into control-plane board + PR comment bot
