#!/usr/bin/env python3
"""PR intelligence: overlap graph + issue candidates + closure campaigns.

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
from typing import Dict, List, Tuple

STOP = {
    "the", "and", "for", "with", "from", "that", "this", "into", "when", "where",
    "openclaw", "issue", "pull", "request", "fix", "bug", "regression", "mode", "core",
}

CATEGORY_KEYWORDS = {
    "bug": ["bug", "broken", "error", "fails", "crash", "regression", "panic"],
    "ci": ["ci", "workflow", "github actions", "build", "runner", "pipeline"],
    "flaky": ["flaky", "intermittent", "sometimes", "nondeterministic", "randomly"],
    "performance": ["slow", "latency", "perf", "performance", "throughput", "optimize"],
    "security": ["security", "secret", "token", "auth", "permission", "vulnerability"],
    "docs": ["docs", "documentation", "readme", "typo", "guide"],
    "infra": ["gateway", "transport", "websocket", "docker", "k8s", "launchctl"],
}


def run(cmd: str) -> str:
    return subprocess.check_output(cmd, shell=True, text=True)


def gh_json(path: str) -> object:
    return json.loads(run(f"gh api {path}"))


def tokenize(text: str) -> List[str]:
    toks = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}", (text or "").lower())
    return [t for t in toks if t not in STOP]


def classify_categories(*parts: str) -> List[dict]:
    text = " ".join(parts).lower()
    scored = []
    for cat, kws in CATEGORY_KEYWORDS.items():
        hits = sum(1 for k in kws if k in text)
        if hits:
            scored.append({"category": cat, "score": round(min(1.0, hits / 3), 3), "hits": hits})
    if not scored:
        scored = [{"category": "uncategorized", "score": 0.2, "hits": 0}]
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored


def tier(score: float) -> str:
    if score >= 2.5:
        return "high"
    if score >= 1.2:
        return "medium"
    return "low"


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
            overlap_pct = overlap / denom
            related.append(
                {
                    "number": other,
                    "overlapFiles": overlap,
                    "overlapPct": round(overlap_pct, 3),
                    "title": by_num[other].title,
                    "tier": tier(overlap_pct * 3),
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
            {
                "number": n,
                "score": round(s, 3),
                "reason": r,
                "tier": tier(s),
                "policy": "auto-draft" if tier(s) == "high" else ("suggest" if tier(s) == "medium" else "report"),
            }
            for n, s, r in scored[:10]
        ]
    return result


def issue_campaigns(issues: List[Issue], limit: int = 8) -> List[dict]:
    groups: Dict[str, List[Issue]] = defaultdict(list)
    for i in issues:
        cats = classify_categories(i.title, i.body, " ".join(i.labels))
        top = cats[0]["category"]
        groups[top].append(i)

    campaigns = []
    for cat, bucket in groups.items():
        if cat == "uncategorized":
            continue
        bucket_sorted = sorted(bucket, key=lambda x: len(x.body or ""), reverse=True)
        issue_nums = [i.number for i in bucket_sorted[:limit]]
        confidence = round(min(1.0, len(issue_nums) / 6), 3)
        campaigns.append(
            {
                "campaignId": f"{cat}-batch-{len(issue_nums)}",
                "category": cat,
                "issues": issue_nums,
                "tier": "high" if confidence >= 0.8 else ("medium" if confidence >= 0.45 else "low"),
                "confidence": confidence,
                "policy": "auto-draft" if confidence >= 0.8 else ("suggest" if confidence >= 0.45 else "report"),
                "draftPrTitle": f"fix({cat}): close grouped issue batch ({len(issue_nums)} issues)",
                "draftPrBody": (
                    "Automated campaign draft from Stability Lab.\\n\\n"
                    "Proposed issue set: " + ", ".join(f"#{n}" for n in issue_nums) + "\\n\\n"
                    "This PR is generated as a draft for maintainer review."
                ),
            }
        )
    campaigns.sort(key=lambda c: (c["confidence"], len(c["issues"])), reverse=True)
    return campaigns


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="openclaw/openclaw")
    ap.add_argument("--out", default="orchestrator/state/pr-intel.json")
    args = ap.parse_args()

    pulls = load_open_pulls(args.repo)
    issues = load_open_issues(args.repo)

    pr_categories = {
        p.number: classify_categories(p.title, p.body, " ".join(p.labels), " ".join(p.files))
        for p in pulls
    }
    issue_categories = {
        i.number: classify_categories(i.title, i.body, " ".join(i.labels))
        for i in issues
    }

    payload = {
        "repo": args.repo,
        "openPulls": len(pulls),
        "openIssues": len(issues),
        "relatedPulls": related_prs(pulls),
        "issueCandidates": issue_candidates(pulls, issues),
        "categories": {
            "pulls": pr_categories,
            "issues": issue_categories,
        },
        "campaigns": issue_campaigns(issues),
        "tierPolicy": {
            "high": "auto-draft",
            "medium": "suggest",
            "low": "report",
        },
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
