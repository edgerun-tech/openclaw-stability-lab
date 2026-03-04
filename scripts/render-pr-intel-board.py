#!/usr/bin/env python3
"""Render a human-friendly board from pr-intel artifact."""

import json
from pathlib import Path

IN_PATH = Path("orchestrator/state/pr-intel.json")
OUT_PATH = Path("docs/findings/pr-intel-board.md")


def main() -> None:
    data = json.loads(IN_PATH.read_text())

    lines = []
    lines.append("# PR Intelligence Board")
    lines.append("")
    lines.append(f"Repo: `{data['repo']}`")
    lines.append(f"Open PRs: **{data['openPulls']}** | Open issues: **{data['openIssues']}**")
    lines.append("")

    lines.append("## Top closure campaigns")
    lines.append("")
    campaigns = data.get("campaigns", [])[:10]
    if not campaigns:
        lines.append("No campaigns generated.")
    for c in campaigns:
        issues = ", ".join(f"#{n}" for n in c.get("issues", []))
        lines.append(f"- **{c['campaignId']}** ({c['category']}) — tier `{c['tier']}` / policy `{c['policy']}` / confidence `{c['confidence']}`")
        lines.append(f"  - Issues: {issues}")
        lines.append(f"  - Draft title: `{c['draftPrTitle']}`")

    lines.append("")
    lines.append("## PR overlap hot spots")
    lines.append("")
    rel = data.get("relatedPulls", {})
    hot = []
    for pr_num, neighbors in rel.items():
        if not neighbors:
            continue
        top = neighbors[0]
        hot.append((top.get("overlapFiles", 0), int(pr_num), top))
    hot.sort(reverse=True)

    if not hot:
        lines.append("No high-overlap PR pairs found.")
    else:
        for _, pr_num, top in hot[:15]:
            lines.append(
                f"- PR #{pr_num} ↔ PR #{top['number']} — {top['overlapFiles']} shared files ({top['overlapPct']*100:.1f}%), tier `{top.get('tier','low')}`"
            )

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text("\n".join(lines) + "\n")
    print(f"wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
