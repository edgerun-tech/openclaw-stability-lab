#!/usr/bin/env python3
"""PR intelligence: overlap graph + issue candidates.

Usage:
  python orchestrator/pr_intel.py --repo openclaw/openclaw --out orchestrator/state/pr-intel.json

Requires: gh auth login
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

STOP = {
    "the", "and", "for", "with", "from", "that", "this", "into", "when", "where",
    "openclaw", "issue", "pull", "request", "fix", "bug", "regression", "mode", "core",
}


def run(cmd: str) -> str:
    return subprocess.check_output(cmd, shell=True, text=True)


def gh_json(path: str) -> object:
    return json.loads(run(f"gh api {path}"))


def tokenize(text: str) -> List[str]:
    toks = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", (text or "").lower())
    return [t for t in toks if t not in STOP]


@dataclass
class Pull:
    number: int
    title: str
    body: str
    labels: List[str]
    files: List[str]


@dataclass
class Issue:
    number: int
    title: str
    body: str
    labels: List[str]


def load_open_pulls(repo: str) -> List[Pull]:
    pulls = gh_json(f"repos/{repo}/pulls?state=open&per_page=100")
    out: List[Pull] = []
    for p in pulls:
        num = p["number"]
        files = gh_json(f"repos/{repo}/pulls/{num}/files?per_page=100")
        out.append(
            Pull(
                number=num,
                title=p.get("title", ""),
                body=p.get("body") or "",
                labels=[l["name"] for l in p.get("labels", [])],
                files=[f.get("filename", "") for f in files],
            )
        )
    return out


def load_open_issues(repo: str) -> List[Issue]:
    issues = gh_json(f"repos/{repo}/issues?state=open&per_page=100")
    out: List[Issue] = []
    for i in issues:
        if "pull_request" in i:
            continue
        out.append(
            Issue(
                number=i["number"],
                title=i.get("title", ""),
                body=i.get("body") or "",
                labels=[l["name"] for l in i.get("labels", [])],
            )
        )
    return out


def related_prs(pulls: List[Pull]) -> Dict[int, List[dict]]:
    file_index: Dict[str, List[int]] = defaultdict(list)
    for p in pulls:
        for f in set(p.files):
            file_index[f].append(p.number)

    by_num = {p.number: p for p in pulls}
    result: Dict[int, List[dict]] = {}
    for p in pulls:
        counts: Counter[int] = Counter()
        for f in set(p.files):
            for other in file_index.get(f, []):
                if other != p.number:
                    counts[other] += 1
        related = []
        for other, overlap in counts.most_common(10):
            denom = max(1, len(set(p.files)))
            related.append(
                {
                    "number": other,
                    "overlapFiles": overlap,
                    "overlapPct": round(overlap / denom, 3),
                    "title": by_num[other].title,
                }
            )
        result[p.number] = related
    return result


def issue_candidates(pulls: List[Pull], issues: List[Issue]) -> Dict[int, List[dict]]:
    issue_tokens = {
        i.number: Counter(tokenize(" ".join([i.title, i.body, " ".join(i.labels)])))
        for i in issues
    }

    result: Dict[int, List[dict]] = {}
    for p in pulls:
        text = " ".join([p.title, p.body, " ".join(p.labels), " ".join(p.files)])
        p_tokens = Counter(tokenize(text))

        explicit = {int(n) for n in re.findall(r"(?:fix(?:e[sd])?|close[sd]?|resolve[sd]?)\s+#(\d+)", p.body.lower())}

        scored: List[Tuple[int, float, str]] = []
        for i in issues:
            overlap = sum((p_tokens & issue_tokens[i.number]).values())
            score = overlap / max(1, sum(p_tokens.values()) ** 0.5)
            reason = "token-overlap"
            if i.number in explicit:
                score += 10
                reason = "explicit-reference"
            if score > 0:
                scored.append((i.number, score, reason))

        scored.sort(key=lambda x: x[1], reverse=True)
        result[p.number] = [
            {"number": n, "score": round(s, 3), "reason": r}
            for n, s, r in scored[:10]
        ]
    return result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="openclaw/openclaw")
    ap.add_argument("--out", default="orchestrator/state/pr-intel.json")
    args = ap.parse_args()

    pulls = load_open_pulls(args.repo)
    issues = load_open_issues(args.repo)

    payload = {
        "repo": args.repo,
        "openPulls": len(pulls),
        "openIssues": len(issues),
        "relatedPulls": related_prs(pulls),
        "issueCandidates": issue_candidates(pulls, issues),
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
